"""Phase 5 — synthesize. Produce the strict bilingual Verdict.

When no LLM key is configured, fall back to a deterministic verdict built from the
forensics/verification hard flags so the system still demonstrably works (e.g. for
the autonomous email path) without a paid key.
"""
from __future__ import annotations

from app.agent.llm import structured_llm
from app.agent.prompts import SYNTHESIZE_SYSTEM, build_synthesize_user_message
from app.agent.util import guess_language, resolved_text
from app.agent.verdict import SenderAnalysis, Verdict
from app.core.config import settings


def _escalate_with_hard_flags(verdict: Verdict, state: dict) -> Verdict:
    flags = (state.get("verification") or {}).get("hard_flags") or []
    if flags and verdict.risk_level == "low":
        verdict.risk_level = "high"
        verdict.is_scam = True
    verdict.alert_family = verdict.risk_level == "high"
    if state.get("sender_analysis") and verdict.sender_analysis is None:
        try:
            verdict.sender_analysis = SenderAnalysis(**state["sender_analysis"])
        except Exception:
            pass
    return verdict


def _fallback_verdict(state: dict, error: str | None = None) -> Verdict:
    sa_dict = state.get("sender_analysis") or {}
    flags = (state.get("verification") or {}).get("hard_flags") or []
    reasons = sa_dict.get("reasons") or []
    is_scam = bool(flags or reasons)
    lang = guess_language(resolved_text(state))

    if is_scam:
        why_en = "This message shows clear signs of impersonation. " + (reasons[0] if reasons else "The sender or links do not match the company they claim to be.")
        why_zh = "这条信息有明显的假冒迹象。" + ("发件人或链接与其声称的公司不符。" if not reasons else "")
        act_en = "Do not click, reply, or pay. Check with family or call the official number on the back of your card."
        act_zh = "不要点击、回复或付款。请与家人核实，或拨打卡片背面的官方电话。"
        risk = "high"
    else:
        why_en = "No strong scam signals were detected, but stay cautious."
        why_zh = "未发现明显的诈骗信号，但仍请保持警惕。"
        act_en = "If anything feels off, check with family before acting."
        act_zh = "如有可疑，请先与家人核实再行动。"
        risk = "low"

    return Verdict(
        risk_level=risk,
        is_scam=is_scam,
        confidence=0.75 if is_scam else 0.4,
        tactics=flags,
        scam_category="phishing" if is_scam else None,
        explanation_en=why_en,
        explanation_zh=why_zh,
        action_en=act_en,
        action_zh=act_zh,
        sender_analysis=SenderAnalysis(**sa_dict) if sa_dict else None,
        input_language=lang,
        alert_family=risk == "high",
    )


async def run(state: dict) -> dict:
    if not settings.llm_configured:
        return {"verdict": _fallback_verdict(state)}

    user = build_synthesize_user_message(state)
    verification = state.get("verification") or {}
    if verification.get("hard_flags"):
        user += f"\n\nDETERMINISTIC HARD FLAGS (must be treated as strong evidence): {verification['hard_flags']}"

    try:
        llm = structured_llm(Verdict, "brain")
        verdict = await llm.ainvoke(
            [
                {"role": "system", "content": SYNTHESIZE_SYSTEM},
                {"role": "user", "content": user},
            ]
        )
        return {"verdict": _escalate_with_hard_flags(verdict, state)}
    except Exception:
        return {"verdict": _fallback_verdict(state)}
