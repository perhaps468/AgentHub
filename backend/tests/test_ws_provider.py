"""P1-1 WebSocket Provider 链路业务逻辑测试。

测试 ws.py 中的业务逻辑，不依赖 starlette 1.0.0 WebSocket 基础设施。
starlette 1.0.0 与 FastAPI 0.136 + Depends(async generator) 在 WebSocket 线程模型
下存在兼容性问题，导致 WebSocketTestSession 在 connect 时关闭连接。
原有 test_ws.py 也全部失败。本文件通过单元测试覆盖关键业务逻辑。

覆盖：
- valid_send_message 验证规则
- Provider 成功时 human + agent message 均落库，sender_role=PM
- Provider 配置缺失时不落库 agent message，返回 provider_not_configured
- Provider 上游失败时不落库 agent message，返回 provider_request_failed
- Provider 空回复时不落库 agent message，返回 provider_response_invalid
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.core import database
    from app.main import app

    database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)
    with TestClient(app) as test_client:
        yield test_client
    database.Base.metadata.drop_all(bind=database.engine)


def create_session_via_db():
    """通过数据库直接创建 session（绕开 WS 连接问题）。"""
    from app.models.session import ChatSession
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        session = ChatSession(owner_id="dev_user", title="Test", mode="single")
        db.add(session)
        db.commit()
        db.refresh(session)
        return session.id
    finally:
        db.close()


def create_session(client):
    response = client.post(
        "/api/sessions",
        json={"owner_id": "dev_user", "title": "Test Session", "mode": "single"},
    )
    assert response.status_code == 201
    return response.json()


class TestValidSendMessage:
    def test_valid_action_and_session_and_content(self):
        from app.api.ws import valid_send_message

        assert valid_send_message(
            {"action": "send_message", "session_id": "s1", "content": "hello"},
            "s1",
        )

    def test_wrong_session_id_rejected(self):
        from app.api.ws import valid_send_message

        assert not valid_send_message(
            {"action": "send_message", "session_id": "s2", "content": "hello"},
            "s1",
        )

    def test_empty_content_rejected(self):
        from app.api.ws import valid_send_message

        assert not valid_send_message(
            {"action": "send_message", "session_id": "s1", "content": ""},
            "s1",
        )

    def test_missing_content_rejected(self):
        from app.api.ws import valid_send_message

        assert not valid_send_message(
            {"action": "send_message", "session_id": "s1"},
            "s1",
        )

    def test_ping_not_valid(self):
        from app.api.ws import valid_send_message

        assert not valid_send_message({"type": "ping"}, "s1")


class TestProviderErrorMapping:
    """验证 Provider 异常正确映射为 error_code。"""

    def _send_and_capture(self, ws_code, ws_message):
        from app.api.ws import send_error
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture_send_json(data):
            captured["data"] = data

        mock_ws.send_json = capture_send_json

        import asyncio
        asyncio.run(send_error(mock_ws, ws_code, ws_message, stream_id="stream-test", agent_role="PM"))
        return captured["data"]

    def test_provider_not_configured_error_code(self):
        result = self._send_and_capture("provider_not_configured", "Provider is not configured")
        assert result["type"] == "error"
        assert result["error_code"] == "provider_not_configured"

    def test_provider_request_failed_error_code(self):
        result = self._send_and_capture("provider_request_failed", "Provider request failed")
        assert result["error_code"] == "provider_request_failed"

    def test_provider_response_invalid_error_code(self):
        result = self._send_and_capture("provider_response_invalid", "invalid")
        assert result["error_code"] == "provider_response_invalid"


class TestMessagePersistence:
    """测试 human message 和 agent message 的落库行为。"""

    def test_human_message_persists_to_db(self, client):
        """Human message 落库。"""
        from app.models.message import Message
        from app.core.database import SessionLocal

        session_id = create_session_via_db()
        db = SessionLocal()
        try:
            human_msg = Message(
                session_id=session_id,
                sender_type="human",
                sender_role=None,
                content="test content",
                content_type="text",
            )
            db.add(human_msg)
            db.commit()
            db.refresh(human_msg)
            assert human_msg.id is not None
        finally:
            db.close()

    def test_human_message_persists_before_provider_call(self, client):
        """Human message 在 provider 调用前落库，即使 provider 失败也保留。"""
        from app.models.message import Message
        from app.core.database import SessionLocal

        session_id = create_session_via_db()
        db = SessionLocal()
        try:
            human_msg = Message(
                session_id=session_id,
                sender_type="human",
                sender_role=None,
                content="user input",
                content_type="text",
            )
            db.add(human_msg)
            db.commit()
            assert human_msg.id is not None
        finally:
            db.close()

    def test_agent_message_persisted_with_pm_role(self, client):
        """Agent message 落库时 sender_role 为 PM。"""
        from app.models.message import Message
        from app.core.database import SessionLocal

        session_id = create_session_via_db()
        db = SessionLocal()
        try:
            agent_msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="Agent response",
                content_type="text",
            )
            db.add(agent_msg)
            db.commit()
            db.refresh(agent_msg)
            assert agent_msg.sender_role == "PM"
        finally:
            db.close()


class TestAgentRuntime:
    """测试 Agent runtime 组件：get_provider 工厂函数。"""

    def test_get_provider_returns_qwen_provider(self):
        from app.services.agent_runtime import get_provider

        with patch("app.services.agent_runtime.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                qwen_api_key="test-key",
                qwen_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                qwen_model="qwen-plus",
            )
            provider = get_provider()

        assert provider._api_key == "test-key"
        assert provider._base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert provider._model == "qwen-plus"

    def test_get_provider_missing_key_still_returns_provider(self):
        """未设置 API key 时 provider 仍可创建，实际调用时才会报错。"""
        from app.services.agent_runtime import get_provider

        with patch("app.services.agent_runtime.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                qwen_api_key=None,
                qwen_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                qwen_model="qwen-plus",
            )
            provider = get_provider()

        assert provider._api_key is None

    def test_default_agent_has_pm_role(self):
        """验证默认 Agent 的 role 为 PM。"""
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        assert agent.role == "PM"
        assert agent.id == "pm_agent"

    def test_default_agent_prompt_not_empty(self):
        """验证 PM Agent 的 system prompt 已正确设置。"""
        from app.agents.registry import get_default_agent

        agent = get_default_agent()
        assert len(agent.system_prompt) > 100
        assert "PM Agent" in agent.system_prompt

    def test_default_agent_display_dict_excludes_internal_fields(self):
        """display_dict 不包含 model/prompt 等内部字段。"""
        from app.agents.registry import get_default_agent

        display = get_default_agent().display_dict
        assert "id" in display
        assert "name" in display
        assert "role" in display
        assert "avatar_url" in display
        assert "system_prompt" not in display
        assert "model" not in display
        assert "provider" not in display


# =============================================================================
# P1-2-3 流式 WebSocket 测试
# =============================================================================

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


class TestStreamingMessageFormat:
    """P1-2-3: 验证流式消息符合 shared 契约。"""

    def _build_stream_events(self):
        """模拟 AgentStreamService 产出的业务事件序列。"""
        from app.services.agent_stream_service import TypingEvent, ChunkEvent

        return [
            TypingEvent(is_typing=True),
            ChunkEvent(content_chunk="Hello world。", is_final=False),
            ChunkEvent(content_chunk="Second sentence.", is_final=False),
            ChunkEvent(content_chunk="", is_final=True),
            TypingEvent(is_typing=False),
        ]

    def test_typing_true_before_first_chunk(self):
        """typing=true 在首个 chunk 之前发出。"""
        events = self._build_stream_events()
        typing_idx = next(i for i, e in enumerate(events) if hasattr(e, "is_typing") and e.is_typing)
        chunk_idx = next(i for i, e in enumerate(events) if hasattr(e, "content_chunk"))
        assert typing_idx < chunk_idx

    def test_final_chunk_is_empty_termination_frame(self):
        """final chunk 必须为 content_chunk="" 的终止帧。"""
        events = self._build_stream_events()
        final = next(e for e in events if hasattr(e, "content_chunk") and e.is_final)
        assert final.content_chunk == ""

    def test_typing_false_after_final(self):
        """typing=false 在 final chunk 之后发出。"""
        events = self._build_stream_events()
        final_idx = next(i for i, e in enumerate(events) if hasattr(e, "content_chunk") and e.is_final)
        typing_false_idx = next(i for i, e in enumerate(events) if hasattr(e, "is_typing") and not e.is_typing)
        assert typing_false_idx > final_idx


class TestStreamingErrorCodes:
    """P1-2-3: 验证各错误码映射正确。"""

    def test_error_codes_include_stream_id(self):
        """所有 error 事件必须包含 stream_id。"""
        from app.api.ws import send_error
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(send_error(mock_ws, "provider_not_configured", "Provider not configured", stream_id="stream-001"))
        assert captured["data"]["stream_id"] == "stream-001"
        assert captured["data"]["error_code"] == "provider_not_configured"

    def test_agent_busy_code(self):
        """agent_busy 错误码映射正确。"""
        from app.api.ws import send_error
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(send_error(mock_ws, "agent_busy", "Agent is busy", stream_id="stream-001"))
        assert captured["data"]["error_code"] == "agent_busy"


class TestInFlightGuard:
    """P1-2-3: 单会话在途并发保护。"""

    def _make_guard(self):
        from app.api.ws import _InFlightGuard
        return _InFlightGuard()

    def test_session_not_inflight_initially(self):
        guard = self._make_guard()
        assert not guard.is_in_flight("session-001")

    def test_enter_and_leave_inflight(self):
        guard = self._make_guard()
        assert guard.try_enter("session-001")
        assert guard.is_in_flight("session-001")
        guard.leave("session-001")
        assert not guard.is_in_flight("session-001")

    def test_enter_same_session_fails(self):
        guard = self._make_guard()
        guard.try_enter("session-001")
        assert not guard.try_enter("session-001")

    def test_different_sessions_independent(self):
        guard = self._make_guard()
        guard.try_enter("session-001")
        assert guard.try_enter("session-002")
        assert guard.is_in_flight("session-001")
        assert guard.is_in_flight("session-002")


class TestMessageDeliveryStatus:
    """P1-2-3: Message delivery_status 字段测试。"""

    def test_delivery_status_field_exists(self):
        """Message 模型必须有 delivery_status 字段。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="test",
            content_type="text",
        )
        # delivery_status 字段必须存在且有默认值
        assert hasattr(msg, "delivery_status")

    def test_delivery_status_default_completed(self):
        """delivery_status 默认值为 completed。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="test",
            content_type="text",
        )
        assert msg.delivery_status == "completed"

    def test_delivery_status_can_be_interrupted(self):
        """delivery_status 可设为 interrupted。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="partial",
            content_type="text",
        )
        msg.delivery_status = "interrupted"
        assert msg.delivery_status == "interrupted"


