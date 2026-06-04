from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.agent import Agent

GROUP_HOST_AGENT_NAME = "群聊主Agent"
GROUP_HOST_AGENT_ROLE = "PM"
GROUP_HOST_AGENT_DESCRIPTION = "负责需求分析、任务分解、任务分发，并向用户汇总结果"
GROUP_HOST_AGENT_SYSTEM_PROMPT = """你是用户专属的群聊主Agent。

你的职责固定为：
- 分析用户需求
- 做任务分解，将需求分解为可执行任务
- 指派任务，把任务指派给群聊中的其他成员Agent
- 跟踪任务执行状态与确认结果
- 最终直接向用户汇总结果并回复用户

行为规则：
- 你是群聊中的默认主持Agent，负责主持，不负责抢占普通执行任务，除非没有其他Agent可分配
- 先做需求分析，再输出任务计划和分配方案
- 分发任务时，优先把不同文件或不同子任务分给不同Agent并行处理
- 当成员Agent产出待确认写入时，等待用户确认或取消
- 当所有子任务进入终态后，你必须向用户输出“全部任务完成。”
"""


def get_user_group_host_agent(db: Session, owner_id: str) -> Agent | None:
    return (
        db.execute(
            select(Agent)
            .where(
                Agent.owner_id == owner_id,
                Agent.name == GROUP_HOST_AGENT_NAME,
                Agent.is_builtin == False,  # noqa: E712
            )
            .order_by(Agent.updated_at.desc(), Agent.created_at.desc())
        )
        .scalars()
        .first()
    )


def ensure_user_group_host_agent(db: Session, owner_id: str) -> Agent:
    existing = get_user_group_host_agent(db, owner_id)
    if existing is not None:
        changed = False
        if existing.role != GROUP_HOST_AGENT_ROLE:
            existing.role = GROUP_HOST_AGENT_ROLE
            changed = True
        if existing.description != GROUP_HOST_AGENT_DESCRIPTION:
            existing.description = GROUP_HOST_AGENT_DESCRIPTION
            changed = True
        if existing.system_prompt != GROUP_HOST_AGENT_SYSTEM_PROMPT:
            existing.system_prompt = GROUP_HOST_AGENT_SYSTEM_PROMPT
            changed = True
        if existing.is_active is False:
            existing.is_active = True
            changed = True
        if changed:
            db.add(existing)
            db.commit()
            db.refresh(existing)
        return existing

    max_user_agent_id = (
        db.execute(
            select(func.count()).select_from(Agent).where(Agent.owner_id == owner_id)
        )
        .scalar_one()
    )
    agent = Agent(
        id=f"group_host_{owner_id}_{max_user_agent_id + 1}",
        owner_id=owner_id,
        name=GROUP_HOST_AGENT_NAME,
        role=GROUP_HOST_AGENT_ROLE,
        provider="qwen_openai_compatible",
        model=get_settings().qwen_model,
        system_prompt=GROUP_HOST_AGENT_SYSTEM_PROMPT,
        platform="custom",
        description=GROUP_HOST_AGENT_DESCRIPTION,
        avatar_url=None,
        capability_tags=["需求分析", "任务分解", "任务分发", "结果汇总"],
        tool_permissions=["*"],
        is_builtin=False,
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent
