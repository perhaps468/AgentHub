from datetime import datetime

from app.schemas.common import TimestampedModel


class MessageResponse(TimestampedModel):
    id: str
    session_id: str
    sender_type: str
    sender_role: str | None
    content: str
    content_type: str
    created_at: datetime
