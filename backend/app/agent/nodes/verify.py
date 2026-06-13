"""Phase 4b — verify (the deterministic half of the swarm).

Turns forensics + link intel into hard flags, independent of the LLM. Strong flags
escalate the verdict in synthesize even if the wording looks clean.
"""
from __future__ import annotations


async def run(state: dict) -> dict:
    sa = state.get("sender_analysis") or {}
    li = state.get("link_intel") or []

    hard_flags: list[str] = []
    for key in ("display_name_mismatch", "lookalike_domain", "freemail_as_company", "replyto_mismatch"):
        if sa.get(key):
            hard_flags.append(key)
    if sa.get("auth_results") and any(x in sa["auth_results"] for x in ("fail", "none", "softfail")):
        hard_flags.append("auth_failure")

    link_summary: list[dict] = []
    for item in li:
        di = item.get("domain_intel") or {}
        sb = item.get("sandbox") or {}
        if sb.get("redirects", 0) > 0:
            hard_flags.append("link_redirects")
        if di.get("scam_mentions"):
            hard_flags.append("scam_mentions")
        link_summary.append(
            {
                "url": item.get("url"),
                "domain": di.get("domain"),
                "created_date": di.get("created_date"),
                "scam_mentions": di.get("scam_mentions"),
                "final_url": sb.get("final_url"),
                "redirects": sb.get("redirects"),
            }
        )

    return {
        "verification": {
            "hard_flags": sorted(set(hard_flags)),
            "sender_analysis": sa,
            "link_summary": link_summary,
        }
    }
