import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime

from database import get_db
from models import Account, Transaction, User, AuditLog
from auth import get_current_user, CurrentUser

router = APIRouter(prefix="/transfer", tags=["Transfer"])

STEP_UP_THRESHOLD = 100000.0


async def get_account_by_username(username: str, db: AsyncSession):
    result = await db.execute(
        select(Account)
        .join(User)
        .where(User.username == username)
        .options(selectinload(Account.user))
    )
    return result.scalar_one_or_none()


from opa_middleware import enforce_policy
from fastapi import Request

@router.post("/")
async def make_transfer(
    to_username: str,
    amount: float,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Admins cannot initiate transfers"
        )

    if amount <= 0:
        raise HTTPException(
            status_code=400,
            detail="Amount must be greater than zero"
        )

    if to_username == current_user.username:
        raise HTTPException(
            status_code=400,
            detail="Cannot transfer to your own account"
        )

    # OPA check — passes amount for scoring
    await enforce_policy(
        username=current_user.username,
        role=current_user.role,
        path="/transfer/",
        method="POST",
        ip=current_user.ip,
        db=db,
        device_id=current_user.device_id,
        amount=amount
    )

    sender_account = await get_account_by_username(current_user.username, db)
    if not sender_account:
        raise HTTPException(status_code=404, detail="Sender account not found")

    receiver_account = await get_account_by_username(to_username, db)
    if not receiver_account:
        raise HTTPException(status_code=404, detail="Receiver account not found")

    if sender_account.balance < amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: ₹{sender_account.balance:,.2f}"
        )

    sender_account.balance -= amount
    receiver_account.balance += amount

    transaction = Transaction(
        from_account_id=sender_account.id,
        to_account_id=receiver_account.id,
        amount=amount,
        status="success",
        timestamp=datetime.utcnow()
    )

    db.add(transaction)
    await db.commit()
    await db.refresh(sender_account)

    return {
        "message": "Transfer successful",
        "from": current_user.username,
        "to": to_username,
        "amount": amount,
        "remaining_balance": sender_account.balance,
        "transaction_id": str(transaction.id),
        "timestamp": transaction.timestamp.isoformat()
    }


@router.get("/history")
async def get_transfer_history(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # get current user's account first
    my_account = await get_account_by_username(current_user.username, db)

    # managers and admins see all transactions
    if current_user.role in ("manager", "admin"):
        result = await db.execute(
            select(Transaction)
            .options(
                selectinload(Transaction.from_account),
                selectinload(Transaction.to_account)
            )
            .order_by(Transaction.timestamp.desc())
        )
        transactions = result.scalars().all()

    # customers and tellers see only their own
    else:
        if not my_account:
            return {"transactions": []}

        result = await db.execute(
            select(Transaction)
            .where(
                (Transaction.from_account_id == my_account.id) |
                (Transaction.to_account_id == my_account.id)
            )
            .options(
                selectinload(Transaction.from_account),
                selectinload(Transaction.to_account)
            )
            .order_by(Transaction.timestamp.desc())
        )
        transactions = result.scalars().all()

    return {
        "transactions": [
            {
                "id": str(t.id),
                "from_account": t.from_account.account_number,
                "to_account": t.to_account.account_number,
                "amount": t.amount,
                "status": t.status,
                "timestamp": t.timestamp.isoformat()
            }
            for t in transactions
        ]
    }