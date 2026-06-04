# -*- coding: utf-8 -*-
"""Orchestration plan validation and lightweight repair."""
from __future__ import annotations

import re

from app.schemas.orchestration_planner import (
    PlannerPlan,
    PlannerTask,
    ValidationStatus,
    ValidatorResult,
)


MAX_TASKS = 8
BALANCE_THRESHOLD_MIN_AGENTS = 2
BALANCE_THRESHOLD_MIN_TASKS = 2
_TARGET_PATH_PATTERN = re.compile(r"([a-zA-Z_][a-zA-Z0-9_\-./\\]*\.[a-zA-Z]+)")


def _round_robin_balance_tasks(
    tasks: list[PlannerTask],
    valid_agent_ids: set[str],
) -> tuple[list[PlannerTask], list[str]]:
    repair_actions: list[str] = []
    sub_agents = sorted(
        agent_id for agent_id in valid_agent_ids if not agent_id.startswith("group_host_")
    )

    if len(sub_agents) < BALANCE_THRESHOLD_MIN_AGENTS or len(tasks) < BALANCE_THRESHOLD_MIN_TASKS:
        return tasks, repair_actions

    current_assignments: dict[str, int] = {agent_id: 0 for agent_id in valid_agent_ids}
    for task in tasks:
        current_assignments[task.assigned_agent_id] = current_assignments.get(task.assigned_agent_id, 0) + 1

    sub_agents_with_tasks = sum(1 for agent_id in sub_agents if current_assignments.get(agent_id, 0) > 0)
    if sub_agents_with_tasks >= min(len(sub_agents), len(tasks)):
        return tasks, repair_actions

    balanced_tasks: list[PlannerTask] = []
    for index, task in enumerate(tasks):
        target_agent = sub_agents[index % len(sub_agents)]
        if task.assigned_agent_id != target_agent:
            repair_actions.append(
                f"均衡分配修复: 任务 '{task.client_task_id}' 从 '{task.assigned_agent_id}' 重新分配给 '{target_agent}'"
            )
            balanced_tasks.append(
                PlannerTask(
                    client_task_id=task.client_task_id,
                    title=task.title,
                    goal=task.goal,
                    assigned_agent_id=target_agent,
                    reason=f"[均衡分配] {task.reason}",
                    input_payload=task.input_payload,
                    depends_on=task.depends_on,
                )
            )
        else:
            balanced_tasks.append(task)

    return balanced_tasks, repair_actions


class OrchestrationPlanValidator:
    def __init__(self, valid_agent_ids: list[str]) -> None:
        self.valid_agent_ids = set(valid_agent_ids)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.repair_actions: list[str] = []

    def validate(self, plan: PlannerPlan, user_request: str | None = None) -> ValidatorResult:
        self.errors = []
        self.warnings = []
        self.repair_actions = []

        self._validate_task_count(plan)
        self._validate_agent_ids(plan)
        self._validate_dependency_references(plan)
        self._validate_no_circular_dependencies(plan)
        self._validate_primary_agent_self_assignment(plan)
        self._validate_task_granularity(plan, user_request)
        self._balance_task_distribution(plan)

        if self.errors:
            return ValidatorResult(
                status=ValidationStatus.INVALID,
                normalized_plan=None,
                errors=self.errors,
                warnings=self.warnings,
                repair_actions=self.repair_actions,
            )

        if self.repair_actions:
            return ValidatorResult(
                status=ValidationStatus.REPAIRED,
                normalized_plan=plan,
                errors=self.errors,
                warnings=self.warnings,
                repair_actions=self.repair_actions,
            )

        return ValidatorResult(
            status=ValidationStatus.VALID,
            normalized_plan=plan,
            errors=self.errors,
            warnings=self.warnings,
            repair_actions=self.repair_actions,
        )

    def _validate_task_count(self, plan: PlannerPlan) -> None:
        if len(plan.tasks) == 0:
            self.errors.append("任务列表不能为空")
            return

        if len(plan.tasks) > MAX_TASKS:
            self.errors.append(f"任务数量超过限制: {len(plan.tasks)} > {MAX_TASKS}")

    def _validate_agent_ids(self, plan: PlannerPlan) -> None:
        for task in plan.tasks:
            if not task.assigned_agent_id:
                self.errors.append(f"任务 '{task.client_task_id}' 的 assigned_agent_id 为空")
            elif task.assigned_agent_id not in self.valid_agent_ids:
                self.errors.append(
                    f"任务 '{task.client_task_id}' 的 assigned_agent_id '{task.assigned_agent_id}' 不在有效 agent 列表中"
                )

    def _validate_dependency_references(self, plan: PlannerPlan) -> None:
        valid_client_ids = {task.client_task_id for task in plan.tasks}
        for task in plan.tasks:
            for dep in task.depends_on:
                if dep == task.client_task_id:
                    self.errors.append(f"任务 '{task.client_task_id}' 不能依赖自己")
                elif dep not in valid_client_ids:
                    self.errors.append(f"任务 '{task.client_task_id}' 的依赖 '{dep}' 不存在")

    def _validate_no_circular_dependencies(self, plan: PlannerPlan) -> None:
        graph = {task.client_task_id: task.depends_on.copy() for task in plan.tasks}
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def has_cycle(node: str) -> tuple[bool, list[str]]:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle_found, cycle_path = has_cycle(neighbor)
                    if cycle_found:
                        return True, cycle_path
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor)
                    return True, path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return False, []

        for task in plan.tasks:
            if task.client_task_id not in visited:
                cycle_found, cycle_path = has_cycle(task.client_task_id)
                if cycle_found:
                    self.errors.append(f"检测到循环依赖: {' -> '.join(cycle_path)}")
                    break

    def _validate_primary_agent_self_assignment(self, plan: PlannerPlan) -> None:
        return

    def _validate_task_granularity(self, plan: PlannerPlan, user_request: str | None) -> None:
        if not user_request:
            return

        request_paths = self._extract_target_paths(user_request)
        if len(request_paths) < 2:
            return

        if len(plan.tasks) < len(request_paths):
            self.errors.append(
                f"用户请求包含多个目标文件 {request_paths}，但计划只拆出 {len(plan.tasks)} 个任务，存在多文件拆分不足"
            )
            return

        if len(plan.tasks) == 1:
            payload_paths = self._extract_target_paths_from_plan(plan)
            if len(payload_paths) >= 2:
                self.errors.append(f"单个任务承载了多个目标文件 {payload_paths}，应优先按多个目标文件拆分")

    def _extract_target_paths(self, text: str) -> list[str]:
        paths: list[str] = []
        for match in _TARGET_PATH_PATTERN.findall(text or ""):
            if match not in paths:
                paths.append(match)
        return paths

    def _extract_target_paths_from_plan(self, plan: PlannerPlan) -> list[str]:
        paths: list[str] = []
        for task in plan.tasks:
            payload = task.input_payload or {}
            target_paths = payload.get("target_paths")
            if isinstance(target_paths, list):
                for item in target_paths:
                    if isinstance(item, str) and item and item not in paths:
                        paths.append(item)
            target_path = payload.get("target_path")
            if isinstance(target_path, str) and target_path and target_path not in paths:
                paths.append(target_path)
        return paths

    def _balance_task_distribution(self, plan: PlannerPlan) -> None:
        balanced_tasks, balance_actions = _round_robin_balance_tasks(plan.tasks, self.valid_agent_ids)
        if balance_actions:
            plan.tasks = balanced_tasks
            self.repair_actions.extend(balance_actions)


def validate_plan(
    plan: PlannerPlan,
    valid_agent_ids: list[str],
    user_request: str | None = None,
) -> ValidatorResult:
    validator = OrchestrationPlanValidator(valid_agent_ids)
    return validator.validate(plan, user_request=user_request)


def validate_plan_dict(
    plan_dict: dict,
    valid_agent_ids: list[str],
) -> ValidatorResult:
    try:
        plan = PlannerPlan.model_validate(plan_dict)
    except Exception as exc:
        return ValidatorResult(
            status=ValidationStatus.INVALID,
            normalized_plan=None,
            errors=[f"Plan 解析失败: {str(exc)}"],
            warnings=[],
            repair_actions=[],
        )
    return validate_plan(plan, valid_agent_ids)
