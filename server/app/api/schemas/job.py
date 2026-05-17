"""Schemas describing a generation job and its stage/status enums."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class _ApiModel(BaseModel):
    """Base model that lets handlers populate fields by either snake_case or camelCase alias."""

    model_config = {
        "populate_by_name": True,
    }


JobStage = Literal[
    "reading_question",
    "generating_animation",
    "rendering_video",
    "validating_output",
    "preparing_assets",
    "awaiting_review",
    "appending_to_form",
    "completed",
    "failed",
]

JobStatus = Literal["queued", "running", "completed", "failed"]


class GenerationJobModel(_ApiModel):
    """One generation job record as seen by the frontend (state machine: stage + status + attempt)."""

    job_id: str = Field(alias="jobId")
    workspace_id: str = Field(alias="workspaceId")
    question_item_id: str = Field(alias="questionItemId")
    stage: JobStage
    status: JobStatus
    attempt: int
    max_attempts: int = Field(alias="maxAttempts")
    message: str
    error: Any = None
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    finished_at: str | None = Field(default=None, alias="finishedAt")
