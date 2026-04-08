import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy import select
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

from database import get_db, AsyncSessionLocal
from models import User
from routes import router
from auth_routes import router as auth_router

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

app = FastAPI(title="Transfer Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    response = await call_next(request)
    return response

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
        return {
            "access_token": token,
            "token_type": "bearer",
            "role": user.role,
            "username": user.username
        }

# Inject the cleaned-up router
app.include_router(router)
app.include_router(auth_router)