import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
from uuid import UUID

from database import get_db
from models import Transaction, Account, User
from auth import get_current_user, CurrentUser
from keycloak_auth import verify_token
router = APIRouter(prefix="/transactions", tags=["Transactions"])


async def get_account_by_username(username: str, db: AsyncSession):
    result = await db.execute(
        select(Account)
        .join(User)
        .where(User.username == username)
        .options(selectinload(Account.user))
    )
    return result.scalar_one_or_none()


def format_transaction(t: Transaction, role: str) -> dict:
    base = {
        "id": str(t.id),
        "amount": t.amount,
        "status": t.status,
        "timestamp": t.timestamp.isoformat(),
    }

    # customers see masked account numbers
    if role == "customer":
        base["from_account"] = "XXXX-XXXX-" + t.from_account.account_number[-4:]
        base["to_account"] = "XXXX-XXXX-" + t.to_account.account_number[-4:]
        return base

    # tellers see masked numbers but with owner name
    if role == "teller":
        base["from_account"] = "XXXX-XXXX-" + t.from_account.account_number[-4:]
        base["to_account"] = "XXXX-XXXX-" + t.to_account.account_number[-4:]
        base["from_owner"] = t.from_account.user.username
        base["to_owner"] = t.to_account.user.username
        return base

    # managers and admins see everything
    base["from_account"] = t.from_account.account_number
    base["to_account"] = t.to_account.account_number
    base["from_owner"] = t.from_account.user.username
    base["to_owner"] = t.to_account.user.username
    return base


@router.get("/")
async def get_transactions(
    status: Optional[str] = Query(None, description="Filter by status: success, failed, flagged"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    query = select(Transaction).options(
        selectinload(Transaction.from_account).selectinload(Account.user),
        selectinload(Transaction.to_account).selectinload(Account.user)
    )

    # customers only see their own transactions
    if current_user.role == "customer":
        my_account = await get_account_by_username(current_user.username, db)
        if not my_account:
            return {"transactions": [], "total": 0}
        query = query.where(
            or_(
                Transaction.from_account_id == my_account.id,
                Transaction.to_account_id == my_account.id
            )
        )

    # tellers only see their own transactions too
    elif current_user.role == "teller":
        my_account = await get_account_by_username(current_user.username, db)
        if my_account:
            query = query.where(
                or_(
                    Transaction.from_account_id == my_account.id,
                    Transaction.to_account_id == my_account.id
                )
            )

    # filter by status if provided
    if status:
        query = query.where(Transaction.status == status)

    query = query.order_by(Transaction.timestamp.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return {
        "transactions": [format_transaction(t, current_user.role) for t in transactions],
        "count": len(transactions)
    }


@router.get("/{transaction_id}")
async def get_transaction_by_id(
    transaction_id: UUID,
    current_user: CurrentUser = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == transaction_id)
        .options(
            selectinload(Transaction.from_account).selectinload(Account.user),
            selectinload(Transaction.to_account).selectinload(Account.user)
        )
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # customers can only view their own transactions
    if current_user.role == "customer":
        my_account = await get_account_by_username(current_user.username, db)
        if not my_account:
            raise HTTPException(status_code=403, detail="Access denied")
        if transaction.from_account_id != my_account.id and \
           transaction.to_account_id != my_account.id:
            raise HTTPException(status_code=403, detail="Access denied")

    return format_transaction(transaction, current_user.role)


@router.get("/flagged/all")
async def get_flagged_transactions(
    current_user: CurrentUser = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(Transaction)
        .where(Transaction.status == "flagged")
        .options(
            selectinload(Transaction.from_account).selectinload(Account.user),
            selectinload(Transaction.to_account).selectinload(Account.user)
        )
        .order_by(Transaction.timestamp.desc())
    )
    transactions = result.scalars().all()

    return {
        "flagged_transactions": [format_transaction(t, current_user.role) for t in transactions],
        "count": len(transactions)
    }