# -*- coding: utf-8 -*-
"""Planner Schema - 结构化规划输出定义

本模块定义了主agent语义规划的结构化输出schema。
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PlanningMode(str, Enum):
    """规划模式枚举"""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    MIXED = "mixed"


class PlannerTask(BaseModel):
    """规划任务结构

    描述主agent规划出的单个任务。
    """
    client_task_id: str = Field(
        ...,
        description="Planner内部任务ID，用于plan内部引用和depends_on",
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    title: str = Field(
        ...,
        description="任务标题",
        min_length=1,
        max_length=80,
    )
    goal: str = Field(
        ...,
        description="任务目标描述",
        min_length=1,
        max_length=300,
    )
    assigned_agent_id: str = Field(
        ...,
        description="分配的agent ID",
        min_length=1,
        max_length=50,
    )
    reason: str = Field(
        ...,
        description="分配理由",
        min_length=1,
        max_length=200,
    )
    input_payload: dict = Field(
        default_factory=dict,
        description="任务输入负载，可包含target_paths、requested_changes等",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="依赖的前置任务client_task_id列表",
    )

    @field_validator("client_task_id")
    @classmethod
    def validate_client_task_id(cls, v: str) -> str:
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("client_task_id只能包含字母、数字、下划线和连字符")
        return v


class PlannerPlan(BaseModel):
    """完整规划结构

    主agent输出的完整结构化规划，包含summary和tasks列表。
    """
    planner_summary: str = Field(
        ...,
        description="规划摘要说明",
        min_length=1,
        max_length=500,
    )
    planning_mode: PlanningMode = Field(
        ...,
        description="规划模式：并行、串行或混合",
    )
    tasks: list[PlannerTask] = Field(
        ...,
        description="任务列表",
        min_length=1,
        max_length=8,
    )

    @field_validator("tasks")
    @classmethod
    def validate_tasks_unique(cls, v: list[PlannerTask]) -> list[PlannerTask]:
        client_ids = [t.client_task_id for t in v]
        if len(client_ids) != len(set(client_ids)):
            raise ValueError("client_task_id必须唯一")
        return v


class ValidationStatus(str, Enum):
    """校验状态枚举"""
    VALID = "valid"
    REPAIRED = "repaired"
    INVALID = "invalid"


class ValidatorResult(BaseModel):
    """校验结果结构

    描述planner输出校验的结果。
    """
    status: ValidationStatus = Field(
        ...,
        description="校验状态：valid/repaired/invalid",
    )
    normalized_plan: Optional[PlannerPlan] = Field(
        None,
        description="修复后的标准化plan（如果状态为valid或repaired）",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="不可接受的错误列表",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="可接受但需要记录的警告列表",
    )
    repair_actions: list[str] = Field(
        default_factory=list,
        description="实际执行的自动修复动作",
    )


class PlannerStatus(str, Enum):
    """Planner状态枚举 - 状态机状态"""
    PLANNER_REQUESTED = "planner_requested"
    PLANNER_RETURNED_RAW = "planner_returned_raw"
    PLANNER_PARSED = "planner_parsed"
    VALIDATOR_VALID = "validator_valid"
    VALIDATOR_REPAIRED = "validator_repaired"
    VALIDATOR_INVALID = "validator_invalid"
    FALLBACK_STARTED = "fallback_started"
    FALLBACK_SUCCEEDED = "fallback_succeeded"
    FALLBACK_FAILED = "fallback_failed"
    PLAN_COMMITTED = "plan_committed"


class PlanningSource(str, Enum):
    """规划来源枚举"""
    PLANNER = "planner"
    PLANNER_REPAIRED = "planner_repaired"
    FALLBACK_SPLITTER = "fallback_splitter"


class PlannerResult(BaseModel):
    """Planner服务结果结构

    描述planner service的返回结果。
    """
    status: PlannerStatus = Field(
        ...,
        description="Planner状态",
    )
    planning_source: PlanningSource = Field(
        ...,
        description="规划来源标识",
    )
    raw_output: Optional[str] = Field(
        None,
        description="LLM原始输出",
    )
    parsed_plan: Optional[PlannerPlan] = Field(
        None,
        description="解析后的结构化plan",
    )
    validator_result: Optional[ValidatorResult] = Field(
        None,
        description="校验结果",
    )
    fallback_used: bool = Field(
        default=False,
        description="是否使用了fallback",
    )
    error_message: Optional[str] = Field(
        None,
        description="错误信息（如果失败）",
    )
