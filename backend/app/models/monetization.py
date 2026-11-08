from datetime import datetime
from uuid import uuid4
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.identity import User


class SponsorshipDeal(Base):
    __tablename__ = "sponsorship_deals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    deal_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    platform: Mapped[str] = mapped_column(String(50), default="youtube", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="pitched", nullable=False, index=True)  # 'pitched', 'negotiating', 'contracted', 'paid'
    deliverable_type: Mapped[str] = mapped_column(String(50), default="video", nullable=False)  # 'video', 'post', 'story'
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="sponsorship_deals", foreign_keys=[user_id])


class WorkspaceAlert(Base):
    __tablename__ = "workspace_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), default="milestone", nullable=False, index=True)  # 'milestone', 'revenue', 'engagement'
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    user: Mapped["User"] = relationship(back_populates="workspace_alerts", foreign_keys=[user_id])