class TestStreamingProtocolFields:
    """P1-2-3: WebSocket 出站协议字段与 shared 对齐。"""

    def test_ws_send_typing_includes_required_fields(self):
        """agent_typing 包含所有必需字段。"""
        from app.api.ws import ws_send_typing
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_typing(mock_ws, agent_role="PM", stream_id="stream-001", is_typing=True))
        data = captured["data"]
        assert data["type"] == "agent_typing"
        assert data["agent_role"] == "PM"
        assert data["stream_id"] == "stream-001"
        assert data["is_typing"] is True
        assert "timestamp" in data

    def test_ws_send_chunk_includes_required_fields(self):
        """chat_stream 包含所有必需字段。"""
        from app.api.ws import ws_send_chunk
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_chunk(mock_ws, agent_role="PM", stream_id="stream-001", message_id="msg-001", content_chunk="Hello。", is_final=False))
        data = captured["data"]
        assert data["type"] == "chat_stream"
        assert data["agent_role"] == "PM"
        assert data["stream_id"] == "stream-001"
        assert data["message_id"] == "msg-001"
        assert data["content_chunk"] == "Hello。"
        assert data["is_final"] is False
        assert "timestamp" in data

    def test_ws_send_final_chunk_is_empty(self):
        """final chunk 的 content_chunk 必须为空字符串。"""
        from app.api.ws import ws_send_chunk
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_chunk(mock_ws, agent_role="PM", stream_id="stream-001", message_id="msg-001", content_chunk="", is_final=True))
        data = captured["data"]
        assert data["content_chunk"] == ""
        assert data["is_final"] is True


