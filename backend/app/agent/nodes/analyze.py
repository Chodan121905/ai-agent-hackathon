"""Phase 4a — analyze (the LLM half of the swarm): Kimi tactic detection."""
from __future__ import annotations

from app.agent.llm import make_llm
from app.agent.prompts import build_synthesize_user_message
from app.agent.util import resolved_text
from app.core.config import settings

_ANALYZE_SYSTEM = (
    "You are a scam analyst. Read the message and any sender forensics / link intelligence, "
    "then list the manipulation tactics present (urgency, authority impersonation, threat, "
    "secrecy, unusual payment, credential request, too-good-to-be-true, sender/link mismatch, "
    "emotional leverage) with a one-line rationale each. Be concise. This is internal analysis "
    "for a later structured verdict — do not write the final user reply."
)


async def run(state: dict) -> dict:
    if not settings.llm_configured:
        return {"analysis": {"available": False, "reason": "llm_not_configured"}}
    if not resolved_text(state) and not state.get("sender_analysis") and not state.get("link_intel"):
        return {"analysis": {"available": False, "reason": "no_content"}}
    try:
        llm = make_llm("brain")
        resp = await llm.ainvoke(
            [
                {"role": "system", "content": _ANALYZE_SYSTEM},
                {"role": "user", "content": build_synthesize_user_message(state)},
            ]
        )
        return {"analysis": {"available": True, "notes": getattr(resp, "content", str(resp))}}
    except Exception as e:
        return {"analysis": {"available": False, "error": str(e)}}
