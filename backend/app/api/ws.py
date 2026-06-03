# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import os
import uuid
from json import JSONDecodeError
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings, load_env_file
from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.agent import Agent
from app.models.message import Message
from app.models.orchestration import OrchestrationRun
from app.models.session import ChatSession, utcnow
from app.models.session_member import SessionMember
from app.observability.group_chat_audit import get_group_chat_audit_recorder
from app.schemas.common import to_iso_z
from app.api.agents import resolve_default_agent
from app.services.fixed_agent_responder import FixedAgentResponder
from app.services.orchestration import OrchestrationService
from app.services.orchestration_executor import OrchestrationExecutor
from app.services.task_splitter import plan_tasks_from_message
from app.services.workspace import WorkspaceService

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
        await websocket.send_json(payload)
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


def get_primary_agent_for_group(db, session: ChatSession) -> Agent | None:
    if session.mode != "group":
        return None
    primary_member = db.query(SessionMember).filter(
        SessionMember.session_id == session.id,
        SessionMember.is_primary == True,
    ).first()
    if primary_member is None:
        return None
    return db.get(Agent, primary_member.member_id)


class _InFlightGuard:
    def __init__(self) -> None:
        self._sessions: set[str] = set()

    def is_in_flight(self, session_id: str) -> bool:
        return session_id in self._sessions

    def try_enter(self, session_id: str) -> bool:
        if session_id in self._sessions:
            return False
        self._sessions.add(session_id)
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
    await websocket.send_json({
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
    await websocket.send_json(payload)


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
    await websocket.send_json(payload)


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
    await websocket.send_json(payload)


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
    await websocket.send_json(payload)


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
    await websocket.send_json(payload)


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
    await websocket.send_json(payload)


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
    await websocket.send_json(payload)


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
    await websocket.send_json({
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
    await websocket.send_json({
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
    await websocket.send_json({
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
    await websocket.send_json(payload)


async def ws_send_task_error(
    websocket: WebSocket,
    run_id: str,
    task_id: str,
    agent_id: str,
    stream_id: str,
    error_code: str,
    error_message: str,
) -> None:
    await websocket.send_json({
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
    await websocket.send_json({
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
    await websocket.send_json(payload)


async def ws_send_run_updated(
    websocket: WebSocket,
    run_id: str,
    session_id: str,
    status: str,
) -> None:
    """Send orchestration_run_updated event.

    M6: For intermediate run status changes (e.g., planned -> running).
    """
    await websocket.send_json({
        "type": "orchestration_run_updated",
        "run_id": run_id,
        "session_id": session_id,
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
        metadata={"source": source, "stream_id": stream_id, "group_chat_direct": True},
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


async def _respond_pings(websocket: WebSocket) -> None:
    try:
        msg = await asyncio.wait_for(websocket.receive_json(), timeout=0)
        if isinstance(msg, dict) and msg.get("type") == "ping":
            await websocket.send_json({"type": "pong"})
    except asyncio.TimeoutError:
        pass
    except WebSocketDisconnect:
        raise


def valid_send_message(payload: object, session_id: str) -> bool:
    if not isinstance(payload, dict):
        return False

    content = payload.get("content")
    if not isinstance(content, str) or len(content) == 0:
        return False

    if payload.get("type") == "send_message":
        return True

    return payload.get("action") == "send_message" and payload.get("session_id") == session_id


def _is_orchestration_request(content: str) -> bool:
    text = content.lower()
    return any(keyword in text for keyword in ("创建", "create", "新增", "添加", "生成", "拆分", "任务"))


def _build_plan_payload(run: OrchestrationRun) -> dict:
    return {
        "run_id": run.id,
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
            }
            for task in run.tasks
        ],
    }


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


def _create_plan_message(session_id: str, planner_role: str, run: OrchestrationRun) -> Message:
    summary = run.summary or "已生成任务计划"
    return Message(
        session_id=session_id,
        sender_type="agent",
        sender_role=planner_role,
        content=summary,
        type="text",
        status="completed",
        payload=_build_plan_payload(run),
        metadata={"run_id": run.id, "is_orchestration_plan": True},
    )


async def _create_orchestration_plan(
    db,
    session: ChatSession,
    planner_agent: Agent,
    content: str,
    human_message: Message,
) -> OrchestrationRun | None:
    member_ids = [
        member.member_id
        for member in db.query(SessionMember).filter(SessionMember.session_id == session.id).all()
        if member.member_type == "agent" and member.member_id != planner_agent.id
    ]
    if not member_ids:
        member_ids = [planner_agent.id]
    planned_tasks = plan_tasks_from_message(content, member_ids)
    if not planned_tasks:
        return None

    service = OrchestrationService(db)
    run = service.create_run(
        session_id=session.id,
        trigger_message_id=human_message.id,
        planner_agent_id=planner_agent.id,
        summary=f"已拆解出 {len(planned_tasks)} 个任务",
        status="planned",
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
    run_with_tasks = service.get_run(run.id)
    if run_with_tasks is None:
        raise RuntimeError("Failed to load orchestration run after creation")
    db.add(_create_plan_message(session.id, getattr(planner_agent, "role", "PM"), run_with_tasks))
    db.commit()
    final_run = service.get_run(run.id)
    if final_run is not None:
        _GROUP_CHAT_AUDIT.record_run_created(
            session_id=session.id,
            run_id=final_run.id,
            trigger_message_id=human_message.id,
            planner_agent_id=planner_agent.id,
            planner_role=getattr(planner_agent, "role", "PM"),
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
                }
                for task in final_run.tasks
            ],
        )
    return final_run


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
                    final_result = {"message_id": event.message_id, "final_content": getattr(event, "final_content", None)}
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
    except Exception as exc:
        if active_message_id:
            agent_message = db.get(Message, active_message_id)
            if agent_message is not None:
                agent_message.status = "failed"
                db.add(agent_message)
                db.commit()
        await ws_send_message_error(
            websocket,
            agent_role=active_agent_role,
            stream_id=active_stream_id,
            message_id=active_message_id or "",
            error_code=active_error_code,
            error_message=str(exc),
        )


@router.websocket("/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    db = SessionLocal()
    agent_role = "PM"
    try:
        session = db.get(ChatSession, session_id)
        if session is None:
            await websocket.accept()
            await _send_error(websocket, "session_not_found", "Session not found", stream_id=str(uuid.uuid4()), agent_role=agent_role)
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
            selected_agent = get_session_agent(db, session) or get_default_agent(session.owner_id)
        agent_role = getattr(selected_agent, "role", "PM")

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
            await _send_error(websocket, "forbidden", "Forbidden: session does not belong to current user", stream_id=str(uuid.uuid4()), agent_role=agent_role)
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
                await _send_error(websocket, "invalid_request", "Invalid request", stream_id=str(uuid.uuid4()), agent_role=agent_role)
                continue
            except WebSocketDisconnect:
                break

            if isinstance(payload, dict) and payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if not valid_send_message(payload, session_id):
                await _send_error(websocket, "invalid_request", "Invalid request", stream_id=str(uuid.uuid4()), agent_role=agent_role)
                continue

            stream_id = str(uuid.uuid4())
            if not _IN_FLIGHT_GUARD.try_enter(session_id):
                await _send_error(websocket, "agent_busy", "Agent is busy, please wait", stream_id=stream_id, agent_role=agent_role)
                continue

            content = payload["content"]
            human_message = Message(
                session_id=session_id,
                sender_type="human",
                sender_role=None,
                content=content,
                type="text",
                status="completed",
                payload={"text": content},
                metadata={},
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
                if session.mode == "group" and _is_orchestration_request(content):
                    run = await _create_orchestration_plan(db, session, selected_agent, content, human_message)
                    if run is not None:
                        plan_message = (
                            db.query(Message)
                            .filter(
                                Message.session_id == session_id,
                                Message.sender_type == "agent",
                                Message.msg_metadata["run_id"].as_string() == run.id,
                            )
                            .order_by(Message.created_at.desc())
                            .first()
                        )
                        if plan_message is not None:
                            _GROUP_CHAT_AUDIT.record_plan_published(
                                session_id=session_id,
                                run_id=run.id,
                                planner_agent_id=selected_agent.id,
                                planner_role=agent_role,
                                plan_message_id=plan_message.id,
                                summary=plan_message.content,
                            )
                            await ws_send_message_start(websocket, agent_role=agent_role, stream_id=stream_id, message=plan_message, run_id=run.id)
                            await ws_send_message_end(websocket, agent_role=agent_role, stream_id=stream_id, message_id=plan_message.id, status="completed", final_content=plan_message.content)

                        # Execute all planned tasks
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
                                await ws_send_run_finished(
                                    websocket,
                                    run_id=finalized_run.id,
                                    session_id=session_id,
                                    status=finalized_run.status,
                                    summary=finalized_run.summary,
                                )
                        continue

                if session.mode == "group" and _is_workspace_listing_request(content):
                    listing_reply = _build_workspace_listing_reply(db, session)
                    if listing_reply is not None:
                        await _send_group_plain_response(
                            websocket=websocket,
                            db=db,
                            session_id=session_id,
                            agent_role=agent_role,
                            stream_id=stream_id,
                            final_content=listing_reply,
                            source="group_workspace_listing",
                        )
                        continue

                await _handle_streaming_response(
                    websocket=websocket,
                    db=db,
                    session_id=session_id,
                    agent_role=agent_role,
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
