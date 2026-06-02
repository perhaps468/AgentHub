"""P6-2 & P6-4: Pydantic schemas for session members."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MemberType = Literal["agent", "user"]


class MemberResponse(BaseModel):
    """Response schema for a session member."""

    id: str
    session_id: str
    member_type: str
    member_id: str
    is_primary: bool = False
    health_status: str = "connected"
    created_at: str
