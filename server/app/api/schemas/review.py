from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.job import GenerationJobModel
from app.api.schemas.question import QuestionItemModel


class _ApiModel(BaseModel):
    model_config = {
        "populate_by_name": True,
    }


class ReviewSourceModel(_ApiModel):
    input_type: Literal["image", "text"] = Field(alias="inputType")
    image_url: str | None = Field(default=None, alias="imageUrl")
    text: str | None = None


class ReviewResultAssetsModel(_ApiModel):
    video_url: str | None = Field(default=None, alias="videoUrl")
    gif_url: str | None = Field(default=None, alias="gifUrl")
    gif_drive_file_id: str | None = Field(default=None, alias="gifDriveFileId")
    thumbnail_url: str | None = Field(default=None, alias="thumbnailUrl")


class ReviewSummaryModel(_ApiModel):
    scenario: str
    given_information: list[str] = Field(alias="givenInformation")
    student_task: str = Field(alias="studentTask")


class ReviewValidationModel(_ApiModel):
    verdict: Literal["PASS", "FAIL"]
    summary: str


class ReviewAppendModel(_ApiModel):
    status: Literal["not_started", "in_progress", "added", "error"]
    form_id: str = Field(alias="formId")
    error_message: str | None = Field(default=None, alias="errorMessage")


class ReviewResultModel(_ApiModel):
    question_item_id: str = Field(alias="questionItemId")
    source: ReviewSourceModel
    result: ReviewResultAssetsModel
    summary: ReviewSummaryModel
    validation: ReviewValidationModel
    append: ReviewAppendModel
    gif_status: Literal["pending", "done", "failed"] | None = Field(default=None, alias="gifStatus")


class FormLinksModel(_ApiModel):
    workspace_id: str = Field(alias="workspaceId")
    form_edit_url: str = Field(alias="formEditUrl")
    form_responder_url: str = Field(alias="formResponderUrl")


class QuestionDecisionResponse(_ApiModel):
    question: QuestionItemModel
    review: ReviewResultModel
    form_links: FormLinksModel = Field(alias="formLinks")
    job: GenerationJobModel | None = None
