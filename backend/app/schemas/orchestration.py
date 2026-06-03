# -*- coding: utf-8 -*-
from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.schemas.common import TimestampedModel


class OrchestrationTaskResponse(TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    parent_task_id: str | None
    sequence: int
    assigned_agent_id: str
    kind: str
    title: str
    goal: str
    input_payload: dict
    result_payload: dict | None = None
    error_payload: dict | None = None
    status: str


class OrchestrationRunResponse(TimestampedModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    trigger_message_id: str
    planner_agent_id: str
    status: str
    summary: str | None = None
    tasks: list[OrchestrationTaskResponse] = []


class LatestRunResponse(BaseModel):
    run: OrchestrationRunResponse | None = None
