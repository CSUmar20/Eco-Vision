from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIRECTORY = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    database_url: str
    hf_model: str = "openai/clip-vit-base-patch32"
    max_image_bytes: int = 10_000_000

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIRECTORY / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
