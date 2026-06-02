import asyncio
import os
import uuid
from json import JSONDecodeError
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from app.core.config import get_settings, load_env_file
from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.agent import Agent
from app.models.message import Message
from app.models.session import ChatSession, utcnow
from app.models.session_member import SessionMember
from app.schemas.common import to_iso_z
from app.services.fixed_agent_responder import FixedAgentResponder


router = APIRouter(prefix="/ws", tags=["websocket"])


# ---- WebSocket 连接管理器（用于 REST API 推送） ----

class _WsConnectionManager:
    """管理活跃的 WebSocket 连接，支持向特定会话推送事件。

    用于 REST API（如 apply 接口）向 WebSocket 会话推送 apply_result 事件。
    """

    def __init__(self) -> None:
        # session_id -> (websocket, user_id)
        self._connections: dict[str, tuple[WebSocket, str]] = {}

    def register(self, session_id: str, websocket: WebSocket, user_id: str) -> None:
        """注册一个 WebSocket 连接。"""
        self._connections[session_id] = (websocket, user_id)

    def unregister(self, session_id: str) -> None:
        """取消注册一个 WebSocket 连接。"""
        self._connections.pop(session_id, None)

    def get_connection(self, session_id: str) -> Optional[tuple[WebSocket, str]]:
        """获取指定会话的 WebSocket 连接。"""
        return self._connections.get(session_id)

    def is_connected(self, session_id: str) -> bool:
        """检查指定会话是否有活跃连接。"""
        return session_id in self._connections


_WS_CONNECTION_MANAGER = _WsConnectionManager()


def get_ws_connection_manager() -> _WsConnectionManager:
    """获取全局 WebSocket 连接管理器。"""
    return _WS_CONNECTION_MANAGER


async def ws_send_apply_result(
    session_id: str,
    change_id: str,
    success: bool,
    status: str,
    message: str,
) -> bool:
    """向指定会话推送 apply_result 事件。

    Args:
        session_id: 会话 ID
        change_id: 变更 ID
        success: 是否成功
        status: 状态（applied, rejected, failed）
        message: 结果消息

    Returns:
        True 如果推送成功，False 如果会话未连接或推送失败。
    """
    conn = _WS_CONNECTION_MANAGER.get_connection(session_id)
    if conn is None:
        return False

    websocket, _ = conn
    try:
        await websocket.send_json({
            "type": "apply_result",
            "change_id": change_id,
            "success": success,
            "status": status,
            "message": message,
            "timestamp": _utcnow_iso(),
        })
        return True
    except Exception:
        return False


def runtime_use_runtime_agent() -> bool:
    """Read the runtime-switch flag after loading project .env files."""
    load_env_file()
    return os.getenv("RUNTIME_USE_RUNTIME_AGENT", "0") in ("1", "true", "True")


def chat_stream_output_enabled() -> bool:
    """Whether WS should forward incremental message_delta events to clients."""
    return get_settings().chat_stream_output_enabled

def get_default_agent():
    """兼容旧测试与旧调用路径。返回数据库中的默认 Agent 记录。"""
    db = SessionLocal()
    try:
        return db.get(Agent, "pm_agent")
    finally:
        db.close()


def get_session_agent(db, session: ChatSession) -> Agent | None:
    agent_id = getattr(session, "agent_id", None)
    if not agent_id:
        return None
    return db.get(Agent, agent_id)


def get_primary_agent_for_group(db, session: ChatSession) -> Agent | None:
    """P6-5: Resolve the primary agent for a group session.

    Queries session_members for the member with is_primary=True
    and returns the corresponding Agent record.
    """
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


# ---- 工具函数 ----

def _utcnow_iso() -> str:
    return to_iso_z(utcnow())


# ---- Pre-start 错误发送（复用旧 error 类型） ----

async def _send_error(
    websocket: WebSocket,
    code: str,
    message: str,
    stream_id: str | None = None,
    agent_role: str = "PM",
) -> None:
    payload = {
        "type": "error",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id or str(uuid.uuid4()),
        "error_code": code,
        "error_message": message,
    }
    await websocket.send_json(payload)


