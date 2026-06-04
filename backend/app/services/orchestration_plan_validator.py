# -*- coding: utf-8 -*-
"""Orchestration Plan Validator Service

负责校验和修复主agent输出的结构化plan。
"""
from __future__ import annotations

from typing import Optional

from app.schemas.orchestration_planner import (
    PlannerPlan,
    PlannerTask,
    ValidationStatus,
    ValidatorResult,
)


# 系统限制
MAX_TASKS = 8
MAX_SUMMARY_LENGTH = 500
MAX_TITLE_LENGTH = 80
MAX_GOAL_LENGTH = 300
MAX_REASON_LENGTH = 200

# 均衡分配阈值：当子agent数量 >= 2 且任务数量 >= 2时，强制均衡分配
BALANCE_THRESHOLD_MIN_AGENTS = 2
BALANCE_THRESHOLD_MIN_TASKS = 2


def _round_robin_balance_tasks(
    tasks: list[PlannerTask],
    valid_agent_ids: set[str],
) -> tuple[list[PlannerTask], list[str]]:
    """均衡分配任务给不同的子agent。

    策略：
    1. 过滤出子agent（非主agent/PM）
    2. 按round-robin轮流分配任务给子agent
    3. 只在有多于1个子agent时才触发均衡分配

    Args:
        tasks: 原始任务列表
        valid_agent_ids: 有效agent ID集合

    Returns:
        (修复后的任务列表, repair_actions列表)
    """
    repair_actions: list[str] = []

    # 过滤出可用的子agent（非主agent）
    # 主agent通常是PM角色，我们优先把任务分配给其他agent
    # 按字典序排序以确保round-robin分配的一致性
    sub_agents = sorted([aid for aid in valid_agent_ids if not aid.startswith("group_host_")])

    # 如果没有足够的子agent或任务数不满足阈值，不做均衡
    if len(sub_agents) < BALANCE_THRESHOLD_MIN_AGENTS:
        return tasks, repair_actions

    if len(tasks) < BALANCE_THRESHOLD_MIN_TASKS:
        return tasks, repair_actions

    # 检查当前分配是否已经均衡（每个子agent都有任务）
    current_assignments: dict[str, int] = {agent_id: 0 for agent_id in valid_agent_ids}
    for task in tasks:
        current_assignments[task.assigned_agent_id] = current_assignments.get(task.assigned_agent_id, 0) + 1

    # 统计有多少个子agent有任务
    sub_agents_with_tasks = sum(1 for agent_id in sub_agents if current_assignments.get(agent_id, 0) > 0)

    # 如果已经有足够的子agent在处理任务，不需要重新分配
    if sub_agents_with_tasks >= min(len(sub_agents), len(tasks)):
        return tasks, repair_actions

    # 执行round-robin均衡分配
    balanced_tasks: list[PlannerTask] = []
    agent_index = 0

    for task in tasks:
        # 选择下一个子agent
        target_agent = sub_agents[agent_index % len(sub_agents)]

        if task.assigned_agent_id != target_agent:
            repair_actions.append(
                f"均衡分配修复: 任务 '{task.client_task_id}' 从 '{task.assigned_agent_id}' "
                f"重新分配给 '{target_agent}' (round-robin策略)"
            )
            # 创建新任务对象（因为Pydantic模型是不可变的）
            balanced_task = PlannerTask(
                client_task_id=task.client_task_id,
                title=task.title,
                goal=task.goal,
                assigned_agent_id=target_agent,
                reason=f"[均衡分配] {task.reason}",
                input_payload=task.input_payload,
                depends_on=task.depends_on,
            )
            balanced_tasks.append(balanced_task)
        else:
            balanced_tasks.append(task)

        agent_index += 1

    return balanced_tasks, repair_actions


