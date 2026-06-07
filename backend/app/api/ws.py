# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import os
import uuid
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uvicorn.protocols.utils import ClientDisconnected

from app.core.config import get_settings, load_env_file
from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.agent import Agent
from app.models.message import Message
from app.models.orchestration import OrchestrationRun, OrchestrationTask
from app.models.session import ChatSession, utcnow
from app.models.session_member import SessionMember
from app.observability.group_chat_audit import get_group_chat_audit_recorder
from app.schemas.common import to_iso_z
from app.api.agents import resolve_default_agent
from app.services.fixed_agent_responder import FixedAgentResponder
from app.services.agent_runtime import get_provider_for_agent
from app.runtime.llm_adapter import LLMAdapter
from app.services.orchestration import OrchestrationService
from app.services.orchestration_executor import OrchestrationExecutor
from app.services.orchestration_planner import (
    OrchestrationPlanner,
    build_planner_prompt,
    parse_planner_output,
    DEFAULT_PLANNER_PROMPT_TEMPLATE,
)
from app.services.orchestration_plan_validator import validate_plan
from app.services.task_splitter import plan_tasks_from_message
from app.services.workspace import WorkspaceService
from app.schemas.orchestration_planner import (
    PlanningSource,
    PlannerPlan,
    ValidationStatus,
)
from starlette.websockets import WebSocketState

router = APIRouter(prefix="/ws", tags=["websocket"])
_GROUP_CHAT_AUDIT = get_group_chat_audit_recorder()


class _WsConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, tuple[WebSocket, str]] = {}

    def register(self, session_id: str, websocket: WebSocket, user_id: str) -> None:
        self._connections[session_id] = (websocket, user_id)

    def unregister(self, session_id: str) -> None:
        self._connections.pop(session_id, None)

    def get_connection(self, session_id: str) -> Optional[tuple[WebSocket, str]]:
        return self._connections.get(session_id)

    def is_connected(self, session_id: str) -> bool:
        return session_id in self._connections


_WS_CONNECTION_MANAGER = _WsConnectionManager()


def get_ws_connection_manager() -> _WsConnectionManager:
    return _WS_CONNECTION_MANAGER


def _is_ws_disconnect_error(exc: BaseException) -> bool:
    if isinstance(exc, (WebSocketDisconnect, ClientDisconnected)):
        return True
    if isinstance(exc, RuntimeError):
        return "Cannot call \"send\" once a close message has been sent." in str(exc)
    return False


async def _safe_send_json(websocket: WebSocket, payload: dict[str, Any]) -> bool:
    if (
        getattr(websocket, "client_state", None) is WebSocketState.DISCONNECTED
        or getattr(websocket, "application_state", None) is WebSocketState.DISCONNECTED
    ):
        return False
    try:
        await websocket.send_json(payload)
        return True
    except Exception as exc:
        if _is_ws_disconnect_error(exc):
            return False
        raise


async def ws_send_apply_result(
    session_id: str,
    change_id: str,
    success: bool,
    status: str,
    message: str,
    run_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
) -> bool:
    """向 WebSocket 会话推送 apply_result 事件。

    使用异步方式推送，避免阻塞 REST 请求。

    M4: Added task-aware fields for precise frontend state sync.
    """
    conn = _WS_CONNECTION_MANAGER.get_connection(session_id)
    if conn is None:
        return False

    websocket, _ = conn
    try:
        payload = {
            "type": "apply_result",
            "change_id": change_id,
            "success": success,
            "status": status,
            "message": message,
            "timestamp": _utcnow_iso(),
        }
        if run_id is not None:
            payload["run_id"] = run_id
        if task_id is not None:
            payload["task_id"] = task_id
        if agent_id is not None:
            payload["agent_id"] = agent_id
        await _safe_send_json(websocket, payload)
        return True
    except Exception:
        return False


def runtime_use_runtime_agent() -> bool:
    load_env_file()
    return os.getenv("RUNTIME_USE_RUNTIME_AGENT", "0") in ("1", "true", "True")


def chat_stream_output_enabled() -> bool:
    return get_settings().chat_stream_output_enabled


def get_default_agent(owner_id: str | None = None):
    db = SessionLocal()
    try:
        return resolve_default_agent(db, owner_id)
    finally:
        db.close()


def get_session_agent(db, session: ChatSession) -> Agent | None:
    agent_id = getattr(session, "agent_id", None)
    if not agent_id:
        return None
    return db.get(Agent, agent_id)


def _resolve_default_agent_for_single_chat(db, owner_id: str | None) -> Agent | None:
    """Get default agent for single chat mode, excluding group host agent."""
    return resolve_default_agent(db, owner_id, include_group_host=False)


def get_primary_agent_for_group(db, session: ChatSession) -> Agent | None:
    if session.mode != "group":
        return None
    primary_member = db.query(SessionMember).filter(
        SessionMember.session_id == session.id,
        SessionMember.is_primary.is_(True),
    ).first()
    if primary_member is not None:
        return db.get(Agent, primary_member.member_id)

    fallback_member = db.query(SessionMember).filter(
        SessionMember.session_id == session.id,
        SessionMember.member_type == "agent",
    ).order_by(SessionMember.created_at.asc()).first()
    if fallback_member is None:
        return None
    return db.get(Agent, fallback_member.member_id)


class _InFlightGuard:
    """Per-session concurrency guard.

    Now allows concurrent streaming responses for the same session — multiple
    requests with different stream_ids are routed independently by the frontend
    via the stream_id. This class is kept for future use (e.g. rate-limiting
    or interrupting a specific stream).
    """

    def __init__(self) -> None:
        self._sessions: set[str] = set()

    def is_in_flight(self, session_id: str) -> bool:
        return session_id in self._sessions

    def try_enter(self, session_id: str) -> bool:
        """Always allow — concurrent streaming per session is now supported."""
        return True

    def leave(self, session_id: str) -> None:
        self._sessions.discard(session_id)

    def interrupt(self, session_id: str) -> None:
        self._sessions.discard(session_id)

    def clear(self) -> None:
        self._sessions.clear()


_IN_FLIGHT_GUARD = _InFlightGuard()


def set_guard(guard: _InFlightGuard) -> None:
    global _IN_FLIGHT_GUARD
    _IN_FLIGHT_GUARD = guard


def _utcnow_iso() -> str:
    return to_iso_z(utcnow())


async def _send_error(
    websocket: WebSocket,
    code: str,
    message: str,
    stream_id: str | None = None,
    agent_role: str = "PM",
) -> None:
    await _safe_send_json(websocket, {
        "type": "error",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id or str(uuid.uuid4()),
        "error_code": code,
        "error_message": message,
    })


async def ws_send_message_start(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message: Message,
    run_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    payload = {
        "type": "message_start",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message": {
            "id": message.id,
            "session_id": message.session_id,
            "sender_type": "agent",
            "sender_role": message.sender_role,
            "type": message.type,
            "content": message.content,
            "payload": message.payload,
            "metadata": message.msg_metadata,
            "status": message.status,
            "created_at": to_iso_z(message.created_at),
        },
    }
    if run_id is not None:
        payload["run_id"] = run_id
    if task_id is not None:
        payload["task_id"] = task_id
    if agent_id is not None:
        payload["agent_id"] = agent_id
    await _safe_send_json(websocket, payload)


