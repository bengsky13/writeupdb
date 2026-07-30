from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.security import require_admin_session
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Attachment, Chunk, ExtractionResult, IngestionJob, SearchQueryLog, Section, Writeup, WriteupRevision
from app.schemas.writeups import IngestionResponse, WriteupCreate
from app.workers.queue import get_queue
from app.workers.tasks import process_ingestion_job

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin_session)])


def _legacy_attachment_paths(external_id: str) -> list[Path]:
    attachment_dir = get_settings().attachment_dir
    return [path for path in attachment_dir.glob(f"{external_id}-*") if path.is_file()]


def dispatch_job(job_id: str) -> None:
    queue = get_queue()
    if queue is None:
        process_ingestion_job(job_id)
    else:
        queue.enqueue("app.workers.tasks.process_ingestion_job", job_id)


def _language_from_filename(filename: str) -> str | None:
    suffix = Path(filename).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".php": "php",
        ".c": "c",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".kt": "kotlin",
        ".swift": "swift",
        ".sh": "shell",
        ".sql": "sql",
    }.get(suffix)


async def _stage_upload_payload(
    payload: dict,
    job_id: str,
    content_file: UploadFile | None,
    source_files: list[UploadFile],
) -> dict:
    settings = get_settings()
    staging_dir = settings.data_dir / "staging" / job_id
    staging_dir.mkdir(parents=True, exist_ok=True)

    staged_attachment_paths: dict[str, str] = {}
    attachments = list(payload.get("attachments", []))

    if content_file is not None:
        payload["content"] = (await content_file.read()).decode()

    for index, upload in enumerate(source_files, start=1):
        blob = await upload.read()
        attachment_id = f"source-{index}"
        filename = upload.filename or f"{attachment_id}.txt"
        target = staging_dir / f"{attachment_id}{Path(filename).suffix}"
        target.write_bytes(blob)
        staged_attachment_paths[attachment_id] = str(target)
        attachments.append(
            {
                "attachment_id": attachment_id,
                "filename": filename,
                "relative_path": f"attachments/{filename}",
                "sha256": hashlib.sha256(blob).hexdigest(),
                "type": "source",
                "language": _language_from_filename(filename),
                "mime_type": upload.content_type or mimetypes.guess_type(filename)[0] or "text/plain",
            }
        )

    payload["attachments"] = attachments
    if staged_attachment_paths:
        payload["_attachment_paths"] = staged_attachment_paths
    return payload


