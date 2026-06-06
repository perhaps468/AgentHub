# -*- coding: utf-8 -*-
"""Builtin agent seed helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.builtin import GLM_CODER_SYSTEM_PROMPT, GLM_REVIEWER_SYSTEM_PROMPT
from app.models.agent import Agent

LEGACY_PM_AGENT_IDS = {"primary_pm_agent", "pm_agent"}

BUILTIN_AGENTS = [
    Agent(
        id="glm_coder",
        owner_id=None,
        name="GLM Coder",
        role="Coder",
        provider="glm",
        model="glm-4.7-flash",
        system_prompt=GLM_CODER_SYSTEM_PROMPT,
        platform="custom",
        description="内置 Coder Agent，负责代码生成与调试",
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
        description="内置 Reviewer Agent，负责代码审查与质量保障",
        avatar_url=None,
        capability_tags=["代码审查", "安全审计", "性能分析", "测试验证"],
        tool_permissions=[],
        is_builtin=True,
        is_active=True,
    ),
]


def seed_builtin_agents(db: Session) -> None:
    """Seed supported builtin agents and retire legacy builtin PM agents."""
    legacy_pm_agents = (
        db.execute(select(Agent).where(Agent.id.in_(LEGACY_PM_AGENT_IDS)))
        .scalars()
        .all()
    )
    for agent in legacy_pm_agents:
        if agent.is_active:
            agent.is_active = False
            db.add(agent)

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
        else:
            existing.is_active = True
            db.add(existing)

    db.commit()
