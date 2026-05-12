from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import gettempdir

from fastapi import UploadFile

from app.config import get_settings
from app.repositories.firestore.job_repo import create_job
from app.repositories.firestore.question_repo import (
    create_question,
    list_questions_by_workspace,
)
from app.repositories.firestore.workspace_repo import get_workspace
from app.repositories.storage.gcs_repo import upload_bytes
from app.services.job_service import enqueue_generation_job
from app.utils.errors import AppError

_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _now_iso() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _to_question_item_model(entity: dict) -> dict:
    """Reshape a Firestore question document into the API response shape."""
    return {
        "questionItemId": entity["question_id"],
        "label": entity["label"],
        "inputType": entity["input_type"],
        "status": entity["status"],
        "createdAt": entity["created_at"],
    }


def _to_generation_job_model(entity: dict) -> dict:
    """Reshape a Firestore job document into the API job response shape."""
    return {
        "jobId": entity["job_id"],
        "workspaceId": entity["workspace_id"],
        "questionItemId": entity["question_id"],
        "stage": entity["stage"],
        "status": entity["status"],
        "attempt": entity["attempt"],
        "maxAttempts": entity["max_attempts"],
        "message": entity["message"],
        "error": entity.get("error"),
        "createdAt": entity["created_at"],
        "updatedAt": entity["updated_at"],
        "finishedAt": entity.get("finished_at"),
    }


def list_workspace_questions_service(workspace_id: str) -> list[dict]:
    """Verify the workspace exists and return its questions formatted for the API."""
    if not get_workspace(workspace_id):
        raise AppError(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found.",
            details={"workspaceId": workspace_id},
            status_code=404,
        )
    return [_to_question_item_model(item) for item in list_questions_by_workspace(workspace_id)]


def _validate_input(text: str | None, image: UploadFile | None) -> None:
    """Raise an error if the request provides both inputs or neither."""
    has_text = bool(text and text.strip())
    has_image = image is not None and bool(image.filename)
    if has_text == has_image:
        raise AppError(
            code="INVALID_QUESTION_INPUT",
            message="Provide exactly one input: text or image.",
            status_code=422,
        )


def _persist_local_image(question_id: str, ext: str, data: bytes) -> str:
    """Save raw image bytes to a local temp directory and return the file path."""
    base = Path(gettempdir()) / "physicsanimator" / "question_sources"
    base.mkdir(parents=True, exist_ok=True)
    local_path = base / f"{question_id}{ext}"
    local_path.write_bytes(data)
    return str(local_path)


async def create_question_service(workspace_id: str, text: str | None, image: UploadFile | None) -> dict:
    """Validate input, persist the question and source asset, create a job record, and enqueue generation."""
    settings = get_settings()
    workspace = get_workspace(workspace_id)
    if not workspace:
        raise AppError(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found.",
            details={"workspaceId": workspace_id},
            status_code=404,
        )

    _validate_input(text, image)

    question_id = str(uuid.uuid4())
    now = _now_iso()
    source_text: str | None = None
    source_image_url: str | None = None
    source_local_path: str | None = None
    input_type: str
    label: str

    if image is not None and image.filename:
        ext = Path(image.filename).suffix.lower()
        if ext not in _IMAGE_EXTENSIONS:
            raise AppError(
                code="UNSUPPORTED_IMAGE_TYPE",
                message="Unsupported image type.",
                details={"supported": sorted(_IMAGE_EXTENSIONS)},
                status_code=422,
            )
        raw = await image.read()
        if not raw:
            raise AppError(
                code="EMPTY_IMAGE_FILE",
                message="Uploaded image is empty.",
                status_code=422,
            )
        local_path = _persist_local_image(question_id, ext, raw)
        object_name = f"questions/{workspace_id}/{question_id}/source{ext}"
        uploaded = upload_bytes(object_name, raw, content_type=_MIME_MAP[ext])
        input_type = "image"
        label = image.filename.strip() or "Uploaded image question"
        source_image_url = uploaded["public_url"]
        source_local_path = local_path
    else:
        clean_text = (text or "").strip()
        compact = " ".join(clean_text.split())
        label = compact if len(compact) <= 96 else f"{compact[:96]}..."
        input_type = "text"
        source_text = clean_text

    question_payload = {
        "workspace_id": workspace_id,
        "label": label,
        "input_type": input_type,
        "status": "generated",
        "source_text": source_text,
        "source_image_url": source_image_url,
        "source_local_path": source_local_path,
        "form_id": workspace["form_id"],
        "created_at": now,
        "updated_at": now,
    }
    create_question(question_id, question_payload)

    job_id = str(uuid.uuid4())
    job_payload = {
        "workspace_id": workspace_id,
        "question_id": question_id,
        "status": "queued",
        "stage": "reading_question",
        "attempt": 1,
        "max_attempts": settings.pipeline_max_retries,
        "message": "Job queued.",
        "error": None,
        "created_at": now,
        "updated_at": now,
        "finished_at": None,
    }
    create_job(job_id, job_payload)

    enqueue_generation_job(job_id)

    question_payload["question_id"] = question_id
    job_payload["job_id"] = job_id

    return {
        "question": _to_question_item_model(question_payload),
        "job": _to_generation_job_model(job_payload),
    }
