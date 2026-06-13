"""Application configuration via pydantic-settings.

All values come from environment / backend/.env (see .env.example). Optional-int
fields are kept as strings with helper properties so an empty value in .env
(e.g. ADMIN_TELEGRAM_ID=) does not raise a validation error.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("*", mode="before")
    @classmethod
    def _clean_str(cls, v):
        # Defends against .env footguns: surrounding whitespace, and an inline "# comment"
        # left on an otherwise-empty value (python-dotenv keeps it as the value).
        if isinstance(v, str):
            s = v.strip()
            return "" if s.startswith("#") else s
        return v

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
    # kimi-k2.6 "thinking" mode is accurate but slow (~50s); off → ~4s. Off by default for the demo.
    # When off, the model requires temperature 0.6; when on, it requires 1.0.
    LLM_THINKING: bool = False
    DEFAULT_LANGUAGES: str = "en"  # one active language at a time; switch by asking the bot
    CHINESE_VARIANT: str = "simplified"  # simplified | traditional

    # --- Autonomous email monitoring ---
    EMAIL_IMAP_HOST: str = "imap.gmail.com"
    EMAIL_IMAP_USER: str = ""
    EMAIL_IMAP_PASSWORD: str = ""
    EMAIL_FOLDERS: str = "INBOX,[Gmail]/Spam"  # also scan Spam — scams often get filed there
    EMAIL_MAX_PER_POLL: int = 10               # cap processed per poll (avoid a spam backlog flood)
    EMAIL_POLL_SECONDS: int = 20
    EMAIL_OWNER_ELDER_ID: str = "1"
    ALERT_THRESHOLD: str = "high"  # high | medium | low
    ALERT_ELDER_TOO: bool = True   # locked decision: alert family AND the elder

    # --- OCR (screenshot reading) via TokenRouter; falls back to Kimi-vision ---
    TOKENROUTER_API_KEY: str = ""
    TOKENROUTER_BASE_URL: str = "https://api.tokenrouter.io/v1"
    OCR_MODEL: str = ""  # a vision-capable model id on TokenRouter; blank → Kimi-vision fallback

    # --- Sponsors ---
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
    def email_folders(self) -> list[str]:
        return [f.strip() for f in self.EMAIL_FOLDERS.split(",") if f.strip()] or ["INBOX"]

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
