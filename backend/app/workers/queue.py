from __future__ import annotations

from redis import Redis
from rq import Queue

from app.core.config import get_settings


def get_queue() -> Queue | None:
    settings = get_settings()
    if settings.queue_eager:
        return None
    return Queue("ingestion", connection=Redis.from_url(settings.redis_url))

