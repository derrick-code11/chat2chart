from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ConversationDataset


async def is_dataset_attached_to_conversation(
    session: AsyncSession,
    conversation_id: uuid.UUID,
    dataset_id: uuid.UUID,
) -> bool:
    result = await session.execute(
        select(ConversationDataset.id).where(
            ConversationDataset.conversation_id == conversation_id,
            ConversationDataset.dataset_id == dataset_id,
        )
    )
    return result.scalar_one_or_none() is not None