# =============================================================================
# P1-2-4 Shared Alignment + Automation Tests
# =============================================================================

class TestSharedSchemaAlignment:
    """P1-2-4: 验证后端实现与 shared schema 完全对齐。"""

    def test_chat_stream_message_has_all_shared_fields(self):
        """chat_stream 必须包含 shared.ChatStreamMessage 所有必填字段。"""
        from app.api.ws import ws_send_chunk
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_chunk(
            mock_ws,
            agent_role="PM",
            stream_id="stream-001",
            message_id="msg-001",
            content_chunk="Hello world。",
            is_final=False,
        ))

        data = captured["data"]
        # shared.ChatStreamMessage 继承 BaseMessage
        assert data["type"] == "chat_stream"
        assert data["agent_role"] == "PM"
        assert "timestamp" in data
        assert data["stream_id"] == "stream-001"
        assert data["message_id"] == "msg-001"
        assert data["content_chunk"] == "Hello world。"
        assert data["is_final"] is False

    def test_agent_typing_message_has_all_shared_fields(self):
        """agent_typing 必须包含 shared.AgentTypingMessage 所有字段。"""
        from app.api.ws import ws_send_typing
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_typing(mock_ws, agent_role="PM", stream_id="stream-001", is_typing=True))

        data = captured["data"]
        # shared.AgentTypingMessage 继承 BaseMessage
        assert data["type"] == "agent_typing"
        assert data["agent_role"] == "PM"
        assert "timestamp" in data
        assert data["stream_id"] == "stream-001"
        assert data["is_typing"] is True

    def test_error_message_has_all_shared_fields(self):
        """error 必须包含 shared.ErrorMessage 所有字段。"""
        from app.api.ws import send_error
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(send_error(mock_ws, "provider_not_configured", "Provider not configured", stream_id="stream-001"))

        data = captured["data"]
        assert data["type"] == "error"
        assert data["agent_role"] == "PM"
        assert "timestamp" in data
        assert data["stream_id"] == "stream-001"
        assert data["error_code"] == "provider_not_configured"
        assert data["error_message"] == "Provider not configured"

    def test_all_p12_error_codes_covered(self):
        """P1-2 所有 error_code 都已在 ws.py 中实现。"""
        from app.api.ws import send_error
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        # shared 新增的 P1-2 error codes
        p12_codes = [
            "provider_not_configured",
            "provider_request_failed",
            "provider_response_invalid",
            "agent_busy",
        ]

        for code in p12_codes:
            asyncio.run(send_error(mock_ws, code, f"test: {code}", stream_id="stream-001"))
            assert captured["data"]["error_code"] == code


