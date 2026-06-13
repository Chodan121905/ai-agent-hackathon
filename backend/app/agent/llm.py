"""LLM factory — Kimi k2.6 by default, TokenRouter by env flip (both OpenAI-compatible)."""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings


def make_llm(role: str = "brain") -> ChatOpenAI:
    """role: 'brain' (synthesize) | 'triage' (cheap intent classification).

    kimi-k2.6 'thinking' mode is accurate but ~50s/call; disabling it drops to ~4s. The model
    requires temperature 1.0 with thinking on and 0.6 with it off, so we set both together.
    """
    model = settings.LLM_MODEL_TRIAGE if role == "triage" else settings.LLM_MODEL_BRAIN
    kwargs = dict(
        model=model,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY or "missing",
        timeout=60,
        max_retries=2,
    )
    if settings.LLM_THINKING:
        kwargs["temperature"] = 1.0
    else:
        kwargs["temperature"] = 0.6
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    return ChatOpenAI(**kwargs)


def structured_llm(schema, role: str = "brain"):
    """Bind a Pydantic schema for structured output.

    Tries json_schema first (Kimi supports it); falls back to function-calling if the
    provider rejects the method.
    """
    llm = make_llm(role)
    try:
        return llm.with_structured_output(schema, method="json_schema")
    except Exception:  # pragma: no cover - provider capability differences
        return llm.with_structured_output(schema)
