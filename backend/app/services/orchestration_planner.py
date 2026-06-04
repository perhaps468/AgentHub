# -*- coding: utf-8 -*-
"""Orchestration Planner Service

主agent语义规划服务，负责：
1. 组装主agent的planner prompt
2. 调用LLM获取结构化plan
3. 解析和校验结果
4. 处理fallback
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.schemas.orchestration_planner import (
    PlannerPlan,
    PlannerResult,
    PlannerStatus,
    PlanningSource,
    ValidationStatus,
    ValidatorResult,
)
from app.services.orchestration_plan_validator import validate_plan


# 默认Planner Prompt模板
DEFAULT_PLANNER_PROMPT_TEMPLATE = """你是群聊中的主Agent，负责将用户请求拆解为可执行的任务计划。

## 你的职责
1. 分析用户需求，理解任务目标
2. 判断是否需要拆分任务，还是单一任务即可完成
3. 选择最合适的agent来执行每个任务
4. 输出结构化的任务计划

## 输出格式要求
你必须严格按照以下JSON格式输出，不得包含任何其他内容：

{
    "planner_summary": "规划摘要，说明将需求拆成几个任务、并行还是串行执行",
    "planning_mode": "parallel | sequential | mixed",
    "tasks": [
        {
            "client_task_id": "task_1",
            "title": "任务标题，简洁明了",
            "goal": "任务的具体目标描述",
            "assigned_agent_id": "分配到的agent_id",
            "reason": "为什么分配给这个agent",
            "input_payload": {{"target_paths": [], "requested_changes": []}},
            "depends_on": ["依赖的client_task_id列表，没有则为空数组"]
        }
    ]
}

## 约束条件
- 任务数量：1-8个，不要为了凑数硬拆
- client_task_id格式：仅允许字母、数字、下划线、连字符，如 task_1, task_2
- 必须是有效存在的agent_id，不要自己发明
- 每个任务的depends_on只能引用在tasks数组中已定义的任务
- 不要产生循环依赖

## Agent选择策略
1. 优先按capability_tags匹配：
   - 前端任务：frontend, ui, vue, react
   - 后端任务：backend, api, python, fastapi
   - 测试任务：test, qa, pytest
   - 文档任务：docs, spec, writing
2. 其次按role匹配
3. 最后按agent_id字典序稳定选择

## 重要提示
- 若请求本质上只能拆成1个task，不要硬拆成多个
- 主agent默认只主持不执行，除非没有更合适的子agent
- 输出必须是合法的JSON，不要用markdown包裹

