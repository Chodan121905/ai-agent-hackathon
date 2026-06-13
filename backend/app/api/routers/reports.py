"""GET /api/v1/reports — history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_session
from app.models.tables import Report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", operation_id="list_reports")
async def list_reports(limit: int = 50, session: AsyncSession = Depends(get_session)) -> list[Report]:
    res = await session.execute(select(Report).order_by(Report.created_at.desc()).limit(limit))
    return list(res.scalars().all())


@router.get("/{report_id}", operation_id="get_report")
async def get_report(report_id: int, session: AsyncSession = Depends(get_session)) -> Report:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report
