from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppError(Exception):
    """Structured application error carrying an error code, human-readable message, optional details, and HTTP status."""

    code: str
    message: str
    details: Any = None
    status_code: int = 400

    def __str__(self) -> str:
        """Return a compact string representation of the error for logging."""
        return f"{self.code}: {self.message}"
