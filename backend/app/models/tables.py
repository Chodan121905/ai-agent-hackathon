"""SQLModel tables (SQLite). Created on startup; no migrations (demo scope, PLAN §9)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    telegram_chat_id: int | None = Field(default=None, index=True)
    telegram_user_id: int | None = Field(default=None, index=True)
    name: str | None = None
    # active reply language (one at a time): en | zh | ms | ta — changed in natural language
    language: str = "en"
    role: str = "both"  # elder | guardian | both
    verified: bool = False
    is_admin: bool = False
    created_at: str = Field(default_factory=now_iso)


class GuardianLink(SQLModel, table=True):
    __tablename__ = "guardian_links"

    id: int | None = Field(default=None, primary_key=True)
    elder_id: int = Field(foreign_key="users.id", index=True)
    guardian_id: int | None = Field(default=None, foreign_key="users.id")
    pairing_code: str = Field(index=True)
    status: str = "pending"  # pending | active | revoked
    created_at: str = Field(default_factory=now_iso)


class EmailAccount(SQLModel, table=True):
    __tablename__ = "email_accounts"

    id: int | None = Field(default=None, primary_key=True)
    elder_id: int = Field(foreign_key="users.id", index=True)
    email_address: str = Field(index=True)
    imap_host: str = "imap.gmail.com"
    active: bool = True
    created_at: str = Field(default_factory=now_iso)


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, foreign_key="users.id")
    channel: str = "telegram"  # telegram | email | web
    modality: str = "text"
    sender: str | None = None
    subject: str | None = None
    raw_text: str = ""
    extracted_text: str = ""
    source_url: str | None = None
    risk_level: str = "low"
    is_scam: bool = False
    confidence: float = 0.0
    scam_category: str | None = None
    tactics: str = "[]"            # json
    sender_analysis: str | None = None  # json
    input_language: str = "en"
    verdict: str = "{}"           # json (full Verdict)
    created_at: str = Field(default_factory=now_iso, index=True)


class ScamOfWeek(SQLModel, table=True):
    __tablename__ = "scam_of_week"

    id: int | None = Field(default=None, primary_key=True)
    week: str = ""
    title: str = ""
    body: str = ""
    image_url: str | None = None
    language: str = "both"
    created_at: str = Field(default_factory=now_iso)
