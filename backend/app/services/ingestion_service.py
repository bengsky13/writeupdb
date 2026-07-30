from __future__ import annotations

import hashlib
import mimetypes
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.embeddings.providers import EmbeddingProvider
from app.extraction.rules import extract_metadata
from app.ingestion.chunking import build_chunks
from app.models import Attachment, Chunk, ExtractionResult, IngestionJob, Section, Writeup, WriteupRevision
from app.parsing.parsers import parse_content

SECTION_HEADING_MAX_LENGTH = 512


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_text(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_heading(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if len(normalized) <= SECTION_HEADING_MAX_LENGTH:
        return normalized
    return normalized[: SECTION_HEADING_MAX_LENGTH - 1].rstrip() + "…"


def attachment_fingerprints(attachments: list[dict[str, Any]]) -> list[str]:
    return sorted(
        attachment["sha256"]
        for attachment in attachments
        if attachment.get("sha256")
    )


@dataclass
class IngestionOutcome:
    writeup_id: int
    revision_id: int
    content_hash: str


class IngestionService:
    def __init__(self, db: Session, embedding_provider: EmbeddingProvider, attachment_dir: Path) -> None:
        self.db = db
        self.embedding_provider = embedding_provider
        self.attachment_dir = attachment_dir

    def ingest_payload(self, payload: dict[str, Any], job: IngestionJob | None = None) -> IngestionOutcome:
        normalized_content = normalize_text(payload["content"])
        content_hash = sha256_text(normalized_content)
        incoming_attachments = payload.get("attachments", [])
        incoming_attachment_hashes = attachment_fingerprints(incoming_attachments)
        writeup = self.db.scalar(select(Writeup).where(Writeup.external_id == payload["external_id"]))
        if writeup is None:
            writeup = Writeup(
                external_id=payload["external_id"],
                title=payload["title"],
                event=payload.get("event"),
                event_year=payload.get("event_year"),
                challenge=payload.get("challenge"),
                category=payload.get("category"),
                difficulty=payload.get("difficulty"),
                language=payload.get("language"),
                team=payload.get("team"),
                published_at=payload.get("published_at"),
                source_reference=payload.get("source_reference"),
                original_source_url=payload.get("original_source_url"),
            )
            self.db.add(writeup)
            self.db.flush()
        else:
            active = self.db.scalar(select(WriteupRevision).where(WriteupRevision.id == writeup.active_revision_id))
            existing_attachment_hashes = sorted(attachment.sha256 for attachment in writeup.attachments)
            if active and active.content_hash == content_hash and existing_attachment_hashes == incoming_attachment_hashes:
                return IngestionOutcome(writeup.id, active.id, content_hash)
            writeup.title = payload["title"]
            writeup.event = payload.get("event")
            writeup.event_year = payload.get("event_year")
            writeup.challenge = payload.get("challenge")
            writeup.category = payload.get("category")
            writeup.difficulty = payload.get("difficulty")
            writeup.language = payload.get("language")
            writeup.team = payload.get("team")

        current_revision_number = (
            self.db.query(WriteupRevision).filter(WriteupRevision.writeup_id == writeup.id).count()
        )
        revision = WriteupRevision(
            writeup_id=writeup.id,
            revision_number=current_revision_number + 1,
            content_format=payload["content_format"],
            raw_content=payload["content"],
            normalized_content=normalized_content,
            content_hash=content_hash,
            metadata_json=payload.get("metadata", {}),
            is_active=True,
        )
        self.db.add(revision)
        self.db.flush()
        self.db.execute(delete(Chunk).where(Chunk.writeup_id == writeup.id))
        parsed = parse_content(normalized_content, payload["content_format"])
        created_sections: list[Section] = []
        for index, (heading, text) in enumerate(parsed.sections, start=1):
            truncated_heading = truncate_heading(heading)
            section = Section(
                revision_id=revision.id,
                heading=truncated_heading,
                heading_path=[truncated_heading] if truncated_heading else [],
                section_order=index,
                content_text=text,
            )
            self.db.add(section)
            self.db.flush()
            created_sections.append(section)
        section_map = {section.section_order: section for section in created_sections}
        chunk_inputs = build_chunks(parsed)
        embeddings = self.embedding_provider.embed([chunk.text for chunk in chunk_inputs] or [""])
        for index, chunk_input in enumerate(chunk_inputs, start=1):
            truncated_heading = truncate_heading(chunk_input.heading)
            chunk = Chunk(
                writeup_id=writeup.id,
                revision_id=revision.id,
                section_id=section_map.get(index).id if section_map.get(index) else None,
                chunk_order=index,
                chunk_type=chunk_input.chunk_type,
                heading=truncated_heading,
                text=chunk_input.text,
                code_text=chunk_input.code_text,
                language_hint=chunk_input.language_hint,
                metadata_json=payload.get("metadata", {}),
                embedding=embeddings[min(index - 1, len(embeddings) - 1)],
                embedding_model=self.embedding_provider.model_id,
            )
            self.db.add(chunk)
            self.db.flush()
            for extracted in extract_metadata(chunk.text):
                self.db.add(
                    ExtractionResult(
                        writeup_id=writeup.id,
                        chunk_id=chunk.id,
                        field_name=extracted.field,
                        value=extracted.value,
                        confidence=extracted.confidence,
                        extractor_version="1.0",
                        rule_name=extracted.rule_name,
                    )
                )
        writeup.active_revision_id = revision.id
        self.db.execute(delete(Attachment).where(Attachment.writeup_id == writeup.id))
        self._store_attachments(writeup.id, incoming_attachments, payload.get("_attachment_bytes", {}))
        if job:
            job.status = "completed"
            job.submission_hash = content_hash
        self.db.commit()
        return IngestionOutcome(writeup.id, revision.id, content_hash)

    def _store_attachments(
        self,
        writeup_id: int,
        attachments: list[dict[str, Any]],
        attachment_bytes: dict[str, bytes],
    ) -> None:
        self.attachment_dir.mkdir(parents=True, exist_ok=True)
        for attachment in attachments:
            blob = attachment_bytes.get(attachment["attachment_id"])
            if blob is None:
                continue
            extension = Path(attachment["filename"]).suffix
            safe_filename = f"{uuid.uuid4().hex}{extension}"
            target = self.attachment_dir / safe_filename
            target.write_bytes(blob)
            self.db.add(
                Attachment(
                    writeup_id=writeup_id,
                    attachment_id=attachment["attachment_id"],
                    original_filename=attachment["filename"],
                    safe_filename=safe_filename,
                    mime_type=mimetypes.guess_type(attachment["filename"])[0] or "application/octet-stream",
                    size_bytes=len(blob),
                    sha256=attachment["sha256"],
                    attachment_type=attachment.get("type"),
                    storage_path=str(target),
                    ingestion_source="agent",
                )
            )
