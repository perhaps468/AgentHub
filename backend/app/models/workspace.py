# -*- coding: utf-8 -*-
"""Task B - Workspace domain model.

Minimal workspace entity with owner boundary, as defined in
openspec/docs/migration/06-task-b-workspace-boundary.md Section 7.2.

Task B+C-1: Added 'name' field for frontend display.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _derive_name_from_root_path(root_path: str) -> str:
    """Derive workspace name from root_path folder name."""
    return os.path.basename(root_path.rstrip(os.sep)) or root_path


class Workspace(Base):
    """Minimal workspace domain model.

    Represents a code workspace that a development session is bound to.
    The owner boundary is enforced at the service/API layer.

    Task B+C-1: Includes 'name' field for frontend display.
    """

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    owner_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    root_path: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

    def __init__(self, **kwargs):
        # Auto-derive name from root_path if not provided
        if "name" not in kwargs or not kwargs["name"]:
            root_path = kwargs.get("root_path", "")
            kwargs["name"] = _derive_name_from_root_path(root_path)
        super().__init__(**kwargs)

    @property
    def display_name(self) -> str:
        """Return the display name for the workspace."""
        return self.name

    def get_guard_root(self) -> Path:
        """Return the root_path as a resolved Path object."""
        return Path(self.root_path).expanduser().resolve()

    def is_root_path_accessible(self) -> bool:
        """Check if the root path exists and is a directory."""
        try:
            p = self.get_guard_root()
            return p.exists() and p.is_dir()
        except (OSError, RuntimeError):
            return False
