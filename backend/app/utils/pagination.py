from __future__ import annotations

import base64
import json

from app.core.errors import VALIDATION_ERROR, AppError


def decode_offset_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        pad = "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode((cursor + pad).encode("ascii"))
        obj = json.loads(raw.decode())
        return int(obj["offset"])
    except Exception as e:
        raise AppError(400, VALIDATION_ERROR, "Invalid cursor.") from e


def encode_offset_cursor(offset: int) -> str:
    raw = json.dumps({"offset": offset}).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")
