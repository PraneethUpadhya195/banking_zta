import sys
import os
import json
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import insert

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from database import AsyncSessionLocal
from models import AuditLog
from routes import router

app = FastAPI(title="Account Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    response = await call_next(request)
    return response

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from passlib.context import CryptContext
from jose import jwt
from datetime import timedelta
from models import User
from sqlalchemy import select
from dotenv import load_dotenv

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

@app.post("/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == form_data.username)
        )
        user = result.scalar_one_or_none()

        if not user or not pwd_context.verify(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        expire = datetime.utcnow() + timedelta(
            minutes=int(os.getenv("JWT_EXPIRE_MINUTES", 15))
        )
        token = jwt.encode(
            {"sub": user.username, "role": user.role, "exp": expire},
            SECRET_KEY,
            algorithm=ALGORITHM
        )

        return {"access_token": token, "token_type": "bearer", "role": user.role}

from fastapi import FastAPI, Depends, Request
import sys
import os

# Ensure the shared directory is accessible
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.opa_middleware import check_opa_policy

app = FastAPI()

@app.get("/api/test-auth")
async def test_auth(auth_context: dict = Depends(check_opa_policy)):
    # Note the change from "opa_decision" to "opa_result"
    result_data = auth_context.get("opa_result", {})
    
    return {
        "message": "Access Granted by Zero Trust Engine!",
        "user": auth_context["username"],
        "risk_score": result_data.get("score"),
        "reasons": result_data.get("reasons"),
        "decision": result_data.get("decision")
    }

from fastapi import Body, Response
from models import User, RegisteredDevice # Ensure these are imported from your models file
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shared.keycloak_auth import verify_token
from shared.database import get_db

@app.post("/api/register-device")
async def register_device(
    response: Response,
    device_name: str = Body(..., embed=True),
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db)
):
    username = token_payload.get("preferred_username")
    
    # 1. Find the user in Postgres
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    
    if not user:
        return {"error": "User not found in database"}

    # 2. Generate a unique cryptographic fingerprint for this device
    new_fingerprint = str(uuid.uuid4())

    # 3. Save it to the database
    new_device = RegisteredDevice(
        user_id=user.id,
        device_fingerprint=new_fingerprint,
        label=device_name
    )
    db.add(new_device)
    await db.commit()

    # 4. Set it as an HTTP-Only Cookie so the browser remembers it
    response.set_cookie(
        key="device_id",
        value=new_fingerprint,
        httponly=True,
        samesite="lax",
        max_age=60*60*24*30 # 30 days
    )

    return {
        "message": f"Device '{device_name}' successfully registered!",
        "device_fingerprint": new_fingerprint
    }

app.include_router(router)

