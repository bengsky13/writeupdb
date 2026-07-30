from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Writeup(Base, TimestampMixin):
    __tablename__ = "writeups"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512), index=True)
    event: Mapped[str | None] = mapped_column(String(255), index=True)
    event_year: Mapped[int | None] = mapped_column(Integer, index=True)
    challenge: Mapped[str | None] = mapped_column(String(255), index=True)
    category: Mapped[str | None] = mapped_column(String(64), index=True)
    difficulty: Mapped[str | None] = mapped_column(String(64), index=True)
    language: Mapped[str | None] = mapped_column(String(32), index=True)
    team: Mapped[str | None] = mapped_column(String(255), index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_reference: Mapped[str | None] = mapped_column(String(255), index=True)
    original_source_url: Mapped[str | None] = mapped_column(String(1024))
    active_revision_id: Mapped[int | None] = mapped_column(ForeignKey("writeup_revisions.id"))
    duplicate_group_id: Mapped[int | None] = mapped_column(ForeignKey("duplicate_groups.id"))
    active_revision: Mapped["WriteupRevision | None"] = relationship(foreign_keys=[active_revision_id], post_update=True)
    revisions: Mapped[list["WriteupRevision"]] = relationship(back_populates="writeup", foreign_keys="WriteupRevision.writeup_id")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="writeup")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="writeup")


class WriteupRevision(Base, TimestampMixin):
    __tablename__ = "writeup_revisions"
    __table_args__ = (UniqueConstraint("writeup_id", "revision_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    writeup_id: Mapped[int] = mapped_column(ForeignKey("writeups.id"), index=True)
    revision_number: Mapped[int] = mapped_column(Integer)
    content_format: Mapped[str] = mapped_column(String(32))
    raw_content: Mapped[str] = mapped_column(Text)
    normalized_content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    writeup: Mapped[Writeup] = relationship(back_populates="revisions", foreign_keys=[writeup_id])
    sections: Mapped[list["Section"]] = relationship(back_populates="revision")


class Section(Base, TimestampMixin):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("writeup_revisions.id"), index=True)
    heading: Mapped[str | None] = mapped_column(String(512))
    heading_path: Mapped[list[str]] = mapped_column(JSON, default=list)
    section_order: Mapped[int] = mapped_column(Integer)
    content_text: Mapped[str] = mapped_column(Text)
    revision: Mapped[WriteupRevision] = relationship(back_populates="sections")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="section")


class Chunk(Base, TimestampMixin):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    writeup_id: Mapped[int] = mapped_column(ForeignKey("writeups.id"), index=True)
    revision_id: Mapped[int] = mapped_column(ForeignKey("writeup_revisions.id"), index=True)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"))
    chunk_order: Mapped[int] = mapped_column(Integer)
    chunk_type: Mapped[str] = mapped_column(String(32), index=True)
    heading: Mapped[str | None] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(Text)
    code_text: Mapped[str | None] = mapped_column(Text)
    language_hint: Mapped[str | None] = mapped_column(String(64))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    embedding_model: Mapped[str | None] = mapped_column(String(255))
    writeup: Mapped[Writeup] = relationship(back_populates="chunks")
    section: Mapped[Section | None] = relationship(back_populates="chunks")


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    writeup_id: Mapped[int] = mapped_column(ForeignKey("writeups.id"), index=True)
    section_id: Mapped[int | None] = mapped_column(ForeignKey("sections.id"))
    attachment_id: Mapped[str] = mapped_column(String(255))
    original_filename: Mapped[str] = mapped_column(String(255))
    safe_filename: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(255))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    attachment_type: Mapped[str | None] = mapped_column(String(64))
    storage_path: Mapped[str] = mapped_column(String(1024))
    ingestion_source: Mapped[str | None] = mapped_column(String(255))
    writeup: Mapped[Writeup] = relationship(back_populates="attachments")


class IngestionJob(Base, TimestampMixin):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id: Mapped[str | None] = mapped_column(String(255), index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="queued")
    idempotency_key: Mapped[str | None] = mapped_column(String(255), index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    submission_hash: Mapped[str | None] = mapped_column(String(64), index=True)


class IngestionError(Base, TimestampMixin):
    __tablename__ = "ingestion_errors"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id"), index=True)
    code: Mapped[str] = mapped_column(String(128))
    detail: Mapped[str] = mapped_column(Text)


class AgentToken(Base, TimestampMixin):
    __tablename__ = "agent_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    allowed_operations: Mapped[list[str]] = mapped_column(JSON, default=list)


class AdminSession(Base, TimestampMixin):
    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(255), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ExtractionResult(Base, TimestampMixin):
    __tablename__ = "extraction_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    writeup_id: Mapped[int] = mapped_column(ForeignKey("writeups.id"), index=True)
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("chunks.id"))
    field_name: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[float] = mapped_column(Float)
    extractor_version: Mapped[str] = mapped_column(String(64))
    rule_name: Mapped[str] = mapped_column(String(128))
    provenance: Mapped[str] = mapped_column(String(64), default="extracted")


class DuplicateGroup(Base, TimestampMixin):
    __tablename__ = "duplicate_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    reason: Mapped[str] = mapped_column(String(255))
    confidence: Mapped[float] = mapped_column(Float)
    primary_writeup_id: Mapped[int | None] = mapped_column(ForeignKey("writeups.id"))


class SearchQueryLog(Base, TimestampMixin):
    __tablename__ = "search_query_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(Text, index=True)
    parsed_query: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[int] = mapped_column(Integer)
    result_count: Mapped[int] = mapped_column(Integer)
    zero_result: Mapped[bool] = mapped_column(Boolean, default=False)
