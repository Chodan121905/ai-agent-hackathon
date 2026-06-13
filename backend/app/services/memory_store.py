"""Per-person memory as a simple markdown file (one memory.md per person).

The companion reads it for context and rewrites it after each chat turn. Stored under
backend/memory/<person>.md (gitignored — it holds personal data).
"""
from __future__ import annotations

import re
from pathlib import Path

BASE = Path(__file__).resolve().parents[2] / "memory"  # backend/memory


def _safe(key) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(key))[:64] or "anon"


def path_for(key) -> Path:
    return BASE / f"{_safe(key)}.md"


def load(key) -> str:
    p = path_for(key)
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:
        return ""


def save(key, content: str) -> None:
    try:
        BASE.mkdir(parents=True, exist_ok=True)
        path_for(key).write_text((content or "")[:8000], encoding="utf-8")
    except Exception:
        pass
