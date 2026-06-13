"""Link/list a monitored inbox (optional; .env EMAIL_OWNER_ELDER_ID covers the demo)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_session
from app.models.tables import EmailAccount
from app.schemas.check import EmailAccountIn

router = APIRouter(prefix="/email-accounts", tags=["email-accounts"])


@router.post("", operation_id="create_email_account")
async def create_email_account(body: EmailAccountIn, session: AsyncSession = Depends(get_session)) -> EmailAccount:
    acct = EmailAccount(elder_id=body.elder_id, email_address=body.email_address, imap_host=body.imap_host)
    session.add(acct)
    await session.commit()
    await session.refresh(acct)
    return acct


@router.get("", operation_id="list_email_accounts")
async def list_email_accounts(session: AsyncSession = Depends(get_session)) -> list[EmailAccount]:
    res = await session.execute(select(EmailAccount))
    return list(res.scalars().all())
