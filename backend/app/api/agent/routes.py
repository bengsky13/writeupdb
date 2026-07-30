from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import require_agent_token
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Attachment, IngestionJob, Writeup
from app.schemas.writeups import IngestionResponse, WriteupCreate
from app.workers.queue import get_queue
from app.workers.tasks import process_ingestion_job

router = APIRouter(prefix="/api/agent", tags=["agent"])


def payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _safe_attachment_filename(filename: str | None, attachment_id: str) -> str:
    if not filename:
        return attachment_id
    return Path(filename).name


@router.post("/writeups", response_model=IngestionResponse)
def submit_writeup(
    writeup: WriteupCreate,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    db: Session = Depends(get_db),
    _: object = Depends(require_agent_token),
) -> IngestionResponse:
    submission_hash = payload_hash(writeup.model_dump())
    existing = db.scalar(
        select(IngestionJob).where(
            IngestionJob.external_id == writeup.external_id,
            IngestionJob.submission_hash == submission_hash,
        )
    )
    if existing is not None:
        return IngestionResponse(job_id=existing.id, status=existing.status)
    job = IngestionJob(
        external_id=writeup.external_id,
        source_type="agent_api",
        status="queued",
        idempotency_key=idempotency_key,
        payload_json=writeup.model_dump(mode="json"),
        submission_hash=submission_hash,
    )
    db.add(job)
    db.commit()
    queue = get_queue()
    if queue is None:
        process_ingestion_job(job.id)
    else:
        queue.enqueue("app.workers.tasks.process_ingestion_job", job.id)
    return IngestionResponse(job_id=job.id, status="queued")


@router.post("/writeups/batch", response_model=list[IngestionResponse])
def submit_batch(
    writeups: list[WriteupCreate],
    db: Session = Depends(get_db),
    _: object = Depends(require_agent_token),
) -> list[IngestionResponse]:
    return [submit_writeup(writeup, None, db, _) for writeup in writeups]


@router.post("/writeups/{external_id}/attachments")
async def upload_attachment(
    external_id: str,
    attachment_id: Annotated[str, Form(...)],
    sha256: Annotated[str, Form(...)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: object = Depends(require_agent_token),
) -> dict:
    writeup = db.scalar(select(Writeup).where(Writeup.external_id == external_id))
    if writeup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="writeup not found")
    content = await file.read()
    computed_sha256 = hashlib.sha256(content).hexdigest()
    if computed_sha256 != sha256:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="attachment sha256 mismatch")

    filename = _safe_attachment_filename(file.filename, attachment_id)
    settings = get_settings()
    settings.attachment_dir.mkdir(parents=True, exist_ok=True)

    existing = db.scalar(
        select(Attachment).where(
            Attachment.writeup_id == writeup.id,
            Attachment.attachment_id == attachment_id,
        )
    )
    if existing is not None and existing.storage_path:
        try:
            os.remove(existing.storage_path)
        except FileNotFoundError:
            pass
        db.delete(existing)
        db.flush()

    extension = Path(filename).suffix
    safe_filename = f"{uuid.uuid4().hex}{extension}"
    target = settings.attachment_dir / safe_filename
    target.write_bytes(content)

    attachment = Attachment(
        writeup_id=writeup.id,
        attachment_id=attachment_id,
        original_filename=filename,
        safe_filename=safe_filename,
        mime_type=file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        size_bytes=len(content),
        sha256=computed_sha256,
        attachment_type="source",
        storage_path=str(target),
        ingestion_source="agent",
    )
    db.add(attachment)
    db.commit()
    return {"status": "stored", "attachment_id": attachment_id, "sha256": computed_sha256}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), _: object = Depends(require_agent_token)) -> dict:
    job = db.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return {"id": job.id, "status": job.status, "error_message": job.error_message}


@router.get("/writeups/{external_id}/status")
def get_writeup_status(external_id: str, db: Session = Depends(get_db), _: object = Depends(require_agent_token)) -> dict:
    writeup = db.scalar(select(Writeup).where(Writeup.external_id == external_id))
    if writeup is None:
        return {"status": "missing"}
    return {"status": "indexed", "id": writeup.id, "active_revision_id": writeup.active_revision_id}


@router.post("/writeups/{external_id}/reindex")
def reindex_writeup(external_id: str, db: Session = Depends(get_db), _: object = Depends(require_agent_token)) -> dict:
    writeup = db.scalar(select(Writeup).where(Writeup.external_id == external_id))
    if writeup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="writeup not found")
    return {"status": "accepted", "external_id": external_id}


@router.delete("/writeups/{external_id}")
def delete_writeup(external_id: str, db: Session = Depends(get_db), _: object = Depends(require_agent_token)) -> dict:
    writeup = db.scalar(select(Writeup).where(Writeup.external_id == external_id))
    if writeup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="writeup not found")
    db.delete(writeup)
    db.commit()
    return {"status": "deleted"}
