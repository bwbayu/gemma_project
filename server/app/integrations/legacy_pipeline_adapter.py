"""Adapter that calls into `src.app` and normalizes its loose tuple return into a `PipelineRunResult`."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.config import get_settings


Verdict = Literal["PASS", "FAIL"]


@dataclass
class PipelineRunResult:
    verdict: Verdict
    summary: str
    video_local_path: str | None = None
    form_url: str | None = None


async def run_legacy_pipeline(question_arg: str) -> PipelineRunResult:
    """
    Run generation-only legacy pipeline (Coder -> Validator).
    """
    from src.app import run_generation_pipeline

    settings = get_settings()
    raw_result = await run_generation_pipeline(
        question_arg=question_arg,
        max_retries=settings.pipeline_max_retries,
        timeout=settings.pipeline_timeout_seconds,
    )

    video_path: str | None = None
    verdict: Verdict = "FAIL"
    feedback = ""

    # `src.app.run_generation_pipeline` returns a plain `(video_path, verdict, feedback)`
    # tuple with no schema, so we defensively check the type/length here rather than
    # destructuring directly.
    if isinstance(raw_result, tuple):
        video_path = raw_result[0] if len(raw_result) > 0 else None
        verdict = raw_result[1] if len(raw_result) > 1 else "FAIL"
        feedback = raw_result[2] if len(raw_result) > 2 else ""

    if video_path:
        normalized = str(Path(video_path))
        return PipelineRunResult(
            verdict=verdict,
            summary=feedback or "Legacy generation pipeline completed.",
            video_local_path=normalized,
        )
    verdict = "FAIL"
    return PipelineRunResult(
        verdict=verdict,
        summary=feedback or "Legacy generation pipeline did not produce a valid video.",
        video_local_path=None,
    )