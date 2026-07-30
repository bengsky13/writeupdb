from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.embeddings.providers import build_embedding_provider
from app.models import IngestionJob
from app.services.ingestion_service import IngestionService


def process_ingestion_job(job_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        job = db.scalar(select(IngestionJob).where(IngestionJob.id == job_id))
        if job is None:
            return
        job.status = "processing"
        db.commit()
        provider = build_embedding_provider(settings)
        provider.verify()
        payload = dict(job.payload_json)
        attachment_paths = payload.get("_attachment_paths", {})
        if attachment_paths:
            payload["_attachment_bytes"] = {
                attachment_id: Path(path).read_bytes()
                for attachment_id, path in attachment_paths.items()
            }
        service = IngestionService(db, provider, settings.attachment_dir)
        service.ingest_payload(payload, job=job)
        if attachment_paths:
            staging_dirs = {str(Path(path).parent) for path in attachment_paths.values()}
            for directory in staging_dirs:
                shutil.rmtree(directory, ignore_errors=True)
    except Exception as exc:
        if job is not None:
            db.rollback()
            job.status = "failed"
            job.error_message = str(exc)
            db.commit()
        raise
    finally:
        db.close()
