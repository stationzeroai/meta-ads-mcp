from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    META_ACCESS_TOKEN: str

    # AWS credentials for S3 operations
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str = "us-west-2"
    AWS_S3_REGION: Optional[str] = None  # Deprecated, use AWS_REGION

    LOG_LEVEL: str = "INFO"
    MAX_RETRIES: int = 3


config = Settings()  # type: ignore
