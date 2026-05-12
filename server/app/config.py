from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    api_prefix: str = "/api/v1"

    google_cloud_project: str = Field(alias="GOOGLE_CLOUD_PROJECT")
    google_application_credentials: str = Field(alias="GOOGLE_APPLICATION_CREDENTIALS")
    gcs_bucket_name: str = Field(alias="GCS_BUCKET_NAME")
    firebase_storage_bucket: str = Field(alias="FIREBASE_STORAGE_BUCKET")
    firestore_database_id: str = Field(default="physicsanimator-hackathon", alias="FIRESTORE_DATABASE_ID")
    pipeline_mode: str = Field(default="legacy_generation", alias="PIPELINE_MODE")
    pipeline_max_retries: int = Field(default=1, alias="PIPELINE_MAX_RETRIES")
    pipeline_timeout_seconds: int = Field(default=1200, alias="PIPELINE_TIMEOUT_SECONDS")


def get_settings() -> Settings:
    """Load and return application settings from environment variables or the .env file."""
    return Settings()
