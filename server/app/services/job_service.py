from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from app.repositories.firestore.job_repo import get_job, update_job
from app.repositories.firestore.question_repo import get_question, update_question
from app.repositories.storage.gcs_repo import upload_file
from app.services.pipeline_service import run_pipeline_for_question
from app.utils.errors import AppError

_JOB_TASKS: set[asyncio.Task] = set()


def _now_iso() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _to_job_model(entity: dict) -> dict:
    """Reshape a Firestore job document into the API job response shape."""
    return {
        "jobId": entity["job_id"],
        "workspaceId": entity["workspace_id"],
        "questionItemId": entity["question_id"],
        "stage": entity["stage"],
        "status": entity["status"],
        "attempt": entity.get("attempt", 1),
        "maxAttempts": entity.get("max_attempts", 1),
        "message": entity.get("message", ""),
        "error": entity.get("error"),
        "createdAt": entity["created_at"],
        "updatedAt": entity["updated_at"],
        "finishedAt": entity.get("finished_at"),
    }


def get_job_service(job_id: str) -> dict:
    """Fetch a job by ID and return it formatted for the API, raising 404 if not found."""
    entity = get_job(job_id)
    if not entity:
        raise AppError(
            code="JOB_NOT_FOUND",
            message="Job not found.",
            details={"jobId": job_id},
            status_code=404,
        )
    return _to_job_model(entity)


def _patch_job(job_id: str, **fields) -> None:
    """Merge the given fields into a job document, automatically updating the timestamp."""
    payload = {"updated_at": _now_iso(), **fields}
    update_job(job_id, payload)


async def _run_generation_job(job_id: str) -> None:
    """Drive the full generation pipeline for a job, updating stage/status in Firestore along the way."""
    job = get_job(job_id)
    if not job:
        return

    question = get_question(job["question_id"])
    if not question:
        _patch_job(
            job_id,
            status="failed",
            stage="failed",
            message="Question record not found for this job.",
            error={"code": "QUESTION_NOT_FOUND"},
            finished_at=_now_iso(),
        )
        return

    try:
        _patch_job(job_id, status="running", stage="reading_question", message="Reading question source...")
        await asyncio.sleep(0.5)

        _patch_job(job_id, stage="generating_animation", message="Generating Manim animation...")
        await asyncio.sleep(0.5)

        run_result = await run_pipeline_for_question(question)

        _patch_job(job_id, stage="rendering_video", message="Preparing render assets...")
        await asyncio.sleep(0.5)

        review_payload = {
            "question_item_id": question["question_id"],
            "source": {
                "input_type": question["input_type"],
                "image_url": question.get("source_image_url"),
                "text": question.get("source_text"),
            },
            "result": {
                "video_url": question.get("result_video_url"),
                "gif_url": question.get("result_gif_url"),
                "thumbnail_url": question.get("result_thumbnail_url"),
            },
            "summary": {
                "scenario": "Physics scenario extracted from source input.",
                "given_information": ["Refer to source prompt and visual cues."],
                "student_task": "Observe animation and solve the target quantity.",
            },
            "validation": {
                "verdict": run_result.verdict,
                "summary": run_result.summary,
                "local_video_path": run_result.video_local_path
            },
            "append": {
                "status": "not_started",
                "form_id": question.get("form_id"),
            },
        }

        _patch_job(job_id, stage="validating_output", message="Validating generated output...")
        await asyncio.sleep(0.5)

        if run_result.video_local_path and os.path.exists(run_result.video_local_path):
            workspace_id = question["workspace_id"]
            question_id = question["question_id"]
            ext = Path(run_result.video_local_path).suffix.lower() or ".mp4"
            object_name = f"questions/{workspace_id}/{question_id}/result{ext}"
            uploaded = upload_file(object_name, run_result.video_local_path, content_type="video/mp4")
            review_payload["result"]["video_url"] = uploaded["public_url"]

        _patch_job(job_id, stage="preparing_assets", message="Preparing review assets...")
        await asyncio.sleep(0.5)

        question_status = "generated" if run_result.verdict == "PASS" else "failed"
        update_question(
            question["question_id"],
            {
                "status": question_status,
                "review_result": review_payload,
                "result_video_url": review_payload["result"]["video_url"],
                "updated_at": _now_iso(),
            },
        )

        _patch_job(
            job_id,
            status="completed",
            stage="awaiting_review",
            message="Generation completed. Awaiting teacher review.",
            finished_at=_now_iso(),
        )
    except Exception as exc:
        _patch_job(
            job_id,
            status="failed",
            stage="failed",
            message="Generation job failed.",
            error={"code": "JOB_EXECUTION_FAILED", "details": str(exc)[:400]},
            finished_at=_now_iso(),
        )
        update_question(
            question["question_id"],
            {
                "status": "failed",
                "updated_at": _now_iso(),
            },
        )


def enqueue_generation_job(job_id: str) -> None:
    """Schedule the generation pipeline as a background asyncio task."""
    task = asyncio.create_task(_run_generation_job(job_id))
    _JOB_TASKS.add(task)
    task.add_done_callback(_JOB_TASKS.discard)