现在开始分析用户请求并输出任务计划。
"""


def build_planner_prompt(
    user_request: str,
    session_mode: str,
    primary_agent: dict[str, Any] | None,
    candidate_agents: list[dict[str, Any]],
) -> str:
    """构建planner prompt

    Args:
        user_request: 用户原始请求
        session_mode: session模式（group/single）
        primary_agent: 主agent信息
        candidate_agents: 候选执行agent列表

    Returns:
        完整的prompt字符串
    """
    parts = [DEFAULT_PLANNER_PROMPT_TEMPLATE]

    # 添加用户请求
    parts.append("\n\n## 用户请求\n")
    parts.append(user_request)

    # 添加主agent信息
    if primary_agent:
        parts.append("\n\n## 主Agent信息\n")
        parts.append(f"- ID: {primary_agent.get('id', 'unknown')}")
        parts.append(f"- Name: {primary_agent.get('name', 'unknown')}")
        parts.append(f"- Role: {primary_agent.get('role', 'unknown')}")
        if primary_agent.get('capability_tags'):
            parts.append(f"- Capability Tags: {', '.join(primary_agent['capability_tags'])}")

    # 添加候选agent信息
    if candidate_agents:
        parts.append("\n\n## 可用Agent列表\n")
        for agent in candidate_agents:
            agent_id = agent.get('id', 'unknown')
            parts.append(f"\n### {agent_id}\n")
            parts.append(f"- Name: {agent.get('name', agent_id)}\n")
            parts.append(f"- Role: {agent.get('role', 'unknown')}\n")
            tags = agent.get('capability_tags', [])
            if tags:
                parts.append(f"- Capability Tags: {', '.join(tags)}\n")
            parts.append(f"- Is Primary: {agent.get('is_primary', False)}\n")

    # 添加系统限制
    parts.append("\n\n## 系统限制\n")
    parts.append(f"- 最大任务数: 8\n")
    parts.append(f"- 不允许分配给不存在的agent\n")
    parts.append(f"- 不允许循环依赖\n")

    return "".join(parts)


def parse_planner_output(raw_output: str | None) -> PlannerPlan | None:
    """解析LLM输出为PlannerPlan

    Args:
        raw_output: LLM原始输出

    Returns:
        解析后的PlannerPlan，解析失败返回None
    """
    if not raw_output:
        return None

    output = raw_output.strip()

    # 尝试提取JSON
    # 1. 去掉markdown代码块包装
    json_match = re.search(
        r'```(?:json)?\s*([\s\S]*?)```',
        output,
        re.IGNORECASE
    )
    if json_match:
        output = json_match.group(1).strip()
    else:
        # 尝试找第一个 { 到最后一个 }
        first_brace = output.find('{')
        last_brace = output.rfind('}')
        if first_brace >= 0 and last_brace > first_brace:
            output = output[first_brace:last_brace + 1]

    # 解析JSON
    try:
        data = json.loads(output)
        return PlannerPlan.model_validate(data)
    except json.JSONDecodeError:
        return None
    except Exception:
        return None


class OrchestrationPlanner:
    """Orchestration Planner

    负责调用LLM生成结构化任务计划。
    """

    def __init__(
        self,
        valid_agent_ids: list[str],
        prompt_template: str | None = None,
    ) -> None:
        """初始化Planner

        Args:
            valid_agent_ids: 有效agent ID列表
            prompt_template: 自定义prompt模板
        """
        self.valid_agent_ids = set(valid_agent_ids)
        self.prompt_template = prompt_template or DEFAULT_PLANNER_PROMPT_TEMPLATE

    async def plan(
        self,
        user_request: str,
        session_mode: str,
        primary_agent: dict[str, Any] | None,
        candidate_agents: list[dict[str, Any]],
    ) -> PlannerResult:
        """执行规划

        Args:
            user_request: 用户原始请求
            session_mode: session模式
            primary_agent: 主agent信息
            candidate_agents: 候选执行agent列表

        Returns:
            PlannerResult: 规划结果
        """
        # 1. 构建prompt
        prompt = self._build_prompt(
            user_request=user_request,
            session_mode=session_mode,
            primary_agent=primary_agent,
            candidate_agents=candidate_agents,
        )

        # 2. 调用LLM
        raw_output = await self._call_llm(prompt)

        if raw_output is None:
            return PlannerResult(
                status=PlannerStatus.PLANNER_RETURNED_RAW,
                planning_source=PlanningSource.PLANNER,
                raw_output=None,
                parsed_plan=None,
                validator_result=None,
                fallback_used=False,
                error_message="LLM调用失败",
            )

        # 3. 解析输出
        parsed_plan = parse_planner_output(raw_output)

        if parsed_plan is None:
            return PlannerResult(
                status=PlannerStatus.PLANNER_PARSED,
                planning_source=PlanningSource.PLANNER,
                raw_output=raw_output,
                parsed_plan=None,
                validator_result=None,
                fallback_used=False,
                error_message="无法解析LLM输出为有效JSON",
            )

        # 4. 校验plan
        validator_result = validate_plan(parsed_plan, list(self.valid_agent_ids))

        # 5. 确定最终状态
        if validator_result.status == ValidationStatus.VALID:
            return PlannerResult(
                status=PlannerStatus.VALIDATOR_VALID,
                planning_source=PlanningSource.PLANNER,
                raw_output=raw_output,
                parsed_plan=parsed_plan,
                validator_result=validator_result,
                fallback_used=False,
                error_message=None,
            )

        if validator_result.status == ValidationStatus.REPAIRED:
            return PlannerResult(
                status=PlannerStatus.VALIDATOR_REPAIRED,
                planning_source=PlanningSource.PLANNER_REPAIRED,
                raw_output=raw_output,
                parsed_plan=validator_result.normalized_plan,
                validator_result=validator_result,
                fallback_used=False,
                error_message=None,
            )

        # validator_result.status == ValidationStatus.INVALID
        return PlannerResult(
            status=PlannerStatus.VALIDATOR_INVALID,
            planning_source=PlanningSource.PLANNER,
            raw_output=raw_output,
            parsed_plan=None,
            validator_result=validator_result,
            fallback_used=False,
            error_message="Planner输出校验失败: " + "; ".join(validator_result.errors),
        )

    def _build_prompt(
        self,
        user_request: str,
        session_mode: str,
        primary_agent: dict[str, Any] | None,
        candidate_agents: list[dict[str, Any]],
    ) -> str:
        """构建prompt"""
        return build_planner_prompt(
            user_request=user_request,
            session_mode=session_mode,
            primary_agent=primary_agent,
            candidate_agents=candidate_agents,
        )

    async def _call_llm(self, prompt: str) -> str | None:
        """调用LLM

        子类可以重写此方法以自定义LLM调用逻辑。

        Args:
            prompt: 构造好的prompt

        Returns:
            LLM输出文本，失败返回None
        """
        # 默认实现抛出异常，由调用者处理
        # 实际调用时需要通过依赖注入或子类重写
        raise NotImplementedError("请重写_call_llm方法或使用OrchestrationPlannerWithLLM")


class OrchestrationPlannerWithLLM(OrchestrationPlanner):
    """带LLM集成的OrchestrationPlanner"""

    def __init__(
        self,
        valid_agent_ids: list[str],
        llm_adapter: Any,  # LLMAdapter
        model: str = "qwen-plus",
        prompt_template: str | None = None,
    ) -> None:
        """初始化

        Args:
            valid_agent_ids: 有效agent ID列表
            llm_adapter: LLMAdapter实例
            model: 模型名称
            prompt_template: 自定义prompt模板
        """
        super().__init__(valid_agent_ids, prompt_template)
        self.llm_adapter = llm_adapter
        self.model = model

    async def _call_llm(self, prompt: str) -> str | None:
        """调用LLM"""
        try:
            from app.runtime.memory import Message as RuntimeMessage

            messages = [RuntimeMessage(role="user", content=prompt)]
            response = await self.llm_adapter.async_generate_with_history(
                messages_history=messages,
                model=self.model,
                temperature=0.3,  # 使用较低温度以获得更稳定的JSON输出
            )
            return response.response
        except Exception as e:
            return None
