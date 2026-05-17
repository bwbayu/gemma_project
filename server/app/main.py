"""FastAPI app factory: wires CORS, exception handlers, and routers under the configured prefix."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi import APIRouter
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.schemas.common import ErrorEnvelope
from app.api.routers.health import router as health_router
from app.api.routers.jobs import router as jobs_router
from app.api.routers.questions import router as questions_router
from app.api.routers.workspaces import router as workspaces_router
from app.config import get_settings
from app.utils.errors import AppError

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application with middleware, routers, and exception handlers."""
    settings = get_settings()
    allowed_origins = [
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
    ]
    app = FastAPI(
        title="VisiQ Backend API",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        """Return a structured JSON error response for known application errors."""
        body = ErrorEnvelope(
            error={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Return a 422 response with Pydantic validation error details."""
        body = ErrorEnvelope(
            error={
                "code": "REQUEST_VALIDATION_ERROR",
                "message": "Request payload validation failed.",
                "details": exc.errors(),
            }
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        """Catch-all handler that logs unexpected exceptions and returns a 500 response."""
        logger.exception("Unhandled API error")
        body = ErrorEnvelope(
            error={
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Unexpected server error.",
                "details": {"type": type(exc).__name__},
            }
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body.model_dump())

    api_router = APIRouter(prefix=settings.api_prefix)
    api_router.include_router(workspaces_router)
    api_router.include_router(questions_router)
    api_router.include_router(jobs_router)

    app.include_router(api_router)
    app.include_router(health_router)

    return app


app = create_app()
