from __future__ import annotations

import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import Dataset, DatasetColumn
from app.services import dataset_parse, storage


async def run_dataset_parse(session: AsyncSession, dataset_id: uuid.UUID) -> None:
    ds = await session.get(Dataset, dataset_id)
    if ds is None:
        return
    try:
        data = await storage.get_dataset_object(ds.storage_key)
        df = dataset_parse.read_tabular(data, ds.original_filename)
        meta = dataset_parse.build_column_metadata(df)
        await session.execute(delete(DatasetColumn).where(DatasetColumn.dataset_id == ds.id))
        for m in meta:
            session.add(
                DatasetColumn(
                    dataset_id=ds.id,
                    ordinal=m["ordinal"],
                    name=m["name"],
                    inferred_type=m["inferred_type"],
                    sample_values=m["sample_values"],
                )
            )
        ds.row_count = int(len(df))
        ds.column_count = int(len(df.columns))
        ds.status = "ready"
        ds.parse_error = None
        await session.flush()
    except Exception as e:
        ds.status = "failed"
        ds.parse_error = (e.message if isinstance(e, AppError) else str(e))[:2000]
        await session.flush()
