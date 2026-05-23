import uuid
from json import JSONDecodeError

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.registry import get_default_agent
from app.core.database import SessionLocal
from app.models.message import Message
from app.models.session import ChatSession, utcnow
from app.providers.base import (
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderResponseInvalidError,
)
from app.schemas.common import to_iso_z
from app.services.agent_runtime import get_provider
from app.services.agent_stream_service import (
    AgentStreamService,
    ChunkEvent,
    ErrorEvent,
    TypingEvent,
)

router = APIRouter(tags=["websocket"])


# ---- 在途并发保护 ----

class _InFlightGuard:
    """单会话单在途回复保护。

    规则：
    - try_enter 返回 True 表示成功进入，False 表示已被占用。
    - leave 释放占用。
    - interrupt 中断但不抛异常。
    """

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
    """注入测试用 guard。用于测试隔离。"""
    global _IN_FLIGHT_GUARD
    _IN_FLIGHT_GUARD = guard


# ---- WebSocket 消息发送辅助函数 ----

def _utcnow_iso() -> str:
    return to_iso_z(utcnow())


async def send_error(
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


async def ws_send_typing(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    is_typing: bool,
) -> None:
    await websocket.send_json({
        "type": "agent_typing",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "is_typing": is_typing,
    })


async def ws_send_chunk(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message_id: str,
    content_chunk: str,
    is_final: bool,
) -> None:
    await websocket.send_json({
        "type": "chat_stream",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "content_chunk": content_chunk,
        "is_final": is_final,
    })


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
    x_token: str | None = None,
) -> None:
    await websocket.accept()

    # 尽早初始化 agent，使 session_not_found、invalid_request 等错误路径
    # 也能使用 agent.role 生成符合 BaseMessage 契约的错误事件。
    agent = get_default_agent()

    db = SessionLocal()
    try:
        session = db.get(ChatSession, session_id)
        if session is None:
            await send_error(websocket, "session_not_found", "Session not found", stream_id=str(uuid.uuid4()), agent_role=agent.role)
            await websocket.close()
            return

        if x_token and x_token != session.owner_id:
            await send_error(websocket, "forbidden", "You do not have access to this session", stream_id=str(uuid.uuid4()), agent_role=agent.role)
            await websocket.close()
            return

        while True:
            try:
                payload = await websocket.receive_json()
            except JSONDecodeError:
                await send_error(websocket, "invalid_request", "Invalid request", stream_id=str(uuid.uuid4()), agent_role=agent.role)
                continue

            if isinstance(payload, dict) and payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if not valid_send_message(payload, session_id):
                await send_error(websocket, "invalid_request", "Invalid request", stream_id=str(uuid.uuid4()), agent_role=agent.role)
                continue

            # 预先生成 stream_id
            stream_id = str(uuid.uuid4())

            # 在途保护
            if not _IN_FLIGHT_GUARD.try_enter(session_id):
                await send_error(websocket, "agent_busy", "Agent is busy, please wait", stream_id=stream_id, agent_role=agent.role)
                continue

            content = payload["content"]

            # human message 落库
            human_message = Message(
                session_id=session_id,
                sender_type="human",
                sender_role=None,
                content=content,
                content_type="text",
            )
            db.add(human_message)
            session.updated_at = utcnow()
            db.add(session)
            db.commit()
            db.refresh(human_message)

            provider = get_provider()

            service = AgentStreamService(
                session_id=session_id,
                human_message_id=human_message.id,
                agent_role=agent.role,
                system_prompt=agent.system_prompt,
                user_message=content,
                provider=provider,
                db=db,
                stream_id=stream_id,
            )

            try:
                async for event in service.stream_events():
                    if isinstance(event, TypingEvent):
                        await ws_send_typing(websocket, agent.role, stream_id, event.is_typing)
                    elif isinstance(event, ChunkEvent):
                        await ws_send_chunk(
                            websocket,
                            agent.role,
                            stream_id,
                            service._agent_message.id,
                            event.content_chunk,
                            event.is_final,
                        )
                    elif isinstance(event, ErrorEvent):
                        await send_error(websocket, event.error_code, event.error_message, stream_id=stream_id, agent_role=agent.role)
            except Exception:
                # WebSocket 断开，触发中断收口
                service.interrupt()
                _IN_FLIGHT_GUARD.interrupt(session_id)
                raise

            _IN_FLIGHT_GUARD.leave(session_id)

    except WebSocketDisconnect:
        pass
    except Exception:
        await send_error(websocket, "unknown", "Unknown error", stream_id=str(uuid.uuid4()), agent_role=agent.role)
    finally:
        db.close()
