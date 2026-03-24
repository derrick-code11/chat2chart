from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Chat2Chart"
    cors_origins: str = "*"
    database_url: str
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-2"
    s3_bucket: str
    debug: bool = False


settings = Settings()
