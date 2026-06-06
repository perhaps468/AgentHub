# -*- coding: utf-8 -*-
"""Session schemas with workspace binding enforcement.

Task B+C-1: Session creation REQUIRES workspace_id.
SessionResponse includes workspace details for frontend display.
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.common import TimestampedModel
from app.schemas.session_member import MemberResponse


class WorkspaceSummary(BaseModel):
    """Minimal workspace info for embedding in other responses.

    Task B+C-1: Provides id, name, root_path for frontend display.
    """

    id: str
    name: str
    root_path: str


class SessionCreate(TimestampedModel):
    """Session creation request.

    Task B+C-1: workspace_id is REQUIRED for all new sessions.
    P6-3: participant_agent_ids for group chat creation.
    """
    owner_id: str | None = Field(default=None)
    title: str | None = Field(default=None, max_length=255)
    mode: Literal["single", "group"]
    workspace_id: str = Field(..., min_length=1)
    agent_id: str | None = Field(default=None)
    participant_agent_ids: list[str] | None = Field(default=None)

    @field_validator("workspace_id", mode="after")
    @classmethod
    def workspace_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("workspace_id cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_agent_selection(self):
        if self.mode == "single" and not self.agent_id:
            raise ValueError("agent_id is required for single sessions")
        if self.mode == "group":
            participant_ids = self.participant_agent_ids or []
            if not participant_ids:
                raise ValueError("participant_agent_ids must include the user group host agent for group sessions")
        return self


class SessionUpdate(TimestampedModel):
    title: str | None = Field(default=None, max_length=255)
    is_pinned: bool | None = None
    is_archived: bool | None = None
    workspace_id: str | None = Field(default=None)
    agent_id: str | None = Field(default=None)

    @model_validator(mode="after")
    def require_update_field(self):
        if (
            self.title is None
            and self.is_pinned is None
            and self.is_archived is None
            and self.workspace_id is None
            and self.agent_id is None
        ):
            raise ValueError("At least one field is required")
        return self


class SessionResponse(TimestampedModel):
    """Session response with workspace details.

    Task B+C-1: Includes nested workspace info for frontend display.
    """
    id: str
    owner_id: str
    workspace_id: str | None
    agent_id: str | None
    title: str | None
    mode: str
    is_pinned: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    workspace: WorkspaceSummary | None = None
    members: list[MemberResponse] | None = None
