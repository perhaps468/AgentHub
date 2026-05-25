import uuid
from json import JSONDecodeError

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.registry import get_default_agent
from app.core.database import SessionLocal
from app.models.message import Message
from app.models.session import ChatSession, utcnow
from app.schemas.common import to_iso_z
from app.services.fixed_agent_responder import FixedAgentResponder

router = APIRouter(prefix="/ws", tags=["websocket"])


# ---- 在途并发保护 ----

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
) -> None:
    await websocket.send_json({
        "type": "message_end",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "status": status,
    })


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

    agent = get_default_agent()

    db = SessionLocal()
    try:
        session = db.get(ChatSession, session_id)
        if session is None:
            await _send_error(websocket, "session_not_found", "Session not found", stream_id=str(uuid.uuid4()), agent_role=agent.role)
            await websocket.close()
            return

        while True:
            try:
                payload = await websocket.receive_json()
            except JSONDecodeError:
                await _send_error(websocket, "invalid_request", "Invalid request", stream_id=str(uuid.uuid4()), agent_role=agent.role)
                continue

            if isinstance(payload, dict) and payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if not valid_send_message(payload, session_id):
                await _send_error(websocket, "invalid_request", "Invalid request", stream_id=str(uuid.uuid4()), agent_role=agent.role)
                continue

            stream_id = str(uuid.uuid4())

            if not _IN_FLIGHT_GUARD.try_enter(session_id):
                await _send_error(websocket, "agent_busy", "Agent is busy, please wait", stream_id=stream_id, agent_role=agent.role)
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
                responder = FixedAgentResponder(
                    session_id=session_id,
                    user_message=content,
                    agent_role=agent.role,
                    db=db,
                    stream_id=stream_id,
                )

                active_stream_id = stream_id
                active_agent_role = agent.role
                active_message_id: str | None = None

                async for event in responder.stream_events():
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
                        )
                    elif event.type == "message_error":
                        active_stream_id = event.stream_id
                        active_agent_role = event.agent_role
                        active_message_id = event.message_id
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
                    error_code="fixed_responder_failed",
                    error_message=str(exc),
                )
            finally:
                _IN_FLIGHT_GUARD.leave(session_id)

    except WebSocketDisconnect:
        pass
    except Exception:
        await _send_error(websocket, "unknown", "Unknown error", stream_id=str(uuid.uuid4()), agent_role=agent.role)
    finally:
        db.close()
