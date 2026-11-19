import os
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Telegram Bot
    BOT_TOKEN: str = Field(default="", description="Telegram Bot API Token")

    # Webhook & Server
    BASE_URL: str = Field(default="", description="Base HTTPS URL of the service for Webhook")
    WEBHOOK_PATH: str = Field(default="/webhook", description="Path for incoming Telegram updates")
    WEBHOOK_SECRET: str = Field(default="", description="Secret token for Telegram Webhook verification")
    PORT: int = Field(default=8080, description="Server port (Railway $PORT)")
    HOST: str = Field(default="0.0.0.0", description="Server bind host")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/levelup",
        description="PostgreSQL asyncpg connection string"
    )

    # Admin IDs
    ADMIN_IDS: List[int] = Field(default_factory=list, description="List of Telegram admin user IDs")

    # Settings
    TIMEZONE: str = Field(default="Asia/Tashkent", description="Timezone for display purposes")
    USE_POLLING: bool = Field(default=False, description="Run bot in polling mode for local dev")
    DROP_PENDING_UPDATES: bool = Field(default=True, description="Drop pending updates on startup")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v):
        if isinstance(v, list):
            return [int(x) for x in v if str(x).strip()]
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip().isdigit()]
        if isinstance(v, int):
            return [v]
        return []

    @property
    def webhook_url(self) -> str:
        base = self.BASE_URL.rstrip("/")
        path = self.WEBHOOK_PATH.lstrip("/")
        return f"{base}/{path}"

    @property
    def async_database_url(self) -> str:
        """Convert standard postgres:// or postgresql:// to asyncpg compatible URL if needed."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url


settings = Settings()
