"""Schemas for the review-and-decide flow (review payload + approve/regenerate/discard response)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.job import GenerationJobModel
from app.api.schemas.question import QuestionItemModel


class _ApiModel(BaseModel):
    """Base model that lets handlers populate fields by either snake_case or camelCase alias."""

    model_config = {
        "populate_by_name": True,
    }


class ReviewSourceModel(_ApiModel):
    """The original input the student-facing question was built from (image URL or raw text)."""

    input_type: Literal["image", "text"] = Field(alias="inputType")
    image_url: str | None = Field(default=None, alias="imageUrl")
    text: str | None = None


class ReviewResultAssetsModel(_ApiModel):
    """URLs/IDs for the generated media (video on GCS, GIF on Drive, thumbnail)."""

    video_url: str | None = Field(default=None, alias="videoUrl")
    gif_url: str | None = Field(default=None, alias="gifUrl")
    gif_drive_file_id: str | None = Field(default=None, alias="gifDriveFileId")
    thumbnail_url: str | None = Field(default=None, alias="thumbnailUrl")


class ReviewSummaryModel(_ApiModel):
    """LLM-produced human summary of the scenario for the teacher to skim before approving."""

    scenario: str
    given_information: list[str] = Field(alias="givenInformation")
    student_task: str = Field(alias="studentTask")


class ReviewValidationModel(_ApiModel):
    """Verdict from the validator agent (PASS/FAIL plus a short rationale)."""

    verdict: Literal["PASS", "FAIL"]
    summary: str


class ReviewAppendModel(_ApiModel):
    """State of the Google Form append step (separate from generation success)."""

    status: Literal["not_started", "in_progress", "added", "error"]
    form_id: str = Field(alias="formId")
    error_message: str | None = Field(default=None, alias="errorMessage")


class ReviewResultModel(_ApiModel):
    """Everything the review UI needs to render one question: source, assets, summary, verdict, append state."""

    question_item_id: str = Field(alias="questionItemId")
    source: ReviewSourceModel
    result: ReviewResultAssetsModel
    summary: ReviewSummaryModel
    validation: ReviewValidationModel
    append: ReviewAppendModel
    gif_status: Literal["pending", "done", "failed"] | None = Field(default=None, alias="gifStatus")


class FormLinksModel(_ApiModel):
    """Form share links surfaced after a successful approve."""

    workspace_id: str = Field(alias="workspaceId")
    form_edit_url: str = Field(alias="formEditUrl")
    form_responder_url: str = Field(alias="formResponderUrl")


class QuestionDecisionResponse(_ApiModel):
    """Response payload for approve/regenerate/discard (regenerate also returns a fresh `job`)."""

    question: QuestionItemModel
    review: ReviewResultModel
    form_links: FormLinksModel = Field(alias="formLinks")
    job: GenerationJobModel | None = None
