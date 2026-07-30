from __future__ import annotations

import logging
import traceback

from fastapi.exceptions import RequestValidationError
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette import status
from sqlalchemy import text

from app.api.auth.routes import router as auth_router
from app.api.admin.routes import router as admin_router
from app.api.agent.routes import router as agent_router
from app.api.public.routes import router as public_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import Base, SessionLocal, engine
from app.embeddings.providers import build_embedding_provider

settings = get_settings()
configure_logging(settings.backend_debug)
logger = logging.getLogger(__name__)
app = FastAPI(title="CTF Search", version="0.1.0", debug=settings.backend_debug)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(public_router)
app.include_router(agent_router)
app.include_router(admin_router)


def _debug_error_payload(exc: Exception) -> dict:
    return {
        "error": type(exc).__name__,
        "detail": str(exc),
        "traceback": traceback.format_exception(type(exc), exc, exc.__traceback__),
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    if settings.backend_debug:
        logger.debug("request.start method=%s path=%s query=%s", request.method, request.url.path, request.url.query)
    response = await call_next(request)
    if settings.backend_debug:
        logger.debug("request.end method=%s path=%s status=%s", request.method, request.url.path, response.status_code)
    return response


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    if not settings.backend_debug:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            **_debug_error_payload(exc),
            "path": request.url.path,
            "method": request.method,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("request.failed method=%s path=%s", request.method, request.url.path, exc_info=exc)
    if not settings.backend_debug:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "internal server error"},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            **_debug_error_payload(exc),
            "path": request.url.path,
            "method": request.method,
        },
    )


@app.on_event("startup")
def startup() -> None:
    settings.attachment_dir.mkdir(parents=True, exist_ok=True)
    settings.import_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    build_embedding_provider(settings).verify()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        provider = build_embedding_provider(settings)
        provider.verify()
        return {"status": "ready"}
    finally:
        db.close()
