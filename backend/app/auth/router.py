from fastapi import APIRouter, Depends
from google.auth import exceptions as google_auth_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import UNAUTHORIZED, AppError
from app.database import get_db
from app.schemas.auth import GoogleSignInRequest
from app.schemas.envelope import success
from app.services.jwt_tokens import create_access_token
from app.services.user_sync import upsert_user_from_google_claims

router = APIRouter()


@router.post("/google")
async def google_sign_in(
    body: GoogleSignInRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    token = body.token()
    try:
        claims = id_token.verify_oauth2_token(
            token, google_requests.Request(), settings.google_oauth_client_id
        )
    except (ValueError, google_auth_exceptions.GoogleAuthError) as e:
        raise AppError(
            401,
            UNAUTHORIZED,
            "Invalid Google credential.",
            details={"reason": str(e)},
        ) from e

    user = await upsert_user_from_google_claims(session, claims)
    access_token, expires_in = create_access_token(user.id)
    return success(
        {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": expires_in,
        }
    )
