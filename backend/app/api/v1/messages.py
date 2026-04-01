from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NOT_FOUND, VALIDATION_ERROR, AppError
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Conversation, Dataset, DatasetColumn, Message, User
from app.schemas.envelope import success
from app.schemas.messages import MessageCreate
from app.services.chart_llm import build_chart_spec_llm
from app.utils.conversation_datasets import is_dataset_attached_to_conversation
from app.utils.time import iso_z

router = APIRouter(prefix="/conversations/{conversation_id}/messages", tags=["Messages"])

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 100


def _encode_cursor(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _message_dict(m: Message) -> dict:
    return {
        "id": str(m.id),
        "conversation_id": str(m.conversation_id),
        "role": m.role,
        "content": m.content,
        "chart_spec": m.chart_spec,
        "dataset_id": str(m.dataset_id) if m.dataset_id else None,
        "sequence": m.sequence,
        "created_at": iso_z(m.created_at),
    }


def _conversation_patch_payload(c: Conversation) -> dict:
    return {
        "id": str(c.id),
        "updated_at": iso_z(c.updated_at),
        "current_dataset_id": str(c.current_dataset_id) if c.current_dataset_id else None,
    }


async def _get_owned_conversation(
    session: AsyncSession,
    user: User,
    conversation_id: uuid.UUID,
) -> Conversation:
    c = await session.get(Conversation, conversation_id)
    if c is None or c.user_id != user.id:
        raise AppError(404, NOT_FOUND, "Conversation not found.")
    return c


@router.get("")
async def list_messages(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    cursor: str | None = Query(default=None),
    before_sequence: int | None = Query(default=None, ge=1),
    after_sequence: int | None = Query(default=None, ge=1),
    order: str = Query(default="asc"),
) -> dict:
    await _get_owned_conversation(session, user, conversation_id)
    if order not in ("asc", "desc"):
        raise AppError(400, VALIDATION_ERROR, "order must be asc or desc.")
    if before_sequence is not None and after_sequence is not None:
        raise AppError(
            400,
            VALIDATION_ERROR,
            "Use only one of before_sequence or after_sequence.",
        )

    if cursor:
        try:
            pad = "=" * (-len(cursor) % 4)
            raw = base64.urlsafe_b64decode((cursor + pad).encode("ascii"))
            cur = json.loads(raw.decode())
            if "after_sequence" in cur:
                after_sequence = int(cur["after_sequence"])
        except Exception as e:
            raise AppError(400, VALIDATION_ERROR, "Invalid cursor.") from e

    rows: list[Message]
    if before_sequence is not None:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sequence < before_sequence,
            )
            .order_by(Message.sequence.desc())
            .limit(limit + 1)
        )
        rows = list((await session.execute(stmt)).scalars().all())
        rows.reverse()
    elif after_sequence is not None:
        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.sequence > after_sequence,
            )
            .order_by(Message.sequence.asc())
            .limit(limit + 1)
        )
        rows = list((await session.execute(stmt)).scalars().all())
    else:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence.asc())
            .limit(limit + 1)
        )
        rows = list((await session.execute(stmt)).scalars().all())

    if order == "desc":
        rows = list(reversed(rows))

    has_more = len(rows) > limit
    page = rows[:limit]
    items = [_message_dict(m) for m in page]
    next_cursor = None
    if has_more and page:
        next_cursor = _encode_cursor({"after_sequence": page[-1].sequence})
    return success({"items": items, "next_cursor": next_cursor})


@router.post("")
async def create_message(
    conversation_id: uuid.UUID,
    body: MessageCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    conv = await _get_owned_conversation(session, user, conversation_id)

    dataset_id = body.dataset_id
    if dataset_id is None:
        dataset_id = conv.current_dataset_id
    if dataset_id is None:
        raise AppError(
            422,
            VALIDATION_ERROR,
            "No dataset for this turn; set dataset_id or conversation current_dataset_id.",
        )
    if not await is_dataset_attached_to_conversation(session, conversation_id, dataset_id):
        raise AppError(
            422,
            VALIDATION_ERROR,
            "dataset_id must be attached to this conversation.",
        )

    ds = await session.get(Dataset, dataset_id)
    if ds is None or ds.user_id != user.id:
        raise AppError(404, NOT_FOUND, "Dataset not found.")

    max_seq = await session.scalar(
        select(func.coalesce(func.max(Message.sequence), 0)).where(
            Message.conversation_id == conversation_id
        )
    )
    assert max_seq is not None
    user_seq = int(max_seq) + 1
    assistant_seq = int(max_seq) + 2

    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=body.content,
        chart_spec=None,
        dataset_id=dataset_id,
        sequence=user_seq,
    )
    session.add(user_msg)

    cols = (
        await session.scalars(
            select(DatasetColumn)
            .where(DatasetColumn.dataset_id == ds.id)
            .order_by(DatasetColumn.ordinal)
        )
    ).all()

    prior_msgs: list[Message] = list(
        (
            await session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.sequence.desc())
                .limit(10)
            )
        ).all()
    )
    prior_msgs.reverse()

    chart_spec, assistant_content = await build_chart_spec_llm(
        ds, list(cols), body.content, conversation_history=prior_msgs,
    )

    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_content,
        chart_spec=chart_spec,
        dataset_id=dataset_id,
        sequence=assistant_seq,
    )
    session.add(assistant_msg)

    conv.updated_at = datetime.now(timezone.utc)
    await session.flush()
    await session.refresh(user_msg)
    await session.refresh(assistant_msg)
    await session.refresh(conv)

    return success(
        {
            "user_message": _message_dict(user_msg),
            "assistant_message": _message_dict(assistant_msg),
            "conversation": _conversation_patch_payload(conv),
        }
    )
