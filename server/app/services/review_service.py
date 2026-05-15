from __future__ import annotations

import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.config import get_settings
from app.repositories.firestore.job_repo import create_job, get_latest_job_by_question
from app.repositories.firestore.question_repo import get_question, update_question
from app.repositories.firestore.workspace_repo import get_workspace
from app.repositories.storage.gcs_repo import download_file, upload_file
from app.services.job_service import enqueue_generation_job
from app.utils.errors import AppError

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _to_question_item_model(entity: dict) -> dict:
    """Reshape a Firestore question document into the API question item shape."""
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


def _to_workspace_links_model(workspace: dict) -> dict:
    """Extract form edit/responder URLs from a workspace document."""
    return {
        "workspaceId": workspace["workspace_id"],
        "formEditUrl": workspace["form_edit_url"],
        "formResponderUrl": workspace["form_responder_url"],
    }


def _to_review_model(review: dict) -> dict:
    """Reshape the nested review dict stored in Firestore into the API response schema."""
    source = review.get("source", {})
    result = review.get("result", {})
    summary = review.get("summary", {})
    validation = review.get("validation", {})
    append = review.get("append", {})
    return {
        "questionItemId": review.get("question_item_id"),
        "source": {
            "inputType": source.get("input_type"),
            "imageUrl": source.get("image_url"),
            "text": source.get("text"),
        },
        "result": {
            "videoUrl": result.get("video_url"),
            "gifUrl": result.get("gif_url"),
            "gifDriveFileId": result.get("gif_drive_file_id"),
            "thumbnailUrl": result.get("thumbnail_url"),
        },
        "summary": {
            "scenario": summary.get("scenario", ""),
            "givenInformation": summary.get("given_information", []),
            "studentTask": summary.get("student_task", ""),
        },
        "validation": {
            "verdict": validation.get("verdict", "FAIL"),
            "summary": validation.get("summary", ""),
        },
        "append": {
            "status": append.get("status", "not_started"),
            "formId": append.get("form_id", ""),
            "errorMessage": append.get("error_message"),
        },
        "gifStatus": review.get("gif_status"),
    }


def _get_question_or_404(question_id: str) -> dict:
    """Fetch a question document by ID, raising a 404 AppError if it does not exist."""
    question = get_question(question_id)
    if not question:
        raise AppError(
            code="QUESTION_NOT_FOUND",
            message="Question not found.",
            details={"questionId": question_id},
            status_code=404,
        )
    return question

def _gcs_object_from_url(public_url: str | None) -> str | None:
    """Fallback parser: derive a GCS object path from a public storage URL."""
    if not public_url:
        return None
    path = urlparse(public_url).path.lstrip("/")
    if "/" not in path:
        return None
    return path.split("/", 1)[1]


def _retry_gif_pipeline(question: dict, review_result: dict) -> str:
    """Download the MP4 from GCS, convert to GIF, upload to GCS + Drive, persist new IDs to Firestore, return drive file id."""
    from src.tools.form_tools import upload_image_to_drive
    from src.utils.mp42gif import mp4_to_gif_best_quality

    result = review_result.get("result", {}) or {}
    video_object = result.get("video_gcs_object") or _gcs_object_from_url(result.get("video_url"))
    if not video_object:
        raise AppError(
            code="REVIEW_MEDIA_UNAVAILABLE",
            message="No GIF on Drive and no MP4 available to convert.",
            details={"questionId": question["question_id"]},
            status_code=409,
        )

    workspace_id = question["workspace_id"]
    question_id = question["question_id"]

    base_dir = os.path.join(tempfile.gettempdir(), "physicsanimator")
    mp4_dir = os.path.join(base_dir, "mp4")
    gif_dir = os.path.join(base_dir, "gif")
    os.makedirs(mp4_dir, exist_ok=True)
    os.makedirs(gif_dir, exist_ok=True)

    mp4_local = os.path.join(mp4_dir, f"{question_id}.mp4")
    gif_local = os.path.join(gif_dir, f"{question_id}_retry.gif")

    download_file(video_object, mp4_local)
    mp4_to_gif_best_quality(mp4_local, gif_local)

    gif_object_name = f"questions/{workspace_id}/{question_id}/result.gif"
    gif_uploaded = upload_file(gif_object_name, gif_local, content_type="image/gif")
    drive_result = upload_image_to_drive(gif_local)
    drive_file_id = drive_result.get("driveFileId")
    if not drive_file_id:
        raise AppError(
            code="DRIVE_UPLOAD_FAILED",
            message="Drive upload did not return a file id.",
            status_code=502,
        )

    result["gif_url"] = gif_uploaded["public_url"]
    result["gif_gcs_object"] = gif_uploaded["object_name"]
    result["gif_drive_file_id"] = drive_file_id
    review_result["result"] = result
    review_result["gif_status"] = "done"

    update_question(
        question_id,
        {
            "review_result": review_result,
            "result_gif_url": gif_uploaded["public_url"],
            "updated_at": _now_iso(),
        },
    )
    return drive_file_id


