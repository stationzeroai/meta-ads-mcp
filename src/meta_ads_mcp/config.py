from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    META_ACCESS_TOKEN: str

    # AWS credentials for S3 operations (optional, not all tools need them)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    AWS_S3_REGION: Optional[str] = None  # Deprecated, use AWS_REGION

    LOG_LEVEL: str = "INFO"
    MAX_RETRIES: int = 3


config = Settings()  # type: ignore
