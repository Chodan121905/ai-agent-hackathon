"""Link / domain verification + brand-domain truth check via Bright Data (PLAN §8).

Uses the unified `POST https://api.brightdata.com/request` endpoint (Unlocker for raw
fetch, SERP for search). All fetched HTML is treated as hostile — we never feed it raw
to the user; only derived signals go forward. Returns "" / {} when not configured.
"""
from __future__ import annotations

import asyncio
import re

import httpx
import tldextract

from app.core.config import settings

_API = "https://api.brightdata.com/request"
_TIMEOUT = 10  # keep Bright Data off the critical path; Daytona is the real link check


async def _request(zone: str, url: str, fmt: str = "raw") -> str:
    if not settings.BRIGHTDATA_API_TOKEN:
        return ""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        r = await client.post(
            _API,
            headers={"Authorization": f"Bearer {settings.BRIGHTDATA_API_TOKEN}"},
            json={"zone": zone, "url": url, "format": fmt},
        )
        r.raise_for_status()
        return r.text


async def domain_intel(url: str) -> dict:
    """Best-effort domain signals for a URL. Always returns a dict (never raises)."""
    ext = tldextract.extract(url)
    registrable = ".".join(p for p in [ext.domain, ext.suffix] if p)
    out: dict = {"url": url, "domain": registrable, "configured": bool(settings.BRIGHTDATA_API_TOKEN)}

    if not settings.BRIGHTDATA_API_TOKEN:
        return out

    async def whois_age():
        try:
            html = await _request(settings.BRIGHTDATA_UNLOCKER_ZONE, f"https://who.is/whois/{registrable}")
            m = re.search(r"(Creat|Register)\w*\s*Date[:\s]+([0-9]{4}-[0-9]{2}-[0-9]{2})", html, re.IGNORECASE)
            return ("created_date", m.group(2)) if m else None
        except Exception:
            return None

    async def scam_mentions():
        try:
            serp = await _request(settings.BRIGHTDATA_SERP_ZONE, f'https://www.google.com/search?q="{registrable}"+scam')
            return ("scam_mentions", len(re.findall(r"scam|phishing|fraud", serp, re.IGNORECASE)))
        except Exception:
            return None

    # Run both lookups concurrently so Bright Data adds ~10s worst case, not 2×.
    for r in await asyncio.gather(whois_age(), scam_mentions()):
        if r:
            out[r[0]] = r[1]

    return out


async def brand_canonical_domain(brand: str) -> str | None:
    """Resolve a brand name to its canonical domain via SERP (feeds §7.3 truth check)."""
    if not settings.BRIGHTDATA_API_TOKEN or not brand:
        return None
    try:
        serp = await _request(settings.BRIGHTDATA_SERP_ZONE, f"https://www.google.com/search?q={brand}+official+site")
        m = re.search(r"https?://(?:www\.)?([a-z0-9.-]+\.[a-z]{2,})", serp, re.IGNORECASE)
        return m.group(1) if m else None
    except Exception:
        return None
