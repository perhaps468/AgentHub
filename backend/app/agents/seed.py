# -*- coding: utf-8 -*-
"""内置 Agent 预置脚本

在 create_all() 之后调用，将内置 Agent 写入数据库。
保证幂等：若已存在则跳过，不重复插入。
"""
from sqlalchemy.orm import Session

from app.agents.builtin import PM_AGENT_SYSTEM_PROMPT, PRIMARY_PM_AGENT_SYSTEM_PROMPT, GLM_CODER_SYSTEM_PROMPT, GLM_REVIEWER_SYSTEM_PROMPT
from app.models.agent import Agent

BUILTIN_AGENTS = [
    Agent(
        id="primary_pm_agent",
        owner_id=None,
        name="Primary PM Agent",
        role="PM",
        provider="qwen_openai_compatible",
        model="qwen-plus",
        system_prompt=PRIMARY_PM_AGENT_SYSTEM_PROMPT,
        platform="custom",
        description="内置主 PM Agent，群聊模式下默认参与对话，负责需求协调与任务分发",
        avatar_url=None,
        capability_tags=["需求分析", "方案设计", "任务拆解", "群聊协调"],
        tool_permissions=[],
        is_builtin=True,
        is_active=True,
    ),
    Agent(
        id="pm_agent",
        owner_id=None,
        name="PM Agent",
        role="PM",
        provider="qwen_openai_compatible",
        model="qwen-plus",
        system_prompt=PM_AGENT_SYSTEM_PROMPT,
        platform="custom",
        description="内置产品经理 Agent，负责需求理解、功能拆解与任务规划",
        avatar_url=None,
        capability_tags=["需求分析", "方案设计", "任务拆解", "产品规划"],
        tool_permissions=[],
        is_builtin=True,
        is_active=True,
    ),
    Agent(
        id="glm_coder",
        owner_id=None,
        name="GLM Coder",
        role="Coder",
        provider="glm",
        model="glm-4.7-flash",
        system_prompt=GLM_CODER_SYSTEM_PROMPT,
        platform="custom",
        description="内置 Coder Agent，基于智谱 GLM-4.7-Flash，负责代码生成与调试",
        avatar_url=None,
        capability_tags=["代码生成", "调试修复", "前端开发", "后端开发", "测试验证"],
        tool_permissions=["*"],
        is_builtin=True,
        is_active=True,
    ),
    Agent(
        id="glm_reviewer",
        owner_id=None,
        name="GLM Reviewer",
        role="Reviewer",
        provider="glm",
        model="glm-4.7-flash",
        system_prompt=GLM_REVIEWER_SYSTEM_PROMPT,
        platform="custom",
        description="内置 Reviewer Agent，基于智谱 GLM-4.7-Flash，负责代码审查与质量保障",
        avatar_url=None,
        capability_tags=["代码审查", "安全审计", "性能分析", "测试验证"],
        tool_permissions=[],
        is_builtin=True,
        is_active=True,
    ),
]


def seed_builtin_agents(db: Session) -> None:
    """预置内置 Agent，幂等执行（已存在则跳过）。"""
    for agent_def in BUILTIN_AGENTS:
        existing = db.get(Agent, agent_def.id)
        if existing is None:
            db.add(
                Agent(
                    id=agent_def.id,
                    owner_id=agent_def.owner_id,
                    name=agent_def.name,
                    role=agent_def.role,
                    provider=agent_def.provider,
                    model=agent_def.model,
                    system_prompt=agent_def.system_prompt,
                    platform=agent_def.platform,
                    description=agent_def.description,
                    avatar_url=agent_def.avatar_url,
                    capability_tags=agent_def.capability_tags,
                    tool_permissions=agent_def.tool_permissions,
                    is_builtin=agent_def.is_builtin,
                    is_active=agent_def.is_active,
                )
            )
    db.commit()
