from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import boto3

from app.config import settings


def _root() -> Path:
    return Path(settings.dataset_local_storage_path).resolve()


def _safe_local_path(storage_key: str) -> Path:
    if ".." in storage_key or storage_key.startswith(("/", "\\")):
        raise ValueError("Invalid storage key.")
    root = _root()
    path = (root / storage_key).resolve()
    path.relative_to(root)
    return path


def _s3_client():
    kwargs: dict[str, Any] = {"region_name": settings.aws_region}
    ep = settings.aws_s3_endpoint_url
    if ep and str(ep).strip():
        kwargs["endpoint_url"] = str(ep).strip()
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            kwargs["aws_session_token"] = settings.aws_session_token
    return boto3.client("s3", **kwargs)


def _local_get(storage_key: str) -> bytes:
    path = _safe_local_path(storage_key)
    if not path.is_file():
        raise FileNotFoundError(storage_key)
    return path.read_bytes()


def _s3_get(storage_key: str) -> bytes:
    c = _s3_client()
    r = c.get_object(Bucket=settings.s3_bucket, Key=storage_key)
    return r["Body"].read()


async def get_dataset_object(storage_key: str) -> bytes:
    if settings.use_s3_for_datasets:
        return await asyncio.to_thread(_s3_get, storage_key)
    return await asyncio.to_thread(_local_get, storage_key)


def _local_put(storage_key: str, data: bytes) -> None:
    path = _safe_local_path(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _s3_put(storage_key: str, data: bytes, content_type: str | None) -> None:
    c = _s3_client()
    extra: dict = {"Bucket": settings.s3_bucket, "Key": storage_key, "Body": data}
    if content_type:
        extra["ContentType"] = content_type
    c.put_object(**extra)


async def put_dataset_object(storage_key: str, data: bytes, content_type: str | None) -> None:
    if settings.use_s3_for_datasets:
        await asyncio.to_thread(_s3_put, storage_key, data, content_type)
    else:
        await asyncio.to_thread(_local_put, storage_key, data)


def _local_delete(storage_key: str) -> None:
    path = _safe_local_path(storage_key)
    if path.is_file():
        path.unlink()


def _s3_delete(storage_key: str) -> None:
    c = _s3_client()
    c.delete_object(Bucket=settings.s3_bucket, Key=storage_key)


async def delete_dataset_object(storage_key: str) -> None:
    if settings.use_s3_for_datasets:
        await asyncio.to_thread(_s3_delete, storage_key)
    else:
        await asyncio.to_thread(_local_delete, storage_key)
