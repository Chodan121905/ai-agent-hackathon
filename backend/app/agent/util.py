"""Small shared helpers for agent nodes."""
from __future__ import annotations

import re

URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)
_CJK = re.compile(r"[一-鿿]")


def resolved_text(state: dict) -> str:
    """The full text the agent should reason over (message + any extracted/transcribed text)."""
    text = state.get("raw_text") or ""
    extracted = state.get("extracted_text") or []
    return "\n".join(t for t in [text, *extracted] if t).strip()


def find_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def guess_language(text: str) -> str:
    return "zh" if _CJK.search(text or "") else "en"
