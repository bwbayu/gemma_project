"""Shared response schemas: structured error envelope and health payload."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorContent(BaseModel):
    """Body of a structured API error: machine-readable code + human-readable message + optional details."""

    code: str
    message: str
    details: Any = None


class ErrorEnvelope(BaseModel):
    """Top-level wrapper returned for every non-2xx response."""

    error: ErrorContent


class HealthResponse(BaseModel):
    """Response payload for the `/healthz` endpoint."""

    status: str
    project_id: str
    firestore_database_id: str
    gcs_bucket: str
