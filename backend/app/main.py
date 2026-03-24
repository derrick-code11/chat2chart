from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.auth.router import router as auth_router
from app.config import settings
from app.core.errors import (
    AppError,
    FORBIDDEN,
    INTERNAL_ERROR,
    NOT_FOUND,
    UNAUTHORIZED,
    VALIDATION_ERROR,
)

app = FastAPI(
    title=settings.app_name,
    description="Upload spreadsheets, chat in plain English, create beautiful charts.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_code_for_status(status: int) -> str:
    if status == 401:
        return UNAUTHORIZED
    if status == 403:
        return FORBIDDEN
    if status == 404:
        return NOT_FOUND
    if status == 400:
        return VALIDATION_ERROR
    return INTERNAL_ERROR


@app.exception_handler(AppError)
async def app_error_handler(_: object, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "data": None,
            "error": {"code": exc.code, "details": exc.details},
            "message": exc.message,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_: object, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "data": None,
            "error": {
                "code": VALIDATION_ERROR,
                "details": {"errors": exc.errors()},
            },
            "message": "Request validation failed.",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: object, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    message = detail if isinstance(detail, str) else str(detail)
    code = _error_code_for_status(exc.status_code)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "data": None,
            "error": {"code": code, "details": {}},
            "message": message,
        },
    )


app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(api_router, prefix="/api/v1")
