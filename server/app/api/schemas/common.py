from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorContent(BaseModel):
    code: str
    message: str
    details: Any = None


class ErrorEnvelope(BaseModel):
    error: ErrorContent


class HealthResponse(BaseModel):
    status: str
    project_id: str
    firestore_database_id: str
    gcs_bucket: str
