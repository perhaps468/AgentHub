import asyncio

import pytest
from starlette.websockets import WebSocketDisconnect


class MockWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None
        self.sent_messages: list[dict] = []
        self.received_messages: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000) -> None:
        self.closed = True
        self.close_code = code

    async def send_json(self, data: dict) -> None:
        self.sent_messages.append(data)

    async def receive_json(self) -> dict:
        if not self.received_messages:
            raise WebSocketDisconnect(code=1000)
        return self.received_messages.pop(0)

    def queue_message(self, msg: dict) -> None:
        self.received_messages.append(msg)


@pytest.fixture()
def setup_db():
    from app.core import database

    database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)
    yield
    database.Base.metadata.drop_all(bind=database.engine)


def create_session_via_db() -> str:
    from app.core.database import SessionLocal
    from app.models.session import ChatSession

    db = SessionLocal()
    try:
        session = ChatSession(owner_id="dev_user", title="Test", mode="single")
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()


def test_ws_does_not_reject_login_token(setup_db):
    from app.api.ws import session_websocket

    session_id = create_session_via_db()
    ws = MockWebSocket()
    ws.queue_message({"type": "ping"})

    asyncio.run(session_websocket(ws, session_id, x_token="login-token-123"))

    error_codes = [
        m.get("error_code")
        for m in ws.sent_messages
        if m.get("type") in ("message_error", "error")
    ]
    assert "forbidden" not in error_codes
    assert any(m.get("type") == "pong" for m in ws.sent_messages)
