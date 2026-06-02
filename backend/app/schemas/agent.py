# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    provider: Optional[str] = Field(default=None, max_length=50)
    platform: str = Field(default="custom", max_length=20)
    description: Optional[str] = Field(default=None, max_length=500)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    capability_tags: list[str] = Field(default_factory=list)
    tool_permissions: list[str] = Field(default_factory=list)

    @field_validator("capability_tags", "tool_permissions", mode="before")
    @classmethod
    def ensure_list(cls, v: object) -> list:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return []

    @field_validator("name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    model: Optional[str] = Field(default=None, min_length=1, max_length=100)
    provider: Optional[str] = Field(default=None, max_length=50)
    system_prompt: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    description: Optional[str] = Field(default=None, max_length=500)
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    capability_tags: Optional[list[str]] = None
    tool_permissions: Optional[list[str]] = None
    is_active: Optional[bool] = None

    @field_validator("capability_tags", "tool_permissions", mode="before")
    @classmethod
    def ensure_list(cls, v: object) -> list | None:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return []


class AgentResponse(BaseModel):
    id: str
    owner_id: Optional[str]
    name: str
    role: str
    provider: str
    model: str
    system_prompt: str
    platform: str
    description: Optional[str]
    avatar_url: Optional[str]
    capability_tags: list[str]
    tool_permissions: list[str]
    is_builtin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    total: int


class AgentConfigResponse(BaseModel):
    available_models: list[str]
    available_capability_tags: list[str]
