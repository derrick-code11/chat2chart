from fastapi import APIRouter

from app.schemas.envelope import success

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return success({"status": "ok"})