@router.get("/jobs")
def list_jobs(
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    limit = max(1, min(limit, 20))
    total = db.scalar(select(func.count()).select_from(IngestionJob)) or 0
    offset = (max(page, 1) - 1) * limit
    jobs = db.scalars(select(IngestionJob).order_by(IngestionJob.created_at.desc()).offset(offset).limit(limit)).all()
    return {
        "items": [{"id": job.id, "status": job.status, "external_id": job.external_id} for job in jobs],
        "page": max(page, 1),
        "page_size": limit,
        "total": total,
        "total_pages": max((total + limit - 1) // limit, 1),
    }


@router.delete("/jobs")
def delete_all_jobs(db: Session = Depends(get_db)) -> dict:
    deleted = db.query(IngestionJob).count()
    db.execute(delete(IngestionJob))
    db.commit()
    return {"status": "deleted", "deleted_count": deleted}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    writeup = None
    if job.external_id:
        writeup = db.scalar(select(Writeup).where(Writeup.external_id == job.external_id))
    return {
        "id": job.id,
        "status": job.status,
        "external_id": job.external_id,
        "writeup_id": writeup.id if writeup else None,
        "payload": job.payload_json,
        "error": job.error_message,
    }


@router.delete("/jobs/{job_id}")
def delete_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    db.delete(job)
    db.commit()
    return {"status": "deleted", "job_id": job_id}


@router.post("/ingest/raw", response_model=IngestionResponse)
def ingest_raw(writeup: WriteupCreate, db: Session = Depends(get_db)) -> IngestionResponse:
    job = IngestionJob(
        external_id=writeup.external_id,
        source_type="admin",
        status="queued",
        payload_json=writeup.model_dump(mode="json"),
    )
    db.add(job)
    db.commit()
    dispatch_job(job.id)
    return IngestionResponse(job_id=job.id, status="queued")


@router.post("/ingest/upload")
async def ingest_upload(
    metadata_json: str = Form(...),
    content_file: UploadFile | None = File(default=None),
    source_files: list[UploadFile] = File(default_factory=list),
    db: Session = Depends(get_db),
) -> IngestionResponse:
    payload = WriteupCreate.model_validate_json(metadata_json).model_dump(mode="json")
    job = IngestionJob(
        external_id=payload["external_id"],
        source_type="admin_upload",
        status="queued",
        payload_json={},
    )
    db.add(job)
    db.flush()
    payload = await _stage_upload_payload(payload, job.id, content_file, source_files)
    job.payload_json = payload
    db.commit()
    dispatch_job(job.id)
    return IngestionResponse(job_id=job.id, status="queued")


@router.get("/analytics/searches")
def search_analytics(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(SearchQueryLog).order_by(SearchQueryLog.created_at.desc()).limit(50)).all()
    return [{"query": row.query, "latency_ms": row.latency_ms, "result_count": row.result_count} for row in rows]


@router.get("/writeups")
def list_writeups(
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    limit = max(1, min(limit, 20))
    total = db.scalar(select(func.count()).select_from(Writeup)) or 0
    offset = (max(page, 1) - 1) * limit
    writeups = db.scalars(select(Writeup).order_by(Writeup.created_at.desc()).offset(offset).limit(limit)).all()
    return {
        "items": [
            {
                "id": writeup.id,
                "title": writeup.title,
                "external_id": writeup.external_id,
                "event": writeup.event,
                "challenge": writeup.challenge,
                "category": writeup.category,
                "team": writeup.team,
            }
            for writeup in writeups
        ],
        "page": max(page, 1),
        "page_size": limit,
        "total": total,
        "total_pages": max((total + limit - 1) // limit, 1),
    }


@router.get("/writeups/{writeup_id}")
def get_writeup(writeup_id: int, db: Session = Depends(get_db)) -> dict:
    writeup = db.scalar(select(Writeup).where(Writeup.id == writeup_id))
    if writeup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="writeup not found")
    revision = db.scalar(select(WriteupRevision).where(WriteupRevision.id == writeup.active_revision_id))
    return {
        "id": writeup.id,
        "external_id": writeup.external_id,
        "title": writeup.title,
        "event": writeup.event,
        "event_year": writeup.event_year,
        "challenge": writeup.challenge,
        "category": writeup.category,
        "difficulty": writeup.difficulty,
        "team": writeup.team,
        "language": writeup.language,
        "published_at": writeup.published_at.isoformat() if writeup.published_at else None,
        "source_reference": writeup.source_reference,
        "content_format": revision.content_format if revision else "markdown",
        "content": revision.raw_content if revision else "",
        "metadata": revision.metadata_json if revision else {},
    }


@router.patch("/writeups/{writeup_id}", response_model=IngestionResponse)
def update_writeup(writeup_id: int, writeup_update: WriteupCreate, db: Session = Depends(get_db)) -> IngestionResponse:
    writeup = db.scalar(select(Writeup).where(Writeup.id == writeup_id))
    if writeup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="writeup not found")
    if writeup_update.external_id != writeup.external_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="external_id cannot be changed during edit",
        )
    job = IngestionJob(
        external_id=writeup.external_id,
        source_type="admin_edit",
        status="queued",
        payload_json=writeup_update.model_dump(mode="json"),
    )
    db.add(job)
    db.commit()
    dispatch_job(job.id)
    return IngestionResponse(job_id=job.id, status="queued")


@router.patch("/writeups/{writeup_id}/upload", response_model=IngestionResponse)
async def update_writeup_upload(
    writeup_id: int,
    metadata_json: str = Form(...),
    content_file: UploadFile | None = File(default=None),
    source_files: list[UploadFile] = File(default_factory=list),
    db: Session = Depends(get_db),
) -> IngestionResponse:
    writeup = db.scalar(select(Writeup).where(Writeup.id == writeup_id))
    if writeup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="writeup not found")
    payload = WriteupCreate.model_validate_json(metadata_json).model_dump(mode="json")
    if payload["external_id"] != writeup.external_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="external_id cannot be changed during edit",
        )
    job = IngestionJob(
        external_id=writeup.external_id,
        source_type="admin_edit_upload",
        status="queued",
        payload_json={},
    )
    db.add(job)
    db.flush()
    payload = await _stage_upload_payload(payload, job.id, content_file, source_files)
    job.payload_json = payload
    db.commit()
    dispatch_job(job.id)
    return IngestionResponse(job_id=job.id, status="queued")


@router.delete("/writeups/{writeup_id}")
def delete_writeup(writeup_id: int, db: Session = Depends(get_db)) -> dict:
    writeup = db.scalar(select(Writeup).where(Writeup.id == writeup_id))
    if writeup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="writeup not found")

    attachment_paths = [Path(attachment.storage_path) for attachment in writeup.attachments]
    attachment_paths.extend(_legacy_attachment_paths(writeup.external_id))
    revision_ids = db.scalars(select(WriteupRevision.id).where(WriteupRevision.writeup_id == writeup.id)).all()
    writeup.active_revision_id = None
    db.flush()

    db.execute(delete(ExtractionResult).where(ExtractionResult.writeup_id == writeup.id))
    db.execute(delete(Attachment).where(Attachment.writeup_id == writeup.id))
    db.execute(delete(Chunk).where(Chunk.writeup_id == writeup.id))
    if revision_ids:
        db.execute(delete(Section).where(Section.revision_id.in_(revision_ids)))
        db.execute(delete(WriteupRevision).where(WriteupRevision.id.in_(revision_ids)))
    db.execute(delete(IngestionJob).where(IngestionJob.external_id == writeup.external_id))
    db.delete(writeup)
    db.commit()

    for path in {path for path in attachment_paths}:
        try:
            os.remove(path)
        except FileNotFoundError:
            continue

    return {"status": "deleted", "writeup_id": writeup_id}
