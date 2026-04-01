from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NOT_FOUND, VALIDATION_ERROR, AppError
from app.database import get_db
from app.dependencies import get_current_user
from app.models import Conversation, Export, Message, User
from app.services.chart_render_png import chart_spec_to_png_bytes_async

router = APIRouter(prefix="/messages", tags=["Exports"])


@router.get("/{message_id}/export")
async def export_message_chart_png(
    message_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    export_format: str = Query("png", alias="format"),
) -> Response:
    if export_format != "png":
        raise AppError(422, VALIDATION_ERROR, "Only format=png is supported.")

    stmt = (
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Message.id == message_id, Conversation.user_id == user.id)
    )
    msg = (await session.execute(stmt)).scalar_one_or_none()
    if msg is None:
        raise AppError(404, NOT_FOUND, "Message not found.")

    spec = msg.chart_spec
    if not isinstance(spec, dict) or not spec:
        raise AppError(
            422,
            VALIDATION_ERROR,
            "This message has no chart to export. Use the assistant reply that includes the chart.",
        )
    rows = spec.get("data", {}).get("rows") if isinstance(spec.get("data"), dict) else None
    if not rows or not isinstance(rows, list):
        raise AppError(
            422,
            VALIDATION_ERROR,
            "Chart data is missing or empty; cannot export PNG.",
        )

    png_bytes = await chart_spec_to_png_bytes_async(spec)

    session.add(
        Export(
            user_id=user.id,
            message_id=msg.id,
            format="png",
            byte_size=len(png_bytes),
            storage_key=None,
        )
    )

    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={
            "Content-Disposition": 'attachment; filename="chart.png"',
        },
    )
