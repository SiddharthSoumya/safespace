from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    access_code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_text: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_identity: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    manual_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    department: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    messages: Mapped[list["ComplaintMessage"]] = relationship(
        back_populates="complaint", cascade="all, delete-orphan", order_by="ComplaintMessage.created_at"
    )


class ComplaintMessage(Base):
    __tablename__ = "complaint_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    encrypted_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    complaint: Mapped[Complaint] = relationship(back_populates="messages")
