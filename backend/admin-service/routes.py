import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime
from uuid import UUID

from database import get_db
from models import User, Account, AuditLog, Alert
from auth import get_current_user, CurrentUser

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─────────────────────────────────────────
# User Management
# ─────────────────────────────────────────

@router.get("/users")
async def get_all_users(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(User).options(selectinload(User.account))
    )
    users = result.scalars().all()

    return {
        "users": [
            {
                "id": str(u.id),
                "username": u.username,
                "role": u.role,
                "is_blocked": u.is_blocked,
                "created_at": u.created_at.isoformat(),
                "account_number": u.account.account_number if u.account else None,
                "balance": u.account.balance if u.account else None
            }
            for u in users
        ]
    }


@router.post("/users/block/{username}")
async def block_user(
    username: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can block users")

    if username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot block yourself")

    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_blocked:
        raise HTTPException(status_code=400, detail="User is already blocked")

    user.is_blocked = True
    await db.commit()

    return {"message": f"User {username} has been blocked successfully"}


@router.post("/users/unblock/{username}")
async def unblock_user(
    username: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can unblock users")

    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_blocked:
        raise HTTPException(status_code=400, detail="User is not blocked")

    user.is_blocked = False
    await db.commit()

    return {"message": f"User {username} has been unblocked successfully"}


# ─────────────────────────────────────────
# Audit Logs
# ─────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    username: Optional[str] = Query(None),
    decision: Optional[str] = Query(None, description="allow, step_up, block"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    query = select(AuditLog).order_by(AuditLog.timestamp.desc())

    if username:
        query = query.where(AuditLog.username == username)
    if decision:
        query = query.where(AuditLog.decision == decision)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "logs": [
            {
                "id": str(log.id),
                "timestamp": log.timestamp.isoformat(),
                "username": log.username,
                "role": log.role,
                "path": log.path,
                "method": log.method,
                "ip": log.ip,
                "device_id": log.device_id,
                "risk_score": log.risk_score,
                "decision": log.decision,
                "reasons": log.reasons,
                "response_status": log.response_status
            }
            for log in logs
        ],
        "count": len(logs)
    }


# ─────────────────────────────────────────
# Alerts
# ─────────────────────────────────────────

@router.get("/alerts")
async def get_alerts(
    resolved: Optional[bool] = Query(None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    query = select(Alert).order_by(Alert.timestamp.desc())

    if resolved is not None:
        query = query.where(Alert.resolved == resolved)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return {
        "alerts": [
            {
                "id": str(a.id),
                "timestamp": a.timestamp.isoformat(),
                "username": a.username,
                "risk_score": a.risk_score,
                "reasons": a.reasons,
                "resolved": a.resolved,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None
            }
            for a in alerts
        ],
        "count": len(alerts)
    }


@router.post("/alerts/resolve/{alert_id}")
async def resolve_alert(
    alert_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(
        select(Alert).where(Alert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.resolved:
        raise HTTPException(status_code=400, detail="Alert already resolved")

    alert.resolved = True
    alert.resolved_at = datetime.utcnow()
    await db.commit()

    return {"message": "Alert resolved successfully"}


# ─────────────────────────────────────────
# Dashboard Summary
# ─────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard_summary(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Access denied")

    # total users
    users_result = await db.execute(select(User))
    users = users_result.scalars().all()
    total_users = len(users)
    blocked_users = sum(1 for u in users if u.is_blocked)

    # total audit logs
    logs_result = await db.execute(select(AuditLog))
    logs = logs_result.scalars().all()
    total_requests = len(logs)
    blocked_requests = sum(1 for l in logs if l.decision == "block")
    stepup_requests = sum(1 for l in logs if l.decision == "step_up")

    # unresolved alerts
    alerts_result = await db.execute(
        select(Alert).where(Alert.resolved == False)
    )
    unresolved_alerts = len(alerts_result.scalars().all())

    return {
        "total_users": total_users,
        "blocked_users": blocked_users,
        "total_requests": total_requests,
        "blocked_requests": blocked_requests,
        "stepup_requests": stepup_requests,
        "unresolved_alerts": unresolved_alerts
    }