"""Render a Verdict into a bilingual Telegram message + family alert (PLAN §11).

Plain text (no Markdown) so sender addresses / URLs with special characters never break
formatting. Lights: 🔴 high · 🟡 medium · 🟢 low. Always shows a confidence %.
"""
from __future__ import annotations

from app.agent.verdict import Verdict

_LIGHT = {"high": "🔴", "medium": "🟡", "low": "🟢"}


def format_verdict(v: Verdict, langs: list[str] | None = None) -> str:
    langs = langs or ["en", "zh"]
    pct = round(v.confidence * 100)
    label_en = "SCAM" if v.is_scam else "Likely safe"
    label_zh = "诈骗" if v.is_scam else "大致安全"
    light = _LIGHT.get(v.risk_level, "🟡")

    lines = [f"{light} {label_en} · {pct}% sure   |   {label_zh} · {pct}% 确定"]
    if v.tactics:
        lines.append("🧠 Tactics: " + " · ".join(v.tactics))
    lines.append("")

    if "en" in langs:
        lines.append(f"EN — {v.explanation_en}")
    if "zh" in langs:
        lines.append(f"中文 — {v.explanation_zh}")
    if "ms" in langs and v.explanation_ms:
        lines.append(f"BM — {v.explanation_ms}")
    if "ta" in langs and v.explanation_ta:
        lines.append(f"TA — {v.explanation_ta}")
    lines.append("")

    if "en" in langs:
        lines.append(f"✅ EN — {v.action_en}")
    if "zh" in langs:
        lines.append(f"✅ 中文 — {v.action_zh}")
    if "ms" in langs and v.action_ms:
        lines.append(f"✅ BM — {v.action_ms}")
    if "ta" in langs and v.action_ta:
        lines.append(f"✅ TA — {v.action_ta}")

    if v.sender_analysis and v.sender_analysis.reasons:
        lines.append("")
        lines.append("📧 " + v.sender_analysis.reasons[0])

    return "\n".join(lines).strip()


def format_alert(v: Verdict, who: str, source: dict) -> str:
    pct = round(v.confidence * 100)
    head = f"⚠️ Scam alert · {pct}% sure   |   ⚠️ 诈骗警报 · {pct}% 确定"

    if source.get("channel") == "email":
        sender = (
            (v.sender_analysis.from_address if v.sender_analysis and v.sender_analysis.from_address else None)
            or source.get("sender_raw")
            or "an unknown sender"
        )
        intro_en = f"📧 {who}'s inbox just received a scam email from {sender}."
        intro_zh = f"📧 {who} 的邮箱刚收到一封来自 {sender} 的诈骗邮件。"
    else:
        intro_en = f"{who} forwarded something that looks like a scam."
        intro_zh = f"{who} 转发了一条疑似诈骗的信息。"

    return "\n".join(
        [
            head,
            "",
            intro_en,
            intro_zh,
            "",
            f"EN — {v.explanation_en}",
            f"中文 — {v.explanation_zh}",
            "",
            f"✅ EN — Please call {who} now; tell them not to click or reply.",
            f"✅ 中文 — 请立即联系 {who}，提醒他们不要点击或回复。",
        ]
    ).strip()
