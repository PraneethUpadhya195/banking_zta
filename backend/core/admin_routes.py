import os
import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models import User, Account
from keycloak_auth import verify_token

router = APIRouter(prefix="/admin", tags=["Admin Operations"])

KEYCLOAK_URL = "http://localhost:8080"
REALM = "banking"
# Use Keycloak's built-in admin client
ADMIN_CLIENT_ID = "admin-cli" 
# For this demo, we use your master admin credentials to let Python do the work
# In production, you would use a dedicated Service Account Client Secret
KEYCLOAK_ADMIN_USER = "admin1" 
KEYCLOAK_ADMIN_PASS = "password123" 

async def get_keycloak_admin_token():
    """Fetches a temporary Admin token so Python can create users in Keycloak"""
    url = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
    
    payload = {
        "client_id": "admin-cli",
        # THIS MUST BE YOUR KEYCLOAK WEB CONSOLE LOGIN
        # Change these if you set a different admin password when you installed Keycloak
        "username": "admin", 
        "password": "admin", 
        "grant_type": "password"
    }
    
    response = requests.post(url, data=payload)
    
    # --- NEW DEBUGGING LINE ---
    print(f"KEYCLOAK RESPONSE CODE: {response.status_code}")
    print(f"KEYCLOAK RESPONSE TEXT: {response.text}")
    # --------------------------

    if response.status_code != 200:
        # We will now send Keycloak's actual complaint to the React frontend
        raise HTTPException(status_code=500, detail=f"Keycloak Auth Failed: {response.text}")
        
    return response.json().get("access_token")


@router.post("/create-customer")
async def create_new_customer(
    new_username: str,
    starting_balance: float = 0.0,
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    # 1. ENFORCE MANAGER ROLE
    role = token_payload.get("normalized_role")
    if role not in ["manager", "admin"]:
        raise HTTPException(status_code=403, detail="Only Managers and Admins can create customers.")

    # 2. CREATE IN KEYCLOAK
    admin_token = await get_keycloak_admin_token()
    headers = {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}
    
   # A. Create the User with a COMPLETE profile so Keycloak doesn't block them
    user_payload = {
        "username": new_username,
        "enabled": True,
        "emailVerified": True, # Skips the "Verify Email" action
        "firstName": "Bank",
        "lastName": "User",
        "email": f"{new_username}@trustedbank.com", # Dummy email
        "credentials": [{"type": "password", "value": "password123", "temporary": False}]
    }
    create_req = requests.post(f"{KEYCLOAK_URL}/admin/realms/{REALM}/users", json=user_payload, headers=headers)
    
    if create_req.status_code not in [201, 409]: # 201 Created, 409 Conflict (Already exists)
        raise HTTPException(status_code=500, detail=f"Keycloak Error: {create_req.text}")
    
    if create_req.status_code == 409:
        raise HTTPException(status_code=400, detail="User already exists in Keycloak")

    # B. Assign the 'customer' role (Requires finding the Role ID and User ID first in a real setup)
    # Note: To keep the demo fast, we assume the user logs in as a default customer if role mapping isn't strict. 
    # For a perfect implementation, you'd make two more API calls here to map the exact role UUID.

    # 3. CREATE IN POSTGRES DATABASE
    try:
        new_user = User(username=new_username, hashed_password="keycloak_managed", role="customer")
        db.add(new_user)
        await db.flush() # Get the new user ID

        # Grab just the first 8 characters of the UUID to keep it short
        short_id = str(new_user.id).split('-')[0].upper()

        new_account = Account(
            user_id=new_user.id,
            account_number=f"ACC{short_id}999", # E.g., ACC10E2E75F999 (14 chars)
            balance=starting_balance
        )
        db.add(new_account)
        await db.commit()

        return {"message": f"Customer {new_username} successfully created in Identity Provider and Database!"}
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database Error during creation")