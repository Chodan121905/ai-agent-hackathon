"""Application configuration via pydantic-settings.

All values come from environment / backend/.env (see .env.example). Optional-int
fields are kept as strings with helper properties so an empty value in .env
(e.g. ADMIN_TELEGRAM_ID=) does not raise a validation error.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- App ---
    ENV: str = "dev"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # --- Storage ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./scamguardian.db"

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = ""

    # --- Access control ---
    ACCESS_CODE: str = "family-2026"
    ADMIN_TELEGRAM_ID: str = ""  # numeric id as string; "" = no admin

    # --- LLM ---
    LLM_BASE_URL: str = "https://api.moonshot.ai/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL_BRAIN: str = "kimi-k2.6"
    LLM_MODEL_TRIAGE: str = "kimi-k2.6"
    DEFAULT_LANGUAGES: str = "en,zh"
    CHINESE_VARIANT: str = "simplified"  # simplified | traditional

    # --- Autonomous email monitoring ---
    EMAIL_IMAP_HOST: str = "imap.gmail.com"
    EMAIL_IMAP_USER: str = ""
    EMAIL_IMAP_PASSWORD: str = ""
    EMAIL_POLL_SECONDS: int = 20
    EMAIL_OWNER_ELDER_ID: str = "1"
    ALERT_THRESHOLD: str = "high"  # high | medium | low
    ALERT_ELDER_TOO: bool = True   # locked decision: alert family AND the elder

    # --- Sponsors ---
    SENSENOVA_API_KEY: str = ""
    SENSENOVA_BASE_URL: str = "https://token.sensenova.cn/v1"
    SENSENOVA_MODEL: str = "SenseNova-U1"
    VIDEO_DB_API_KEY: str = ""
    BRIGHTDATA_API_TOKEN: str = ""
    BRIGHTDATA_SERP_ZONE: str = "serp_api1"
    BRIGHTDATA_UNLOCKER_ZONE: str = "unblocker"
    DAYTONA_API_KEY: str = ""

    # --- STT ---
    STT_PROVIDER: str = "whisper"  # whisper | videodb
    WHISPER_MODEL: str = "base"

    # ----- derived helpers -----
    @property
    def default_languages(self) -> list[str]:
        return [x.strip() for x in self.DEFAULT_LANGUAGES.split(",") if x.strip()] or ["en", "zh"]

    @property
    def admin_id(self) -> int | None:
        return int(self.ADMIN_TELEGRAM_ID) if self.ADMIN_TELEGRAM_ID.strip().isdigit() else None

    @property
    def email_owner_elder_id(self) -> int | None:
        v = self.EMAIL_OWNER_ELDER_ID.strip()
        return int(v) if v.isdigit() else None

    @property
    def llm_configured(self) -> bool:
        return bool(self.LLM_API_KEY.strip())

    @property
    def email_configured(self) -> bool:
        return bool(self.EMAIL_IMAP_USER.strip() and self.EMAIL_IMAP_PASSWORD.strip())

    @property
    def telegram_configured(self) -> bool:
        return bool(self.TELEGRAM_BOT_TOKEN.strip() and ":" in self.TELEGRAM_BOT_TOKEN)

    @property
    def chinese_label(self) -> str:
        return "Traditional Chinese (繁體中文)" if self.CHINESE_VARIANT.lower().startswith("trad") else "Simplified Chinese (简体中文)"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
