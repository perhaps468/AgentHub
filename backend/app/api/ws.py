from json import JSONDecodeError

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.message import Message
from app.models.session import ChatSession, utcnow
from app.schemas.common import to_iso_z

router = APIRouter(tags=["websocket"])


async def send_error(websocket: WebSocket, code: str, message: str) -> None:
    await websocket.send_json(
        {
            "type": "error",
            "error_code": code,
            "error_message": message,
        }
    )


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
    db: Session = Depends(get_db),
) -> None:
    await websocket.accept()
    session = db.get(ChatSession, session_id)
    if session is None:
        await send_error(websocket, "session_not_found", "Session not found")
        await websocket.close()
        return

    if x_token and x_token != session.owner_id:
        await send_error(websocket, "forbidden", "You do not have access to this session")
        await send_error(websocket, "forbidden", "You do not have access to this session")
        await websocket.close()
        return

    try:
        while True:
            try:
                payload = await websocket.receive_json()
            except JSONDecodeError:
                await send_error(websocket, "invalid_request", "Invalid request")
                continue

            if isinstance(payload, dict) and payload.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if not valid_send_message(payload, session_id):
                await send_error(websocket, "invalid_request", "Invalid request")
                continue

            content = payload["content"]
            human_message = Message(
                session_id=session_id,
                sender_type="human",
                sender_role=None,
                content=content,
                content_type="text",
            )
            agent_message = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content=f"Echo: {content}",
                content_type="text",
            )
            session.updated_at = utcnow()
            db.add_all([human_message, agent_message])
            db.add(session)
            db.commit()
            db.refresh(agent_message)

            await websocket.send_json(
                {
                    "type": "chat_stream",
                    "message_id": agent_message.id,
                    "session_id": agent_message.session_id,
                    "sender_type": agent_message.sender_type,
                    "sender_role": agent_message.sender_role,
                    "content": agent_message.content,
                    "content_type": agent_message.content_type,
                    "created_at": to_iso_z(agent_message.created_at),
                }
            )
    except WebSocketDisconnect:
        return
    except Exception:
        await send_error(websocket, "unknown", "Unknown error")
