"""The shared Verdict contract (PLAN §6).

This one model flows through the agent → API → Telegram reply → email alert, and via
OpenAPI codegen into the future TS and Dart clients. Chinese fields are Simplified
(locked decision); Malay/Tamil are filled only when a member asks for them.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SenderAnalysis(BaseModel):
    """Deterministic email-forensics signals (PLAN §7.3). Null outside the email channel."""

    from_display_name: Optional[str] = None
    from_address: Optional[str] = None
    claimed_brand: Optional[str] = None
    display_name_mismatch: bool = False
    lookalike_domain: bool = False
    freemail_as_company: bool = False
    replyto_mismatch: bool = False
    auth_results: Optional[str] = None  # e.g. "spf=fail dkim=none dmarc=fail"
    reasons: list[str] = Field(default_factory=list)

    @property
    def has_hard_signal(self) -> bool:
        return any(
            [
                self.display_name_mismatch,
                self.lookalike_domain,
                self.freemail_as_company,
                self.replyto_mismatch,
            ]
        )


class Verdict(BaseModel):
    risk_level: Literal["high", "medium", "low"]
    is_scam: bool
    confidence: float = Field(ge=0, le=1, description="0..1; shown to the user as a %")
    tactics: list[str] = Field(
        default_factory=list,
        description=(
            "tactic keys (translated for display) from: urgency, authority_impersonation, "
            "threat_fear, secrecy, unusual_payment, credential_request, too_good_to_be_true, "
            "sender_link_mismatch, emotional_leverage; [] if none"
        ),
    )
    scam_category: Optional[str] = Field(
        default=None,
        description="bank_impersonation | govt_official | phishing | lottery | romance | job | other",
    )
    # Output languages follow the member's preference (default English + 简体中文).
    explanation_en: str = Field(description="1–2 simple sentences a 70-year-old understands (English)")
    explanation_zh: str = Field(description="同上，简体中文")
    action_en: str = Field(description="the single clearest next step (English)")
    action_zh: str = Field(description="同上，简体中文")
    explanation_ms: Optional[str] = None  # Malay — only on request
    explanation_ta: Optional[str] = None  # Tamil — only on request
    action_ms: Optional[str] = None
    action_ta: Optional[str] = None
    sender_analysis: Optional[SenderAnalysis] = None
    input_language: str = Field(description="detected language of the input: en | zh | ms | ta | other")
    alert_family: bool = Field(description="true when risk_level == 'high'")
