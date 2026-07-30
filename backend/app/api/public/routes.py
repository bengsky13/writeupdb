from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import require_admin_session
from app.core.config import get_settings
from app.db.session import get_db
from app.embeddings.providers import build_embedding_provider
from app.models import Attachment, Writeup, WriteupRevision
from app.search.service import SearchService

router = APIRouter(prefix="/api", tags=["public"], dependencies=[Depends(require_admin_session)])

TEXT_ATTACHMENT_MIME_PREFIXES = ("text/",)
TEXT_ATTACHMENT_MIME_TYPES = {
    "application/json",
    "application/javascript",
    "application/x-javascript",
    "application/xml",
}


@router.get("/writeups")
def list_writeups(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=20),
    db: Session = Depends(get_db),
) -> dict:
    total = db.scalar(select(func.count()).select_from(Writeup)) or 0
    offset = (page - 1) * limit
    writeups = db.scalars(select(Writeup).order_by(Writeup.created_at.desc()).offset(offset).limit(limit)).all()
    results: list[dict] = []
    for writeup in writeups:
        revision = db.scalar(select(WriteupRevision).where(WriteupRevision.id == writeup.active_revision_id))
        results.append(
            {
                "id": writeup.id,
                "external_id": writeup.external_id,
                "title": writeup.title,
                "event": writeup.event,
                "event_year": writeup.event_year,
                "challenge": writeup.challenge,
                "category": writeup.category,
                "team": writeup.team,
                "published_at": writeup.published_at.isoformat() if writeup.published_at else None,
                "content": revision.normalized_content if revision else "",
            }
        )
    total_pages = max((total + limit - 1) // limit, 1)
    return {
        "items": results,
        "page": page,
        "page_size": limit,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/events")
def list_events(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=20),
    db: Session = Depends(get_db),
) -> dict:
    base_stmt = (
        select(
            Writeup.event,
            Writeup.event_year,
            func.count(Writeup.id).label("writeup_count"),
            func.max(Writeup.created_at).label("latest_writeup_at"),
        )
        .where(Writeup.event.is_not(None))
        .group_by(Writeup.event, Writeup.event_year)
    )
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = db.scalar(count_stmt) or 0
    offset = (page - 1) * limit
    rows = db.execute(
        base_stmt
        .order_by(func.max(Writeup.created_at).desc(), Writeup.event.asc(), Writeup.event_year.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    total_pages = max((total + limit - 1) // limit, 1)
    return {
        "items": [
            {
                "event": row.event,
                "event_year": row.event_year,
                "writeup_count": row.writeup_count,
                "latest_writeup_at": row.latest_writeup_at.isoformat() if row.latest_writeup_at else None,
            }
            for row in rows
        ],
        "page": page,
        "page_size": limit,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/events/{event_name}")
def get_event_writeups(
    event_name: str,
    event_year: int | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=20),
    db: Session = Depends(get_db),
) -> dict:
    filters = [Writeup.event == event_name]
    if event_year is not None:
        filters.append(Writeup.event_year == event_year)

    total = db.scalar(select(func.count()).select_from(Writeup).where(*filters)) or 0
    offset = (page - 1) * limit
    writeups = db.scalars(
        select(Writeup)
        .where(*filters)
        .order_by(Writeup.published_at.desc().nullslast(), Writeup.created_at.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    if not writeups and page == 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")

    items: list[dict] = []
    for writeup in writeups:
        revision = db.scalar(select(WriteupRevision).where(WriteupRevision.id == writeup.active_revision_id))
        items.append(
            {
                "id": writeup.id,
                "external_id": writeup.external_id,
                "title": writeup.title,
                "event": writeup.event,
                "event_year": writeup.event_year,
                "challenge": writeup.challenge,
                "category": writeup.category,
                "team": writeup.team,
                "published_at": writeup.published_at.isoformat() if writeup.published_at else None,
                "content": revision.normalized_content if revision else "",
            }
        )

    total_pages = max((total + limit - 1) // limit, 1)
    return {
        "event": event_name,
        "event_year": event_year,
        "items": items,
        "page": page,
        "page_size": limit,
        "total": total,
        "total_pages": total_pages,
    }


@router.get("/search")
def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=20),
    debug: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    provider = build_embedding_provider(get_settings())
    return SearchService(db, provider).search(q, page=page, limit=limit, debug=debug)


@router.get("/writeups/{writeup_id}")
def get_writeup(writeup_id: int, db: Session = Depends(get_db)) -> dict:
    writeup = db.scalar(select(Writeup).where(Writeup.id == writeup_id))
    if writeup is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="writeup not found")
    revision = db.scalar(select(WriteupRevision).where(WriteupRevision.id == writeup.active_revision_id))
    attachments = db.scalars(select(Attachment).where(Attachment.writeup_id == writeup.id).order_by(Attachment.created_at.asc())).all()
    return {
        "id": writeup.id,
        "external_id": writeup.external_id,
        "title": writeup.title,
        "event": writeup.event,
        "event_year": writeup.event_year,
        "challenge": writeup.challenge,
        "category": writeup.category,
        "team": writeup.team,
        "content": revision.normalized_content if revision else "",
        "metadata": revision.metadata_json if revision else {},
        "attachments": [
            {
                "id": attachment.id,
                "attachment_id": attachment.attachment_id,
                "filename": attachment.original_filename,
                "type": attachment.attachment_type,
                "mime_type": attachment.mime_type,
                "size_bytes": attachment.size_bytes,
            }
            for attachment in attachments
        ],
    }


@router.get("/writeups/{writeup_id}/attachments/{attachment_id}")
def download_attachment(writeup_id: int, attachment_id: int, db: Session = Depends(get_db)) -> FileResponse:
    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == attachment_id,
            Attachment.writeup_id == writeup_id,
        )
    )
    if attachment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="attachment not found")
    if attachment.mime_type.startswith(TEXT_ATTACHMENT_MIME_PREFIXES) or attachment.mime_type in TEXT_ATTACHMENT_MIME_TYPES:
        return PlainTextResponse(
            Path(attachment.storage_path).read_text(errors="replace"),
            headers={"Content-Disposition": "inline"},
        )
    return FileResponse(
        attachment.storage_path,
        media_type=attachment.mime_type,
        headers={"Content-Disposition": "inline"},
    )
