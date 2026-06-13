"""Companion node — friendly chat / Q&A with per-person memory.

Runs only when intent is "chat"/"help" (no link, image, or scam content). Reads the
person's memory.md from state, replies warmly, and returns an updated memory.md. The
service layer persists it. No report is saved and no family alert fires for chat.
"""
from __future__ import annotations

import json
import re

from app.agent.llm import make_llm
from app.agent.prompts import COMPANION_SYSTEM
from app.agent.util import resolved_text
from app.core.config import settings


def _parse(content: str) -> dict:
    m = re.search(r"\{.*\}", content or "", re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return {}
    return {}


async def run(state: dict) -> dict:
    text = resolved_text(state)
    if not settings.llm_configured:
        return {
            "chat_reply": "Hi! I'm here for you. (Connect an AI key to chat fully.)\n你好！我在这里陪你。",
            "intent": "chat",
        }

    memory = state.get("memory") or "(no memory yet — this may be a new person)"
    who = (state.get("source") or {}).get("who") or "friend"
    pref = state.get("pref_languages") or settings.default_languages
    active = (pref[0] if pref else "en")
    lang_name = {"en": "English", "zh": "Chinese (简体中文)", "ms": "Malay", "ta": "Tamil"}.get(active, "English")
    user = (
        f"PERSON: {who}\nACTIVE REPLY LANGUAGE: {lang_name} — reply ONLY in this language.\n\n"
        f"MEMORY.md:\n{memory}\n\n"
        f"THEIR MESSAGE:\n{text}\n\n"
        "Respond as their companion, then return the JSON object."
    )
    try:
        resp = await make_llm("brain").ainvoke(
            [
                {"role": "system", "content": COMPANION_SYSTEM},
                {"role": "user", "content": user},
            ]
        )
        data = _parse(getattr(resp, "content", "") or "")
        reply = data.get("reply") or "I'm here — tell me more?"
        new_memory = data.get("memory") or state.get("memory") or ""
        return {"chat_reply": reply, "memory_out": new_memory, "intent": "chat"}
    except Exception:
        return {"chat_reply": "Sorry, I had trouble replying just now — please try again.", "intent": "chat"}
