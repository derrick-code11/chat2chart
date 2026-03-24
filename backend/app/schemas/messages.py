from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., min_length=1)
    dataset_id: uuid.UUID | None = None

    @field_validator("content")
    @classmethod
    def strip_content(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("content must not be empty")
        return s