def _append_question_to_form(question: dict, review_result: dict) -> None:
    """Append an image question to the Google Form, using the pre-uploaded Drive GIF or retrying conversion if missing."""
    from src.tools.form_tools import add_image_question

    form_id = question.get("form_id")
    if not form_id:
        raise AppError(
            code="FORM_ID_MISSING",
            message="Question has no target form_id.",
            status_code=400,
        )
    if str(form_id).startswith("mock_form_"):
        raise AppError(
            code="MOCK_FORM_NOT_APPENDABLE",
            message="Workspace form_id is mock and cannot be appended.",
            details={"formId": form_id},
            status_code=400,
        )

    result = review_result.get("result", {}) or {}
    gif_status = review_result.get("gif_status")
    drive_file_id = result.get("gif_drive_file_id")
    if gif_status != "done" or not drive_file_id:
        logger.info(
            "GIF not ready for question %s (gif_status=%s, has_drive_id=%s) — running retry pipeline",
            question["question_id"],
            gif_status,
            bool(drive_file_id),
        )
        drive_file_id = _retry_gif_pipeline(question, review_result)

    add_image_question(
        form_id=form_id,
        question_title="Watch the animation to answer the question. Provide a step-by-step solution",
        drive_file_id=drive_file_id,
        alt_text="Physics animation",
        required=True,
    )


def get_review_service(question_id: str) -> dict:
    """Return the review payload for a question, raising 404 if generation has not completed yet."""
    question = _get_question_or_404(question_id)
    review_result = question.get("review_result")
    if not review_result:
        raise AppError(
            code="REVIEW_NOT_READY",
            message="Review result is not ready yet.",
            details={"questionId": question_id},
            status_code=404,
        )
    return _to_review_model(review_result)


def approve_question_service(question_id: str) -> dict:
    """Append the question's animation to the linked Google Form and update the question status."""
    question = _get_question_or_404(question_id)
    workspace = get_workspace(question["workspace_id"])
    if not workspace:
        raise AppError(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found for question.",
            details={"workspaceId": question["workspace_id"]},
            status_code=404,
        )
    review_result = question.get("review_result")
    if not review_result:
        raise AppError(
            code="REVIEW_NOT_READY",
            message="Cannot approve before review is available.",
            details={"questionId": question_id},
            status_code=400,
        )
    if question.get("status") == "discarded":
        raise AppError(
            code="QUESTION_DISCARDED",
            message="Discarded question cannot be approved.",
            status_code=400,
        )

    review_result.setdefault("append", {})
    review_result["append"]["status"] = "in_progress"
    review_result["append"]["error_message"] = None
    update_question(
        question_id,
        {
            "review_result": review_result,
            "updated_at": _now_iso(),
        },
    )

    try:
        _append_question_to_form(question, review_result)
        append_status = "added"
        append_error = None
        question_status = "added"
    except Exception as exc:
        append_status = "error"
        append_error = str(exc)[:500]
        question_status = "generated"

    review_result.setdefault("append", {})
    review_result["append"]["status"] = append_status
    review_result["append"]["error_message"] = append_error

    update_question(
        question_id,
        {
            "status": question_status,
            "review_result": review_result,
            "updated_at": _now_iso(),
        },
    )
    updated = _get_question_or_404(question_id)
    final_job = get_latest_job_by_question(question_id)
    return {
        "question": _to_question_item_model(updated),
        "review": _to_review_model(updated["review_result"]),
        "formLinks": _to_workspace_links_model(workspace),
        "job": _to_generation_job_model(final_job) if final_job else None,
    }


