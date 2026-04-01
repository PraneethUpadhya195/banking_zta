import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import get_db
from models import Account, User
from masking import apply_mask
from auth import get_current_user, CurrentUser
from opa_middleware import enforce_policy

router = APIRouter(prefix="/account", tags=["Account"])


@router.get("/me")
async def get_my_account(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    await enforce_policy(
        username=current_user.username,
        role=current_user.role,
        path="/account/me",
        method="GET",
        ip=current_user.ip,
        db=db,
        device_id=current_user.device_id
    )

    result = await db.execute(
        select(Account)
        .join(User)
        .where(User.username == current_user.username)
        .options(selectinload(Account.user))
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    raw = {
        "account_number": account.account_number,
        "balance": account.balance,
        "owner": account.user.username
    }

    return apply_mask(raw, current_user.role)


@router.get("/all")
async def get_all_accounts(
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("teller", "manager", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    await enforce_policy(
        username=current_user.username,
        role=current_user.role,
        path="/account/all",
        method="GET",
        ip=current_user.ip,
        db=db,
        device_id=current_user.device_id
    )

    result = await db.execute(
        select(Account).options(selectinload(Account.user))
    )
    accounts = result.scalars().all()

    return [
        apply_mask(
            {
                "account_number": acc.account_number,
                "balance": acc.balance,
                "owner": acc.user.username
            },
            current_user.role
        )
        for acc in accounts
    ]


@router.get("/{username}")
async def get_account_by_username(
    username: str,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("teller", "manager", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    await enforce_policy(
        username=current_user.username,
        role=current_user.role,
        path=f"/account/{username}",
        method="GET",
        ip=current_user.ip,
        db=db,
        device_id=current_user.device_id
    )

    result = await db.execute(
        select(Account)
        .join(User)
        .where(User.username == username)
        .options(selectinload(Account.user))
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    raw = {
        "account_number": account.account_number,
        "balance": account.balance,
        "owner": account.user.username
    }

    return apply_mask(raw, current_user.role)