# ---- 新协议发送函数（P1-3-3） ----

async def ws_send_message_start(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message: Message,
) -> None:
    await websocket.send_json({
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
    })


async def ws_send_message_delta(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message_id: str,
    delta: str,
) -> None:
    await websocket.send_json({
        "type": "message_delta",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "delta": delta,
    })


async def ws_send_message_end(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message_id: str,
    status: str,
    final_content: str | None = None,
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
    await websocket.send_json(payload)


async def ws_send_message_error(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message_id: str,
    error_code: str,
    error_message: str,
) -> None:
    await websocket.send_json({
        "type": "message_error",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "error_code": error_code,
        "error_message": error_message,
    })


# ---- Task A: Runtime 扩展事件发送函数 ----


async def ws_send_tool_event(
    websocket: WebSocket,
    tool_name: str,
    arguments: dict,
    response: str | None,
    status: str,
    stream_id: str,
    message_id: str,
) -> None:
    """Send a structured tool_event notification to the WebSocket client.

    Notifies the frontend when a tool execution starts or finishes,
    enabling runtime process visibility and minimal replay.
    """
    payload = {
        "type": "tool_event",
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "tool_name": tool_name,
        "status": status,  # "started" | "finished"
        "arguments": arguments,
    }
    if response is not None:
        payload["response"] = response
    await websocket.send_json(payload)


async def ws_send_runtime_state(
    websocket: WebSocket,
    stream_id: str,
    message_id: str,
    state: str,
    timestamp: str,
) -> None:
    """Send a runtime_state notification to the WebSocket client.

    Notifies the frontend when the agent moves between execution phases
    (thinking, calling_tool, observing, responding, finished, error).
    """
    await websocket.send_json({
        "type": "runtime_state",
        "stream_id": stream_id,
        "message_id": message_id,
        "state": state,
        "timestamp": timestamp,
    })


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
) -> None:
    """Send a change_preview notification to the WebSocket client.

    Notifies the frontend when a file write/replace produces a PendingChange.
    This enables the frontend to display the diff and provide a confirm button.
    """
    await websocket.send_json({
        "type": "change_preview",
        "stream_id": stream_id,
        "message_id": message_id,
        "change_id": change_id,
        "operation": operation,
        "path": path,
        "unified_diff": unified_diff,
        "status": status,
        "timestamp": timestamp,
    })


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
    """Send a preview_result notification to the WebSocket client.

    Notifies the frontend when a preview is ready for display.
    """
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
    """Send a repair_state notification to the WebSocket client.

    Notifies the frontend when self-repair state changes occur.
    """
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


async def _respond_pings(websocket: WebSocket) -> None:
    """Non-blockingly check for a client ping and respond with pong.

    Must be called from inside a streaming loop so that long-running
    AI responses do not starve the ping/pong protocol.
    """
    try:
        msg = await asyncio.wait_for(websocket.receive_json(), timeout=0)
        if isinstance(msg, dict) and msg.get("type") == "ping":
            await websocket.send_json({"type": "pong"})
    except asyncio.TimeoutError:
        pass  # no pending message – expected in the common case
    except WebSocketDisconnect:
        raise  # let the outer handler clean up


def valid_send_message(payload: object, session_id: str) -> bool:
    if not isinstance(payload, dict):
        return False
    return (
        payload.get("action") == "send_message"
        and payload.get("session_id") == session_id
        and isinstance(payload.get("content"), str)
        and len(payload["content"]) > 0
    )


