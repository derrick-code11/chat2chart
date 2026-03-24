from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.config import settings
from app.core.errors import INTERNAL_ERROR, NOT_FOUND, VALIDATION_ERROR, AppError
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Dataset, DatasetColumn, User
from app.schemas.envelope import success
from app.services import dataset_parse, storage
from app.services.dataset_pipeline import run_dataset_parse
from app.utils.pagination import decode_offset_cursor, encode_offset_cursor
from app.utils.time import iso_z

router = APIRouter()

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


def _summary(ds: Dataset) -> dict:
    return {
        "id": str(ds.id),
        "original_filename": ds.original_filename,
        "content_type": ds.content_type,
        "byte_size": ds.byte_size,
        "status": ds.status,
        "row_count": ds.row_count,
        "column_count": ds.column_count,
        "parse_error": ds.parse_error,
        "created_at": iso_z(ds.created_at),
        "updated_at": iso_z(ds.updated_at),
    }


async def _detail(
    session: AsyncSession,
    ds: Dataset,
) -> dict:
    out = _summary(ds)
    result = await session.execute(
        select(DatasetColumn)
        .where(DatasetColumn.dataset_id == ds.id)
        .order_by(DatasetColumn.ordinal)
    )
    cols = result.scalars().all()
    out["columns"] = [
        {
            "id": str(c.id),
            "ordinal": c.ordinal,
            "name": c.name,
            "inferred_type": c.inferred_type,
            "sample_values": c.sample_values if c.sample_values is not None else [],
        }
        for c in cols
    ]
    if ds.status == "ready":
        try:
            data = await storage.get_dataset_object(ds.storage_key)
            df = dataset_parse.read_tabular_head(
                data,
                ds.original_filename,
                settings.dataset_preview_max_rows,
            )
            rows, truncated = dataset_parse.preview_records(df, settings.dataset_preview_max_rows)
            out["preview"] = {"rows": rows, "truncated": truncated}
        except Exception:
            out["preview"] = {"rows": [], "truncated": False}
    else:
        out["preview"] = None
    return out


async def _get_owned_dataset(
    session: AsyncSession,
    user: User,
    dataset_id: uuid.UUID,
) -> Dataset:
    ds = await session.get(Dataset, dataset_id)
    if ds is None or ds.user_id != user.id:
        raise AppError(404, NOT_FOUND, "Dataset not found.")
    return ds


@router.post("/datasets", status_code=201)
async def create_dataset(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> JSONResponse:
    filename = file.filename or "upload"
    ext = dataset_parse.extension_from_filename(filename)
    if not ext:
        raise AppError(
            400,
            VALIDATION_ERROR,
            "Unsupported file type. Use .csv, .xlsx, or .xls.",
        )
    data = await file.read()
    if not data:
        raise AppError(400, VALIDATION_ERROR, "Empty file.")
    if len(data) > settings.max_upload_bytes:
        raise AppError(
            400,
            VALIDATION_ERROR,
            f"File exceeds max size of {settings.max_upload_bytes} bytes.",
        )

    dataset_id = uuid.uuid4()
    original = dataset_parse.normalize_filename(filename)
    storage_key = f"datasets/{user.id}/{dataset_id}/upload{ext}"

    try:
        await storage.put_dataset_object(storage_key, data, file.content_type)
    except Exception as e:
        raise AppError(500, INTERNAL_ERROR, f"Storage failed: {e}") from e

    ds = Dataset(
        id=dataset_id,
        user_id=user.id,
        original_filename=original,
        content_type=file.content_type,
        byte_size=len(data),
        storage_key=storage_key,
        status="pending",
    )
    session.add(ds)
    await session.flush()
    await run_dataset_parse(session, dataset_id)
    # Refresh: avoid lazy reload on expired columns (asyncpg MissingGreenlet).
    await session.refresh(ds)

    payload = await _detail(session, ds)
    return JSONResponse(status_code=201, content=success(payload))


@router.get("/datasets")
async def list_datasets(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT),
    cursor: str | None = Query(default=None),
    sort: str = Query(default="created_at"),
    order: str = Query(default="desc"),
    status: str | None = Query(default=None),
) -> dict:
    if status is not None and status not in ("pending", "ready", "failed"):
        raise AppError(400, VALIDATION_ERROR, "Invalid status filter.")
    if sort not in ("created_at", "updated_at"):
        raise AppError(400, VALIDATION_ERROR, "sort must be created_at or updated_at.")
    if order not in ("asc", "desc"):
        raise AppError(400, VALIDATION_ERROR, "order must be asc or desc.")

    offset = decode_offset_cursor(cursor)
    sort_col = Dataset.created_at if sort == "created_at" else Dataset.updated_at
    order_expr = sort_col.desc() if order == "desc" else sort_col.asc()
    id_order = Dataset.id.desc() if order == "desc" else Dataset.id.asc()

    stmt: Select = select(Dataset).where(Dataset.user_id == user.id)
    if status:
        stmt = stmt.where(Dataset.status == status)
    stmt = stmt.order_by(order_expr, id_order)
    stmt = stmt.offset(offset).limit(limit + 1)

    rows = (await session.execute(stmt)).scalars().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    items = [_summary(ds) for ds in page]
    next_cursor = encode_offset_cursor(offset + limit) if has_more else None
    return success({"items": items, "next_cursor": next_cursor})


@router.get("/datasets/{dataset_id}")
async def get_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    ds = await _get_owned_dataset(session, user, dataset_id)
    return success(await _detail(session, ds))


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    ds = await _get_owned_dataset(session, user, dataset_id)
    key = ds.storage_key
    try:
        await storage.delete_dataset_object(key)
    except Exception:
        pass
    await session.delete(ds)
    return success(None, message="Deleted.")
