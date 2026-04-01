from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID


# ─────────────────────────────────────────
# Auth
# ─────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str
    device_id: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str

class CurrentUser(BaseModel):
    username: str
    role: str
    device_id: Optional[str] = None
    ip: Optional[str] = None


# ─────────────────────────────────────────
# User
# ─────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    password: str
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed = {"customer", "teller", "manager", "admin"}
        if v not in allowed:
            raise ValueError(f"Role must be one of {allowed}")
        return v

class UserResponse(BaseModel):
    id: UUID
    username: str
    role: str
    is_blocked: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Account
# ─────────────────────────────────────────

class AccountResponse(BaseModel):
    id: UUID
    account_number: str
    balance: float
    created_at: datetime

    class Config:
        from_attributes = True

class AccountResponseMasked(BaseModel):
    account_number: str
    balance: float

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Transaction
# ─────────────────────────────────────────

class TransferRequest(BaseModel):
    to_account_number: str
    amount: float

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return v

class TransactionResponse(BaseModel):
    id: UUID
    from_account_id: UUID
    to_account_id: UUID
    amount: float
    status: str
    timestamp: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Device
# ─────────────────────────────────────────

class DeviceRegisterRequest(BaseModel):
    device_fingerprint: str
    label: Optional[str] = "unknown device"

class DeviceResponse(BaseModel):
    id: UUID
    device_fingerprint: str
    label: str
    registered_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: UUID
    timestamp: datetime
    username: Optional[str]
    role: Optional[str]
    path: str
    method: str
    ip: str
    device_id: Optional[str]
    risk_score: int
    decision: str
    reasons: Optional[str]
    response_status: Optional[int]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────
# Alert
# ─────────────────────────────────────────

class AlertResponse(BaseModel):
    id: UUID
    timestamp: datetime
    username: str
    risk_score: int
    reasons: str
    resolved: bool
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True

class AlertResolveRequest(BaseModel):
    alert_id: UUID


# ─────────────────────────────────────────
# OPA
# ─────────────────────────────────────────

class OPAInput(BaseModel):
    user: str
    role: str
    path: str
    method: str
    ip: str
    device_id: Optional[str] = None
    device_registered: bool = False
    hour: int
    amount: Optional[float] = 0.0

class OPADecision(BaseModel):
    decision: str        # allow, step_up, block
    score: int
    reasons: List[str]