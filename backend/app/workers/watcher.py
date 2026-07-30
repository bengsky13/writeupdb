from __future__ import annotations

import json
import time
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.embeddings.providers import build_embedding_provider
from app.ingestion.package_validator import move_package, validate_package
from app.models import IngestionJob
from app.services.ingestion_service import IngestionService


def process_pending_package(package_dir: Path) -> None:
    settings = get_settings()
    processing = settings.import_dir / "processing" / package_dir.name
    completed = settings.import_dir / "completed" / package_dir.name
    rejected = settings.import_dir / "rejected" / package_dir.name
    moved = move_package(package_dir, processing)
    db = SessionLocal()
    try:
        validated = validate_package(moved)
        content = (validated.root / validated.manifest["content_file"]).read_text(encoding="utf-8")
        payload = {
            **validated.manifest,
            "content": content,
            "attachments": [
                {
                    "attachment_id": Path(item["path"]).name,
                    "filename": Path(item["path"]).name,
                    "relative_path": item["path"],
                    "sha256": "",
                    "type": item.get("type"),
                }
                for item in validated.manifest.get("attachments", [])
            ],
            "_attachment_bytes": {
                Path(item["path"]).name: (validated.root / item["path"]).read_bytes()
                for item in validated.manifest.get("attachments", [])
            },
        }
        job = IngestionJob(
            external_id=payload["external_id"],
            source_type="watcher",
            status="processing",
            payload_json=payload,
        )
        db.add(job)
        db.commit()
        provider = build_embedding_provider(settings)
        service = IngestionService(db, provider, settings.attachment_dir)
        service.ingest_payload(payload, job)
        move_package(moved, completed)
    except Exception as exc:
        error_path = rejected.with_suffix(".error.json")
        rejected.parent.mkdir(parents=True, exist_ok=True)
        move_package(moved, rejected)
        error_path.write_text(json.dumps({"error": str(exc)}, indent=2), encoding="utf-8")
    finally:
        db.close()


def main() -> None:
    settings = get_settings()
    pending = settings.import_dir / "pending"
    pending.mkdir(parents=True, exist_ok=True)
    while True:
        for package_dir in sorted(path for path in pending.iterdir() if path.is_dir()):
            process_pending_package(package_dir)
        time.sleep(5)


if __name__ == "__main__":
    main()

