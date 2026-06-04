# -*- coding: utf-8 -*-
"""Orchestration Service with Planner Integration

将主agent语义规划与fallback规则拆分整合的编排服务。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from app.models.orchestration import OrchestrationRun, OrchestrationTask
from app.schemas.orchestration_planner import (
    PlanningSource,
    PlannerPlan,
    PlannerResult,
    PlannerStatus,
    ValidationStatus,
)
from app.services.orchestration import OrchestrationService
from app.services.orchestration_plan_validator import validate_plan
from app.services.task_splitter import PlannedTask, plan_tasks_from_message

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.session import ChatSession


def _convert_planner_task_to_dict(task_index: int, planner_task, run_id: str) -> dict:
    """将PlannerTask转换为task字典

    Args:
        task_index: 任务序号
        planner_task: PlannerTask实例
        run_id: run_id

    Returns:
        task字典
    """
    return {
        "sequence": task_index + 1,
        "assigned_agent_id": planner_task.assigned_agent_id,
        "kind": "file_write",  # 默认kind，后续可扩展
        "title": planner_task.title,
        "goal": planner_task.goal,
        "input_payload": planner_task.input_payload,
        "status": "planned",
        # 新增字段
        "client_task_id": planner_task.client_task_id,
        "assignment_reason": planner_task.reason,
        "depends_on": planner_task.depends_on,
    }


def _convert_fallback_task_to_dict(task_index: int, fallback_task: PlannedTask) -> dict:
    """将PlannedTask转换为task字典

    Args:
        task_index: 任务序号
        fallback_task: PlannedTask实例

    Returns:
        task字典
    """
    return {
        "sequence": task_index + 1,
        "assigned_agent_id": fallback_task.assigned_agent_id,
        "kind": fallback_task.kind,
        "title": fallback_task.title,
        "goal": fallback_task.goal,
        "input_payload": fallback_task.input_payload,
        "status": "planned",
    }


def build_plan_summary_from_planner_plan(plan: PlannerPlan) -> str:
    """从结构化plan生成主持性计划消息

    Args:
        plan: 结构化plan

    Returns:
        主持性计划消息
    """
    task_count = len(plan.tasks)
    lines = [f"已拆解出 {task_count} 个任务。"]

    # 添加并行/串行模式说明
    mode_text = {
        "parallel": "这些任务可以并行执行。",
        "sequential": "这些任务需要按顺序执行。",
        "mixed": "这些任务包含并行和串行部分，我会协调执行顺序。",
    }
    lines.append(mode_text.get(plan.planning_mode.value, ""))

    # 添加任务分配详情
    lines.append("\n任务分配：")
    for idx, task in enumerate(plan.tasks):
        depends_text = ""
        if task.depends_on:
            depends_text = f" (等待: {', '.join(task.depends_on)})"
        lines.append(f"{idx + 1}. [{task.assigned_agent_id}] {task.title}{depends_text}")
        lines.append(f"   目标: {task.goal}")
        lines.append(f"   原因: {task.reason}")

    # 添加结束语
    if task_count > 1:
        lines.append("\n各任务将并行推进，我会继续统一主持进度并在完成后汇总结果。")
    else:
        lines.append("\n该任务将立即开始执行，我会继续统一主持进度并在完成后汇总结果。")

    return "\n".join(lines)


def build_plan_payload_from_run(run: OrchestrationRun) -> dict:
    """从run构建plan payload

    Args:
        run: OrchestrationRun实例

    Returns:
        plan payload字典
    """
    return {
        "run_id": run.id,
        "planning_source": getattr(run, 'planning_source', 'unknown'),
        "tasks": [
            {
                "id": task.id,
                "sequence": task.sequence,
                "assigned_agent_id": task.assigned_agent_id,
                "kind": task.kind,
                "title": task.title,
                "goal": task.goal,
                "status": task.status,
                "input_payload": task.input_payload,
                # 新增字段
                "client_task_id": getattr(task, 'client_task_id', None),
                "assignment_reason": getattr(task, 'assignment_reason', None),
                "depends_on": getattr(task, 'depends_on', []),
            }
            for task in run.tasks
        ],
    }


class PlannerOrchestrationService:
    """支持Planner的编排服务

    整合语义规划和fallback规则拆分的完整编排链路。
    """

    def __init__(self, db) -> None:
        self.db = db
        self.orchestration_service = OrchestrationService(db)

    def create_run_with_planner_plan(
        self,
        session_id: str,
        trigger_message_id: str,
        planner_agent_id: str,
        plan: PlannerPlan,
        planning_source: PlanningSource,
    ) -> OrchestrationRun:
        """使用Planner输出的plan创建run

        Args:
            session_id: session ID
            trigger_message_id: 触发消息ID
            planner_agent_id: 主agent ID
            plan: 结构化plan
            planning_source: 规划来源

        Returns:
            创建的OrchestrationRun
        """
        # 构建summary
        summary = plan.planner_summary
        task_count = len(plan.tasks)

        # 创建run
        run = self.orchestration_service.create_run(
            session_id=session_id,
            trigger_message_id=trigger_message_id,
            planner_agent_id=planner_agent_id,
            summary=f"已拆解出 {task_count} 个任务",
            status="planned",
        )

        # 保存planning_source到run的扩展字段
        run.planning_source = planning_source.value

        # 创建tasks
        task_dicts = [
            _convert_planner_task_to_dict(idx, task, run.id)
            for idx, task in enumerate(plan.tasks)
        ]
        self.orchestration_service.create_tasks(run.id, task_dicts)

        self.db.commit()

        # 刷新获取完整数据
        return self.orchestration_service.get_run(run.id)

    def create_run_with_fallback(
        self,
        session_id: str,
        trigger_message_id: str,
        planner_agent_id: str,
        user_message: str,
        member_ids: list[str],
    ) -> OrchestrationRun | None:
        """使用fallback规则拆分创建run

        Args:
            session_id: session ID
            trigger_message_id: 触发消息ID
            planner_agent_id: 主agent ID
            user_message: 用户原始消息
            member_ids: 可用agent ID列表

        Returns:
            创建的OrchestrationRun，失败返回None
        """
        # 使用规则拆分
        planned_tasks = plan_tasks_from_message(user_message, member_ids)
        if not planned_tasks:
            return None

        task_count = len(planned_tasks)

        # 创建run
        run = self.orchestration_service.create_run(
            session_id=session_id,
            trigger_message_id=trigger_message_id,
            planner_agent_id=planner_agent_id,
            summary=f"已拆解出 {task_count} 个任务 (fallback)",
            status="planned",
        )

        # 保存planning_source
        run.planning_source = PlanningSource.FALLBACK_SPLITTER.value

        # 创建tasks
        task_dicts = [
            _convert_fallback_task_to_dict(idx, task)
            for idx, task in enumerate(planned_tasks)
        ]
        self.orchestration_service.create_tasks(run.id, task_dicts)

        self.db.commit()

        # 刷新获取完整数据
        return self.orchestration_service.get_run(run.id)

    def get_run(self, run_id: str) -> OrchestrationRun | None:
        """获取run"""
        return self.orchestration_service.get_run(run_id)
