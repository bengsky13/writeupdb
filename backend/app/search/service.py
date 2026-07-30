from __future__ import annotations

import math
import time
from typing import Any

from sqlalchemy import Select, and_, or_, select
from sqlalchemy.orm import Session

from app.embeddings.providers import EmbeddingProvider
from app.models import Attachment, Chunk, SearchQueryLog, Writeup
from app.schemas.writeups import SearchResult
from app.search.query_parser import parse_query


def cosine_similarity(lhs: list[float], rhs: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(lhs, rhs, strict=False))
    lhs_norm = math.sqrt(sum(v * v for v in lhs)) or 1.0
    rhs_norm = math.sqrt(sum(v * v for v in rhs)) or 1.0
    return numerator / (lhs_norm * rhs_norm)


class SearchService:
    def __init__(self, db: Session, embedding_provider: EmbeddingProvider) -> None:
        self.db = db
        self.embedding_provider = embedding_provider

    def search(self, query: str, page: int = 1, limit: int = 20, debug: bool = False) -> dict[str, Any]:
        started = time.perf_counter()
        parsed = parse_query(query)
        terms = [term for term in parsed["tokens"] if term]
        term_clauses = [
            or_(
                Chunk.text.ilike(f"%{term}%"),
                Chunk.code_text.ilike(f"%{term}%"),
                Writeup.title.ilike(f"%{term}%"),
                Writeup.challenge.ilike(f"%{term}%"),
            )
            for term in terms
        ]
        base_query_clause = or_(
            Chunk.text.ilike(f"%{query}%"),
            Chunk.code_text.ilike(f"%{query}%"),
            Writeup.title.ilike(f"%{query}%"),
            Writeup.challenge.ilike(f"%{query}%"),
        )
        lexical_stmt: Select[tuple[Chunk, Writeup]] = (
            select(Chunk, Writeup)
            .join(Writeup, Chunk.writeup_id == Writeup.id)
            .where(
                or_(
                    base_query_clause,
                    and_(*term_clauses) if term_clauses else base_query_clause,
                    or_(*term_clauses) if term_clauses else base_query_clause,
                )
            )
        )
        lexical_rows = self.db.execute(lexical_stmt).all()
        semantic_query = self.embedding_provider.embed([query])[0]
        attachments_by_writeup: dict[int, list[dict[str, Any]]] = {}
        scored_by_writeup: dict[int, SearchResult] = {}
        for chunk, writeup in lexical_rows:
            semantic_score = cosine_similarity(semantic_query, chunk.embedding or semantic_query)
            haystacks = [
                chunk.text or "",
                chunk.code_text or "",
                writeup.title or "",
                writeup.challenge or "",
            ]
            lexical_score = 1.0
            matched_terms = sum(
                1
                for term in terms
                if any(term.lower() in haystack.lower() for haystack in haystacks)
            )
            if terms:
                lexical_score += matched_terms / max(len(terms), 1)
            if any(phrase.lower() in (chunk.text or "").lower() for phrase in parsed["quoted_phrases"]):
                lexical_score += 1.0
            if writeup.challenge and writeup.challenge.lower() in query.lower():
                lexical_score += 0.8
            if writeup.title.lower() == query.lower():
                lexical_score += 1.2
            metadata_score = 0.2 if parsed["category"] and parsed["category"] == writeup.category else 0.0
            total = (lexical_score * 0.45) + (semantic_score * 0.35) + (metadata_score * 0.1) + 0.1
            if writeup.id not in attachments_by_writeup:
                attachments_by_writeup[writeup.id] = [
                    {
                        "id": attachment.id,
                        "filename": attachment.original_filename,
                        "type": attachment.attachment_type,
                    }
                    for attachment in self.db.scalars(
                        select(Attachment).where(Attachment.writeup_id == writeup.id)
                    ).all()
                ]
            candidate = SearchResult(
                id=writeup.id,
                title=writeup.title,
                event=writeup.event,
                event_year=writeup.event_year,
                challenge=writeup.challenge,
                category=writeup.category,
                matched_section=chunk.heading,
                highlight=(chunk.text or "")[:320],
                score=round(total, 4),
                explanation={
                    "lexical_score": lexical_score,
                    "semantic_score": semantic_score,
                    "metadata_score": metadata_score,
                }
                if debug
                else {"match": "hybrid"},
                attachments=attachments_by_writeup[writeup.id],
            )
            existing = scored_by_writeup.get(writeup.id)
            if existing is None or candidate.score > existing.score:
                scored_by_writeup[writeup.id] = candidate

        scored = sorted(scored_by_writeup.values(), key=lambda item: item.score, reverse=True)
        latency_ms = int((time.perf_counter() - started) * 1000)
        self.db.add(
            SearchQueryLog(
                query=query,
                parsed_query=parsed,
                latency_ms=latency_ms,
                result_count=len(scored),
                zero_result=not scored,
            )
        )
        self.db.commit()
        offset = (page - 1) * limit
        paged = scored[offset:offset + limit]
        total = len(scored)
        return {
            "query": parsed,
            "results": [item.model_dump() for item in paged],
            "latency_ms": latency_ms,
            "page": page,
            "page_size": limit,
            "total": total,
            "total_pages": max((total + limit - 1) // limit, 1),
        }
