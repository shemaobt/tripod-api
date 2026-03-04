import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Notification(Base):
    """App-agnostic notification record."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "ix_notifications_user_app_unread_created",
            "user_id",
            "app_id",
            "is_read",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    app_id: Mapped[str] = mapped_column(ForeignKey("apps.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(50))
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationMeaningMapDetail(Base):
    """Meaning-map-specific detail for a notification (child table)."""

    __tablename__ = "notification_meaning_map_details"

    notification_id: Mapped[str] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), primary_key=True
    )
    related_map_id: Mapped[str | None] = mapped_column(
        ForeignKey("meaning_maps.id", ondelete="SET NULL"), nullable=True, index=True
    )
    pericope_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