@router.websocket("/{session_id}")
async def session_websocket(
    websocket: WebSocket,
    session_id: str,
) -> None:
    await websocket.accept()

    query_params = getattr(websocket, "query_params", {}) or {}
    token = query_params.get("x-token") if hasattr(query_params, "get") else None
    if not token and hasattr(websocket, "headers"):
        token = websocket.headers.get("x-token")

    db = SessionLocal()
    try:
        session = db.get(ChatSession, session_id)
        if session is None:
            await websocket.close(code=4004, reason="Session not found")
            return

        if token:
            try:
                payload = decode_token(token)
                user_id = str(payload.get("sub"))
            except Exception:
                await websocket.close(code=4002, reason="Invalid or expired token")
                return
        else:
            user_id = session.owner_id or "dev_user"

        stream_output_enabled = chat_stream_output_enabled()

        # P6-5: For group sessions, resolve the primary agent from session_members
        if session.mode == "group":
            selected_agent = get_primary_agent_for_group(db, session) or get_default_agent()
        else:
            selected_agent = get_session_agent(db, session) or get_default_agent()
        agent_role = getattr(selected_agent, 'role', 'PM')

        if session.owner_id != user_id:
            await _send_error(websocket, "forbidden", "Forbidden: session does not belong to current user", stream_id=str(uuid.uuid4()), agent_role=agent_role)
            await websocket.close(code=4003, reason="Forbidden")
            return

        # 注册 WebSocket 连接以便 REST API 可以推送事件
        _WS_CONNECTION_MANAGER.register(session_id, websocket, user_id)

        while True:
            try:
                payload = await websocket.receive_json()
            except JSONDecodeError:
                await _send_error(websocket, "invalid_request", "Invalid request", stream_id=str(uuid.uuid4()), agent_role=agent_role)
                continue

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

            # human message 落库（status=completed）
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

            try:
                active_stream_id = stream_id
                active_agent_role = agent_role
                active_message_id: str | None = None
                active_error_code = "unknown"

                if runtime_use_runtime_agent():
                    # M5: Real runtime path via RuntimeAgentService
                    from app.runtime.runtime_agent_service import (
                        RuntimeAgentService,
                        load_session_history,
                        WorkspaceNotBoundError,
                        WorkspaceAccessDeniedError,
                        WorkspaceRootInvalidError,
                    )
                    from app.runtime.llm_adapter import LLMAdapter
                    from app.services.agent_runtime import get_provider_for_agent

                    provider = get_provider_for_agent(selected_agent)
                    llm_adapter = LLMAdapter(provider=provider)

                    # T1: Load session history from DB, excluding the current human message
                    # (which is already committed and will be the user_message input).
                    session_history = load_session_history(db, session_id)

                    runtime_service = RuntimeAgentService(
                        session_id=session_id,
                        user_message=content,
                        agent_role=agent_role,
                        llm_adapter=llm_adapter,
                        db=db,
                        stream_id=stream_id,
                        session_history=session_history,
                    )

                    async for event in runtime_service.stream_events():
                        await _respond_pings(websocket)
                        if event.type == "message_start":
                            active_stream_id = event.stream_id
                            active_agent_role = event.agent_role
                            active_message_id = event.message.id
                            await ws_send_message_start(
                                websocket,
                                agent_role=event.agent_role,
                                stream_id=event.stream_id,
                                message=event.message,
                            )
                        elif event.type == "message_delta":
                            active_stream_id = event.stream_id
                            active_agent_role = event.agent_role
                            active_message_id = event.message_id
                            if stream_output_enabled:
                                await ws_send_message_delta(
                                    websocket,
                                    agent_role=event.agent_role,
                                    stream_id=event.stream_id,
                                    message_id=event.message_id,
                                    delta=event.delta,
                                )
                        elif event.type == "message_end":
                            active_stream_id = event.stream_id
                            active_agent_role = event.agent_role
                            active_message_id = event.message_id
                            await ws_send_message_end(
                                websocket,
                                agent_role=event.agent_role,
                                stream_id=event.stream_id,
                                message_id=event.message_id,
                                status=event.status,
                                final_content=getattr(event, "final_content", None),
                            )
                        elif event.type == "message_error":
                            active_stream_id = event.stream_id
                            active_agent_role = event.agent_role
                            active_message_id = event.message_id
                            active_error_code = event.error_code
                            await ws_send_message_error(
                                websocket,
                                agent_role=event.agent_role,
                                stream_id=event.stream_id,
                                message_id=event.message_id,
                                error_code=event.error_code,
                                error_message=event.error_message,
                            )
                        # Task A: Runtime 扩展事件转发
                        elif event.type == "tool_event":
                            active_stream_id = event.stream_id
                            active_message_id = event.message_id
                            await ws_send_tool_event(
                                websocket,
                                tool_name=event.tool_name,
                                arguments=event.arguments,
                                response=event.response,
                                status=event.status,
                                stream_id=event.stream_id,
                                message_id=event.message_id,
                            )
                        elif event.type == "runtime_state":
                            active_stream_id = event.stream_id
                            active_message_id = event.message_id
                            await ws_send_runtime_state(
                                websocket,
                                stream_id=event.stream_id,
                                message_id=event.message_id,
                                state=event.state,
                                timestamp=event.timestamp,
                            )
                        # Task C-2: change_preview event forwarding
                        elif event.type == "change_preview":
                            active_stream_id = event.stream_id
                            active_message_id = event.message_id
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
                            )
                        # Task 3: preview_result event forwarding
                        elif event.type == "preview_result":
                            await ws_send_preview_result(
                                websocket,
                                preview_id=event.preview_id,
                                workspace_id=event.workspace_id,
                                preview_url=event.preview_url,
                                status=event.status,
                                message_id=event.message_id,
                                stream_id=event.stream_id,
                                timestamp=event.timestamp,
                            )
                        # Task 3: repair_state event forwarding
                        elif event.type == "repair_state":
                            await ws_send_repair_state(
                                websocket,
                                state=event.state,
                                attempt=event.attempt,
                                max_attempts=event.max_attempts,
                                message=event.message,
                                stream_id=event.stream_id,
                                message_id=event.message_id,
                                timestamp=event.timestamp,
                            )
                else:
                    # Fallback: FixedAgentResponder (default)
                    responder = FixedAgentResponder(
                        session_id=session_id,
                        user_message=content,
                        agent_role=agent_role,
                        db=db,
                        stream_id=stream_id,
                    )

                    async for event in responder.stream_events():
                        await _respond_pings(websocket)
                        if event.type == "message_start":
                            active_stream_id = event.stream_id
                            active_agent_role = event.agent_role
                            active_message_id = event.message.id
                            await ws_send_message_start(
                                websocket,
                                agent_role=event.agent_role,
                                stream_id=event.stream_id,
                                message=event.message,
                            )
                        elif event.type == "message_delta":
                            active_stream_id = event.stream_id
                            active_agent_role = event.agent_role
                            active_message_id = event.message_id
                            if stream_output_enabled:
                                await ws_send_message_delta(
                                    websocket,
                                    agent_role=event.agent_role,
                                    stream_id=event.stream_id,
                                    message_id=event.message_id,
                                    delta=event.delta,
                                )
                        elif event.type == "message_end":
                            active_stream_id = event.stream_id
                            active_agent_role = event.agent_role
                            active_message_id = event.message_id
                            await ws_send_message_end(
                                websocket,
                                agent_role=event.agent_role,
                                stream_id=event.stream_id,
                                message_id=event.message_id,
                                status=event.status,
                                final_content=getattr(event, "final_content", None),
                            )
                        elif event.type == "message_error":
                            active_stream_id = event.stream_id
                            active_agent_role = event.agent_role
                            active_message_id = event.message_id
                            active_error_code = "fixed_responder_failed"
                            await ws_send_message_error(
                                websocket,
                                agent_role=event.agent_role,
                                stream_id=event.stream_id,
                                message_id=event.message_id,
                                error_code=event.error_code,
                                error_message=event.error_message,
                            )
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
            finally:
                _IN_FLIGHT_GUARD.leave(session_id)

    except WebSocketDisconnect:
        pass
    except Exception:
        await _send_error(websocket, "unknown", "Unknown error", stream_id=str(uuid.uuid4()), agent_role=agent_role)
    finally:
        # 取消注册 WebSocket 连接
        _WS_CONNECTION_MANAGER.unregister(session_id)
        db.close()