class OrchestrationPlanValidator:
    """Orchestration Plan 校验器

    职责：
    1. 校验 plan 结构完整性
    2. 校验 agent ID 有效性
    3. 校验依赖关系合法性
    4. 检测循环依赖
    5. 执行自动修复
    """

    def __init__(self, valid_agent_ids: list[str]) -> None:
        """初始化校验器

        Args:
            valid_agent_ids: 当前session中有效的agent ID列表
        """
        self.valid_agent_ids = set(valid_agent_ids)
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.repair_actions: list[str] = []

    def validate(self, plan: PlannerPlan) -> ValidatorResult:
        """执行完整校验流程

        Args:
            plan: 待校验的结构化plan

        Returns:
            ValidatorResult: 校验结果
        """
        self.errors = []
        self.warnings = []
        self.repair_actions = []

        # 1. Pydantic已校验的字段（长度、必填、格式等）由schema层保证
        # 2. 执行业务层校验

        # 检查任务数量
        self._validate_task_count(plan)

        # 检查agent有效性
        self._validate_agent_ids(plan)

        # 检查依赖引用
        self._validate_dependency_references(plan)

        # 检查循环依赖
        self._validate_no_circular_dependencies(plan)

        # 检查primary agent自分配
        self._validate_primary_agent_self_assignment(plan)

        # 均衡分配修复：当有多于1个子agent时，确保任务分配给不同agent
        self._balance_task_distribution(plan)

        # 确定最终状态
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
        """校验任务数量"""
        if len(plan.tasks) == 0:
            self.errors.append("任务列表不能为空 (tasks数组为空)")
            return

        if len(plan.tasks) > MAX_TASKS:
            self.errors.append(
                f"任务数量超过限制：{len(plan.tasks)} > {MAX_TASKS}"
            )

    def _validate_agent_ids(self, plan: PlannerPlan) -> None:
        """校验所有任务的agent ID有效性"""
        for task in plan.tasks:
            if not task.assigned_agent_id:
                self.errors.append(
                    f"任务 '{task.client_task_id}' 的 assigned_agent_id 为空"
                )
            elif task.assigned_agent_id not in self.valid_agent_ids:
                self.errors.append(
                    f"任务 '{task.client_task_id}' 的 assigned_agent_id '{task.assigned_agent_id}' "
                    f"不在有效agent列表中 (有效列表: {sorted(self.valid_agent_ids)})"
                )

    def _validate_dependency_references(self, plan: PlannerPlan) -> None:
        """校验依赖引用是否指向存在的任务"""
        # 构建client_task_id集合
        valid_client_ids = {task.client_task_id for task in plan.tasks}

        for task in plan.tasks:
            for dep in task.depends_on:
                if dep == task.client_task_id:
                    self.errors.append(
                        f"任务 '{task.client_task_id}' 不能依赖自己"
                    )
                elif dep not in valid_client_ids:
                    self.errors.append(
                        f"任务 '{task.client_task_id}' 的依赖 '{dep}' 引用了不存在的client_task_id"
                    )

    def _validate_no_circular_dependencies(self, plan: PlannerPlan) -> None:
        """使用DFS检测循环依赖"""
        # 构建依赖图
        graph: dict[str, list[str]] = {}
        for task in plan.tasks:
            graph[task.client_task_id] = task.depends_on.copy()

        # DFS检测循环
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def has_cycle(node: str) -> tuple[bool, list[str]]:
            """DFS检测从node开始的循环，返回(是否循环, 循环路径)"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    cycle_found, cycle_path = has_cycle(neighbor)
                    if cycle_found:
                        return True, cycle_path
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    return True, path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return False, []

        # 检查所有节点
        for task in plan.tasks:
            if task.client_task_id not in visited:
                cycle_found, cycle_path = has_cycle(task.client_task_id)
                if cycle_found:
                    self.errors.append(
                        f"检测到循环依赖: {' -> '.join(cycle_path)}"
                    )
                    break

    def _validate_primary_agent_self_assignment(self, plan: PlannerPlan) -> None:
        """检查primary agent自分配情况"""
        # 注意：primary agent的ID应该在调用时传入或从配置获取
        # 这里只检查reason是否为空
        pass

    def _balance_task_distribution(self, plan: PlannerPlan) -> None:
        """均衡任务分配，确保子agent一人一个任务。

        策略：
        1. 过滤出可用的子agent（非主agent/PM）
        2. 当子agent数量>=2且任务数量>=2时，强制执行round-robin均衡分配
        3. 主agent（PM角色）默认不分配执行任务，除非没有其他选择
        """
        balanced_tasks, balance_actions = _round_robin_balance_tasks(
            plan.tasks,
            self.valid_agent_ids,
        )
        if balance_actions:
            plan.tasks = balanced_tasks
            self.repair_actions.extend(balance_actions)


def validate_plan(
    plan: PlannerPlan,
    valid_agent_ids: list[str],
) -> ValidatorResult:
    """便捷函数：校验单个plan

    Args:
        plan: 待校验的结构化plan
        valid_agent_ids: 有效agent ID列表

    Returns:
        ValidatorResult: 校验结果
    """
    validator = OrchestrationPlanValidator(valid_agent_ids)
    return validator.validate(plan)


def validate_plan_dict(
    plan_dict: dict,
    valid_agent_ids: list[str],
) -> ValidatorResult:
    """便捷函数：直接从dict校验

    Args:
        plan_dict: 待校验的plan字典
        valid_agent_ids: 有效agent ID列表

    Returns:
        ValidatorResult: 校验结果
    """
    try:
        plan = PlannerPlan.model_validate(plan_dict)
    except Exception as e:
        return ValidatorResult(
            status=ValidationStatus.INVALID,
            normalized_plan=None,
            errors=[f"Plan解析失败: {str(e)}"],
            warnings=[],
            repair_actions=[],
        )
    return validate_plan(plan, valid_agent_ids)
