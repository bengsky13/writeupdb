from __future__ import annotations

from dataclasses import dataclass

from app.parsing.parsers import ParsedDocument


@dataclass
class ChunkInput:
    chunk_type: str
    heading: str | None
    text: str
    code_text: str | None = None
    language_hint: str | None = None


def build_chunks(parsed: ParsedDocument) -> list[ChunkInput]:
    chunks: list[ChunkInput] = []
    for heading, section_text in parsed.sections:
        paragraphs = [part.strip() for part in section_text.split("\n\n") if part.strip()]
        if not paragraphs:
            continue
        buffer: list[str] = []
        for paragraph in paragraphs:
            if paragraph.startswith("```"):
                continue
            buffer.append(paragraph)
            if len(buffer) >= 2:
                chunks.append(ChunkInput("prose", heading, "\n\n".join(buffer)))
                buffer = []
        if buffer:
            chunks.append(ChunkInput("prose", heading, "\n\n".join(buffer)))
    for language_hint, code in parsed.code_blocks:
        chunks.append(ChunkInput("code", None, code, code_text=code, language_hint=language_hint))
    return chunks

