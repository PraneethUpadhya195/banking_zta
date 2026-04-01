import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Boolean,
    DateTime, ForeignKey, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # customer, teller, manager, admin
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="user", uselist=False)
    devices = relationship("RegisteredDevice", back_populates="user")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_number = Column(String(20), unique=True, nullable=False)
    balance = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="account")
    sent_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.from_account_id",
        back_populates="from_account"
    )
    received_transactions = relationship(
        "Transaction",
        foreign_keys="Transaction.to_account_id",
        back_populates="to_account"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), default="success")  # success, failed, flagged
    timestamp = Column(DateTime, default=datetime.utcnow)

    from_account = relationship(
        "Account",
        foreign_keys=[from_account_id],
        back_populates="sent_transactions"
    )
    to_account = relationship(
        "Account",
        foreign_keys=[to_account_id],
        back_populates="received_transactions"
    )


class RegisteredDevice(Base):
    __tablename__ = "registered_devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_fingerprint = Column(String(255), nullable=False)
    label = Column(String(100), default="unknown device")
    registered_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="devices")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow)
    username = Column(String(50), nullable=True)
    role = Column(String(20), nullable=True)
    path = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    ip = Column(String(50), nullable=False)
    device_id = Column(String(255), nullable=True)
    risk_score = Column(Integer, default=0)
    decision = Column(String(20), default="allow")  # allow, step_up, block
    reasons = Column(Text, nullable=True)            # comma separated reasons
    response_status = Column(Integer, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow)
    username = Column(String(50), nullable=False)
    risk_score = Column(Integer, nullable=False)
    reasons = Column(Text, nullable=False)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)