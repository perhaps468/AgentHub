# -*- coding: utf-8 -*-
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Agent(Base):
    """统一 Agent 模型 - 内置 Agent 与用户自建 Agent 共用同一张表"""

    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="qwen_openai_compatible", server_default="qwen_openai_compatible")
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    system_prompt: Mapped[str] = mapped_column(String(10000), nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False, default="custom")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    capability_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    tool_permissions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    def is_owned_by(self, user_id: str) -> bool:
        """检查是否属于指定用户"""
        return self.owner_id == user_id

    def can_be_modified_by(self, user_id: str) -> bool:
        """检查是否可以被指定用户修改"""
        return not self.is_builtin and self.owner_id == user_id
