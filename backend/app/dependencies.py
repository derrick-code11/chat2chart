from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.services.jwt_tokens import decode_access_token

__all__ = ["get_db", "get_current_user"]


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_db),
) -> User:
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header.")
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Authorization must be a Bearer token.",
        )
    raw = parts[1].strip()
    if not raw:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    try:
        user_id = decode_access_token(raw)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.") from None

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists.")
    return user
