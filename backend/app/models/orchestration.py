# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.session import utcnow


class OrchestrationRun(Base):
    __tablename__ = "orchestration_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False, index=True)
    trigger_message_id: Mapped[str] = mapped_column(String(36), ForeignKey("messages.id"), nullable=False, index=True)
    planner_agent_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    planning_source: Mapped[str | None] = mapped_column(String(50), nullable=True, default="fallback_splitter")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    session = relationship("ChatSession")
    trigger_message = relationship("Message", foreign_keys=[trigger_message_id])
    tasks = relationship(
        "OrchestrationTask",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="OrchestrationTask.sequence",
    )


class OrchestrationTask(Base):
    __tablename__ = "orchestration_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("orchestration_runs.id"), nullable=False, index=True)
    parent_task_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("orchestration_tasks.id"), nullable=True, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    assigned_agent_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="file_write")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    client_task_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assignment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    depends_on: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
    )

    run = relationship("OrchestrationRun", back_populates="tasks")
    parent_task = relationship("OrchestrationTask", remote_side=[id])
