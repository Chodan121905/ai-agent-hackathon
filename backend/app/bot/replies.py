"""Render a Verdict into a Telegram message + family alert (PLAN §11).

The bot speaks ONE active language at a time (the member's chosen language); pass that
language list. Plain text (no Markdown) so addresses/URLs never break formatting.
Lights: 🔴 high · 🟡 medium · 🟢 low. Always shows a confidence %.
"""
from __future__ import annotations

from app.agent.verdict import Verdict

_LIGHT = {"high": "🔴", "medium": "🟡", "low": "🟢"}

# Localized labels per supported language.
_L = {
    "en": {"scam": "SCAM", "safe": "Likely safe", "sure": "sure", "tactics": "Tactics"},
    "zh": {"scam": "诈骗", "safe": "大致安全", "sure": "确定", "tactics": "手法"},
    "ms": {"scam": "PENIPUAN", "safe": "Nampak selamat", "sure": "yakin", "tactics": "Taktik"},
    "ta": {"scam": "மோசடி", "safe": "பாதுகாப்பு", "sure": "உறுதி", "tactics": "தந்திரங்கள்"},
}


def _norm(langs: list[str] | None) -> list[str]:
    out = [l for l in (langs or []) if l in _L]
    return out or ["en"]


def _expl(v: Verdict, lang: str) -> str:
    return getattr(v, f"explanation_{lang}", None) or v.explanation_en


def _act(v: Verdict, lang: str) -> str:
    return getattr(v, f"action_{lang}", None) or v.action_en


def format_verdict(v: Verdict, langs: list[str] | None = None) -> str:
    langs = _norm(langs)
    pct = round(v.confidence * 100)
    light = _LIGHT.get(v.risk_level, "🟡")

    label = lambda l: (_L[l]["scam"] if v.is_scam else _L[l]["safe"])
    header = "   |   ".join(f"{label(l)} · {pct}% {_L[l]['sure']}" for l in langs)
    lines = [f"{light} {header}"]

    if v.tactics:
        lines.append("🧠 " + "/".join(_L[l]["tactics"] for l in langs) + ": " + " · ".join(v.tactics))

    lines.append("")
    for l in langs:
        lines.append(_expl(v, l))

    lines.append("")
    for l in langs:
        a = _act(v, l)
        if a:
            lines.append(f"✅ {a}")

    if v.sender_analysis and v.sender_analysis.reasons:
        lines.append("")
        lines.append("📧 " + v.sender_analysis.reasons[0])

    return "\n".join(lines).strip()


# Localized alert pieces.
_ALERT_HEAD = {
    "en": "⚠️ Scam alert", "zh": "⚠️ 诈骗警报",
    "ms": "⚠️ Amaran penipuan", "ta": "⚠️ மோசடி எச்சரிக்கை",
}


def _alert_intro(lang: str, who: str, sender: str, is_email: bool) -> str:
    if is_email:
        return {
            "en": f"📧 {who}'s inbox just received a scam email from {sender}.",
            "zh": f"📧 {who} 的邮箱刚收到一封来自 {sender} 的诈骗邮件。",
            "ms": f"📧 Peti masuk {who} baru menerima e-mel penipuan daripada {sender}.",
            "ta": f"📧 {who} இன் அஞ்சல் பெட்டிக்கு {sender} இடமிருந்து மோசடி மின்னஞ்சல் வந்துள்ளது.",
        }.get(lang, "")
    return {
        "en": f"{who} forwarded something that looks like a scam.",
        "zh": f"{who} 转发了一条疑似诈骗的信息。",
        "ms": f"{who} memajukan sesuatu yang kelihatan seperti penipuan.",
        "ta": f"{who} மோசடி போல் தோன்றும் ஒன்றை அனுப்பியுள்ளார்.",
    }.get(lang, "")


def _alert_call(lang: str, who: str) -> str:
    return {
        "en": f"✅ Please call {who} now; tell them not to click or reply.",
        "zh": f"✅ 请立即联系 {who}，提醒不要点击或回复。",
        "ms": f"✅ Sila hubungi {who} sekarang; beritahu jangan klik atau balas.",
        "ta": f"✅ உடனே {who} ஐ அழைக்கவும்; கிளிக் செய்யவோ பதிலளிக்கவோ வேண்டாம் எனச் சொல்லுங்கள்.",
    }.get(lang, "")


def format_alert(v: Verdict, who: str, source: dict, langs: list[str] | None = None) -> str:
    langs = _norm(langs)
    pct = round(v.confidence * 100)
    is_email = source.get("channel") == "email"
    sender = (
        (v.sender_analysis.from_address if v.sender_analysis and v.sender_analysis.from_address else None)
        or source.get("sender_raw")
        or "an unknown sender"
    )

    lines = ["   |   ".join(f"{_ALERT_HEAD[l]} · {pct}% {_L[l]['sure']}" for l in langs), ""]
    for l in langs:
        lines.append(_alert_intro(l, who, sender, is_email))
    lines.append("")
    for l in langs:
        lines.append(_expl(v, l))
    lines.append("")
    for l in langs:
        lines.append(_alert_call(l, who))

    return "\n".join(lines).strip()
