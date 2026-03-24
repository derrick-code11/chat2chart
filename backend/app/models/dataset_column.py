from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.dataset import Dataset


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"
    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="dataset_columns_ordinal_non_negative"),
        CheckConstraint(
            "inferred_type IN ('text', 'number', 'date', 'boolean', 'unknown')",
            name="dataset_columns_inferred_type_check",
        ),
        UniqueConstraint(
            "dataset_id",
            "ordinal",
            name="dataset_columns_dataset_id_ordinal_key",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    inferred_type: Mapped[str] = mapped_column(Text, nullable=False)
    sample_values: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    dataset: Mapped["Dataset"] = relationship(back_populates="columns")
