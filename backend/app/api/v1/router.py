from fastapi import APIRouter

from app.api.v1 import conversations, datasets, health, me, message_export, messages

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(me.router, tags=["Me"])
api_router.include_router(datasets.router, tags=["Datasets"])
api_router.include_router(conversations.router)
api_router.include_router(messages.router)
api_router.include_router(message_export.router)
