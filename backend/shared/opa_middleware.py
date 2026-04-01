import sys
import os

#from httpx import request

sys.path.append(os.path.dirname(__file__))

from fastapi import HTTPException, Request, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

# Import your DB session maker and our new Keycloak verifier
from database import get_db  # Assuming your session dependency is here
from keycloak_auth import verify_token

from models import User, AuditLog, Alert
from opa_client import evaluate_policy
from sqlalchemy import desc
from datetime import datetime
from models import AuditLog


# ==========================================
# KEEP YOUR EXISTING FUNCTION EXACTLY AS IS
# ==========================================
async def enforce_policy(
    username: str,
    role: str,
    path: str,
    method: str,
    ip: str,
    db: AsyncSession,
    device_id: str = None,
    amount: float = 0.0,
    mfa_verified: bool = False
):
    # check if user is blocked in DB
    result = await db.execute(
        select(User).where(User.username == username)
    )
    user = result.scalar_one_or_none()
    is_blocked = user.is_blocked if user else False

    # check if device is registered
    device_registered = False
    if device_id:
        from models import RegisteredDevice
        device_result = await db.execute(
            select(RegisteredDevice).where(
                RegisteredDevice.user_id == user.id,
                RegisteredDevice.device_fingerprint == device_id
            )
        )
        device_registered = device_result.scalar_one_or_none() is not None
    
    # --- IMPOSSIBLE TRAVEL CHECK ---
    # Find the most recent audit log for this user
    last_log_query = await db.execute(
        select(AuditLog)
        .where(AuditLog.username == username)
        .order_by(desc(AuditLog.timestamp))
        .limit(1)
    )
    last_log = last_log_query.scalar_one_or_none()

    # Default values if this is their first time logging in
    last_ip = ip 
    minutes_since = 99999 

    if last_log and last_log.timestamp:
        last_ip = last_log.ip
        # Calculate how many minutes have passed since their last action
        time_diff = datetime.utcnow() - last_log.timestamp
        minutes_since = time_diff.total_seconds() / 60
    # -------------------------------

    # call OPA
    opa_result = await evaluate_policy(
        user=username,
        role=role,
        path=path,
        method=method,
        ip=ip,
        device_registered=device_registered,
        last_ip=last_ip,
        minutes_since_last_action=minutes_since,
        is_blocked=is_blocked,
        amount=amount,
        device_id=device_id,
        mfa_verified=mfa_verified
    )

    decision = opa_result["decision"]
    score = opa_result["score"]
    reasons = opa_result["reasons"]
    reasons_str = ", ".join(reasons)

    # write audit log
    log = AuditLog(
        timestamp=datetime.utcnow(),
        username=username,
        role=role,
        path=path,
        method=method,
        ip=ip,
        device_id=device_id,
        risk_score=score,
        decision=decision,
        reasons=reasons_str,
        response_status=None
    )
    db.add(log)

    # write alert if blocked
    if decision == "block":
        alert = Alert(
            timestamp=datetime.utcnow(),
            username=username,
            risk_score=score,
            reasons=reasons_str,
            resolved=False
        )
        db.add(alert)

    await db.commit()

    # act on decision
    if decision == "block":
        raise HTTPException(
            status_code=403,
            detail={
                "decision": "block",
                "score": score,
                "reasons": reasons
            }
        )

    if decision == "step_up":
        raise HTTPException(
            status_code=401,
            detail={
                "decision": "step_up",
                "score": score,
                "reasons": reasons
            }
        )

    # allow — return context for the endpoint to use
    return {
        "decision": "allow",
        "score": score,
        "device_registered": device_registered
    }


# ==========================================
# ADD THIS NEW BRIDGE AT THE BOTTOM
# ==========================================
async def check_opa_policy(
    request: Request,
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """
    This intercepts the request, decodes the token, grabs the IP,
    and feeds it all into your robust enforce_policy engine.
    """
    # 1. Extract Identity from the verified Keycloak token
    username = token_payload.get("preferred_username")
    roles = token_payload.get("realm_access", {}).get("roles", [])
    
    # Simple role extraction
    primary_role = "customer" if "customer" in roles else "user"

    # 2. Extract Context from the physical HTTP Request
    client_ip = request.client.host
    path = request.url.path
    method = request.method
    
    # 3. Look for a device ID cookie (we will implement this on the frontend later)
    device_id = request.cookies.get("device_id")
    has_mfa = request.cookies.get("mfa_cleared") == "true"
    # 4. Run your engine!
    enforcement_result = await enforce_policy(
        username=username,
        role=primary_role,
        path=path,
        method=method,
        ip=client_ip,
        db=db,
        device_id=device_id,
        amount=0.0,
        mfa_verified=has_mfa
    )
    
    # If it didn't raise an exception, they are allowed in!
    return {
        "username": username,
        "opa_result": enforcement_result
    }