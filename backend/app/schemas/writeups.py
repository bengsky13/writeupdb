from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AttachmentInput(BaseModel):
    attachment_id: str
    filename: str
    relative_path: str
    sha256: str
    type: str | None = None
    language: str | None = None


class WriteupCreate(BaseModel):
    external_id: str
    title: str
    event: str | None = None
    event_year: int | None = None
    challenge: str | None = None
    category: str | None = None
    difficulty: str | None = None
    authors: list[str] = Field(default_factory=list)
    team: str | None = None
    language: str | None = None
    published_at: datetime | None = None
    source_reference: str | None = None
    original_source_url: str | None = None
    content_format: Literal["markdown", "html", "text", "pdf", "json", "jsonl"]
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    attachments: list[AttachmentInput] = Field(default_factory=list)


class IngestionResponse(BaseModel):
    job_id: str
    status: str


class SearchResult(BaseModel):
    id: int
    title: str
    event: str | None
    event_year: int | None
    challenge: str | None
    category: str | None
    matched_section: str | None
    highlight: str
    score: float
    explanation: dict[str, Any]
    attachments: list[dict[str, Any]]

