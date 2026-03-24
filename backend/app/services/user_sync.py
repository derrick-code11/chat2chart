from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import CONFLICT, VALIDATION_ERROR, AppError
from app.models import User


async def upsert_user_from_google_claims(session: AsyncSession, claims: dict) -> User:
    google_sub = claims.get("sub")
    if not google_sub:
        raise AppError(400, VALIDATION_ERROR, "Google token missing subject (sub).")

    email = claims.get("email")
    if not email:
        raise AppError(
            400,
            VALIDATION_ERROR,
            "Google token missing email; ensure email scope is granted.",
        )

    email_verified = bool(claims.get("email_verified", True))
    display_name = claims.get("name")
    avatar_url = claims.get("picture")

    result = await session.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()

    if user is None:
        other = await session.execute(select(User).where(User.email == email))
        if other.scalar_one_or_none() is not None:
            raise AppError(
                409,
                CONFLICT,
                "This email is already registered with a different Google account.",
            )
        user = User(
            google_sub=google_sub,
            email=email,
            email_verified=email_verified,
            display_name=display_name,
            avatar_url=avatar_url,
        )
        session.add(user)
        try:
            await session.flush()
        except IntegrityError as e:
            await session.rollback()
            raise AppError(
                409,
                CONFLICT,
                "Could not create account due to a conflicting email or identity.",
            ) from e
        return user

    if user.email != email:
        other = await session.execute(
            select(User).where(User.email == email, User.id != user.id)
        )
        if other.scalar_one_or_none() is not None:
            raise AppError(
                409,
                CONFLICT,
                "This email is already in use by another account.",
            )
    user.email = email
    user.email_verified = email_verified
    user.display_name = display_name
    user.avatar_url = avatar_url
    try:
        await session.flush()
    except IntegrityError as e:
        await session.rollback()
        raise AppError(
            409,
            CONFLICT,
            "Could not update profile due to a conflicting email.",
        ) from e
    return user
