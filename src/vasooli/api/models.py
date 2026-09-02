from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Numeric, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.sasyncio import AsyncSession
from datetime import datetime
from typing import Optional

class Base(DeclarativeBase):
    pass

class RecoveryEvent(Base):
    __tablename__ = "recovery_events"

    record_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(String, index=True)
    merchant_id: Mapped[Optional[str]] = mapped_column(String)
    amount_inr: Mapped[float] = mapped_column(Numeric)
    root_cause: Mapped[str] = mapped_column(String)
    channel: Mapped[str] = mapped_column(String)
    tier: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, index=True)
    retry_count_so_far: Mapped[Optional[int]] = mapped_column(Integer)
    message_or_transcript: Mapped[Optional[str]] = mapped_column(String)
    reason: Mapped[Optional[str]] = mapped_column(String)
    amount_recovered_inr: Mapped[float] = mapped_column(Numeric, default=0.0)
    promise_captured: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class PromiseToPay(Base):
    __tablename__ = "promise_to_pay"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String, ForeignKey("recovery_events.record_id"))
    customer_id: Mapped[str] = mapped_column(String)
    promised_amount: Mapped[float] = mapped_column(Numeric)
    promised_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String, ForeignKey("recovery_events.record_id"))
    step: Mapped[str] = mapped_column(String)
    detail: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
