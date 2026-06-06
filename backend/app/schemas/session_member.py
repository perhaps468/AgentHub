"""P6-2 & P6-4: Pydantic schemas for session members."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MemberType = Literal["agent", "user"]
SessionMemberStatus = Literal["online", "busy", "offline"]


class MemberResponse(BaseModel):
    """Response schema for a session member."""

    id: str
    session_id: str
    member_type: MemberType
    member_id: str
    is_primary: bool = False
    health_status: str = "connected"
    status: SessionMemberStatus = "offline"
    agent_name: str | None = None
    agent_avatar: str | None = None
    agent_role: str | None = None
    created_at: str
