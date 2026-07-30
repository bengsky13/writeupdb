from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.security import (
    clear_admin_session,
    create_admin_session,
    require_admin_session,
    set_admin_session_cookie,
    verify_admin_credentials,
)
from app.db.session import get_db
from app.models import AdminSession

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    if not verify_admin_credentials(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    raw_token = create_admin_session(db, payload.username)
    set_admin_session_cookie(response, raw_token)
    return {"status": "authenticated", "username": payload.username}


@router.post("/logout")
def logout(
    response: Response,
    admin_session: AdminSession = Depends(require_admin_session),
    db: Session = Depends(get_db),
) -> dict:
    admin_session.revoked_at = datetime.now(UTC)
    db.commit()
    clear_admin_session(response)
    return {"status": "logged_out"}


@router.get("/me")
def me(admin_session: AdminSession = Depends(require_admin_session)) -> dict:
    return {"authenticated": True, "username": admin_session.username}
