from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import User, Account
from keycloak_auth import verify_token
from masking import mask_account_number  # Your salvaged masking logic!

router = APIRouter(prefix="/accounts", tags=["Account Management"])

@router.get("/me")
async def get_my_account(
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    """Fetches the logged-in user's account details and masks sensitive data."""
    username = token_payload.get("preferred_username")
    
    # 1. Fetch user and account from Postgres
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found in database")
        
    account_result = await db.execute(select(Account).where(Account.user_id == user.id))
    account = account_result.scalars().first()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # 2. Apply Data Masking
    safe_account_number = mask_account_number(account.account_number)

    return {
        "username": user.username,
        "role": token_payload.get("normalized_role"),
        "account_number": safe_account_number,
        "balance": account.balance
    }