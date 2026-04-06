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

    max_image_size_bytes: int = 100 * 1024  # 100 KB   # default, overridden by .env
    
    posts_per_page: int = 10

    reset_token_expire_minutes: int = 60
    # email/SMTP configuration settings used for sending emails, (password reset emails) 
    # loaded from environment variables or .env file, with the defaults shown.
    mail_server: str = "localhost"  # your email provider's SMTP server (e.g., "smtp.gmail.com").
    mail_port: int = 587  #  587 is standard for TLS-encrypted email, alternative: 465 (SSL)
    mail_username: str = ""  # often your email address
    mail_password: SecretStr = SecretStr("")  # set in .env 
    mail_from: str = "noreply@example.com"
    mail_use_tls: bool = True

    frontend_url: str = "http://localhost:8000" # ----------------- change to actual frontend URL in production / in .env file


settings = Settings()  # type: ignore[call-arg] # Loaded from .env file