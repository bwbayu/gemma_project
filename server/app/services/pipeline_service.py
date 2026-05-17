"""Selects which legacy pipeline mode to run for a given question."""

from __future__ import annotations

from app.integrations.legacy_pipeline_adapter import (
    PipelineRunResult,
    run_legacy_pipeline,
)


async def run_pipeline_for_question(question_entity: dict) -> PipelineRunResult:
    """Dispatch the question to the correct pipeline mode (legacy generation or full legacy)."""

    input_type = question_entity.get("input_type")
    if input_type == "image":
        question_arg = question_entity.get("source_local_path", "")
    else:
        question_arg = question_entity.get("source_text", "")

    return await run_legacy_pipeline(question_arg)
