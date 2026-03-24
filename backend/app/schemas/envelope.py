from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    details: dict[str, Any] = Field(default_factory=dict)


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: Any | None = None
    error: ErrorBody | None = None
    message: str | None = None


def success(data: Any | None = None, message: str | None = None) -> dict[str, Any]:
    return {"data": data, "error": None, "message": message}


def error_envelope(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "data": None,
        "error": {"code": code, "details": details or {}},
        "message": message,
    }
