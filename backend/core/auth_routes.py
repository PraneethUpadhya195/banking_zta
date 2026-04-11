from fastapi import APIRouter, Depends, Response, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
import uuid

from database import get_db
from models import User
# Ensure you have a RegisteredDevice model if you haven't created it yet!
from models import RegisteredDevice 
from keycloak_auth import verify_token

import pyotp
import qrcode
import base64
from io import BytesIO

router = APIRouter(prefix="/security", tags=["Security"])

@router.post("/register-device")
async def register_device(
    response: Response,
    request: Request,
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    username = token_payload.get("preferred_username")
    
    # Get the user's UUID from the database
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    device_id = str(uuid.uuid4())
    
    # ACTUALLY SAVE TO THE DATABASE
    new_device = RegisteredDevice(
        user_id=user.id, 
        device_fingerprint=device_id, 
        label="Browser Session"
    )
    db.add(new_device)
    await db.commit()

    # Drop the HttpOnly cookie
    response.set_cookie(
        key="device_id",
        value=device_id,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 365
    )
    
    return {"message": "Device registered securely", "device_id": device_id}

@router.post("/setup-mfa")
async def setup_mfa(
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """Generates a unique seed and a QR code for Google Authenticator"""
    username = token_payload.get("preferred_username")
    
    # 1. Generate a random 16-character Base32 secret
    secret = pyotp.random_base32()
    
    # 2. Save the secret to the user's database row
    await db.execute(
        update(User).where(User.username == username).values(totp_secret=secret)
    )
    await db.commit()

    # 3. Create the Google Authenticator URI
    # This formats it nicely in the app as "Zero Trust Bank (customer1)"
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=username,
        issuer_name="Zero Trust Bank"
    )

    # 4. Generate a QR code image in memory
    qr = qrcode.make(totp_uri)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    
    # 5. Convert the image to a Base64 string to send to React
    qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return {
        "message": "MFA setup initiated", 
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "manual_secret": secret # Just in case their camera is broken
    }


@router.post("/verify-mfa")
async def verify_mfa(
    payload: dict,
    response: Response,
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """Mathematically verifies the 6-digit code from the user's phone"""
    provided_code = payload.get("code")
    username = token_payload.get("preferred_username")
    
    # 1. Fetch the user's unique secret from the DB
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()

    if not user or not user.totp_secret:
        raise HTTPException(status_code=400, detail="MFA is not set up for this user.")

    # 2. THE REAL MATH: Verify the code
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(provided_code):
        raise HTTPException(status_code=401, detail="Invalid or expired MFA Code")

    # 3. Issue the clearance cookie
    response.set_cookie(
        key="mfa_cleared", value="true", httponly=True, secure=False, samesite="lax", max_age=300
    )
    
    return {"message": "Identity verified. You may retry the transaction."}