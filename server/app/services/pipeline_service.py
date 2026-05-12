from __future__ import annotations

from app.config import get_settings
from app.integrations.legacy_pipeline_adapter import (
    PipelineRunResult,
    run_legacy_full_pipeline,
    run_legacy_pipeline,
    run_mock_pipeline,
)


async def run_pipeline_for_question(question_entity: dict) -> PipelineRunResult:
    """Dispatch the question to the correct pipeline mode (mock, legacy generation, or full legacy)."""
    settings = get_settings()
    mode = settings.pipeline_mode.strip().lower()

    input_type = question_entity.get("input_type")
    if input_type == "image":
        question_arg = question_entity.get("source_local_path", "")
    else:
        question_arg = question_entity.get("source_text", "")

    if mode == "legacy_full_fallback":
        return await run_legacy_full_pipeline(question_arg)
    if mode == "legacy_generation":
        return await run_legacy_pipeline(question_arg)
    if mode != "mock":
        # Safe fallback for unsupported mode values.
        return await run_legacy_pipeline(question_arg)
    return await run_mock_pipeline(question_entity.get("label", "question"))
