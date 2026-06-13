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


def _checks_path(key) -> Path:
    return BASE / f"{_safe(key)}.checks.md"


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


def load_checks(key) -> str:
    p = _checks_path(key)
    try:
        return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception:
        return ""


def append_check(key, entry: str, keep: int = 8) -> None:
    """Append a one-line scam-analysis summary, keeping only the last `keep` entries.

    Stored separately from the companion-managed profile so a chat-turn rewrite can't drop it.
    """
    try:
        lines = [l for l in load_checks(key).splitlines() if l.strip()]
        lines.append(entry.strip())
        BASE.mkdir(parents=True, exist_ok=True)
        _checks_path(key).write_text("\n".join(lines[-keep:]), encoding="utf-8")
    except Exception:
        pass
