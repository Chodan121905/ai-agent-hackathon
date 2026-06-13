"""Aggregated trending scams (the B2B data product surface) — PLAN §10."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.services import intelligence_service

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/trends", operation_id="get_trends")
async def get_trends(days: int = 7, session: AsyncSession = Depends(get_session)) -> dict:
    return await intelligence_service.trends(session, days)


@router.get("/stats", operation_id="get_stats")
async def get_stats(session: AsyncSession = Depends(get_session)) -> dict:
    return await intelligence_service.stats(session)
