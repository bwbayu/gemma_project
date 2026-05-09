from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.repositories.firestore.job_repo import create_job, get_latest_job_by_question
from app.repositories.firestore.question_repo import get_question, update_question
from app.repositories.firestore.workspace_repo import get_workspace
from app.services.job_service import enqueue_generation_job
from app.utils.errors import AppError
from pathlib import Path
import os
from urllib.parse import urlparse


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_question_item_model(entity: dict) -> dict:
    return {
        "questionItemId": entity["question_id"],
        "label": entity["label"],
        "inputType": entity["input_type"],
        "status": entity["status"],
        "createdAt": entity["created_at"],
    }


def _to_generation_job_model(entity: dict) -> dict:
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
    return {
        "workspaceId": workspace["workspace_id"],
        "formEditUrl": workspace["form_edit_url"],
        "formResponderUrl": workspace["form_responder_url"],
    }


def _to_review_model(review: dict) -> dict:
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
            "local_video_path": validation.get("local_video_path", "")
        },
        "append": {
            "status": append.get("status", "not_started"),
            "formId": append.get("form_id", ""),
            "errorMessage": append.get("error_message"),
        },
    }


def _get_question_or_404(question_id: str) -> dict:
    question = get_question(question_id)
    if not question:
        raise AppError(
            code="QUESTION_NOT_FOUND",
            message="Question not found.",
            details={"questionId": question_id},
            status_code=404,
        )
    return question

def _get_filename(url: str) -> str:
    ext = ".gif"
    path_obj = Path(urlparse(url).path)
    filename = path_obj.with_suffix(ext).name
    return filename

def _append_question_to_form(question: dict, review_result: dict) -> None:
    from src.tools.form_tools import get_form, add_image_question, upload_image_to_drive
    from src.utils.mp42gif import mp4_to_gif_best_quality

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
    
    # convert video mp4 to Gif
    _PROJECT_ROOT = str(Path(__file__).parent.parent.parent.resolve())
    output_dir = os.path.join(_PROJECT_ROOT, "output/gif")
    os.makedirs(output_dir, exist_ok=True)
    gif_output_path = os.path.join(output_dir, _get_filename(review_result["validation"]["local_video_path"]))

    # print(f"file_path {gif_output_path}")
    mp4_to_gif_best_quality(review_result["validation"]["local_video_path"], gif_output_path)

    # upload Gif to drive
    drive_result = upload_image_to_drive(gif_output_path)

    # add animation to existing form
    add_image_question(form_id=form_id, 
                       question_title="Watch the animation to answer the question. Provide a step-by-step solution", 
                       drive_file_id=drive_result.get("driveFileId", ""),
                       alt_text="Physics animation",
                       required=True)

    # source = review_result.get("source", {})
    # result = review_result.get("result", {})
    # input_type = source.get("input_type", "text")
    # stem = source.get("text") if input_type == "text" else question.get("label")
    # stem = (stem or question.get("label") or "Physics question").strip()
    # video_url = result.get("video_url")

    # prompt = f"{stem}\n\nObserve the animation before solving."
    # if video_url:
    #     prompt = f"{prompt}\nAnimation: {video_url}"

    # form = get_form(form_id)
    # items = form.get("items", []) if isinstance(form, dict) else []
    # next_index = len(items)

    # add_text_question(
    #     form_id=form_id,
    #     question_title=prompt[:500],
    #     required=True,
    #     paragraph=False,
    #     index=next_index,
    # )
    # add_text_question(
    #     form_id=form_id,
    #     question_title="Show your working / solution steps",
    #     required=False,
    #     paragraph=True,
    #     index=next_index + 1,
    # )


def get_review_service(question_id: str) -> dict:
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
            "gif_url": question.get("result_gif_url"),
            "thumbnail_url": question.get("result_thumbnail_url"),
        },
        "summary": {
            "scenario": "",
            "given_information": [],
            "student_task": "",
        },
        "validation": {"verdict": "FAIL", "summary": "Question discarded by teacher."},
        "append": {"status": "not_started", "form_id": question.get("form_id")},
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
                "gif_url": updated.get("result_gif_url"),
                "thumbnail_url": updated.get("result_thumbnail_url"),
            },
            "summary": {
                "scenario": "",
                "given_information": [],
                "student_task": "",
            },
            "validation": {"verdict": "FAIL", "summary": "Regeneration in progress."},
            "append": {"status": "not_started", "form_id": updated.get("form_id")},
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