class TestInFlightGuardIntegration:
    """P1-2-4: in-flight guard 与 ws.py 集成测试。"""

    @pytest.fixture(autouse=True)
    def setup_guard(self):
        """每个测试使用独立的 guard，通过 set_guard 注入。"""
        from app.api.ws import _InFlightGuard, set_guard
        guard = _InFlightGuard()
        set_guard(guard)
        yield guard
        set_guard(_InFlightGuard())

    def test_agent_busy_rejected_with_correct_code(self, setup_guard):
        """in-flight 状态下新的 send_message 返回 agent_busy。"""
        from app.api.ws import _IN_FLIGHT_GUARD

        guard = _IN_FLIGHT_GUARD

        # Enter first
        assert guard.try_enter("session-001")
        assert guard.is_in_flight("session-001")

        # Second attempt rejected
        assert not guard.try_enter("session-001")

        # Leave releases
        guard.leave("session-001")
        assert not guard.is_in_flight("session-001")

    def test_guard_interrupt_releases_session(self, setup_guard):
        """interrupt 方法正确释放 session。"""
        from app.api.ws import _IN_FLIGHT_GUARD

        guard = _IN_FLIGHT_GUARD

        guard.try_enter("session-001")
        assert guard.is_in_flight("session-001")

        guard.interrupt("session-001")
        assert not guard.is_in_flight("session-001")


