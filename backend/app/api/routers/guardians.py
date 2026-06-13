"""Family pairing over REST (the Telegram flow is the primary one; this mirrors it)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.models.tables import GuardianLink
from app.schemas.check import GuardianInviteIn, GuardianInviteOut
from app.services import guardian_service, member_service

router = APIRouter(prefix="/guardians", tags=["guardians"])


@router.post("/invite", response_model=GuardianInviteOut, operation_id="create_guardian_invite")
async def create_invite(body: GuardianInviteIn, session: AsyncSession = Depends(get_session)) -> GuardianInviteOut:
    elder = await member_service.get_user(session, body.elder_id)
    if elder is None:
        raise HTTPException(status_code=404, detail="elder not found")
    link = await guardian_service.create_invite(session, elder)
    return GuardianInviteOut(pairing_code=link.pairing_code, status=link.status)


@router.get("", operation_id="list_guardians")
async def list_guardians(elder_id: int, session: AsyncSession = Depends(get_session)) -> list[GuardianLink]:
    return await guardian_service.list_for_elder(session, elder_id)
