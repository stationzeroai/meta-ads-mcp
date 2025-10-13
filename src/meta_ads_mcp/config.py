from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    META_ACCESS_TOKEN: str

    LOG_LEVEL: str = "INFO"
    MAX_RETRIES: int = 5


config = Settings()  # type: ignore
