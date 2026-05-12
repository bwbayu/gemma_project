from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas.common import HealthResponse
from app.dependencies import get_infra_clients

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    """Return server health status and connected infrastructure identifiers."""
    clients = get_infra_clients()
    return HealthResponse(
        status="ok",
        project_id=clients.settings.google_cloud_project,
        firestore_database_id=clients.settings.firestore_database_id,
        gcs_bucket=clients.settings.gcs_bucket_name,
    )
