from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models import AdminSession, AgentToken


def hash_token(token: str) -> str:
    settings = get_settings()
    return hashlib.sha256(f"{settings.agent_token_pepper}:{token}".encode()).hexdigest()


def create_agent_token_value() -> str:
    return secrets.token_urlsafe(32)


def create_admin_session_value() -> str:
    return secrets.token_urlsafe(32)


def hash_admin_session(token: str) -> str:
    settings = get_settings()
    return hashlib.sha256(f"{settings.admin_session_pepper}:{token}".encode()).hexdigest()


def verify_admin_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    expected_password = settings.admin_password or settings.admin_api_token
    return secrets.compare_digest(username, settings.admin_username) and secrets.compare_digest(password, expected_password)


def create_admin_session(db: Session, username: str) -> str:
    settings = get_settings()
    raw = create_admin_session_value()
    expires_at = datetime.now(UTC) + timedelta(hours=settings.admin_session_ttl_hours)
    db.add(
        AdminSession(
            username=username,
            token_hash=hash_admin_session(raw),
            expires_at=expires_at,
            last_used_at=datetime.now(UTC),
        )
    )
    db.commit()
    return raw


def clear_admin_session(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.admin_session_cookie_name, path="/")


def set_admin_session_cookie(response: Response, raw_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.admin_session_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.admin_session_ttl_hours * 3600,
        path="/",
    )


def require_admin_session(
    db: Session = Depends(get_db),
    session_cookie: str | None = Cookie(default=None, alias="ctf_search_session"),
) -> AdminSession:
    if not session_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    token_hash = hash_admin_session(session_cookie)
    session = db.scalar(select(AdminSession).where(AdminSession.token_hash == token_hash))
    if session is None or session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session")
    if session.expires_at < datetime.now(UTC):
        session.revoked_at = datetime.now(UTC)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")
    session.last_used_at = datetime.now(UTC)
    db.commit()
    return session


def require_agent_token(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> AgentToken:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    raw = authorization.removeprefix("Bearer ").strip()
    token_hash = hash_token(raw)
    token = db.scalar(select(AgentToken).where(AgentToken.token_hash == token_hash))
    if token is None or token.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token")
    if token.expires_at and token.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="expired token")
    token.last_used_at = datetime.now(UTC)
    db.commit()
    return token
