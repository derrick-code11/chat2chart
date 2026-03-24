from pathlib import Path

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Chat2Chart"
    cors_origins: str = "*"
    database_url: str
    google_oauth_client_id: str = Field(
        validation_alias=AliasChoices("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_CLIENT_ID"),
    )
    google_oauth_client_secret: str | None = None
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AWS_SESSION_TOKEN", "aws_session_token"),
    )
    aws_region: str = Field(
        default="us-east-2",
        validation_alias=AliasChoices("AWS_REGION", "AWS_DEFAULT_REGION", "aws_region"),
    )
    s3_bucket: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_BUCKET", "AWS_S3_BUCKET", "s3_bucket"),
        description="Bucket name for dataset files. Empty/unset = local DATASET_LOCAL_STORAGE_PATH.",
    )
    aws_s3_endpoint_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "AWS_S3_ENDPOINT_URL",
            "S3_ENDPOINT_URL",
            "aws_s3_endpoint_url",
        ),
        description="Optional S3 API endpoint (MinIO, LocalStack, etc.).",
    )
    debug: bool = False
    dataset_local_storage_path: Path = Field(
        default=_BACKEND_ROOT / "storage" / "datasets",
        validation_alias=AliasChoices(
            "DATASET_LOCAL_STORAGE_PATH",
            "dataset_local_storage_path",
        ),
    )
    max_upload_bytes: int = Field(
        default=50 * 1024 * 1024,
        validation_alias=AliasChoices("MAX_UPLOAD_BYTES", "max_upload_bytes"),
    )
    dataset_preview_max_rows: int = Field(
        default=50,
        validation_alias=AliasChoices("DATASET_PREVIEW_MAX_ROWS", "dataset_preview_max_rows"),
    )
    openai_api_key: str = Field(
        ...,
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    openai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_BASE_URL", "openai_base_url"),
    )
    openai_model: str = Field(
        default="gpt-5.4-mini",
        validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"),
    )
    llm_chart_timeout_seconds: float = Field(
        default=90.0,
        validation_alias=AliasChoices("LLM_CHART_TIMEOUT_SECONDS", "llm_chart_timeout_seconds"),
    )

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def _openai_api_key_non_empty(cls, v: object) -> str:
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError("OPENAI_API_KEY is required for chart generation")
        return str(v).strip()

    @field_validator("s3_bucket", mode="before")
    @classmethod
    def _s3_bucket_empty_means_local(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    @property
    def use_s3_for_datasets(self) -> bool:
        return bool(self.s3_bucket)


settings = Settings()
