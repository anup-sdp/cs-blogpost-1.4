# config.py
# application configuration settings using pydantic-settings

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
    )
    
    debug: bool = True # fields in .env will override these defaults
    database_url: str

    secret_key: SecretStr = "my-secret-key-2026"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    max_image_size_bytes: int = 512 * 1024  # 512 KB   # default, overridden by .env
    
    posts_per_page: int = 10


settings = Settings()  # type: ignore[call-arg] # Loaded from .env file