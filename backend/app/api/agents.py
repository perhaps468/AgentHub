# -*- coding: utf-8 -*-
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import CurrentUser
from app.models.agent import Agent
from app.schemas.agent import (
    AgentConfigResponse,
    AgentCreate,
    AgentListResponse,
    AgentResponse,
    AgentUpdate,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])

_Db = Annotated[Session, Depends(get_db)]
_DEFAULT_ROLE = "Custom"
_ALL_TOOLS_PERMISSION = "*"
_DEFAULT_CAPABILITY_TAGS = [
    "需求分析",
    "方案设计",
    "任务拆解",
    "代码生成",
    "调试修复",
    "测试验证",
    "文档编写",
    "前端开发",
    "后端开发",
    "数据分析",
]


def _parse_env_list(*env_names: str) -> list[str]:
    for env_name in env_names:
        raw = os.getenv(env_name, "").strip()
        if raw:
            return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def _provider_model_pairs() -> list[tuple[str, str]]:
    settings = get_settings()
    pairs = [
        ("qwen_openai_compatible", settings.qwen_model),
        ("doubao", settings.doubao_model),
        ("glm", settings.glm_model),
    ]
    configured = _parse_env_list("AGENT_AVAILABLE_MODELS", "AVAILABLE_MODELS")
    if configured:
        explicit_pairs: list[tuple[str, str]] = []
        for model in configured:
            matched_provider = _infer_provider_for_model(model)
            explicit_pairs.append((matched_provider, model))
        return explicit_pairs
    return [(provider, model) for provider, model in pairs if model]


def _available_models() -> list[str]:
    seen: set[str] = set()
    models: list[str] = []
    for _, model in _provider_model_pairs():
        if model and model not in seen:
            seen.add(model)
            models.append(model)
    return models


def _infer_provider_for_model(model: str) -> str:
    settings = get_settings()
    provider_by_model = {
        settings.qwen_model: "qwen_openai_compatible",
        settings.doubao_model: "doubao",
        settings.glm_model: "glm",
    }
    if model in provider_by_model:
        return provider_by_model[model]
    lowered = model.lower()
    if lowered.startswith("glm"):
        return "glm"
    if lowered.startswith("doubao"):
        return "doubao"
    return "qwen_openai_compatible"


def _build_agent_system_prompt(
    name: str,
    capability_tags: list[str],
    description: str | None,
) -> str:
    lines = [
        f"You are {name}, a custom AgentHub agent.",
        "Use all available tools when they help complete the task.",
        "Focus on the selected capability areas below.",
    ]
    if capability_tags:
        lines.append("Selected capability tags:")
        lines.extend(f"- {tag}" for tag in capability_tags)
    if description:
        lines.extend(
            [
                "Additional description:",
                description.strip(),
            ]
        )
    lines.extend(
        [
            "Working style:",
            "- Be direct, practical, and execution-oriented.",
            "- Keep responses structured and easy to act on.",
            "- Stay focused on the selected capability tags.",
        ]
    )
    return "\n".join(lines)


def _agent_to_response(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        owner_id=agent.owner_id,
        name=agent.name,
        role=agent.role,
        provider=agent.provider,
        model=agent.model,
        system_prompt=agent.system_prompt,
        platform=agent.platform,
        description=agent.description,
        avatar_url=agent.avatar_url,
        capability_tags=agent.capability_tags or [],
        tool_permissions=agent.tool_permissions or [],
        is_builtin=agent.is_builtin,
        is_active=agent.is_active,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


def _get_agent_or_404(db: Session, agent_id: str) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/default", response_model=AgentResponse)
def get_default_agent(db: _Db) -> AgentResponse:
    """获取默认 Agent 的展示信息。"""
    agent = db.get(Agent, "pm_agent")
    if agent is None:
        raise HTTPException(status_code=404, detail="Default agent not found")
    return _agent_to_response(agent)


@router.get("/config", response_model=AgentConfigResponse)
def get_agent_config() -> AgentConfigResponse:
    return AgentConfigResponse(
        available_models=_available_models(),
        available_capability_tags=_DEFAULT_CAPABILITY_TAGS,
    )


@router.get("", response_model=AgentListResponse)
def list_agents(
    db: _Db,
    current_user: CurrentUser,
    include_builtin: bool = Query(default=True),
    include_inactive: bool = Query(default=False),
) -> AgentListResponse:
    """列出 Agent：当前用户自建 Agent + 全局内置 Agent。"""
    user_id = str(current_user.id)

    stmt = select(Agent).where(
        or_(
            Agent.is_builtin == True,  # noqa: E712
            Agent.owner_id == user_id,
        )
    )

    if not include_builtin:
        stmt = stmt.where(Agent.is_builtin == False)  # noqa: E712

    if not include_inactive:
        stmt = stmt.where(Agent.is_active == True)  # noqa: E712

    agents = db.execute(stmt).scalars().all()
    items = [_agent_to_response(a) for a in agents]
    return AgentListResponse(items=items, total=len(items))


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(
    body: AgentCreate,
    db: _Db,
    current_user: CurrentUser,
) -> AgentResponse:
    """创建用户自建 Agent。is_builtin 强制为 False，owner_id 绑定当前用户。"""
    user_id = str(current_user.id)

    # 检查同一用户下名称是否冲突
    existing = (
        db.execute(
            select(Agent).where(
                Agent.owner_id == user_id,
                Agent.name == body.name.strip(),
            )
        )
        .scalars()
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent with name '{body.name}' already exists",
        )

    agent = Agent(
        id=f"user_{uuid.uuid4().hex[:12]}",
        owner_id=user_id,
        name=body.name,
        role=_DEFAULT_ROLE,
        provider=body.provider or _infer_provider_for_model(body.model),
        model=body.model,
        system_prompt=_build_agent_system_prompt(
            name=body.name,
            capability_tags=body.capability_tags,
            description=body.description,
        ),
        platform=body.platform,
        description=body.description,
        avatar_url=body.avatar_url,
        capability_tags=body.capability_tags,
        tool_permissions=body.tool_permissions or [_ALL_TOOLS_PERMISSION],
        is_builtin=False,
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _agent_to_response(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(
    agent_id: str,
    db: _Db,
    current_user: CurrentUser,
) -> AgentResponse:
    """获取单个 Agent 详情。内置 Agent 所有人可见，自建 Agent 仅所有者可见。"""
    agent = _get_agent_or_404(db, agent_id)
    user_id = str(current_user.id)

    if not agent.is_builtin and agent.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return _agent_to_response(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
def update_agent(
    agent_id: str,
    body: AgentUpdate,
    db: _Db,
    current_user: CurrentUser,
) -> AgentResponse:
    """更新自建 Agent。内置 Agent 不允许修改。"""
    agent = _get_agent_or_404(db, agent_id)
    user_id = str(current_user.id)

    if agent.is_builtin:
        raise HTTPException(status_code=403, detail="Builtin agents cannot be modified")

    if agent.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _agent_to_response(agent)
