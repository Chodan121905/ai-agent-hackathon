"""Shared, typed graph state (PLAN §5).

Parallel branches that write the same key need a reducer, or LangGraph raises
InvalidUpdateError — hence the `a + b` reducers on extracted_text / link_intel and
add_messages on messages.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.agent.verdict import Verdict

Modality = Literal["text", "image", "voice", "link", "email", "mixed"]


def _concat(a: list, b: list) -> list:
    return (a or []) + (b or [])


class GraphState(TypedDict, total=False):
    source: dict                      # {channel, who, telegram_user_id, sender_raw, ...}
    raw_text: str                     # text / email body / caption
    image_bytes: Optional[bytes]
    audio_path: Optional[str]
    urls: list[str]
    email_headers: Optional[dict]     # From, Reply-To, Return-Path, Authentication-Results
    modality: Modality
    language_hint: Optional[str]
    intent: Optional[str]             # "check" (default) | "set_language" | "help"
    requested_languages: Optional[list[str]]
    pref_languages: list[str]         # saved output languages (default ["en","zh"])
    note: Optional[str]               # confirmation text for set_language / help
    extracted_text: Annotated[list[str], _concat]
    link_intel: Annotated[list[dict], _concat]
    sender_analysis: Optional[dict]
    messages: Annotated[list, add_messages]
    analysis: Optional[dict]
    verification: Optional[dict]
    verdict: Optional[Verdict]
