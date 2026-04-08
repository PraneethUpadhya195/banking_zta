from fastapi import APIRouter, Depends, Response, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

from database import get_db
from models import User
# Ensure you have a RegisteredDevice model if you haven't created it yet!
# from models import RegisteredDevice 
from keycloak_auth import verify_token

router = APIRouter(prefix="/security", tags=["Security"])

@router.post("/register-device")
async def register_device(
    response: Response,
    request: Request,
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """
    Called by the frontend upon first successful login. 
    Generates a secure device fingerprint and stores it.
    """
    username = token_payload.get("preferred_username")
    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    
    # Generate a unique cryptographically secure device ID
    device_id = str(uuid.uuid4())
    
    # TODO: Save to your registered_devices table in DB
    # new_device = RegisteredDevice(username=username, device_id=device_id, ip=client_ip)
    # db.add(new_device)
    # await db.commit()

    # Drop an HttpOnly cookie that JS cannot touch
    response.set_cookie(
        key="device_id",
        value=device_id,
        httponly=True,  # Blocks document.cookie access
        secure=False,   # Set to True in production with HTTPS/NGINX
        samesite="lax",
        max_age=60 * 60 * 24 * 365 # 1 year
    )
    
    return {"message": "Device registered securely", "device_id": device_id}


@router.post("/verify-mfa")
async def verify_mfa(
    payload: dict, # Expecting {"code": "123456"}
    response: Response,
    token_payload: dict = Depends(verify_token)
):
    """
    Validates the TOTP code on the backend and issues an HttpOnly clearance cookie.
    """
    provided_code = payload.get("code")
    username = token_payload.get("preferred_username")
    
    # In a real app: verify `provided_code` against a pyotp generated TOTP secret in DB
    # For this demo, we hardcode the validation logic ON THE BACKEND
    if provided_code != "123456":
        raise HTTPException(status_code=401, detail="Invalid MFA Code")

    # Issue the MFA clearance cookie as HttpOnly. 
    # OPA will read this cookie from the incoming headers on the retry request.
    response.set_cookie(
        key="mfa_cleared",
        value="true",
        httponly=True, # Critical: Frontend cannot spoof this now
        secure=False,  # Set to True when NGINX is handling HTTPS
        samesite="lax",
        max_age=300    # Expires in 5 minutes
    )
    
    return {"message": "Identity verified. You may retry the transaction."}