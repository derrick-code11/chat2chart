from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.models import User
from app.schemas.envelope import success
from app.utils.time import iso_z

router = APIRouter()


@router.get("/me")
async def read_me(user: User = Depends(get_current_user)) -> dict:
    return success(
        {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "avatar_url": user.avatar_url,
            "created_at": iso_z(user.created_at),
        }
    )
