import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.session import utcnow


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    sender_type: Mapped[str] = mapped_column(String(20), nullable=False)
    sender_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="text")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    msg_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    session = relationship("ChatSession", back_populates="messages")

    def __init__(self, **kwargs) -> None:
        if "metadata" in kwargs:
            kwargs["msg_metadata"] = kwargs.pop("metadata")
        if "status" not in kwargs:
            if kwargs.get("sender_type") == "agent":
                kwargs["status"] = "streaming"
            else:
                kwargs["status"] = "completed"
        if "type" not in kwargs:
            kwargs["type"] = "text"
        if "payload" not in kwargs:
            kwargs["payload"] = {}
        if "msg_metadata" not in kwargs:
            kwargs["msg_metadata"] = {}
        super().__init__(**kwargs)