def discard_question_service(question_id: str) -> dict:
    """Mark the question as discarded and reset its append status."""
    question = _get_question_or_404(question_id)
    workspace = get_workspace(question["workspace_id"])
    if not workspace:
        raise AppError(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found for question.",
            details={"workspaceId": question["workspace_id"]},
            status_code=404,
        )
    review_result = question.get("review_result") or {
        "question_item_id": question["question_id"],
        "source": {
            "input_type": question.get("input_type"),
            "image_url": question.get("source_image_url"),
            "text": question.get("source_text"),
        },
        "result": {
            "video_url": question.get("result_video_url"),
            "video_gcs_object": None,
            "gif_url": question.get("result_gif_url"),
            "gif_gcs_object": None,
            "gif_drive_file_id": None,
            "thumbnail_url": question.get("result_thumbnail_url"),
        },
        "summary": {
            "scenario": "",
            "given_information": [],
            "student_task": "",
        },
        "validation": {"verdict": "FAIL", "summary": "Question discarded by teacher."},
        "append": {"status": "not_started", "form_id": question.get("form_id")},
        "gif_status": "pending",
    }
    review_result.setdefault("append", {})
    review_result["append"]["status"] = "not_started"

    update_question(
        question_id,
        {
            "status": "discarded",
            "review_result": review_result,
            "updated_at": _now_iso(),
        },
    )
    updated = _get_question_or_404(question_id)
    return {
        "question": _to_question_item_model(updated),
        "review": _to_review_model(updated["review_result"]),
        "formLinks": _to_workspace_links_model(workspace),
        "job": None,
    }


def regenerate_question_service(question_id: str) -> dict:
    """Reset the question to a pending state and queue a new generation job."""
    settings = get_settings()
    question = _get_question_or_404(question_id)
    workspace = get_workspace(question["workspace_id"])
    if not workspace:
        raise AppError(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found for question.",
            details={"workspaceId": question["workspace_id"]},
            status_code=404,
        )
    now = _now_iso()
    previous_attempt = int(question.get("regeneration_count", 0))
    new_attempt = previous_attempt + 1

    update_question(
        question_id,
        {
            "status": "generated",
            "regeneration_count": new_attempt,
            "updated_at": now,
        },
    )

    job_id = str(uuid.uuid4())
    job_payload = {
        "workspace_id": question["workspace_id"],
        "question_id": question_id,
        "status": "queued",
        "stage": "reading_question",
        "attempt": new_attempt,
        "max_attempts": settings.pipeline_max_retries,
        "message": "Regeneration job queued.",
        "error": None,
        "created_at": now,
        "updated_at": now,
        "finished_at": None,
    }
    create_job(job_id, job_payload)
    enqueue_generation_job(job_id)

    updated = _get_question_or_404(question_id)
    review_result = updated.get("review_result")
    if not review_result:
        review_result = {
            "question_item_id": question_id,
            "source": {
                "input_type": updated.get("input_type"),
                "image_url": updated.get("source_image_url"),
                "text": updated.get("source_text"),
            },
            "result": {
                "video_url": updated.get("result_video_url"),
                "video_gcs_object": None,
                "gif_url": updated.get("result_gif_url"),
                "gif_gcs_object": None,
                "gif_drive_file_id": None,
                "thumbnail_url": updated.get("result_thumbnail_url"),
            },
            "summary": {
                "scenario": "",
                "given_information": [],
                "student_task": "",
            },
            "validation": {"verdict": "FAIL", "summary": "Regeneration in progress."},
            "append": {"status": "not_started", "form_id": updated.get("form_id")},
            "gif_status": "pending",
        }
    else:
        review_result.setdefault("append", {})
        review_result["append"]["status"] = "not_started"
        review_result["append"]["error_message"] = None
        update_question(
            question_id,
            {
                "review_result": review_result,
                "updated_at": _now_iso(),
            },
        )

    job_payload["job_id"] = job_id
    return {
        "question": _to_question_item_model(updated),
        "review": _to_review_model(review_result),
        "formLinks": _to_workspace_links_model(workspace),
        "job": _to_generation_job_model(job_payload),
    }
