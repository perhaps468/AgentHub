from json import JSONDecodeError

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.agents.registry import get_default_agent
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.message import Message
from app.models.session import ChatSession, utcnow
from app.providers.base import (
    ProviderInput,
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderResponseInvalidError,
)
from app.schemas.common import to_iso_z
from app.services.agent_runtime import get_provider

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
) -> None:
    await websocket.accept()

    db = SessionLocal()
    try:
        session = db.get(ChatSession, session_id)
        if session is None:
            await send_error(websocket, "session_not_found", "Session not found")
            await websocket.close()
            return

        if x_token and x_token != session.owner_id:
            await send_error(websocket, "forbidden", "You do not have access to this session")
            await websocket.close()
            return

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
            db.add(human_message)
            session.updated_at = utcnow()
            db.add(session)
            db.commit()

            agent = get_default_agent()
            provider = get_provider()
            settings = get_settings()

            try:
                output = await provider.chat(
                    ProviderInput(
                        system_prompt=agent.system_prompt,
                        user_message=content,
                        model=settings.qwen_model,
                    )
                )
            except ProviderNotConfiguredError:
                await send_error(websocket, "provider_not_configured", "Provider is not configured")
                continue
            except ProviderRequestError:
                await send_error(websocket, "provider_request_failed", "Provider request failed")
                continue
            except ProviderResponseInvalidError:
                await send_error(websocket, "provider_response_invalid", "Provider returned invalid response")
                continue

            agent_message = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role=agent.role,
                content=output.text,
                content_type="text",
            )
            db.add(agent_message)
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
        pass
    except Exception:
        await send_error(websocket, "unknown", "Unknown error")
    finally:
        db.close()