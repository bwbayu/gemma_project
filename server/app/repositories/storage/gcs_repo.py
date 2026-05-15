from __future__ import annotations

from urllib.parse import quote

from app.dependencies import get_infra_clients


def upload_bytes(object_name: str, data: bytes, content_type: str) -> dict:
    """Upload raw bytes to GCS and return the bucket name, object name, GS URI, and public URL."""
    bucket = get_infra_clients().gcs_bucket
    blob = bucket.blob(object_name)
    blob.upload_from_string(data, content_type=content_type)
    encoded_name = quote(object_name, safe="/")
    public_url = f"https://storage.googleapis.com/{bucket.name}/{encoded_name}"
    return {
        "bucket": bucket.name,
        "object_name": object_name,
        "gs_uri": f"gs://{bucket.name}/{object_name}",
        "public_url": public_url,
    }


def upload_file(object_name: str, local_path: str, content_type: str = "application/octet-stream") -> dict:
    """Upload a local file to GCS and return the bucket name, object name, GS URI, and public URL."""
    bucket = get_infra_clients().gcs_bucket
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_path, content_type=content_type)
    encoded_name = quote(object_name, safe="/")
    public_url = f"https://storage.googleapis.com/{bucket.name}/{encoded_name}"
    return {
        "bucket": bucket.name,
        "object_name": object_name,
        "gs_uri": f"gs://{bucket.name}/{object_name}",
        "public_url": public_url,
    }


def download_file(object_name: str, local_path: str) -> None:
    """Download a GCS object to a local path. Raises on error."""
    bucket = get_infra_clients().gcs_bucket
    blob = bucket.blob(object_name)
    blob.download_to_filename(local_path)
