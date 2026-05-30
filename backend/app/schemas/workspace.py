# -*- coding: utf-8 -*-
"""Task B - Workspace Pydantic schemas.

Schemas for workspace CRUD API endpoints.

Task B+C-1: Added 'name' field for frontend display.
"""
import os
from datetime import datetime
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from app.schemas.common import TimestampedModel


def _derive_name_from_root_path(root_path: str) -> str:
    """Derive workspace name from root_path folder name."""
    return os.path.basename(root_path.rstrip(os.sep)) or root_path


class WorkspaceCreate(TimestampedModel):
    """Request body for creating a workspace.

    Task B+C-1: name is optional - defaults to derived from root_path.
    """

    owner_id: str | None = Field(default=None)
    root_path: str = Field(..., min_length=1, max_length=1024)
    name: str | None = Field(default=None, max_length=255)

    @field_validator("root_path", mode="after")
    @classmethod
    def root_path_must_be_absolute(cls, v: str) -> str:
        path = v.strip()
        if not Path(path).is_absolute():
            raise ValueError(f"root_path must be an absolute path, got: {v}")
        expanded = os.path.expanduser(path)
        abs_path = os.path.abspath(expanded)
        return abs_path

    @model_validator(mode="after")
    def derive_name_if_not_provided(self) -> "WorkspaceCreate":
        """If name is not provided, derive it from root_path."""
        if self.name is None or not self.name.strip():
            self.name = _derive_name_from_root_path(self.root_path)
        return self


class WorkspaceUpdate(TimestampedModel):
    """Request body for updating a workspace.

    Task B+C-1: Added name field for updates.
    """

    root_path: str | None = Field(default=None, min_length=1, max_length=1024)
    name: str | None = Field(default=None, max_length=255)


class WorkspaceResponse(TimestampedModel):
    """Response schema for a workspace.

    Task B+C-1: Includes name field for frontend display.
    """

    id: str
    owner_id: str
    root_path: str
    name: str
    created_at: datetime
