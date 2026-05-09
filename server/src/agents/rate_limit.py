"""Shared Gemini retry configuration for per-agent 429 handling."""

import logging
import os
from typing import Optional

from google.genai import types

# Fixed 429 backoff (seconds). Use env var to tune without code changes.
RATE_LIMIT_SLEEP_SECONDS = float(os.getenv("GENAI_429_SLEEP_SECONDS", "65"))
RATE_LIMIT_RETRY_ATTEMPTS = int(os.getenv("GENAI_429_RETRY_ATTEMPTS", "15"))

# Retry profile tuned for transient quota spikes.
_HTTP_RETRY_OPTIONS = types.HttpRetryOptions(
    attempts=RATE_LIMIT_RETRY_ATTEMPTS,
    # Constant retry delay:
    # initial == max, exp_base=1, jitter=0
    initial_delay=1.0, # 1.0 | RATE_LIMIT_SLEEP_SECONDS
    max_delay=RATE_LIMIT_SLEEP_SECONDS,
    exp_base=2.0, # 2.0 | 1.0
    jitter=1.0, # 1.0 | 0.0
    http_status_codes=[429],
)

_GENAI_RETRY_LOGGER = "google_genai._api_client"


class _PrintHandler(logging.Handler):
    """Logging handler that forwards retry messages to print()."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            print(msg)
        except Exception:
            self.handleError(record)


def build_generate_content_config(
    *,
    thinking_level: Optional[str] = None,
) -> types.GenerateContentConfig:
    """Create GenerateContentConfig with HTTP retry options for rate limits."""
    kwargs = {
        "http_options": types.HttpOptions(retry_options=_HTTP_RETRY_OPTIONS),
    }
    if thinking_level:
        kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=thinking_level)
    return types.GenerateContentConfig(**kwargs)


def enable_rate_limit_retry_logging(level: int = logging.INFO) -> None:
    """Enable print-only logs for genai retry backoff attempts (including 429)."""
    logger = logging.getLogger(_GENAI_RETRY_LOGGER)
    logger.setLevel(level)
    logger.propagate = False

    # Keep this logger print-only to avoid duplicate Rich/standard logging lines.
    logger.handlers = []

    handler = _PrintHandler()
    handler.name = "genai_retry_console"
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("  [GENAI RETRY] %(message)s"))
    logger.addHandler(handler)


def get_fixed_429_sleep_seconds() -> int:
    """Fixed orchestration fallback sleep in whole seconds."""
    return max(1, int(RATE_LIMIT_SLEEP_SECONDS))
