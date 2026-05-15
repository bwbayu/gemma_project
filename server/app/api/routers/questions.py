"""Question endpoints: submit a question (text or image), fetch its review, and approve/regenerate/discard it."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.schemas.question import CreateQuestionResponse, QuestionItemModel
from app.api.schemas.review import QuestionDecisionResponse, ReviewResultModel
from app.services.review_service import (
    approve_question_service,
    discard_question_service,
    get_review_service,
    regenerate_question_service,
)
from app.services.question_service import create_question_service, list_workspace_questions_service

router = APIRouter(tags=["questions"])


@router.get("/workspaces/{workspace_id}/questions", response_model=list[QuestionItemModel])
def list_workspace_questions(workspace_id: str):
    """Return all questions belonging to the given workspace, ordered newest first."""
    return list_workspace_questions_service(workspace_id)


@router.post(
    "/workspaces/{workspace_id}/questions",
    response_model=CreateQuestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question(
    workspace_id: str,
    text: str | None = Form(default=None),
    image: UploadFile | None = File(default=None),
):
    """Accept a text or image input, persist a question record, and enqueue a generation job."""
    return await create_question_service(workspace_id, text, image)


@router.get("/questions/{question_id}/review", response_model=ReviewResultModel)
def get_question_review(question_id: str):
    """Return the review payload for a question once generation has completed."""
    return get_review_service(question_id)


@router.post("/questions/{question_id}/approve", response_model=QuestionDecisionResponse)
def approve_question(question_id: str):
    """Append the generated animation to the Google Form and mark the question as added."""
    return approve_question_service(question_id)


@router.post("/questions/{question_id}/regenerate", response_model=QuestionDecisionResponse)
def regenerate_question(question_id: str):
    """Reset the question status and enqueue a new generation job."""
    return regenerate_question_service(question_id)


@router.post("/questions/{question_id}/discard", response_model=QuestionDecisionResponse)
def discard_question(question_id: str):
    """Mark the question as discarded so it is excluded from the form."""
    return discard_question_service(question_id)
