"""Lazy singletons for the GCP clients (Firestore, GCS) injected into FastAPI handlers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from google.cloud import firestore
from google.cloud import storage

from app.config import Settings, get_settings
from app.utils.errors import AppError


@dataclass
class InfraClients:
    settings: Settings
    firestore_client: firestore.Client
    gcs_client: storage.Client
    gcs_bucket: storage.Bucket


_clients: InfraClients | None = None


def _validate_env(settings: Settings) -> None:
    """Use a local credentials file when provided; otherwise let ADC resolve credentials."""
    if not settings.google_application_credentials:
        return

    creds_path = Path(settings.google_application_credentials)
    if not creds_path.is_absolute():
        creds_path = Path.cwd() / creds_path
    if not creds_path.exists():
        raise AppError(
            code="ENV_CREDENTIALS_NOT_FOUND",
            message="GOOGLE_APPLICATION_CREDENTIALS file does not exist.",
            details={"path": str(creds_path)},
            status_code=500,
        )

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds_path)


def _build_clients(settings: Settings) -> InfraClients:
    """Instantiate Firestore and GCS clients from the provided settings."""
    # Explicitly target the configured Firestore database (non-default supported).
    firestore_client = firestore.Client(
        project=settings.google_cloud_project,
        database=settings.firestore_database_id,
    )
    gcs_client = storage.Client(project=settings.google_cloud_project)
    gcs_bucket = gcs_client.bucket(settings.gcs_bucket_name)
    return InfraClients(
        settings=settings,
        firestore_client=firestore_client,
        gcs_client=gcs_client,
        gcs_bucket=gcs_bucket,
    )


def initialize_infra_clients() -> InfraClients:
    """Validate credentials, build GCP clients, and cache them in the module-level singleton."""
    global _clients
    if _clients is not None:
        return _clients

    settings = get_settings()
    _validate_env(settings)
    _clients = _build_clients(settings)
    return _clients


def get_infra_clients() -> InfraClients:
    """Return the cached infrastructure clients, initializing them on first call."""
    if _clients is None:
        return initialize_infra_clients()
    return _clients
