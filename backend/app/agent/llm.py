"""LLM factory — Kimi k2.6 by default, TokenRouter by env flip (both OpenAI-compatible)."""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.core.config import settings


def make_llm(role: str = "brain") -> ChatOpenAI:
    """role: 'brain' (synthesize/analyze) | 'triage' (cheap intent classification).

    Note: kimi-k2.6 (thinking model) only accepts temperature=1; lower values are rejected
    with a 400. Configurable via LLM_TEMPERATURE if you point at a model that allows others.
    """
    model = settings.LLM_MODEL_TRIAGE if role == "triage" else settings.LLM_MODEL_BRAIN
    return ChatOpenAI(
        model=model,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY or "missing",
        temperature=settings.LLM_TEMPERATURE,
        timeout=60,
        max_retries=2,
    )


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
