from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.common import TimestampedModel


class SessionCreate(TimestampedModel):
    owner_id: str | None = Field(default=None)
    title: str | None = Field(default=None, max_length=255)
    mode: Literal["single", "group"]


class SessionUpdate(TimestampedModel):
    title: str | None = Field(default=None, max_length=255)
    is_pinned: bool | None = None
    is_archived: bool | None = None

    @model_validator(mode="after")
    def require_update_field(self):
        if self.title is None and self.is_pinned is None and self.is_archived is None:
            raise ValueError("At least one field is required")
        return self


class SessionResponse(TimestampedModel):
    id: str
    owner_id: str
    title: str | None
    mode: str
    is_pinned: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime
