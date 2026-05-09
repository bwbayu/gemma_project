from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AppError(Exception):
    code: str
    message: str
    details: Any = None
    status_code: int = 400

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
