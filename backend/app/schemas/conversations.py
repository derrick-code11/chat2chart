from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    dataset_ids: list[uuid.UUID] | None = None
    current_dataset_id: uuid.UUID | None = None


class ConversationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    current_dataset_id: uuid.UUID | None = None


class AttachDatasetBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: uuid.UUID
