from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    LOG_LEVEL: str = "INFO"
    META_ACCESS_TOKEN: str


config = Settings()  # type: ignore
