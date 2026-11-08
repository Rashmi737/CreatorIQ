from datetime import datetime
from uuid import uuid4
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.identity import User


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "platform_name", "platform_user_id"),
        Index("ix_platform_accounts_plat_handle", "platform_name", "platform_user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_name: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    platform_user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    channel_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    subscribers_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    video_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_posts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime)
    scopes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship(back_populates="platform_accounts")
    social_contents: Mapped[list["SocialContent"]] = relationship(back_populates="platform_account", cascade="all, delete-orphan")


class SocialContent(Base):
    __tablename__ = "social_contents"
    __table_args__ = (
        UniqueConstraint("user_id", "platform", "external_id"),
        Index("ix_social_contents_plat_ext", "platform", "external_id"),
        Index("ix_social_contents_account_pub", "platform_account_id", "published_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_account_id: Mapped[str | None] = mapped_column(ForeignKey("platform_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String(40), default="youtube", nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(50), default="Video", nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shares: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(50), default="Published", nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    dwell_time_mins: Mapped[float] = mapped_column(Float, default=3.5, nullable=False)
    duration_secs: Mapped[int] = mapped_column(Integer, default=240, nullable=False)
    external_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)

    user: Mapped["User"] = relationship(back_populates="social_contents")
    platform_account: Mapped[PlatformAccount | None] = relationship(back_populates="social_contents")