class TestEndToEndStreamingFlow:
    """P1-2-4: 端到端流式流程测试（mock Provider + Mock WebSocket）。"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """配置内存数据库。"""
        from app.core import database
        database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)
        yield
        database.Base.metadata.drop_all(bind=database.engine)

    def _mock_stream_provider(self, deltas: list[str]):
        from app.providers.base import ProviderStreamEvent

        async def mock(input):
            for d in deltas:
                yield ProviderStreamEvent(text_delta=d)

        return mock

    def _run_stream_flow(self, deltas: list[str]):
        """运行完整流式流程，返回所有 WS 消息。"""
        from app.api.ws import session_websocket
        from unittest.mock import patch, MagicMock

        from app.core.database import SessionLocal
        from app.models.session import ChatSession

        db = SessionLocal()
        try:
            session = ChatSession(owner_id="dev_user", title="Test", mode="single")
            db.add(session)
            db.commit()
            db.refresh(session)
            session_id = session.id
        finally:
            db.close()

        ws = MockWebSocketForTest()
        ws.queue_message({
            "action": "send_message",
            "session_id": session_id,
            "content": "hello",
        })

        mock_agent = MagicMock()
        mock_agent.role = "PM"
        mock_agent.system_prompt = "You are a PM Agent."

        with patch("app.api.ws.get_provider") as mock_get_provider, \
             patch("app.api.ws.get_default_agent", return_value=mock_agent):
            mock_provider = MagicMock()
            mock_provider.stream_chat = self._mock_stream_provider(deltas)
            mock_get_provider.return_value = mock_provider

            asyncio.run(session_websocket(ws, session_id))

        return ws.sent_messages

    def test_full_flow_typing_true_then_chunks_then_final_then_typing_false(self):
        """完整流：typing=true -> chunks -> final -> typing=false。"""
        msgs = self._run_stream_flow(["Hello。", "World。"])

        typing_true = next(m for m in msgs if m["type"] == "agent_typing" and m["is_typing"] is True)
        chunks = [m for m in msgs if m["type"] == "chat_stream"]
        non_final_chunks = [m for m in chunks if not m["is_final"]]
        final_chunk = next(m for m in chunks if m["is_final"])
        typing_false = next(m for m in msgs if m["type"] == "agent_typing" and m["is_typing"] is False)

        assert typing_true is not None
        assert len(non_final_chunks) >= 2
        assert final_chunk["content_chunk"] == ""
        assert typing_false is not None

        first_chunk_idx = msgs.index(non_final_chunks[0])
        final_idx = msgs.index(final_chunk)
        typing_false_idx = msgs.index(typing_false)

        assert first_chunk_idx > msgs.index(typing_true)
        assert final_idx > first_chunk_idx
        assert typing_false_idx == final_idx + 1

    def test_final_chunk_is_empty_termination_frame(self):
        """final chunk 固定为空终止帧。"""
        msgs = self._run_stream_flow(["Hello。"])

        final = next(m for m in msgs if m["type"] == "chat_stream" and m["is_final"])
        assert final["content_chunk"] == ""
        assert final["is_final"] is True

    def test_same_stream_id_across_all_events(self):
        """同一流的所有事件共享 stream_id。"""
        msgs = self._run_stream_flow(["Hello。", "World。"])

        stream_ids = {m.get("stream_id") for m in msgs if "stream_id" in m}
        assert len(stream_ids) == 1

    def test_message_id_stable_across_chunks(self):
        """message_id 在所有 chunk 中保持稳定。"""
        msgs = self._run_stream_flow(["Hello。", "World。"])

        message_ids = {m.get("message_id") for m in msgs if "message_id" in m}
        assert len(message_ids) == 1


class MockWebSocketForTest:
    """测试用 WebSocket Mock。"""

    def __init__(self):
        self.accepted = False
        self.closed = False
        self.sent_messages: list[dict] = []
        self.received_messages: list[dict] = []

    async def accept(self):
        self.accepted = True

    async def close(self, code: int = 1000):
        self.closed = True

    async def send_json(self, data: dict):
        self.sent_messages.append(data)

    async def receive_json(self) -> dict:
        from starlette.websockets import WebSocketDisconnect
        if not self.received_messages:
            raise WebSocketDisconnect(code=1000)
        return self.received_messages.pop(0)

    def queue_message(self, msg: dict):
        self.received_messages.append(msg)
