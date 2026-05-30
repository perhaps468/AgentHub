# -*- coding: utf-8 -*-
"""Task B - Workspace domain service.

Business logic for workspace operations including CRUD and session resolution.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.workspace import Workspace


class WorkspaceNotFoundError(Exception):
    """Raised when workspace does not exist."""

    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        super().__init__(f"Workspace not found: {workspace_id}")


class WorkspaceAccessDeniedError(Exception):
    """Raised when user does not own the workspace."""

    def __init__(self, workspace_id: str, owner_id: str, requester_id: str):
        self.workspace_id = workspace_id
        self.owner_id = owner_id
        self.requester_id = requester_id
        super().__init__(
            f"Workspace {workspace_id} belongs to {owner_id}, not {requester_id}"
        )


class InvalidWorkspacePathError(Exception):
    """Raised when workspace root path is invalid or inaccessible."""

    def __init__(self, root_path: str, reason: str):
        self.root_path = root_path
        self.reason = reason
        super().__init__(f"Invalid workspace root '{root_path}': {reason}")


class WorkspaceService:
    """Domain service for workspace operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_workspace(self, owner_id: str, root_path: str) -> Workspace:
        """Create a new workspace for an owner.

        Validates that root_path is accessible before saving.
        Returns existing workspace if owner+root_path already exists.
        """
        abs_path = os.path.abspath(os.path.expanduser(root_path))
        self._validate_root_path(abs_path)

        existing = self.db.query(Workspace).filter(
            Workspace.owner_id == owner_id,
            Workspace.root_path == abs_path,
        ).first()
        if existing:
            return existing

        ws = Workspace(owner_id=owner_id, root_path=abs_path)
        self.db.add(ws)
        self.db.commit()
        self.db.refresh(ws)
        return ws

    def get_workspace(self, workspace_id: str, owner_id: str | None = None) -> Workspace:
        """Get workspace by ID, optionally checking owner.

        Args:
            workspace_id: The workspace ID to retrieve.
            owner_id: If provided, also verifies ownership.

        Returns:
            The workspace object.

        Raises:
            WorkspaceNotFoundError: Workspace does not exist.
            WorkspaceAccessDeniedError: workspace_id exists but owner doesn't match.
        """
        ws = self.db.get(Workspace, workspace_id)
        if ws is None:
            raise WorkspaceNotFoundError(workspace_id)

        if owner_id is not None and ws.owner_id != owner_id:
            raise WorkspaceAccessDeniedError(workspace_id, ws.owner_id, owner_id)

        return ws

    def list_user_workspaces(self, owner_id: str) -> list[Workspace]:
        """List all workspaces owned by a user."""
        return (
            self.db.query(Workspace)
            .filter(Workspace.owner_id == owner_id)
            .order_by(Workspace.created_at.desc())
            .all()
        )

    def _validate_root_path(self, root_path: str) -> None:
        """Validate that root_path is accessible and a directory."""
        try:
            p = Path(root_path)
            if not p.exists():
                raise InvalidWorkspacePathError(root_path, "path does not exist")
            if not p.is_dir():
                raise InvalidWorkspacePathError(root_path, "path is not a directory")
            if not os.access(p, os.R_OK | os.W_OK):
                raise InvalidWorkspacePathError(root_path, "path is not readable/writable")
        except OSError as e:
            raise InvalidWorkspacePathError(root_path, str(e))
