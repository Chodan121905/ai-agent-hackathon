"""API request/response schemas (part of the OpenAPI contract for web + Flutter)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.agent.verdict import Verdict


class CheckResponse(BaseModel):
    intent: str = "check"  # "check" | "set_language"
    verdict: Optional[Verdict] = None
    report_id: Optional[int] = None
    alerted: int = 0
    message: Optional[str] = None          # set_language confirmation
    languages: Optional[list[str]] = None  # set_language result


class GuardianInviteIn(BaseModel):
    elder_id: int


class GuardianInviteOut(BaseModel):
    pairing_code: str
    status: str


class EmailAccountIn(BaseModel):
    elder_id: int
    email_address: str
    imap_host: str = "imap.gmail.com"
