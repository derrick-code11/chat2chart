from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import CONFLICT, NOT_FOUND, VALIDATION_ERROR, AppError
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Conversation, ConversationDataset, Dataset, User
from app.schemas.conversations import AttachDatasetBody, ConversationCreate, ConversationPatch
from app.schemas.envelope import success
from app.utils.conversation_datasets import is_dataset_attached_to_conversation
from app.utils.pagination import decode_offset_cursor, encode_offset_cursor
from app.utils.time import iso_z

router = APIRouter(prefix="/conversations", tags=["Conversations"])

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _conversation_summary(c: Conversation) -> dict:
    return {
        "id": str(c.id),
        "title": c.title,
        "current_dataset_id": str(c.current_dataset_id) if c.current_dataset_id else None,
        "created_at": iso_z(c.created_at),
        "updated_at": iso_z(c.updated_at),
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


async def _get_user_dataset(
    session: AsyncSession,
    user: User,
    dataset_id: uuid.UUID,
) -> Dataset:
    ds = await session.get(Dataset, dataset_id)
    if ds is None or ds.user_id != user.id:
        raise AppError(404, NOT_FOUND, "Dataset not found.")
    return ds


@router.post("", status_code=201)
async def create_conversation(
    body: ConversationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    dataset_ids: list[uuid.UUID] = []
    if body.dataset_ids:
        for did in body.dataset_ids:
            if did not in dataset_ids:
                dataset_ids.append(did)
    if body.current_dataset_id and body.current_dataset_id not in dataset_ids:
        dataset_ids.append(body.current_dataset_id)

    for did in dataset_ids:
        await _get_user_dataset(session, user, did)

    conv = Conversation(user_id=user.id, title=body.title)
    session.add(conv)
    await session.flush()

    for did in dataset_ids:
        session.add(ConversationDataset(conversation_id=conv.id, dataset_id=did))
    await session.flush()

    current: uuid.UUID | None = body.current_dataset_id
    if current is None and len(dataset_ids) == 1:
        current = dataset_ids[0]
    if current is not None:
        if not await is_dataset_attached_to_conversation(session, conv.id, current):
            raise AppError(
                422,
                VALIDATION_ERROR,
                "current_dataset_id must be among attached datasets.",
            )
        conv.current_dataset_id = current
        await session.flush()

    await session.refresh(conv)
    return JSONResponse(status_code=201, content=success(_conversation_summary(conv)))


@router.get("")
async def list_conversations(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    cursor: str | None = Query(default=None),
    sort: str = Query(default="updated_at"),
    order: str = Query(default="desc"),
) -> dict:
    if sort not in ("created_at", "updated_at"):
        raise AppError(400, VALIDATION_ERROR, "sort must be created_at or updated_at.")
    if order not in ("asc", "desc"):
        raise AppError(400, VALIDATION_ERROR, "order must be asc or desc.")

    offset = decode_offset_cursor(cursor)
    sort_col = Conversation.created_at if sort == "created_at" else Conversation.updated_at
    order_expr = sort_col.desc() if order == "desc" else sort_col.asc()
    id_order = Conversation.id.desc() if order == "desc" else Conversation.id.asc()

    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(order_expr, id_order)
        .offset(offset)
        .limit(limit + 1)
    )
    rows = (await session.execute(stmt)).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    items = [_conversation_summary(c) for c in page]
    next_cursor = encode_offset_cursor(offset + limit) if has_more else None
    return success({"items": items, "next_cursor": next_cursor})


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    c = await _get_owned_conversation(session, user, conversation_id)
    return success(_conversation_summary(c))


@router.patch("/{conversation_id}")
async def patch_conversation(
    conversation_id: uuid.UUID,
    body: ConversationPatch,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    c = await _get_owned_conversation(session, user, conversation_id)
    data = body.model_dump(exclude_unset=True)
    if "title" in data:
        c.title = data["title"]
    if "current_dataset_id" in data:
        cid = data["current_dataset_id"]
        if cid is None:
            c.current_dataset_id = None
        else:
            if not await is_dataset_attached_to_conversation(session, conversation_id, cid):
                raise AppError(
                    422,
                    VALIDATION_ERROR,
                    "current_dataset_id must refer to a dataset attached to this conversation.",
                )
            c.current_dataset_id = cid
    await session.flush()
    await session.refresh(c)
    return success(_conversation_summary(c))


@router.get("/{conversation_id}/datasets")
async def list_attached_datasets(
    conversation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await _get_owned_conversation(session, user, conversation_id)
    stmt = (
        select(ConversationDataset, Dataset)
        .join(Dataset, Dataset.id == ConversationDataset.dataset_id)
        .where(ConversationDataset.conversation_id == conversation_id)
        .order_by(ConversationDataset.attached_at.desc())
    )
    result = await session.execute(stmt)
    items = []
    for link, ds in result.all():
        items.append(
            {
                "dataset_id": str(ds.id),
                "attached_at": iso_z(link.attached_at),
                "original_filename": ds.original_filename,
                "status": ds.status,
            }
        )
    return success({"items": items})


@router.post("/{conversation_id}/datasets", status_code=201)
async def attach_dataset(
    conversation_id: uuid.UUID,
    body: AttachDatasetBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    await _get_owned_conversation(session, user, conversation_id)
    await _get_user_dataset(session, user, body.dataset_id)

    existing = await session.execute(
        select(ConversationDataset.id).where(
            ConversationDataset.conversation_id == conversation_id,
            ConversationDataset.dataset_id == body.dataset_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise AppError(
            409,
            CONFLICT,
            "Dataset is already attached to this conversation.",
        )

    link = ConversationDataset(
        conversation_id=conversation_id,
        dataset_id=body.dataset_id,
    )
    session.add(link)
    await session.flush()
    await session.refresh(link)

    ds = await session.get(Dataset, body.dataset_id)
    if ds is None:
        raise AppError(404, NOT_FOUND, "Dataset not found.")
    payload = {
        "dataset_id": str(body.dataset_id),
        "attached_at": iso_z(link.attached_at),
        "original_filename": ds.original_filename,
        "status": ds.status,
    }
    return JSONResponse(status_code=201, content=success(payload))


@router.delete("/{conversation_id}/datasets/{dataset_id}")
async def detach_dataset(
    conversation_id: uuid.UUID,
    dataset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    c = await _get_owned_conversation(session, user, conversation_id)
    result = await session.execute(
        select(ConversationDataset).where(
            ConversationDataset.conversation_id == conversation_id,
            ConversationDataset.dataset_id == dataset_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise AppError(404, NOT_FOUND, "Attachment not found.")

    await session.delete(link)
    if c.current_dataset_id == dataset_id:
        c.current_dataset_id = None
    await session.flush()
    await session.refresh(c)
    return success(_conversation_summary(c), message="Detached.")
