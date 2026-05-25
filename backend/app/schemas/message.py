from datetime import datetime

from pydantic import ConfigDict, Field

from app.schemas.common import TimestampedModel


class MessageResponse(TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    sender_type: str
    sender_role: str | None
    type: str
    content: str
    payload: dict
    msg_metadata: dict = Field(serialization_alias="metadata")
    status: str
    created_at: datetime
