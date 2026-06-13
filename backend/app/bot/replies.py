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

# Canonical tactic keys → localized labels.
_TACTICS = {
    "urgency": {"en": "Urgency", "zh": "制造紧迫", "ms": "Mendesak", "ta": "அவசரம்"},
    "authority_impersonation": {"en": "Impersonating authority", "zh": "冒充权威机构", "ms": "Menyamar pihak berkuasa", "ta": "அதிகாரப் போலி"},
    "threat_fear": {"en": "Threats / fear", "zh": "威胁恐吓", "ms": "Ancaman / takut", "ta": "அச்சுறுத்தல்"},
    "secrecy": {"en": "Secrecy", "zh": "要求保密", "ms": "Kerahsiaan", "ta": "இரகசியம்"},
    "unusual_payment": {"en": "Unusual payment", "zh": "异常付款要求", "ms": "Bayaran luar biasa", "ta": "வழக்கமற்ற கட்டணம்"},
    "credential_request": {"en": "Asks for password/OTP", "zh": "索取密码/验证码", "ms": "Minta kata laluan/OTP", "ta": "கடவுச்சொல்/OTP கோரிக்கை"},
    "too_good_to_be_true": {"en": "Too good to be true", "zh": "天上掉馅饼", "ms": "Terlalu indah", "ta": "நம்ப முடியாத சலுகை"},
    "sender_link_mismatch": {"en": "Fake sender / link", "zh": "发件人/链接造假", "ms": "Pengirim/pautan palsu", "ta": "போலி அனுப்புநர்/இணைப்பு"},
    "emotional_leverage": {"en": "Emotional manipulation", "zh": "情感操控", "ms": "Manipulasi emosi", "ta": "உணர்ச்சி சூழ்ச்சி"},
}


def _tactic_label(key: str, lang: str) -> str:
    entry = _TACTICS.get((key or "").strip().lower())
    if entry:
        return entry.get(lang) or entry["en"]
    return (key or "").replace("_", " ").strip()  # fallback for any unexpected value


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
        label = "/".join(_L[l]["tactics"] for l in langs)
        chips = " · ".join(_tactic_label(t, langs[0]) for t in v.tactics)
        lines.append(f"🧠 {label}: {chips}")

    lines.append("")
    for l in langs:
        lines.append(_expl(v, l))

    lines.append("")
    for l in langs:
        a = _act(v, l)
        if a:
            lines.append(f"✅ {a}")

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
