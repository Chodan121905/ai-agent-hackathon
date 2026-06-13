"""Phase 3.5 — intent. Detect a natural-language request to change the reply language
(typed or transcribed from voice); otherwise continue to scam analysis."""
from __future__ import annotations

import json
import re

from app.agent.llm import make_llm
from app.agent.prompts import INTENT_SYSTEM
from app.agent.util import resolved_text
from app.core.config import settings

_LANG_CODE = {
    "english": "en", "英文": "en", "英语": "en", "en": "en",
    "chinese": "zh", "mandarin": "zh", "中文": "zh", "华语": "zh", "中文回答": "zh", "zh": "zh",
    "malay": "ms", "马来": "ms", "ms": "ms",
    "tamil": "ta", "泰米尔": "ta", "ta": "ta",
}
_LANG_REQUEST_HINT = re.compile(
    r"(reply|respond|answer|speak|use|switch|change|说|用|讲|回答|回复).{0,20}"
    r"(english|chinese|mandarin|malay|tamil|英文|中文|华语|马来|泰米尔|both|两种|双语)",
    re.IGNORECASE,
)
_BOTH = re.compile(r"\bboth\b|两种|双语|english and chinese|中英", re.IGNORECASE)


def _normalize_langs(values) -> list[str]:
    out: list[str] = []
    for v in values or []:
        code = _LANG_CODE.get(str(v).strip().lower())
        if code and code not in out:
            out.append(code)
    return out


def _parse_json(content: str) -> dict:
    m = re.search(r"\{.*\}", content, re.DOTALL)
    return json.loads(m.group(0)) if m else {}


def _heuristic(text: str) -> dict:
    if _BOTH.search(text):
        return {"intent": "set_language", "requested_languages": ["en", "zh"]}
    if _LANG_REQUEST_HINT.search(text):
        langs = [c for w, c in _LANG_CODE.items() if w in text.lower()]
        # dedupe preserving order
        seen: list[str] = []
        for c in langs:
            if c not in seen:
                seen.append(c)
        if seen:
            return {"intent": "set_language", "requested_languages": seen}
    return {"intent": "check"}


async def run(state: dict) -> dict:
    src = state.get("source") or {}
    if src.get("channel") == "email":
        return {"intent": "check"}  # autonomous channel never issues commands

    text = resolved_text(state)
    if not text:
        return {"intent": "check"}

    if settings.llm_configured:
        try:
            llm = make_llm("triage")
            resp = await llm.ainvoke(
                [
                    {"role": "system", "content": INTENT_SYSTEM},
                    {"role": "user", "content": text},
                ]
            )
            data = _parse_json(resp.content if hasattr(resp, "content") else str(resp))
            intent = data.get("intent", "check")
            if intent == "set_language":
                return {"intent": "set_language", "requested_languages": _normalize_langs(data.get("languages"))}
            return {"intent": intent}
        except Exception:
            pass
    return _heuristic(text)


_CONFIRM = {
    "en": "Done — I'll reply in English from now on.",
    "zh": "好的 — 我以后会用中文回复你。",
    "both": "Done — I'll reply in both English and Chinese. 好的，我会用中英双语回复。",
    "ms": "Selesai — saya akan membalas dalam Bahasa Melayu mulai sekarang.",
    "ta": "முடிந்தது — இனி தமிழில் பதிலளிப்பேன்.",
}


async def set_language(state: dict) -> dict:
    langs = state.get("requested_languages") or settings.default_languages
    if set(langs) == {"en", "zh"} or len(langs) >= 2:
        note = _CONFIRM["both"] if set(langs) == {"en", "zh"} else \
            "Done — I'll reply in: " + ", ".join(langs)
    else:
        note = _CONFIRM.get(langs[0], f"Done — language set to {langs[0]}.")
    return {"pref_languages": langs, "note": note, "intent": "set_language"}
