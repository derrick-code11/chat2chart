"""File upload endpoints."""

from fastapi import APIRouter, File, UploadFile

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict:
    """Upload a CSV or Excel file. Placeholder for full implementation."""
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "status": "received",
        "message": "Upload endpoint ready. S3 and parsing integration pending.",
    }