async def ws_send_message_delta(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message_id: str,
    delta: str,
    run_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    payload = {
        "type": "message_delta",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "delta": delta,
    }
    if run_id is not None:
        payload["run_id"] = run_id
    if task_id is not None:
        payload["task_id"] = task_id
    if agent_id is not None:
        payload["agent_id"] = agent_id
    await _safe_send_json(websocket, payload)


async def ws_send_message_end(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message_id: str,
    status: str,
    final_content: str | None = None,
    run_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    payload = {
        "type": "message_end",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "status": status,
    }
    if final_content is not None:
        payload["final_content"] = final_content
    if run_id is not None:
        payload["run_id"] = run_id
    if task_id is not None:
        payload["task_id"] = task_id
    if agent_id is not None:
        payload["agent_id"] = agent_id
    await _safe_send_json(websocket, payload)


async def ws_send_message_error(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message_id: str,
    error_code: str,
    error_message: str,
    run_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    payload = {
        "type": "message_error",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "error_code": error_code,
        "error_message": error_message,
    }
    if run_id is not None:
        payload["run_id"] = run_id
    if task_id is not None:
        payload["task_id"] = task_id
    if agent_id is not None:
        payload["agent_id"] = agent_id
    await _safe_send_json(websocket, payload)


async def ws_send_tool_event(
    websocket: WebSocket,
    tool_name: str,
    arguments: dict,
    response: str | None,
    status: str,
    stream_id: str,
    message_id: str,
    run_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    payload = {
        "type": "tool_event",
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "tool_name": tool_name,
        "status": status,
        "arguments": arguments,
    }
    if response is not None:
        payload["response"] = response
    if run_id is not None:
        payload["run_id"] = run_id
    if task_id is not None:
        payload["task_id"] = task_id
    if agent_id is not None:
        payload["agent_id"] = agent_id
    await _safe_send_json(websocket, payload)


async def ws_send_runtime_state(
    websocket: WebSocket,
    stream_id: str,
    message_id: str,
    state: str,
    timestamp: str,
    run_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
) -> None:
    payload = {
        "type": "runtime_state",
        "stream_id": stream_id,
        "message_id": message_id,
        "state": state,
        "timestamp": timestamp,
    }
    if run_id is not None:
        payload["run_id"] = run_id
    if task_id is not None:
        payload["task_id"] = task_id
    if agent_id is not None:
        payload["agent_id"] = agent_id
    await _safe_send_json(websocket, payload)


async def ws_send_change_preview(
    websocket: WebSocket,
    stream_id: str,
    message_id: str,
    change_id: str,
    operation: str,
    path: str,
    unified_diff: str,
    status: str,
    timestamp: str,
    run_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
    agent_role: str | None = None,
) -> None:
    payload = {
        "type": "change_preview",
        "stream_id": stream_id,
        "message_id": message_id,
        "change_id": change_id,
        "operation": operation,
        "path": path,
        "unified_diff": unified_diff,
        "status": status,
        "timestamp": timestamp,
    }
    if run_id is not None:
        payload["run_id"] = run_id
    if task_id is not None:
        payload["task_id"] = task_id
    if agent_id is not None:
        payload["agent_id"] = agent_id
    if agent_role is not None:
        payload["agent_role"] = agent_role
    await _safe_send_json(websocket, payload)


async def ws_send_preview_result(
    websocket: WebSocket,
    preview_id: str,
    workspace_id: str,
    preview_url: str,
    status: str,
    message_id: str,
    stream_id: str,
    timestamp: str,
) -> None:
    await _safe_send_json(websocket, {
        "type": "preview_result",
        "preview_id": preview_id,
        "workspace_id": workspace_id,
        "preview_url": preview_url,
        "status": status,
        "message_id": message_id,
        "stream_id": stream_id,
        "timestamp": timestamp,
    })


async def ws_send_repair_state(
    websocket: WebSocket,
    state: str,
    attempt: int,
    max_attempts: int,
    message: str,
    stream_id: str,
    message_id: str,
    timestamp: str,
) -> None:
    await _safe_send_json(websocket, {
        "type": "repair_state",
        "state": state,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "message": message,
        "stream_id": stream_id,
        "message_id": message_id,
        "timestamp": timestamp,
    })


async def ws_send_task_start(
    websocket: WebSocket,
    run_id: str,
    task_id: str,
    agent_id: str,
    stream_id: str,
    title: str,
    goal: str,
    kind: str,
) -> None:
    await _safe_send_json(websocket, {
        "type": "task_start",
        "run_id": run_id,
        "task_id": task_id,
        "agent_id": agent_id,
        "stream_id": stream_id,
        "title": title,
        "goal": goal,
        "kind": kind,
        "timestamp": _utcnow_iso(),
    })


async def ws_send_task_end(
    websocket: WebSocket,
    run_id: str,
    task_id: str,
    agent_id: str,
    stream_id: str,
    status: str,
    result: dict | None = None,
) -> None:
    payload = {
        "type": "task_end",
        "run_id": run_id,
        "task_id": task_id,
        "agent_id": agent_id,
        "stream_id": stream_id,
        "status": status,
        "timestamp": _utcnow_iso(),
    }
    if result is not None:
        payload["result"] = result
    await _safe_send_json(websocket, payload)

async def ws_send_task_error(
    websocket: WebSocket,
    run_id: str,
    task_id: str,
    agent_id: str,
    stream_id: str,
    error_code: str,
    error_message: str,
) -> None:
    await _safe_send_json(websocket, {
        "type": "task_error",
        "run_id": run_id,
        "task_id": task_id,
        "agent_id": agent_id,
        "stream_id": stream_id,
        "error_code": error_code,
        "error_message": error_message,
        "timestamp": _utcnow_iso(),
    })


async def ws_send_run_started(
    websocket: WebSocket,
    run_id: str,
    session_id: str,
    planner_agent_id: str,
    task_count: int,
) -> None:
    """Send orchestration_run_started event.

    M6: This event marks the transition from planned to running state.
    """
    await _safe_send_json(websocket, {
        "type": "orchestration_run_started",
        "run_id": run_id,
        "session_id": session_id,
        "planner_agent_id": planner_agent_id,
        "task_count": task_count,
        "timestamp": _utcnow_iso(),
    })


async def ws_send_run_finished(
    websocket: WebSocket,
    run_id: str,
    session_id: str,
    status: str,
    summary: str | None = None,
) -> None:
    """Send orchestration_run_finished event.

    M6: This event marks the run reaching a terminal state.
    """
    payload = {
        "type": "orchestration_run_finished",
        "run_id": run_id,
        "session_id": session_id,
        "status": status,
        "timestamp": _utcnow_iso(),
    }
    if summary is not None:
        payload["summary"] = summary
    await _safe_send_json(websocket, payload)


async def ws_send_run_updated(
    websocket: WebSocket,
    run_id: str,
    session_id: str,
    status: str,
) -> None:
    """Send orchestration_run_updated event.

    M6: For intermediate run status changes (e.g., planned -> running).
    """
    await _safe_send_json(websocket, {
        "type": "orchestration_run_updated",
        "run_id": run_id,
        "session_id": session_id,
        "status": status,
        "timestamp": _utcnow_iso(),
    })


async def ws_send_session_member_status(
    websocket: WebSocket,
    session_id: str,
    member_id: str,
    agent_id: str,
    status: str,
) -> None:
    await _safe_send_json(websocket, {
        "type": "session_member_status",
        "session_id": session_id,
        "member_id": member_id,
        "agent_id": agent_id,
        "status": status,
        "timestamp": _utcnow_iso(),
    })


async def _send_group_plain_response(
    websocket: WebSocket,
    db,
    session_id: str,
    agent_role: str,
    stream_id: str,
    final_content: str,
    source: str,
) -> None:
    agent_message = Message(
        session_id=session_id,
        sender_type="agent",
        sender_role=agent_role,
        content=final_content,
        type="text",
        status="completed",
        payload={"text": final_content},
        msg_metadata={"source": source, "stream_id": stream_id, "group_chat_direct": True},
        created_at=utcnow(),
    )
    db.add(agent_message)
    db.commit()
    db.refresh(agent_message)

    await ws_send_message_start(websocket, agent_role=agent_role, stream_id=stream_id, message=agent_message)
    await ws_send_message_end(
        websocket,
        agent_role=agent_role,
        stream_id=stream_id,
        message_id=agent_message.id,
        status="completed",
        final_content=final_content,
    )
    _GROUP_CHAT_AUDIT.record_group_response(
        session_id=session_id,
        stream_id=stream_id,
        agent_role=agent_role,
        final_content=final_content,
        source=source,
    )


async def _send_orchestration_summary_message(
    websocket: WebSocket,
    db,
    session_id: str,
    run_id: str,
    agent_role: str,
) -> bool:
    summary_message = next(
        (
            message
            for message in (
                db.query(Message)
                .filter(
                    Message.session_id == session_id,
                    Message.sender_type == "agent",
                )
                .order_by(Message.created_at.desc(), Message.id.desc())
                .all()
            )
            if (message.msg_metadata or {}).get("run_id") == run_id
            and (message.msg_metadata or {}).get("is_orchestration_summary") is True
        ),
        None,
    )
    if summary_message is None:
        return False

    summary_stream_id = str(uuid.uuid4())
    await ws_send_message_start(
        websocket,
        agent_role=agent_role,
        stream_id=summary_stream_id,
        message=summary_message,
        run_id=run_id,
    )
    await ws_send_message_end(
        websocket,
        agent_role=agent_role,
        stream_id=summary_stream_id,
        message_id=summary_message.id,
        status="completed",
        final_content=summary_message.content,
        run_id=run_id,
    )
    return True


async def _respond_pings(websocket: WebSocket) -> None:
    try:
        msg = await asyncio.wait_for(websocket.receive_json(), timeout=0)
        if isinstance(msg, dict) and msg.get("type") == "ping":
            await websocket.send_json({"type": "pong"})
    except asyncio.TimeoutError:
        pass
    except WebSocketDisconnect:
        raise


def _normalize_mentions(payload: dict[str, Any]) -> list[dict[str, str]]:
    mentions = payload.get("mentions")
    if not isinstance(mentions, list):
        return []

    normalized: list[dict[str, str]] = []
    seen_agent_ids: set[str] = set()
    for item in mentions:
        if not isinstance(item, dict):
            continue
        agent_id = item.get("agent_id") or item.get("agentId")
        agent_name = item.get("agent_name") or item.get("agentName") or ""
        if not isinstance(agent_id, str) or not agent_id:
            continue
        if not isinstance(agent_name, str):
            agent_name = ""
        if agent_id in seen_agent_ids:
            continue
        seen_agent_ids.add(agent_id)
        normalized.append({"agent_id": agent_id, "agent_name": agent_name})
    return normalized


def valid_send_message(payload: object, session_id: str) -> bool:
    if not isinstance(payload, dict):
        return False

    content = payload.get("content")
    if not isinstance(content, str) or len(content) == 0:
        return False

    if payload.get("type") == "send_message":
        return True

    if payload.get("action") != "send_message" or payload.get("session_id") != session_id:
        return False

    target_agent_ids = payload.get("target_agent_ids")
    if target_agent_ids is not None:
        if not isinstance(target_agent_ids, list):
            return False
        if not all(isinstance(aid, str) for aid in target_agent_ids):
            return False

    mentions = payload.get("mentions")
    if mentions is not None:
        if not isinstance(mentions, list):
            return False
        for item in mentions:
            if not isinstance(item, dict):
                return False
            agent_id = item.get("agent_id") if "agent_id" in item else item.get("agentId")
            agent_name = item.get("agent_name") if "agent_name" in item else item.get("agentName")
            if not isinstance(agent_id, str) or len(agent_id) == 0:
                return False
            if agent_name is not None and not isinstance(agent_name, str):
                return False

    return True


def validate_target_agents_in_session(
    db,
    session_id: str,
    target_agent_ids: list[str],
) -> bool:
    """Check that all target_agent_ids are valid agent members of the session."""
    if not target_agent_ids:
        return True
    members = db.query(SessionMember).filter(
        SessionMember.session_id == session_id,
        SessionMember.member_type == "agent",
        SessionMember.member_id.in_(target_agent_ids),
    ).all()
    found_ids = {m.member_id for m in members}
    return all(aid in found_ids for aid in target_agent_ids)


def set_session_member_status(
    db,
    session_id: str,
    agent_id: str,
    status: str,
) -> dict | None:
    """Update a session member's health_status field and return the changed member."""
    member = db.query(SessionMember).filter(
        SessionMember.session_id == session_id,
        SessionMember.member_id == agent_id,
        SessionMember.member_type == "agent",
    ).first()
    if member is None:
        return None
    if member.health_status == status:
        return None
    member.health_status = status
    db.add(member)
    db.commit()
    return {
        "member_id": member.id,
        "agent_id": member.member_id,
        "status": status,
    }


def sync_session_member_statuses_for_run(db, run) -> list[dict]:
    """Update member statuses based on task states in a run.

    - running tasks -> busy
    - terminal tasks -> online
    """
    if not run or not run.tasks:
        return []
    session_id = run.session_id
    running_agents: set[str] = set()
    terminal_states = {"completed", "failed", "rejected", "cancelled"}
    changed_members: list[dict] = []
    for task in run.tasks:
        if task.status == "running":
            running_agents.add(task.assigned_agent_id)
        elif task.status in terminal_states:
            changed = set_session_member_status(db, session_id, task.assigned_agent_id, "online")
            if changed is not None:
                changed_members.append(changed)
    for agent_id in running_agents:
        changed = set_session_member_status(db, session_id, agent_id, "busy")
        if changed is not None:
            changed_members.append(changed)
    return changed_members


async def _sync_and_broadcast_session_member_statuses(db, websocket: WebSocket, run) -> None:
    changed_members = sync_session_member_statuses_for_run(db, run)
    for member in changed_members:
        await ws_send_session_member_status(
            websocket,
            session_id=run.session_id,
            member_id=member["member_id"],
            agent_id=member["agent_id"],
            status=member["status"],
        )


def _is_orchestration_request(content: str) -> bool:
    text = content.lower()
    return any(keyword in text for keyword in (
        "创建", "create", "新增", "添加", "生成", "拆分", "任务",
        "文件", "file", "写入", "write", "保存", "save", "修改",
    ))


def _should_use_orchestration(
    session_mode: str,
    content: str,
    target_agent_ids: list[str],
    mentions: list[dict[str, str]],
) -> bool:
    if session_mode != "group":
        return False
    if target_agent_ids or mentions:
        return True
    return _is_orchestration_request(content)


def _get_session_agent_members(db, session_id: str) -> list[dict]:
    """获取session中的agent成员列表

    Args:
        db: 数据库会话
        session_id: session ID

    Returns:
        agent信息字典列表
    """
    members = db.query(SessionMember).filter(
        SessionMember.session_id == session_id,
        SessionMember.member_type == "agent",
    ).all()

    result = []
    for member in members:
        agent = db.get(Agent, member.member_id)
        if agent and agent.is_active:
            result.append({
                "id": agent.id,
                "name": agent.name,
                "role": agent.role,
                "capability_tags": agent.capability_tags or [],
                "is_primary": member.is_primary,
            })
    return result


def _get_run_metadata(run: OrchestrationRun) -> dict:
    metadata = getattr(run, "run_metadata", None)
    return metadata if isinstance(metadata, dict) else {}


def _resolve_host_display_name(agent: Agent | None) -> str:
    if agent is None:
        return "Agent"
    return getattr(agent, "name", None) or getattr(agent, "role", None) or getattr(agent, "id", None) or "Agent"


def _build_plan_payload(run: OrchestrationRun) -> dict:
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
                "client_task_id": getattr(task, 'client_task_id', None),
                "assignment_reason": getattr(task, 'assignment_reason', None),
                "depends_on": getattr(task, 'depends_on', []) or [],
            }
            for task in run.tasks
        ],
    }


def _build_plan_summary(run: OrchestrationRun) -> str:
    tasks = sorted(run.tasks, key=lambda task: task.sequence)
    lines: list[str] = ["收到，我来主持这次协作。"]

    run_metadata = _get_run_metadata(run)
    mentioned_agents = [
        item.get("agent_name") or item.get("agent_id")
        for item in (run_metadata.get("mentioned_agents") or [])
        if isinstance(item, dict) and (item.get("agent_name") or item.get("agent_id"))
    ]
    if mentioned_agents:
        lines.append(f"你点名了 {'、'.join(mentioned_agents)}，我会在这些候选执行者中安排任务。")

    task_count = len(tasks)
    if task_count == 1:
        task = tasks[0]
        lines.append(
            f"这次我只负责主持，具体执行交给 [{task.assigned_agent_id}] {task.title}。"
        )
        lines.append("它开始执行后，我会在完成后回来给你收尾汇总。")
        return "\n".join(lines)

    lines.append(f"我已经把你的请求拆成 {task_count} 个子任务，并分配给对应执行 Agent：")

    planning_source = getattr(run, 'planning_source', 'fallback_splitter')
    if planning_source == 'fallback_splitter':
        lines.append("(当前使用自动规则拆分)")

    for task in tasks:
        lines.append(f"  {task.sequence}. [{task.assigned_agent_id}] {task.title}")

    lines.append("接下来我继续主持推进，执行完成后我会统一回来收尾。")
    return "\n".join(lines)


def _build_plan_summary_from_planner(run: OrchestrationRun, tasks: list, planning_mode: str) -> str:
    """从planner输出构建计划摘要"""
    lines: list[str] = ["收到，我来主持这次协作。"]

    run_metadata = _get_run_metadata(run)
    mentioned_agents = [
        item.get("agent_name") or item.get("agent_id")
        for item in (run_metadata.get("mentioned_agents") or [])
        if isinstance(item, dict) and (item.get("agent_name") or item.get("agent_id"))
    ]
    if mentioned_agents:
        lines.append(f"你点名了 {'、'.join(mentioned_agents)}，我会从这些候选执行者中选择最合适的一位来执行。")

    lines.append(f"我已拆解出 {len(tasks)} 个任务。")

    mode_text = {
        "parallel": "如果任务彼此独立，我会并行安排。",
        "sequential": "这些任务需要按顺序推进。",
        "mixed": "这些任务包含并行和串行部分，我会协调执行顺序。",
    }
    selected_mode_text = mode_text.get(planning_mode)
    if selected_mode_text:
        lines.append(selected_mode_text)

    lines.append("\n任务分配如下：")
    for idx, task in enumerate(tasks):
        depends_text = ""
        if hasattr(task, 'depends_on') and task.depends_on:
            depends_text = f" (等待: {', '.join(task.depends_on)})"
        lines.append(f"{idx + 1}. [{task.assigned_agent_id}] {task.title}{depends_text}")
        if hasattr(task, 'reason') and task.reason:
            lines.append(f"   分配原因: {task.reason}")

    lines.append("我只负责主持和收尾，具体执行交给上面的 Agent；完成后我会回来统一汇总。")
    return "\n".join(lines)


def _is_workspace_listing_request(content: str) -> bool:
    text = content.lower()
    return any(
        keyword in text
        for keyword in (
            "当前项目有什么文件",
            "当前工作区有什么文件",
            "项目里有什么文件",
            "工作区有什么文件",
            "有什么文件",
            "what files",
            "list files",
            "show files",
        )
    )


def _build_workspace_listing_reply(db, session: ChatSession) -> str | None:
    if not session.workspace_id:
        return None
    try:
        workspace = WorkspaceService(db).get_workspace(session.workspace_id)
    except Exception:
        return None

    root = Path(workspace.root_path)
    if not root.exists() or not root.is_dir():
        return None

    files: list[str] = []
    for path in sorted(root.rglob("*")):
        if ".git" in path.parts:
            continue
        if path.is_file():
            try:
                rel = path.relative_to(root)
            except ValueError:
                rel = path
            files.append(str(rel).replace("\\", "/"))
        if len(files) >= 60:
            break

    if not files:
        return f"当前工作区 `{root}` 下没有可见文件。"

    preview = "\n".join(f"- {name}" for name in files)
    suffix = "\n- ..." if len(files) >= 60 else ""
    return f"当前工作区 `{root}` 下的文件示例如下：\n{preview}{suffix}"


def _create_plan_message(session_id: str, planner_name: str, run: OrchestrationRun) -> Message:
    summary = run.summary or "已生成任务计划"
    return Message(
        session_id=session_id,
        sender_type="agent",
        sender_role=planner_name,
        content=summary,
        type="text",
        status="completed",
        payload=_build_plan_payload(run),
        metadata={
            "run_id": run.id,
            "is_orchestration_plan": True,
            "is_host_message": True,
            "mentioned_agents": _get_run_metadata(run).get("mentioned_agents", []),
        },
    )


def _build_host_message_prompt(run: OrchestrationRun) -> str:
    """构建群聊主agent的主持消息prompt"""
    tasks = sorted(run.tasks, key=lambda t: t.sequence)
    task_lines = []
    for task in tasks:
        task_lines.append(f"- [{task.assigned_agent_id}] {task.title}")

    run_metadata = _get_run_metadata(run)
    mentioned_agents = [
        item.get("agent_name") or item.get("agent_id")
        for item in (run_metadata.get("mentioned_agents") or [])
        if isinstance(item, dict) and (item.get("agent_name") or item.get("agent_id"))
    ]
    mentioned_note = f"\n用户点名候选 Agent：{'、'.join(mentioned_agents)}\n" if mentioned_agents else "\n"

    planning_source = getattr(run, 'planning_source', 'fallback_splitter')
    source_note = "(使用自动规则拆分)" if planning_source == 'fallback_splitter' else ""

    prompt = f"""你是群聊中的主Agent，负责主持任务进度并向用户汇总结果。

当前已拆解出 {len(tasks)} 个任务 {source_note}{mentioned_note}
任务分配如下：
{chr(10).join(task_lines)}

请用自然语言向用户汇报计划，必须满足以下要求：
1. 明确说明“我主持、执行 Agent 执行、我最后收尾汇总”
2. 如果用户点名了候选 Agent，要明确说明会从这些候选中安排执行
3. 不要把主 Agent 描述成亲自执行者
4. 不要使用代码块或特殊格式，直接输出纯文本消息。"""
    return prompt


async def _send_planner_host_message(
    db,
    session_id: str,
    planner_agent: Agent,
    run: OrchestrationRun,
) -> None:
    """通过群聊主agent的LLM生成并发送计划摘要消息

    使用主agent的provider调用LLM，生成人性化的计划摘要消息，
    然后作为该agent的消息发送到会话中。
    """
    from loguru import logger

    try:
        prompt = _build_host_message_prompt(run)

        provider = get_provider_for_agent(planner_agent)
        llm_adapter = LLMAdapter(provider=provider)
        model = getattr(provider, "_model", "") or "qwen-plus"

        from app.runtime.memory import Message as RuntimeMessage
        messages = [RuntimeMessage(role="user", content=prompt)]

        response = await llm_adapter.async_generate_with_history(
            messages_history=messages,
            model=model,
            temperature=0.7,
        )

        if response is None or not response.response:
            logger.warning("群聊主agent LLM调用返回空，使用默认消息")
            host_content = _build_plan_summary(run)
        else:
            host_content = response.response.strip()

        host_name = _resolve_host_display_name(planner_agent)

        message = Message(
            session_id=session_id,
            sender_type="agent",
            sender_role=host_name,
            content=host_content,
            type="text",
            status="completed",
            payload=_build_plan_payload(run),
            metadata={
                "run_id": run.id,
                "is_orchestration_plan": True,
                "is_host_message": True,
                "agent_id": planner_agent.id,
                "mentioned_agents": _get_run_metadata(run).get("mentioned_agents", []),
            },
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        _GROUP_CHAT_AUDIT.record_plan_published(
            session_id=session_id,
            run_id=run.id,
            planner_agent_id=planner_agent.id,
            planner_role=host_name,
            plan_message_id=message.id,
            summary=host_content,
        )

        logger.info(
            "群聊主agent生成计划摘要消息: agent={}, message_id={}",
            planner_agent.id,
            message.id,
        )

    except Exception as exc:
        logger.error("生成群聊主agent计划摘要消息失败: {}", str(exc))
        plan_message = _create_plan_message(
            session_id,
            _resolve_host_display_name(planner_agent),
            run,
        )
        plan_message.content = _build_plan_summary(run)
        db.add(plan_message)
        db.commit()


async def _create_orchestration_plan(
    db,
    session: ChatSession,
    planner_agent: Agent,
    content: str,
    human_message: Message,
    allowed_agent_ids: list[str] | None = None,
) -> OrchestrationRun | None:
    """创建编排计划 - 集成planner版本

    优先使用planner语义规划，失败时fallback到规则拆分。
    """
    candidate_agents = _get_session_agent_members(db, session.id)
    member_ids = [a["id"] for a in candidate_agents if a["id"] != planner_agent.id]
    if not member_ids:
        member_ids = [planner_agent.id]

    run = await _create_orchestration_plan_with_planner(
        db=db,
        session=session,
        planner_agent=planner_agent,
        content=content,
        human_message=human_message,
        candidate_agents=candidate_agents,
        member_ids=member_ids,
    )

    if run is not None:
        return _restrict_run_tasks_to_allowed_agents(db, run.id, allowed_agent_ids)

    _GROUP_CHAT_AUDIT.record_fallback_decision(
        session_id=session.id,
        run_id=None,
        planner_agent_id=planner_agent.id,
        reason="planner_returned_none",
        details={
            "candidate_agents_count": len(candidate_agents),
            "available_agent_ids": member_ids,
            "user_request_preview": content[:100] if len(content) > 100 else content,
        },
    )

    run = _create_orchestration_plan_with_fallback(
        db=db,
        session=session,
        planner_agent=planner_agent,
        content=content,
        human_message=human_message,
        member_ids=member_ids,
    )
    if run is None:
        return None
    return _restrict_run_tasks_to_allowed_agents(db, run.id, allowed_agent_ids)


async def _run_orchestration_in_background(
    db,
    websocket,
    session_id: str,
    session,
    selected_agent,
    content: str,
    human_message,
    allowed_agent_ids: list[str] | None,
    stream_id: str,
    agent_name: str,
    thinking_msg_id: str,
) -> None:
    """Run full orchestration flow in background, sending WS events as it progresses.

    Sends runtime_state(thinking) BEFORE starting plan generation so the user
    immediately sees feedback. Then runs plan -> tasks -> summary in the
    background and sends corresponding events as they complete.
    """
    try:
        run = await _create_orchestration_plan(
            db,
            session,
            selected_agent,
            content,
            human_message,
            allowed_agent_ids=allowed_agent_ids,
        )
        if run is None:
            return

        plan_message = (
            db.query(Message)
            .filter(
                Message.session_id == session_id,
                Message.sender_type == "agent",
                Message.msg_metadata["run_id"].as_string() == run.id,
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .first()
        )
        if plan_message is not None:
            _GROUP_CHAT_AUDIT.record_plan_published(
                session_id=session_id,
                run_id=run.id,
                planner_agent_id=selected_agent.id,
                planner_role=agent_name,
                plan_message_id=plan_message.id,
                summary=plan_message.content,
            )
            await ws_send_message_start(
                websocket,
                agent_role=agent_name,
                stream_id=stream_id,
                message=plan_message,
                run_id=run.id,
            )
            await ws_send_message_end(
                websocket,
                agent_role=agent_name,
                stream_id=stream_id,
                message_id=plan_message.id,
                status="completed",
                final_content=plan_message.content,
            )

        await _execute_orchestration_tasks(db, websocket, session_id, run)
        refreshed_run = OrchestrationService(db).get_run(run.id)
        if refreshed_run is not None:
            finalized_run = OrchestrationExecutor(db).finalize_run(refreshed_run.id)
            if finalized_run is not None and finalized_run.status in {
                "completed",
                "partial",
                "cancelled",
                "failed",
            }:
                await _send_orchestration_summary_message(
                    websocket=websocket,
                    db=db,
                    session_id=session_id,
                    run_id=finalized_run.id,
                    agent_role=agent_name,
                )
                await ws_send_run_finished(
                    websocket,
                    run_id=finalized_run.id,
                    session_id=session_id,
                    status=finalized_run.status,
                    summary=finalized_run.summary,
                )
    except Exception as exc:
        import traceback

        traceback.print_exc()
        try:
            await _safe_send_json(websocket, {
                "type": "error",
                "stream_id": stream_id,
                "message_id": thinking_msg_id,
                "error_code": "orchestration_error",
                "error_message": str(exc),
            })
        except Exception:
            pass


def _restrict_run_tasks_to_allowed_agents(
    db,
    run_id: str,
    allowed_agent_ids: list[str] | None,
) -> OrchestrationRun:
    """Persist the allowed-agent constraint onto the stored task set."""
    service = OrchestrationService(db)
    if not allowed_agent_ids:
        run = service.get_run(run_id)
        if run is None:
            raise RuntimeError("Failed to load orchestration run after creation")
        return run

    allowed_agent_id_set = set(allowed_agent_ids)
    db.query(OrchestrationTask).filter(
        OrchestrationTask.run_id == run_id,
        OrchestrationTask.assigned_agent_id.notin_(allowed_agent_id_set),
    ).delete(synchronize_session=False)
    db.commit()

    run = service.get_run(run_id)
    if run is None:
        raise RuntimeError("Failed to load orchestration run after restricting tasks")
    if not run.tasks:
        raise ValueError("No valid target agents available for this session")
    return run


async def _create_orchestration_plan_with_planner(
    db,
    session: ChatSession,
    planner_agent: Agent,
    content: str,
    human_message: Message,
    candidate_agents: list[dict],
    member_ids: list[str],
) -> OrchestrationRun | None:
    """使用Planner创建编排计划"""
    # 构建planner prompt
    primary_agent_info = {
        "id": planner_agent.id,
        "name": planner_agent.name,
        "role": planner_agent.role,
        "capability_tags": planner_agent.capability_tags or [],
    }

    prompt = build_planner_prompt(
        user_request=content,
        session_mode=session.mode or "group",
        primary_agent=primary_agent_info,
        candidate_agents=candidate_agents,
    )

    # 调用planner (使用主agent的LLM)
    raw_output = await _call_planner_llm(prompt, planner_agent, db, session_id=session.id)

    if raw_output is None:
        _GROUP_CHAT_AUDIT.record_fallback_decision(
            session_id=session.id,
            run_id=None,
            planner_agent_id=planner_agent.id,
            reason="planner_llm_failed",
            details={"prompt_length": len(prompt)},
        )
        return None

    # 解析输出
    parsed_plan = parse_planner_output(raw_output)
    if parsed_plan is None:
        _GROUP_CHAT_AUDIT.record_fallback_decision(
            session_id=session.id,
            run_id=None,
            planner_agent_id=planner_agent.id,
            reason="planner_parse_failed",
            details={"raw_output_preview": raw_output[:200] if len(raw_output) > 200 else raw_output},
        )
        return None

    # 校验
    valid_agent_ids = [a["id"] for a in candidate_agents]
    validator_result = validate_plan(parsed_plan, valid_agent_ids)

    if validator_result.status not in [ValidationStatus.VALID, ValidationStatus.REPAIRED]:
        _GROUP_CHAT_AUDIT.record_fallback_decision(
            session_id=session.id,
            run_id=None,
            planner_agent_id=planner_agent.id,
            reason="planner_validation_failed",
            details={
                "validation_status": validator_result.status,
                "errors": validator_result.errors[:3] if validator_result.errors else [],
            },
        )
        return None

    # 创建run和tasks
    plan = validator_result.normalized_plan or parsed_plan
    service = OrchestrationService(db)

    planning_source = (
        PlanningSource.PLANNER_REPAIRED.value
        if validator_result.status == ValidationStatus.REPAIRED
        else PlanningSource.PLANNER.value
    )

    run = service.create_run(
        session_id=session.id,
        trigger_message_id=human_message.id,
        planner_agent_id=planner_agent.id,
        summary=f"已拆解出 {len(plan.tasks)} 个任务",
        status="planned",
        planning_source=planning_source,
        metadata={
            "mentioned_agents": (human_message.msg_metadata or {}).get("mentioned_agents", []),
            "target_agent_ids": (human_message.msg_metadata or {}).get("target_agent_ids", []),
        },
    )

    # 创建tasks
    tasks_to_create = []
    for idx, planner_task in enumerate(plan.tasks):
        tasks_to_create.append({
            "sequence": idx + 1,
            "assigned_agent_id": planner_task.assigned_agent_id,
            "kind": "file_write",
            "title": planner_task.title,
            "goal": planner_task.goal,
            "input_payload": planner_task.input_payload,
            "status": "planned",
            "client_task_id": planner_task.client_task_id,
            "assignment_reason": planner_task.reason,
            "depends_on": planner_task.depends_on,
        })

    service.create_tasks(run.id, tasks_to_create)
    db.commit()

    run_with_tasks = service.get_run(run.id)
    if run_with_tasks is None:
        raise RuntimeError("Failed to load orchestration run after creation")

    # 创建计划消息
    plan_message = _create_plan_message(
        session.id,
        _resolve_host_display_name(planner_agent),
        run_with_tasks
    )
    plan_message.content = _build_plan_summary_from_planner(
        run_with_tasks,
        plan.tasks,
        plan.planning_mode.value,
    )
    db.add(plan_message)
    db.commit()

    # 审计记录
    final_run = service.get_run(run.id)
    if final_run is not None:
        _GROUP_CHAT_AUDIT.record_run_created(
            session_id=session.id,
            run_id=final_run.id,
            trigger_message_id=human_message.id,
            planner_agent_id=planner_agent.id,
            planner_role=_resolve_host_display_name(planner_agent),
            summary=final_run.summary,
            tasks=[
                {
                    "task_id": task.id,
                    "sequence": task.sequence,
                    "title": task.title,
                    "goal": task.goal,
                    "agent_id": task.assigned_agent_id,
                    "kind": task.kind,
                    "input_payload": task.input_payload,
                    "status": task.status,
                    "planning_source": planning_source,
                }
                for task in final_run.tasks
            ],
        )

    return final_run


async def _call_planner_llm(prompt: str, agent: Agent, db, session_id: str | None = None) -> str | None:
    """调用主agent的LLM获取planner输出

    使用agent配置的Provider进行LLM调用，返回结构化的JSON输出。

    Args:
        prompt: 构建好的planner prompt
        agent: 主agent实例，包含provider和model配置
        db: 数据库会话
        session_id: 可选的session_id，用于审计记录

    Returns:
        LLM输出的原始文本，失败返回None
    """
    from loguru import logger

    try:
        # 获取agent的provider
        provider = get_provider_for_agent(agent)
        llm_adapter = LLMAdapter(provider=provider)

        # 获取模型名称
        model = getattr(provider, "_model", "") or "qwen-plus"

        logger.info(
            "调用主agent LLM进行语义规划: agent={}, model={}",
            getattr(agent, "id", "unknown"),
            model,
        )

        # 构建消息历史
        from app.runtime.memory import Message as RuntimeMessage

        messages = [RuntimeMessage(role="user", content=prompt)]

        # 调用LLM，使用较低温度以获得更稳定的JSON输出
        response = await llm_adapter.async_generate_with_history(
            messages_history=messages,
            model=model,
            temperature=0.3,
        )

        if response is None or not response.response:
            logger.warning("Planner LLM调用返回空响应")
            return None

        raw_output = response.response.strip()
        logger.debug(
            "Planner LLM输出长度: {} chars",
            len(raw_output),
        )

        # 记录到审计日志
        if session_id:
            _GROUP_CHAT_AUDIT.record(
                event_type="planner_llm_call",
                session_id=session_id,
                model=model,
                agent_id=getattr(agent, "id", "unknown"),
                prompt_length=len(prompt),
                response_length=len(raw_output),
                planning_source="planner_llm",
            )

        return raw_output

    except Exception as exc:
        logger.error(
            "Planner LLM调用失败: {}",
            str(exc),
        )
        return None


def _create_orchestration_plan_with_fallback(
    db,
    session: ChatSession,
    planner_agent: Agent,
    content: str,
    human_message: Message,
    member_ids: list[str],
) -> OrchestrationRun | None:
    """使用fallback规则拆分创建编排计划"""
    planned_tasks = plan_tasks_from_message(content, member_ids)
    if not planned_tasks:
        return None

    service = OrchestrationService(db)
    run = service.create_run(
        session_id=session.id,
        trigger_message_id=human_message.id,
        planner_agent_id=planner_agent.id,
        summary=f"已拆解出 {len(planned_tasks)} 个任务 (fallback)",
        status="planned",
        planning_source=PlanningSource.FALLBACK_SPLITTER.value,
        metadata={
            "mentioned_agents": (human_message.msg_metadata or {}).get("mentioned_agents", []),
            "target_agent_ids": (human_message.msg_metadata or {}).get("target_agent_ids", []),
        },
    )

    service.create_tasks(
        run.id,
        [
            {
                "sequence": index + 1,
                "assigned_agent_id": task.assigned_agent_id,
                "kind": task.kind,
                "title": task.title,
                "goal": task.goal,
                "input_payload": task.input_payload,
                "status": "planned",
            }
            for index, task in enumerate(planned_tasks)
        ],
    )
    db.commit()

    run_with_tasks = service.get_run(run.id)
    if run_with_tasks is None:
        raise RuntimeError("Failed to load orchestration run after creation")

    # 审计记录 - fallback任务分配
    persisted_tasks = sorted(run_with_tasks.tasks, key=lambda task: task.sequence)

    _GROUP_CHAT_AUDIT.record_fallback_task_allocation(
        session_id=session.id,
        run_id=run.id,
        planner_agent_id=planner_agent.id,
        user_request=content,
        planned_tasks=[
            {
                "task_id": task.id,
                "sequence": task.sequence,
                "title": task.title,
                "assigned_agent_id": task.assigned_agent_id,
                "input_payload": task.input_payload,
            }
            for task in persisted_tasks
        ],
        agent_ids=member_ids,
    )

    # 通过群聊主agent的LLM生成计划摘要消息
    plan_message = _create_plan_message(
        session.id,
        _resolve_host_display_name(planner_agent),
        run_with_tasks,
    )
    plan_message.content = _build_plan_summary(run_with_tasks)
    db.add(plan_message)
    db.commit()

    return run_with_tasks


async def _execute_orchestration_tasks(
    db,
    websocket: WebSocket,
    session_id: str,
    run: OrchestrationRun,
) -> None:
    """
    Execute all planned tasks in an orchestration run with parallel execution.

    Each task gets its own stream_id and runs independently.
    Failures are isolated per task.
    M2: Updates run status to 'running' before starting tasks.
    M6: Sends orchestration_run_started event.
    """
    executor = OrchestrationExecutor(db)
    task_ids = [task.id for task in run.tasks if task.status == "planned"]

    if not task_ids:
        return

    # M2: Update run status to 'running' before starting tasks
    from app.services.orchestration import OrchestrationService
    service = OrchestrationService(db)
    service.update_run_status(run.id, "running")

    # M6: Send orchestration_run_started event
    await ws_send_run_started(
        websocket,
        run_id=run.id,
        session_id=session_id,
        planner_agent_id=run.planner_agent_id,
        task_count=len(task_ids),
    )

    async def _run_single_task(task_id: str) -> None:
        task = executor.get_task(task_id)
        if task is None:
            return

        stream_id = executor._generate_stream_id(task_id)

        try:
            await ws_send_task_start(
                websocket,
                run_id=run.id,
                task_id=task_id,
                agent_id=task.assigned_agent_id,
                stream_id=stream_id,
                title=task.title,
                goal=task.goal,
                kind=task.kind,
            )

            final_result: dict | None = None
            async for event in executor.stream_task_events(task_id, stream_id):
                if event.type == "message_start":
                    await ws_send_message_start(
                        websocket,
                        agent_role=event.agent_role,
                        stream_id=event.stream_id,
                        message=event.message,
                        run_id=event.run_id,
                        task_id=event.task_id,
                        agent_id=event.agent_id,
                    )
                elif event.type == "message_delta":
                    await ws_send_message_delta(
                        websocket,
                        agent_role=event.agent_role,
                        stream_id=event.stream_id,
                        message_id=event.message_id,
                        delta=event.delta,
                        run_id=event.run_id,
                        task_id=event.task_id,
                        agent_id=event.agent_id,
                    )
                elif event.type == "message_end":
                    final_result = {
                        "message_id": event.message_id,
                        "final_content": getattr(event, "final_content", None),
                    }
                    await ws_send_message_end(
                        websocket,
                        agent_role=event.agent_role,
                        stream_id=event.stream_id,
                        message_id=event.message_id,
                        status=event.status,
                        final_content=getattr(event, "final_content", None),
                        run_id=event.run_id,
                        task_id=event.task_id,
                        agent_id=event.agent_id,
                    )
                elif event.type == "message_error":
                    await ws_send_message_error(
                        websocket,
                        agent_role=event.agent_role,
                        stream_id=event.stream_id,
                        message_id=event.message_id,
                        error_code=event.error_code,
                        error_message=event.error_message,
                        run_id=event.run_id,
                        task_id=event.task_id,
                        agent_id=event.agent_id,
                    )
                    await ws_send_task_error(
                        websocket,
                        run_id=event.run_id,
                        task_id=event.task_id,
                        agent_id=event.agent_id,
                        stream_id=event.stream_id,
                        error_code=event.error_code,
                        error_message=event.error_message,
                    )
                elif event.type == "tool_event":
                    await ws_send_tool_event(
                        websocket,
                        tool_name=event.tool_name,
                        arguments=event.arguments,
                        response=event.response,
                        status=event.status,
                        stream_id=event.stream_id,
                        message_id=event.message_id,
                        run_id=event.run_id,
                        task_id=event.task_id,
                        agent_id=event.agent_id,
                    )
                elif event.type == "runtime_state":
                    await ws_send_runtime_state(
                        websocket,
                        stream_id=event.stream_id,
                        message_id=event.message_id,
                        state=event.state,
                        timestamp=event.timestamp,
                        run_id=event.run_id,
                        task_id=event.task_id,
                        agent_id=event.agent_id,
                    )
                elif event.type == "change_preview":
                    await ws_send_change_preview(
                        websocket,
                        stream_id=event.stream_id,
                        message_id=event.message_id,
                        change_id=event.change_id,
                        operation=event.operation,
                        path=event.path,
                        unified_diff=event.unified_diff,
                        status=event.status,
                        timestamp=event.timestamp,
                        run_id=event.run_id,
                        task_id=event.task_id,
                        agent_id=event.agent_id,
                        agent_role=getattr(event, 'agent_role', None),
                    )

            refreshed_task = executor.get_task(task_id)
            task_status = refreshed_task.status if refreshed_task is not None else "completed"
            await ws_send_task_end(
                websocket,
                run_id=run.id,
                task_id=task_id,
                agent_id=task.assigned_agent_id,
                stream_id=stream_id,
                status=task_status,
                result=final_result,
            )

        except Exception as exc:
            await ws_send_task_error(
                websocket,
                run_id=run.id,
                task_id=task_id,
                agent_id=task.assigned_agent_id,
                stream_id=stream_id,
                error_code="task_execution_exception",
                error_message=str(exc),
            )
            await ws_send_task_end(
                websocket,
                run_id=run.id,
                task_id=task_id,
                agent_id=task.assigned_agent_id,
                stream_id=stream_id,
                status="failed",
            )

    await asyncio.gather(*[_run_single_task(task_id) for task_id in task_ids], return_exceptions=False)


async def _handle_streaming_response(
    websocket: WebSocket,
    db,
    session_id: str,
    agent_role: str,
    content: str,
    selected_agent: Agent,
    stream_id: str,
) -> None:
    active_stream_id = stream_id
    active_agent_role = agent_role
    active_message_id: str | None = None
    active_error_code = "unknown"
    use_runtime = runtime_use_runtime_agent() and isinstance(selected_agent, Agent)
    stream_output_enabled = chat_stream_output_enabled() if use_runtime else True

    try:
        if use_runtime:
            from app.runtime.llm_adapter import LLMAdapter
            from app.runtime.runtime_agent_service import RuntimeAgentService, load_session_history
            from app.services.agent_runtime import get_provider_for_agent

            provider = get_provider_for_agent(selected_agent)
            llm_adapter = LLMAdapter(provider=provider)
            session_history = load_session_history(db, session_id)
            event_source = RuntimeAgentService(
                session_id=session_id,
                user_message=content,
                agent_role=agent_role,
                llm_adapter=llm_adapter,
                db=db,
                stream_id=stream_id,
                session_history=session_history,
            ).stream_events()
        else:
            event_source = FixedAgentResponder(
                session_id=session_id,
                user_message=content,
                agent_role=agent_role,
                db=db,
                stream_id=stream_id,
            ).stream_events()
            active_error_code = "fixed_responder_failed"

        async for event in event_source:
            await _respond_pings(websocket)
            if event.type == "message_start":
                active_stream_id = event.stream_id
                active_agent_role = event.agent_role
                active_message_id = event.message.id
                await ws_send_message_start(websocket, agent_role=event.agent_role, stream_id=event.stream_id, message=event.message)
            elif event.type == "message_delta":
                active_stream_id = event.stream_id
                active_agent_role = event.agent_role
                active_message_id = event.message_id
                if stream_output_enabled:
                    await ws_send_message_delta(websocket, agent_role=event.agent_role, stream_id=event.stream_id, message_id=event.message_id, delta=event.delta)
            elif event.type == "message_end":
                active_stream_id = event.stream_id
                active_agent_role = event.agent_role
                active_message_id = event.message_id
                await ws_send_message_end(websocket, agent_role=event.agent_role, stream_id=event.stream_id, message_id=event.message_id, status=event.status, final_content=getattr(event, "final_content", None))
            elif event.type == "message_error":
                active_stream_id = event.stream_id
                active_agent_role = event.agent_role
                active_message_id = event.message_id
                active_error_code = getattr(event, "error_code", active_error_code)
                await ws_send_message_error(websocket, agent_role=event.agent_role, stream_id=event.stream_id, message_id=event.message_id, error_code=event.error_code, error_message=event.error_message)
            elif event.type == "tool_event":
                await ws_send_tool_event(websocket, tool_name=event.tool_name, arguments=event.arguments, response=event.response, status=event.status, stream_id=event.stream_id, message_id=event.message_id)
            elif event.type == "runtime_state":
                await ws_send_runtime_state(websocket, stream_id=event.stream_id, message_id=event.message_id, state=event.state, timestamp=event.timestamp)
            elif event.type == "change_preview":
                await ws_send_change_preview(
                    websocket,
                    stream_id=event.stream_id,
                    message_id=event.message_id,
                    change_id=event.change_id,
                    operation=event.operation,
                    path=event.path,
                    unified_diff=event.unified_diff,
                    status=event.status,
                    timestamp=event.timestamp,
                    agent_role=getattr(event, 'agent_role', None),
                )
            elif event.type == "preview_result":
                await ws_send_preview_result(websocket, preview_id=event.preview_id, workspace_id=event.workspace_id, preview_url=event.preview_url, status=event.status, message_id=event.message_id, stream_id=event.stream_id, timestamp=event.timestamp)
            elif event.type == "repair_state":
                await ws_send_repair_state(websocket, state=event.state, attempt=event.attempt, max_attempts=event.max_attempts, message=event.message, stream_id=event.stream_id, message_id=event.message_id, timestamp=event.timestamp)
            if (
                getattr(websocket, "client_state", None) is WebSocketState.DISCONNECTED
                or getattr(websocket, "application_state", None) is WebSocketState.DISCONNECTED
            ):
                break
    except Exception as exc:
        disconnected = _is_ws_disconnect_error(exc)
        if active_message_id:
            agent_message = db.get(Message, active_message_id)
            if agent_message is not None:
                agent_message.status = "failed"
                db.add(agent_message)
                db.commit()
        if disconnected:
            return
        try:
            await ws_send_message_error(
                websocket,
                agent_role=active_agent_role,
                stream_id=active_stream_id,
                message_id=active_message_id or "",
                error_code=active_error_code,
                error_message=str(exc),
            )
        except Exception:
            pass


@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    db = SessionLocal()
    agent_name = "PM"
    try:
        session = db.get(ChatSession, session_id)
        if session is None:
            await websocket.accept()
            await _send_error(websocket, "session_not_found", "Session not found", stream_id=str(uuid.uuid4()), agent_role=agent_name)
            try:
                await websocket.close(code=4004, reason="Session not found")
            except TypeError:
                await websocket.close(code=4004)
            return

        query_params = getattr(websocket, "query_params", {}) or {}
        token = query_params.get("x-token") if hasattr(query_params, "get") else None
        if not token and hasattr(websocket, "headers"):
            token = websocket.headers.get("x-token")

        if session.mode == "group":
            selected_agent = get_primary_agent_for_group(db, session) or get_default_agent(session.owner_id)
        else:
            selected_agent = get_session_agent(db, session) or _resolve_default_agent_for_single_chat(db, session.owner_id)
        agent_name = getattr(selected_agent, "name", None) or getattr(selected_agent, "role", "PM")

        if token:
            try:
                payload = decode_token(token)
                user_id = str(payload.get("sub"))
            except Exception:
                try:
                    await websocket.close(code=4002, reason="Invalid or expired token")
                except TypeError:
                    await websocket.close(code=4002)
                return
        else:
            user_id = session.owner_id or "dev_user"

        await websocket.accept()

        if session.owner_id != user_id:
            await _send_error(websocket, "forbidden", "Forbidden: session does not belong to current user", stream_id=str(uuid.uuid4()), agent_role=agent_name)
            try:
                await websocket.close(code=4003, reason="Forbidden")
            except TypeError:
                await websocket.close(code=4003)
            return

        _WS_CONNECTION_MANAGER.register(session_id, websocket, user_id)

        while True:
            try:
                payload = await websocket.receive_json()
            except JSONDecodeError:
                await _send_error(websocket, "invalid_request", "Invalid request", stream_id=str(uuid.uuid4()), agent_role=agent_name)
                continue
            except WebSocketDisconnect:
                break

            if isinstance(payload, dict) and payload.get("type") == "ping":
                await _safe_send_json(websocket, {"type": "pong"})
                continue

            if not valid_send_message(payload, session_id):
                await _send_error(websocket, "invalid_request", "Invalid request", stream_id=str(uuid.uuid4()), agent_role=agent_name)
                continue

            stream_id = str(uuid.uuid4())
            if not _IN_FLIGHT_GUARD.try_enter(session_id):
                await _send_error(websocket, "agent_busy", "Agent is busy, please wait", stream_id=stream_id, agent_role=agent_name)
                continue

            db.refresh(session)
            if session.mode == "group":
                selected_agent = get_primary_agent_for_group(db, session) or get_default_agent(session.owner_id)
            else:
                selected_agent = get_session_agent(db, session) or _resolve_default_agent_for_single_chat(db, session.owner_id)
            agent_name = getattr(selected_agent, "name", None) or getattr(selected_agent, "role", "PM")

            content = payload["content"]
            mentions = _normalize_mentions(payload)
            target_agent_ids = [aid for aid in payload.get("target_agent_ids", []) if isinstance(aid, str)]
            if not target_agent_ids and mentions:
                target_agent_ids = [item["agent_id"] for item in mentions if item.get("agent_id")]
            if session.mode == "group" and target_agent_ids:
                if not validate_target_agents_in_session(db, session_id, target_agent_ids):
                    await _send_error(
                        websocket,
                        "invalid_target_agents",
                        "One or more target agents are not members of this session",
                        stream_id=str(uuid.uuid4()),
                        agent_role=agent_name,
                    )
                    continue
            human_message = Message(
                session_id=session_id,
                sender_type="human",
                sender_role=None,
                content=content,
                type="text",
                status="completed",
                payload={"text": content},
                metadata={
                    "mentioned_agents": mentions,
                    "target_agent_ids": target_agent_ids,
                },
            )
            db.add(human_message)
            session.updated_at = utcnow()
            db.add(session)
            db.commit()
            db.refresh(human_message)
            _GROUP_CHAT_AUDIT.record_user_message(
                session_id=session_id,
                message_id=human_message.id,
                content=content,
                mode=session.mode,
            )

            try:
                if _should_use_orchestration(session.mode, content, target_agent_ids, mentions):
                    thinking_msg_id = str(uuid.uuid4())
                    await ws_send_runtime_state(
                        websocket,
                        stream_id=stream_id,
                        message_id=thinking_msg_id,
                        state="thinking",
                        timestamp=utcnow().isoformat(),
                    )
                    asyncio.create_task(
                        _run_orchestration_in_background(
                            db=db,
                            websocket=websocket,
                            session_id=session_id,
                            session=session,
                            selected_agent=selected_agent,
                            content=content,
                            human_message=human_message,
                            allowed_agent_ids=target_agent_ids or None,
                            stream_id=stream_id,
                            agent_name=agent_name,
                            thinking_msg_id=thinking_msg_id,
                        )
                    )
                    continue

                if session.mode == "group" and _is_workspace_listing_request(content):
                    listing_reply = _build_workspace_listing_reply(db, session)
                    if listing_reply is not None:
                        await _send_group_plain_response(
                            websocket=websocket,
                            db=db,
                            session_id=session_id,
                            agent_role=agent_name,
                            stream_id=stream_id,
                            final_content=listing_reply,
                            source="group_workspace_listing",
                        )
                        continue

                await _handle_streaming_response(
                    websocket=websocket,
                    db=db,
                    session_id=session_id,
                    agent_role=agent_name,
                    content=content,
                    selected_agent=selected_agent,
                    stream_id=stream_id,
                )
            finally:
                _IN_FLIGHT_GUARD.leave(session_id)
    finally:
        _WS_CONNECTION_MANAGER.unregister(session_id)
        db.close()


session_websocket = websocket_endpoint
