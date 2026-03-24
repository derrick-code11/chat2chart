from typing import Any

VALIDATION_ERROR = "VALIDATION_ERROR"
UNAUTHORIZED = "UNAUTHORIZED"
FORBIDDEN = "FORBIDDEN"
NOT_FOUND = "NOT_FOUND"
DATASET_NOT_READY = "DATASET_NOT_READY"
CHART_GENERATION_FAILED = "CHART_GENERATION_FAILED"
LLM_UPSTREAM = "LLM_UPSTREAM"
CONFLICT = "CONFLICT"
INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
