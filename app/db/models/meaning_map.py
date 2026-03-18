import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class Testament(enum.StrEnum):
    OT = "OT"
    NT = "NT"


class MeaningMapStatus(enum.StrEnum):
    DRAFT = "draft"
    CROSS_CHECK = "cross_check"
    APPROVED = "approved"


class BibleBook(Base):
    __tablename__ = "bible_books"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    abbreviation: Mapped[str] = mapped_column(String(20))
    testament: Mapped[Testament] = mapped_column(Enum(Testament, name="testament_enum"))
    order: Mapped[int] = mapped_column(Integer)
    chapter_count: Mapped[int] = mapped_column(Integer)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Pericope(Base):
    __tablename__ = "pericopes"
    __table_args__ = (
        Index("ix_pericopes_book_chapter", "book_id", "chapter_start", "verse_start"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    book_id: Mapped[str] = mapped_column(
        ForeignKey("bible_books.id", ondelete="RESTRICT"), index=True
    )
    chapter_start: Mapped[int] = mapped_column(Integer)
    verse_start: Mapped[int] = mapped_column(Integer)
    chapter_end: Mapped[int] = mapped_column(Integer)
    verse_end: Mapped[int] = mapped_column(Integer)
    reference: Mapped[str] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MeaningMap(Base):
    __tablename__ = "meaning_maps"
    __table_args__ = (Index("ix_meaning_maps_status", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    pericope_id: Mapped[str] = mapped_column(
        ForeignKey("pericopes.id", ondelete="CASCADE"), index=True
    )
    analyst_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    cross_checker_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[MeaningMapStatus] = mapped_column(
        Enum(MeaningMapStatus, name="meaning_map_status_enum"), default=MeaningMapStatus.DRAFT
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    locked_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_approved: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    bcd_version_at_creation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MeaningMapFeedback(Base):
    __tablename__ = "meaning_map_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meaning_map_id: Mapped[str] = mapped_column(
        ForeignKey("meaning_maps.id", ondelete="CASCADE"), index=True
    )
    section_key: Mapped[str] = mapped_column(String(100))
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    content: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
