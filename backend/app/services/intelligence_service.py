"""Trends / stats over the reports table (PLAN §10). Plain aggregation, no analytics infra."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.models.tables import Report


async def _recent(session, days: int) -> list[Report]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    res = await session.execute(select(Report).where(Report.created_at >= cutoff))
    return list(res.scalars().all())


async def trends(session, days: int = 7) -> dict:
    rows = await _recent(session, days)
    by_category: Counter = Counter()
    by_risk: Counter = Counter()
    for r in rows:
        by_risk[r.risk_level] += 1
        if r.is_scam:
            by_category[r.scam_category or "other"] += 1
    return {
        "window_days": days,
        "total_checked": len(rows),
        "scams_detected": sum(1 for r in rows if r.is_scam),
        "top_categories": by_category.most_common(10),
        "by_risk": dict(by_risk),
    }


async def stats(session) -> dict:
    res = await session.execute(select(Report))
    rows = list(res.scalars().all())
    by_channel: Counter = Counter()
    for r in rows:
        by_channel[r.channel] += 1
    return {
        "total_reports": len(rows),
        "total_scams": sum(1 for r in rows if r.is_scam),
        "by_channel": dict(by_channel),
    }
