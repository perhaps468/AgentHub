# -*- coding: utf-8 -*-
"""Task CE: PendingChange DB Model.

This module provides the SQLAlchemy ORM model for persisting pending changes
to the database. It enables:
- Pending change persistence across page refreshes
- Recovery of pending changes on WS reconnect
- History query for applied/rejected/failed changes
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

if TYPE_CHECKING:
    from app.runtime.pending_change import PendingChange, ChangeOperation, ChangeStatus


class PendingChangeModel(Base):
    """SQLAlchemy model for persisting pending changes.

    Stores the full state of a pending change so it can be recovered
    after page refresh or WS reconnect.

    Fields (from migration doc section 5.2):
    - change_id: Unique identifier
    - session_id: Associated session
    - message_id: Associated message
    - stream_id: Associated stream
    - path: Target file path
    - operation: create/update/delete
    - unified_diff: Human-readable unified diff
    - original_content: Current file content (None for new files)
    - proposed_content: Proposed new content
    - status: pending_confirmation/applied/rejected/failed
    - created_at: Creation timestamp
    - applied_at: Apply timestamp (if applied)
    """

    __tablename__ = "pending_changes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    change_id: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), nullable=False, index=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    stream_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    unified_diff: Mapped[str] = mapped_column(Text, nullable=False, default="")
    original_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proposed_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending_confirmation", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @classmethod
    def from_runtime(
        cls,
        pc: "PendingChange",
        session_id: str,
        message_id: Optional[str] = None,
        stream_id: Optional[str] = None,
    ) -> "PendingChangeModel":
        """Create a DB model from a runtime PendingChange.

        Args:
            pc: Runtime PendingChange instance
            session_id: Associated session ID
            message_id: Associated message ID (optional)
            stream_id: Associated stream ID (optional)

        Returns:
            PendingChangeModel instance ready for DB persistence
        """
        return cls(
            change_id=pc.change_id,
            session_id=session_id,
            message_id=message_id,
            stream_id=stream_id,
            path=pc.path,
            operation=pc.operation.value if hasattr(pc.operation, "value") else str(pc.operation),
            unified_diff=pc.unified_diff,
            original_content=pc.original_content,
            proposed_content=pc.proposed_content,
            status=cls._map_status(pc.status),
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _map_status(status: "ChangeStatus") -> str:
        """Map runtime status to DB status string.

        Runtime uses PREVIEW/PENDING/APPLIED/REJECTED
        DB uses pending_confirmation/applied/rejected/failed
        """
        from app.runtime.pending_change import ChangeStatus

        status_map = {
            ChangeStatus.PREVIEW: "pending_confirmation",
            ChangeStatus.PENDING: "pending_confirmation",
            ChangeStatus.APPLIED: "applied",
            ChangeStatus.REJECTED: "rejected",
        }
        return status_map.get(status, "pending_confirmation")

    def to_runtime(self) -> "PendingChange":
        """Convert DB model back to runtime PendingChange.

        Returns:
            Runtime PendingChange instance
        """
        from app.runtime.pending_change import PendingChange, ChangeOperation, ChangeStatus

        # Map DB status to runtime status
        db_to_runtime_status = {
            "pending_confirmation": ChangeStatus.PENDING,
            "preview": ChangeStatus.PENDING,
            "pending": ChangeStatus.PENDING,
            "applied": ChangeStatus.APPLIED,
            "rejected": ChangeStatus.REJECTED,
            "failed": ChangeStatus.REJECTED,
        }
        runtime_status = db_to_runtime_status.get(self.status, ChangeStatus.PENDING)

        # Map operation string to enum
        op_map = {
            "create": ChangeOperation.CREATE,
            "update": ChangeOperation.UPDATE,
            "delete": ChangeOperation.DELETE,
            "rename": ChangeOperation.RENAME,
        }
        runtime_op = op_map.get(self.operation, ChangeOperation.UPDATE)

        pc = PendingChange(
            change_id=self.change_id,
            path=self.path,
            operation=runtime_op,
            original_content=self.original_content,
            proposed_content=self.proposed_content,
            unified_diff=self.unified_diff,
            status=runtime_status,
            error=None,
            created_at=self.created_at.isoformat() if self.created_at else "",
        )
        return pc

    def to_api_response(self) -> dict:
        """Convert to API response format for frontend.

        Returns:
            Dict matching frontend PendingChange interface
        """
        return {
            "change_id": self.change_id,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "stream_id": self.stream_id,
            "path": self.path,
            "operation": self.operation,
            "unified_diff": self.unified_diff,
            "original_content": self.original_content,
            "proposed_content": self.proposed_content,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }
