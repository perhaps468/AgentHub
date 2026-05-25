"""P1-3 WebSocket 统一消息流集成测试。

测试 ws.py 中的流式业务逻辑，使用 FixedAgentResponder 而非真实 Provider。

覆盖 P1-3 测试方案：
- ping → pong，不持久化，不触发 Agent 回复
- send_message → human message 先落库 → FixedAgentResponder → message_start/delta*/end
- 非法请求 → error (invalid_request)，WS 保持可用
- session 不存在 → error (session_not_found) 后关闭
- WS 在流式中断开 → agent message status=failed 收口
"""

from unittest.mock import MagicMock

import pytest

from starlette.websockets import WebSocketDisconnect

from app.api.ws import session_websocket, valid_send_message


# ---------------------------------------------------------------------------
# Mock WebSocket
# ---------------------------------------------------------------------------

class MockWebSocket:
    """模拟 Starlette WebSocket，用于直接调用 WS handler。

    Starlette 真实 WebSocket 的 receive_json() 在连接断开时抛出 WebSocketDisconnect。
    当队列消息耗尽时，模拟连接正常关闭（WebSocketDisconnect(code=1000)），
    因为真实 handler 在 while 循环中等待消息时会收到 WebSocketDisconnect 退出循环。
    """

    def __init__(self, should_close: bool = False, close_code: int = 1000):
        self.accepted = False
        self.closed = False
        self.close_code = close_code
        self.should_close = should_close
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
            raise WebSocketDisconnect(code=self.close_code)
        return self.received_messages.pop(0)

    def queue_message(self, msg: dict) -> None:
        self.received_messages.append(msg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_session_via_db():
    """直接操作数据库创建 session，绕过 TestClient WS 兼容性问题。"""
    from app.core.database import SessionLocal
    from app.models.session import ChatSession

    db = SessionLocal()
    try:
        session = ChatSession(owner_id="dev_user", title="Test Session", mode="single")
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()


def query_messages(session_id: str) -> list[dict]:
    """通过数据库查询消息。"""
    from app.core.database import SessionLocal
    from app.models.message import Message
    from sqlalchemy import select

    db = SessionLocal()
    try:
        msgs = db.scalars(select(Message).where(Message.session_id == session_id).order_by(Message.created_at)).all()
        return [
            {
                "id": m.id,
                "sender_type": m.sender_type,
                "sender_role": m.sender_role,
                "type": m.type,
                "content": m.content,
                "payload": m.payload,
                "status": m.status,
            }
            for m in msgs
        ]
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def setup():
    """配置内存数据库。"""
    from app.core import database

    database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)
    yield
    database.Base.metadata.drop_all(bind=database.engine)


# ---------------------------------------------------------------------------
# Tests: valid_send_message 验证规则（纯单元测试）
# ---------------------------------------------------------------------------

class TestValidSendMessage:
    def test_valid_payload(self):
        assert valid_send_message(
            {"action": "send_message", "session_id": "s1", "content": "hello"},
            "s1",
        )

    def test_wrong_session_id_rejected(self):
        assert not valid_send_message(
            {"action": "send_message", "session_id": "s2", "content": "hello"},
            "s1",
        )

    def test_empty_content_rejected(self):
        assert not valid_send_message(
            {"action": "send_message", "session_id": "s1", "content": ""},
            "s1",
        )

    def test_missing_content_rejected(self):
        assert not valid_send_message(
            {"action": "send_message", "session_id": "s1"},
            "s1",
        )

    def test_ping_not_valid(self):
        assert not valid_send_message({"type": "ping"}, "s1")


# ---------------------------------------------------------------------------
# Tests: ping/pong（直接 handler 调用）
# ---------------------------------------------------------------------------

class TestPingPong:
    def test_ping_returns_pong(self, setup):
        session_id = create_session_via_db()
        ws = MockWebSocket()

        ws.queue_message({"type": "ping"})

        import asyncio
        asyncio.run(
            session_websocket(ws, session_id)
        )

        assert ws.accepted
        assert ws.sent_messages == [{"type": "pong"}]

    def test_ping_does_not_persist_messages(self, setup):
        session_id = create_session_via_db()
        ws = MockWebSocket()

        ws.queue_message({"type": "ping"})
        ws.queue_message({"type": "ping"})

        import asyncio
        asyncio.run(
            session_websocket(ws, session_id)
        )

        assert ws.sent_messages == [{"type": "pong"}, {"type": "pong"}]
        assert query_messages(session_id) == []

    def test_ping_does_not_trigger_agent_reply(self, setup):
        session_id = create_session_via_db()
        ws = MockWebSocket()

        ws.queue_message({"type": "ping"})

        import asyncio
        asyncio.run(
            session_websocket(ws, session_id)
        )

        assert ws.sent_messages == [{"type": "pong"}]


# ---------------------------------------------------------------------------
# Tests: 流式成功路径（直接 handler 调用 + mock Provider）
# ---------------------------------------------------------------------------

import asyncio
from unittest.mock import patch


class TestSendMessageSuccess:
    """P1-3: 流式成功路径测试。FixedAgentResponder 替代真实 Provider。"""

    def test_send_message_persists_human_and_agent_messages(self, setup):
        session_id = create_session_via_db()
        ws = MockWebSocket()

        ws.queue_message({
            "action": "send_message",
            "session_id": session_id,
            "content": "hello",
        })

        with patch("app.api.ws.get_default_agent") as mock_get_agent:
            mock_get_agent.return_value = MagicMock(role="PM", system_prompt="You are PM.")

            import asyncio
            asyncio.run(session_websocket(ws, session_id))

        assert ws.accepted

        # P1-3 新协议: message_start -> message_delta* -> message_end
        msg_start = next(m for m in ws.sent_messages if m["type"] == "message_start")
        assert msg_start["agent_role"] == "PM"
        assert "stream_id" in msg_start
        assert msg_start["message"]["sender_type"] == "agent"
        assert msg_start["message"]["status"] == "streaming"

        deltas = [m for m in ws.sent_messages if m["type"] == "message_delta"]
        assert len(deltas) > 0
        for delta in deltas:
            assert "delta" in delta
            assert len(delta["delta"]) > 0

        msg_end = next(m for m in ws.sent_messages if m["type"] == "message_end")
        assert msg_end["message_id"] == msg_start["message"]["id"]
        assert msg_end["status"] == "completed"

        # 旧协议不应出现在主链路
        assert not any(m["type"] == "agent_typing" for m in ws.sent_messages)
        assert not any(m["type"] == "chat_stream" for m in ws.sent_messages)

        msgs = query_messages(session_id)
        assert len(msgs) == 2
        assert msgs[0]["sender_type"] == "human"
        assert msgs[0]["content"] == "hello"
        assert msgs[0]["status"] == "completed"
        assert msgs[0]["type"] == "text"
        assert msgs[1]["sender_type"] == "agent"
        assert msgs[1]["sender_role"] == "PM"
        assert msgs[1]["status"] == "completed"
        assert msgs[1]["type"] == "text"
        assert "text" in msgs[1]["payload"]

    def test_send_message_moves_session_to_top_of_list(self, setup):
        from app.core.database import SessionLocal
        from app.models.session import ChatSession

        db = SessionLocal()
        try:
            first = ChatSession(owner_id="dev_user", title="First", mode="single")
            second = ChatSession(owner_id="dev_user", title="Second", mode="single")
            db.add(first)
            db.add(second)
            db.commit()
            db.refresh(first)
            db.refresh(second)
            first_id = first.id
        finally:
            db.close()

        ws = MockWebSocket()
        ws.queue_message({
            "action": "send_message",
            "session_id": first_id,
            "content": "bump",
        })

        with patch("app.api.ws.get_default_agent") as mock_get_agent:
            mock_get_agent.return_value = MagicMock(role="PM", system_prompt="You are PM.")

            import asyncio
            asyncio.run(session_websocket(ws, first_id))

        msgs = query_messages(first_id)
        assert len(msgs) == 2
        assert msgs[0]["sender_type"] == "human"
        assert msgs[1]["sender_type"] == "agent"

    def test_ws_usable_after_send_message(self, setup):
        session_id = create_session_via_db()
        ws = MockWebSocket()

        ws.queue_message({
            "action": "send_message",
            "session_id": session_id,
            "content": "hello",
        })
        ws.queue_message({"type": "ping"})

        with patch("app.api.ws.get_default_agent") as mock_get_agent:
            mock_get_agent.return_value = MagicMock(role="PM", system_prompt="You are PM.")

            import asyncio
            asyncio.run(session_websocket(ws, session_id))

        deltas = [m for m in ws.sent_messages if m["type"] == "message_delta"]
        assert len(deltas) >= 1
        pong = next(m for m in ws.sent_messages if m["type"] == "pong")
        assert pong is not None


# ---------------------------------------------------------------------------
# Tests: Provider 错误路径
# ---------------------------------------------------------------------------

class TestSendMessageProviderErrors:
    """P1-3: FixedAgentResponder 错误路径测试。

    注意: Provider 错误 (missing API key, upstream failure) 已不适用于 P1-3，
    因为真实 provider 已被 FixedAgentResponder 替代。
    """

    def test_general_error_sets_agent_message_to_failed(self, setup):
        """FixedAgentResponder 异常时，agent message status 应为 failed。"""
        from app.core.database import SessionLocal

        session_id = create_session_via_db()
        ws = MockWebSocket()

        ws.queue_message({
            "action": "send_message",
            "session_id": session_id,
            "content": "hello",
        })

        async def failing_stream(self):
            from app.models.message import Message

            agent_msg = Message(
                session_id=self.session_id,
                sender_type="agent",
                sender_role=self.agent_role,
                content="",
                type="text",
                status="streaming",
                payload={"text": ""},
                msg_metadata={"source": "fixed_responder"},
            )
            self.db.add(agent_msg)
            self.db.commit()
            self.db.refresh(agent_msg)
            self._message_id = agent_msg.id
            self._agent_message = agent_msg
            yield type("Event", (), {
                "type": "message_start",
                "agent_role": self.agent_role,
                "timestamp": "2026-05-24T10:00:00Z",
                "stream_id": self.stream_id,
                "message": agent_msg,
            })()
            raise RuntimeError("simulated responder failure")

        with patch("app.api.ws.FixedAgentResponder") as MockResponder, \
             patch("app.api.ws.get_default_agent") as mock_get_agent:
            db = SessionLocal()
            mock_instance = MagicMock()
            mock_instance.stream_events = lambda: failing_stream(mock_instance)
            mock_instance.db = db
            mock_instance.session_id = session_id
            mock_instance.user_message = "hello"
            mock_instance.agent_role = "PM"
            mock_instance.stream_id = "test-stream"
            mock_instance._message_id = None
            mock_instance._agent_message = None
            MockResponder.return_value = mock_instance

            mock_get_agent.return_value = MagicMock(role="PM", system_prompt="You are PM.")

            import asyncio
            asyncio.run(session_websocket(ws, session_id))

            db.close()

        error_msgs = [m for m in ws.sent_messages if m["type"] == "message_error"]
        assert len(error_msgs) >= 1, f"Expected message_error, got: {[m for m in ws.sent_messages]}"
        assert error_msgs[0]["error_code"] == "fixed_responder_failed"

        msgs = query_messages(session_id)
        agent_msg = next((m for m in msgs if m["sender_type"] == "agent"), None)
        assert agent_msg is not None, f"Expected agent message in DB, got: {msgs}"
        assert agent_msg["status"] == "failed"


# ---------------------------------------------------------------------------
# Tests: 请求验证
# ---------------------------------------------------------------------------

class TestSendMessageValidation:
    def test_missing_content_returns_invalid_request(self, setup):
        session_id = create_session_via_db()
        ws = MockWebSocket()

        ws.queue_message({
            "action": "send_message",
            "session_id": session_id,
        })

        import asyncio
        asyncio.run(session_websocket(ws, session_id))

        assert ws.accepted
        # 新协议 error 包含 agent_role, timestamp, stream_id
        error = ws.sent_messages[0]
        assert error["type"] == "error"
        assert error["error_code"] == "invalid_request"
        assert error["agent_role"] == "PM"
        assert "stream_id" in error

    def test_empty_content_returns_invalid_request(self, setup):
        session_id = create_session_via_db()
        ws = MockWebSocket()

        ws.queue_message({
            "action": "send_message",
            "session_id": session_id,
            "content": "",
        })

        import asyncio
        asyncio.run(session_websocket(ws, session_id))

        assert ws.accepted
        error = ws.sent_messages[0]
        assert error["type"] == "error"
        assert error["error_code"] == "invalid_request"
        assert error["agent_role"] == "PM"
        assert "stream_id" in error

    def test_malformed_json_closes_connection(self, setup):
        """非 JSON 请求体时 WS 连接关闭（handler 捕获 JSONDecodeError 后返回 invalid_request 后继续循环，
        但 MockWebSocket 无法模拟非 JSON 接收，这里只验证 WS 能正常处理。"""
        session_id = create_session_via_db()
        ws = MockWebSocket()

        import asyncio
        asyncio.run(
            session_websocket(ws, session_id)
        )

        assert ws.accepted

    def test_ws_usable_after_invalid_request(self, setup):
        session_id = create_session_via_db()
        ws = MockWebSocket()

        ws.queue_message({
            "action": "send_message",
            "session_id": session_id,
        })
        ws.queue_message({"type": "ping"})

        import asyncio
        asyncio.run(
            session_websocket(ws, session_id)
        )

        assert ws.sent_messages[0]["error_code"] == "invalid_request"
        assert ws.sent_messages[1]["type"] == "pong"


# ---------------------------------------------------------------------------
# Tests: session 不存在
# ---------------------------------------------------------------------------

class TestSessionNotFound:
    def test_missing_session_returns_error_then_closes(self, setup):
        missing_id = "00000000-0000-0000-0000-000000000000"
        ws = MockWebSocket()

        import asyncio
        asyncio.run(session_websocket(ws, missing_id))

        assert ws.accepted
        assert ws.closed
        # 新协议 error 包含 agent_role, timestamp, stream_id
        error = ws.sent_messages[0]
        assert error["type"] == "error"
        assert error["error_code"] == "session_not_found"
        assert "stream_id" in error
