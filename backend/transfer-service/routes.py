import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from fastapi import APIRouter, Depends, HTTPException, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from models import Account, Transaction, User, AuditLog
from database import get_db
from keycloak_auth import verify_token
from opa_middleware import enforce_policy

router = APIRouter(prefix="/transfer", tags=["Transfer"])

async def get_account_by_username(username: str, db: AsyncSession):
    result = await db.execute(
        select(Account)
        .join(User)
        .where(User.username == username)
        .options(selectinload(Account.user))
    )
    return result.scalar_one_or_none()

@router.post("/")
async def make_transfer(
    request: Request,
    to_username: str = Body(..., embed=True),
    amount: float = Body(..., embed=True),
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    # 1. Extract Identity & Roles from Keycloak Token
    username = token_payload.get("preferred_username")
    roles = token_payload.get("realm_access", {}).get("roles", [])
    
    # Safely extract the highest priority role
    role_priority = ["admin", "manager", "teller", "customer"]
    primary_role = "customer"
    for r in role_priority:
        if r in roles:
            primary_role = r
            break

    if primary_role == "admin":
        raise HTTPException(status_code=403, detail="Admins cannot initiate transfers")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero")
    if to_username == username:
        raise HTTPException(status_code=400, detail="Cannot transfer to your own account")

    # 2. Extract Context (IP, Device, MFA)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    device_id = request.cookies.get("device_id")
    is_device_registered = True if device_id else False
    has_mfa = request.cookies.get("mfa_cleared") == "true"

    # 3. OPA Zero Trust Check
    auth_context = await enforce_policy(
        username=username,
        role=primary_role,
        path=request.url.path,
        method=request.method,
        ip=client_ip,
        db=db,
        device_id=is_device_registered,
        amount=amount,
        mfa_verified=has_mfa
    )

    # 4. Database Business Logic
    sender_account = await get_account_by_username(username, db)
    if not sender_account:
        raise HTTPException(status_code=404, detail="Sender account not found")

    receiver_account = await get_account_by_username(to_username, db)
    if not receiver_account:
        raise HTTPException(status_code=404, detail="Receiver account not found")

    if sender_account.balance < amount:
        raise HTTPException(status_code=400, detail=f"Insufficient balance. Available: ₹{sender_account.balance:,.2f}")

    # Process Transfer
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
        "from": username,
        "to": to_username,
        "amount": amount,
        "remaining_balance": sender_account.balance,
        "transaction_id": str(transaction.id),
        "security_score": auth_context["score"],
        "timestamp": transaction.timestamp.isoformat()
    }


@router.get("/history")
async def get_transfer_history(
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    username = token_payload.get("preferred_username")
    roles = token_payload.get("realm_access", {}).get("roles", [])
    
    my_account = await get_account_by_username(username, db)

    # Managers and admins see all transactions
    if "manager" in roles or "admin" in roles:
        result = await db.execute(
            select(Transaction)
            .options(
                selectinload(Transaction.from_account),
                selectinload(Transaction.to_account)
            )
            .order_by(Transaction.timestamp.desc())
        )
        transactions = result.scalars().all()

    # Customers and tellers see only their own
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

@router.get("/audit")
async def get_audit_logs(
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    # 1. Enforce RBAC
    roles = token_payload.get("realm_access", {}).get("roles", [])
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Only admins can view security logs")

    # 2. Fetch the latest 50 security events
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(50)
    )
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat(),
                "username": log.username,
                "ip": log.ip,
                "risk_score": log.risk_score,
                "decision": log.decision,
                "reasons": log.reasons
            }
            for log in logs
        ]
    }