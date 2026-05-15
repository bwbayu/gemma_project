"""Schemas for question records and the create-question response envelope."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.job import GenerationJobModel


class _ApiModel(BaseModel):
    """Base model that lets handlers populate fields by either snake_case or camelCase alias."""

    model_config = {
        "populate_by_name": True,
    }


QuestionStatus = Literal["generating", "generated", "added", "failed", "discarded"]
QuestionInputType = Literal["image", "text"]


class QuestionItemModel(_ApiModel):
    """One question record (a question can have multiple generation jobs across regenerations)."""

    question_item_id: str = Field(alias="questionItemId")
    label: str
    input_type: QuestionInputType = Field(alias="inputType")
    status: QuestionStatus
    created_at: str = Field(alias="createdAt")
    last_job_id: str | None = Field(default=None, alias="lastJobId")


class CreateQuestionResponse(_ApiModel):
    """Response returned when a question is submitted: the persisted question plus the kicked-off job."""

    question: QuestionItemModel
    job: GenerationJobModel
