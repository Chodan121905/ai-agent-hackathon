"""Phase 1 — intake / normalize. Sets modality + language; runs email forensics."""
from __future__ import annotations

from app.agent.util import find_urls, guess_language
from app.core.config import settings
from app.integrations import email_forensics


async def run(state: dict) -> dict:
    src = state.get("source") or {}
    channel = src.get("channel", "web")
    raw_text = state.get("raw_text") or ""

    urls = list(state.get("urls") or [])
    if not urls and raw_text:
        urls = find_urls(raw_text)

    updates: dict = {"urls": urls}

    is_email = state.get("email_headers") is not None or channel == "email"
    if is_email:
        modality = "email"
        updates["sender_analysis"] = email_forensics.analyze_headers(
            state.get("email_headers") or {}, raw_text
        )
    elif state.get("image_bytes"):
        modality = "image"
    elif state.get("audio_path"):
        modality = "voice"
    elif urls and not raw_text.strip():
        modality = "link"
    else:
        modality = "text"
    updates["modality"] = modality

    updates["language_hint"] = guess_language(raw_text)
    if not state.get("pref_languages"):
        updates["pref_languages"] = settings.default_languages
    return updates


def route_by_modality(state: dict) -> str:
    """Conditional edge: turn non-text inputs into text first; links (incl. email links) get intel."""
    if state.get("modality") == "image":
        return "image"
    if state.get("modality") == "voice":
        return "voice"
    if state.get("urls"):
        return "link"
    return "text"
