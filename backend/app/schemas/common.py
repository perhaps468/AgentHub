from datetime import datetime, timezone
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, field_serializer


T = TypeVar("T")


def to_iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedModel(ApiModel):
    @field_serializer("created_at", "updated_at", check_fields=False)
    def serialize_datetime(self, value: datetime) -> str:
        return to_iso_z(value)


class Page(ApiModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    has_more: bool
