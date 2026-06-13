"""The graph compiles and runs end-to-end without an LLM key (deterministic fallback)."""
from __future__ import annotations

import pytest

from app.agent.graph import get_graph


@pytest.mark.asyncio
async def test_graph_compiles_and_runs_email_without_llm():
    graph = get_graph()
    result = await graph.ainvoke(
        {
            "source": {"channel": "email", "sender_raw": '"DBS Bank" <alerts@dbs-verify.ru>'},
            "raw_text": "Your DBS account is suspended. Verify now.",
            "email_headers": {"From": '"DBS Bank" <alerts@dbs-verify.ru>'},
        }
    )
    verdict = result["verdict"]
    # forensics alone (no LLM) must still flag the impostor sender as a scam
    assert verdict.is_scam is True
    assert verdict.risk_level == "high"
    assert verdict.explanation_en and verdict.explanation_zh


@pytest.mark.asyncio
async def test_set_language_heuristic_short_circuits():
    graph = get_graph()
    result = await graph.ainvoke(
        {"source": {"channel": "telegram"}, "raw_text": "please reply in english only"}
    )
    assert result.get("intent") == "set_language"
    assert "en" in (result.get("pref_languages") or [])
