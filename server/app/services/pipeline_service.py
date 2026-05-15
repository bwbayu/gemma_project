"""Selects which legacy pipeline mode to run for a given question."""

from __future__ import annotations

from app.config import get_settings
from app.integrations.legacy_pipeline_adapter import (
    PipelineRunResult,
    run_legacy_full_pipeline,
    run_legacy_pipeline,
)


async def run_pipeline_for_question(question_entity: dict) -> PipelineRunResult:
    """Dispatch the question to the correct pipeline mode (legacy generation or full legacy)."""
    settings = get_settings()
    mode = settings.pipeline_mode.strip().lower()

    input_type = question_entity.get("input_type")
    if input_type == "image":
        question_arg = question_entity.get("source_local_path", "")
    else:
        question_arg = question_entity.get("source_text", "")

    # `legacy_full_fallback` runs the Form-publish step inside the ADK pipeline itself;
    # the default `legacy_generation` stops after validation and lets this server own
    # the form append (via review_service.approve_question_service).
    if mode == "legacy_full_fallback":
        return await run_legacy_full_pipeline(question_arg)
    return await run_legacy_pipeline(question_arg)
