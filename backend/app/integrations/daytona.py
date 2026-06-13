"""Safe link sandbox via Daytona (PLAN §8).

Opens a suspicious URL inside a fresh, disposable sandbox (curl -sSIL to resolve the
redirect chain / final URL / content-type) without touching the user's device or our
host, then deletes the sandbox. Lazily imported; returns {} when not configured.
"""
from __future__ import annotations

import asyncio
import shlex

from app.core.config import settings


def _safe_open_sync(url: str) -> dict:
    from daytona import Daytona, DaytonaConfig  # lazy import (pip package: daytona)

    daytona = Daytona(DaytonaConfig(api_key=settings.DAYTONA_API_KEY))
    sandbox = None
    try:
        sandbox = daytona.create()
        # -s silent, -S show errors, -I headers only, -L follow redirects
        res = sandbox.process.exec(f"curl -sSIL --max-time 15 {shlex.quote(url)}")
        output = getattr(res, "result", "") or getattr(res, "stdout", "") or str(res)
        final_url = url
        content_type = None
        redirects = 0
        for line in output.splitlines():
            low = line.lower()
            if low.startswith("location:"):
                final_url = line.split(":", 1)[1].strip()
                redirects += 1
            elif low.startswith("content-type:"):
                content_type = line.split(":", 1)[1].strip()
        return {
            "sandboxed": True,
            "final_url": final_url,
            "redirects": redirects,
            "content_type": content_type,
            "headers_excerpt": output[:800],
        }
    finally:
        if sandbox is not None:
            try:
                daytona.delete(sandbox)
            except Exception:
                pass


async def safe_open(url: str) -> dict:
    if not settings.DAYTONA_API_KEY:
        return {"sandboxed": False, "reason": "daytona_not_configured"}
    try:
        return await asyncio.to_thread(_safe_open_sync, url)
    except Exception as e:  # pragma: no cover
        return {"sandboxed": False, "reason": f"daytona_error: {e}"}
