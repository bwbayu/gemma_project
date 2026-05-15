from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.api.schemas.job import GenerationJobModel


class _ApiModel(BaseModel):
    model_config = {
        "populate_by_name": True,
    }


QuestionStatus = Literal["generating", "generated", "added", "failed", "discarded"]
QuestionInputType = Literal["image", "text"]


class QuestionItemModel(_ApiModel):
    question_item_id: str = Field(alias="questionItemId")
    label: str
    input_type: QuestionInputType = Field(alias="inputType")
    status: QuestionStatus
    created_at: str = Field(alias="createdAt")
    last_job_id: str | None = Field(default=None, alias="lastJobId")


class CreateQuestionResponse(_ApiModel):
    question: QuestionItemModel
    job: GenerationJobModel
