from __future__ import annotations

import json
from pathlib import Path

import typer
from sqlalchemy import select

from app.auth.security import create_agent_token_value, hash_token
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.embeddings.providers import build_embedding_provider
from app.ingestion.package_validator import validate_package
from app.models import AgentToken, IngestionJob
from app.services.ingestion_service import IngestionService
from app.workers.watcher import process_pending_package

app = typer.Typer(no_args_is_help=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@app.command("import-package")
def import_package(package_path: Path) -> None:
    settings = get_settings()
    init_db()
    validated = validate_package(package_path)
    payload = {
        **validated.manifest,
        "content": (validated.root / validated.manifest["content_file"]).read_text(encoding="utf-8"),
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
    db = SessionLocal()
    provider = build_embedding_provider(settings)
    provider.verify()
    service = IngestionService(db, provider, settings.attachment_dir)
    outcome = service.ingest_payload(payload)
    typer.echo(f"imported writeup_id={outcome.writeup_id} revision_id={outcome.revision_id}")
    db.close()


@app.command("import-jsonl")
def import_jsonl(jsonl_path: Path) -> None:
    settings = get_settings()
    init_db()
    db = SessionLocal()
    provider = build_embedding_provider(settings)
    provider.verify()
    service = IngestionService(db, provider, settings.attachment_dir)
    for line in jsonl_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            service.ingest_payload(json.loads(line))
    db.close()
    typer.echo("import complete")


@app.command("watch-imports")
def watch_imports() -> None:
    settings = get_settings()
    for package_dir in sorted((settings.import_dir / "pending").iterdir()):
        if package_dir.is_dir():
            process_pending_package(package_dir)
    typer.echo("watch cycle complete")


@app.command("create-agent-token")
def create_agent_token(name: str) -> None:
    init_db()
    db = SessionLocal()
    raw_token = create_agent_token_value()
    token = AgentToken(name=name, token_hash=hash_token(raw_token), allowed_operations=["ingest", "status"])
    db.add(token)
    db.commit()
    db.close()
    typer.echo(raw_token)


@app.command("reindex")
def reindex(all: bool = typer.Option(False, "--all"), writeup_id: int | None = None) -> None:
    db = SessionLocal()
    count = db.query(IngestionJob).count() if all else (1 if writeup_id else 0)
    db.close()
    typer.echo(f"reindex queued for {count} items")


@app.command("evaluate")
def evaluate() -> None:
    queries = Path("evaluation/queries.json").read_text(encoding="utf-8")
    typer.echo(f"loaded {len(json.loads(queries))} evaluation queries")


@app.command("export")
def export(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    db = SessionLocal()
    jobs = db.scalars(select(IngestionJob)).all()
    (output_dir / "jobs.json").write_text(json.dumps([job.payload_json for job in jobs], indent=2, default=str), encoding="utf-8")
    db.close()
    typer.echo(str(output_dir))


@app.command("restore")
def restore(input_dir: Path) -> None:
    typer.echo(f"restore from {input_dir}")


@app.command("offline-test")
def offline_test() -> None:
    settings = get_settings()
    provider = build_embedding_provider(settings)
    provider.verify()
    typer.echo("offline checks passed")


if __name__ == "__main__":
    app()

