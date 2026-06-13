"""Build & compile the multi-phase LangGraph agent (PLAN §5).

Design note (deviation from the PLAN sketch, for simplicity): the graph is a PURE
analysis pipeline ending at `synthesize`. The side-effects the PLAN drew as a `decide`/
`alert_family` node (persisting the report, messaging the family) are performed in the
service layer (check_service + alert_service), which is where the DB session and the
Telegram bot are available. The agent stays stateless and easy to test.
"""
from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.agent.nodes import analyze, companion, extract, intake, intent, synthesize, verify
from app.agent.state import GraphState


def build_graph():
    g = StateGraph(GraphState)

    g.add_node("intake", intake.run)
    g.add_node("ocr", extract.ocr)
    g.add_node("transcribe", extract.transcribe)
    g.add_node("link_intel", extract.link_intel)
    g.add_node("intent", intent.run)
    g.add_node("set_language", intent.set_language)
    g.add_node("chat", companion.run)
    g.add_node("analyze", analyze.run)
    g.add_node("verify", verify.run)
    g.add_node("synthesize", synthesize.run)

    g.add_edge(START, "intake")

    # voice/image/link become text/intel first; plain text goes straight to the intent check
    g.add_conditional_edges(
        "intake",
        extract.route_by_modality,
        {"image": "ocr", "voice": "transcribe", "link": "link_intel", "text": "intent"},
    )
    for n in ("ocr", "transcribe", "link_intel"):
        g.add_edge(n, "intent")

    # language request → set_language; casual talk → chat; otherwise fan out to the swarm
    def route_intent(state: dict):
        i = state.get("intent")
        if i == "set_language":
            return "set_language"
        if i in ("chat", "help"):
            return "chat"
        return ["analyze", "verify"]

    g.add_conditional_edges(
        "intent",
        route_intent,
        {"set_language": "set_language", "chat": "chat", "analyze": "analyze", "verify": "verify"},
    )
    g.add_edge("set_language", END)
    g.add_edge("chat", END)

    g.add_edge("analyze", "synthesize")
    g.add_edge("verify", "synthesize")
    g.add_edge("synthesize", END)

    return g.compile()


@lru_cache
def get_graph():
    """Compile once and reuse (the graph is stateless)."""
    return build_graph()
