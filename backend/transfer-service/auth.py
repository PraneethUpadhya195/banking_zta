import os
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from typing import Optional

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class CurrentUser(BaseModel):
    username: str
    role: str
    device_id: Optional[str] = None
    ip: Optional[str] = None


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme)
) -> CurrentUser:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        return CurrentUser(
            username=username,
            role=role,
            device_id=request.headers.get("X-Device-ID"),
            ip=request.client.host
        )
    except JWTError:
        raise credentials_exception