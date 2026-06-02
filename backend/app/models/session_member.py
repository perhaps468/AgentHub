"""P6-2: SessionMember ORM model for group chat member persistence.

Stores which agents/users are members of a session.
Unique constraint on (session_id, member_type, member_id) prevents duplicates.
"""
from datetime import datetime
import uuid

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.session import utcnow


class SessionMember(Base):
    __tablename__ = "session_members"
    __table_args__ = (
        UniqueConstraint("session_id", "member_type", "member_id", name="uq_session_member"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    member_type: Mapped[str] = mapped_column(String(20), nullable=False)
    member_id: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    health_status: Mapped[str] = mapped_column(String(20), nullable=False, default="connected")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
