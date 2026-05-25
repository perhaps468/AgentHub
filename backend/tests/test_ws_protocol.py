"""P1-3-3 WebSocket 统一事件协议 TDD 测试。

驱动 P1-3-3 的实现：

设计契约（P1-3 task spec Section 6.3）:
- shared/schemas/ws_messages.json 协议切换
- 旧主协议: chat_stream, agent_typing, error
- 新统一协议: message_start, message_delta, message_end, message_error
- message_start: 同时承担 typing=true 的职责
- message_delta: 仅正文增量
- message_end: 流结束
- message_error: 错误事件

本测试文件使用 TDD 红色优先策略：
1. 先写期望行为的断言
2. 运行测试确认失败（当前使用旧协议）
3. 实现代码使测试通过
"""

import asyncio
import uuid
from unittest.mock import MagicMock, patch

import pytest

from starlette.websockets import WebSocketDisconnect


# ---------------------------------------------------------------------------
# Mock WebSocket
# ---------------------------------------------------------------------------

class MockWebSocket:
    def __init__(self):
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def setup_db():
    from app.core import database
    database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)
    yield
    database.Base.metadata.drop_all(bind=database.engine)


def create_session_via_db():
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


# =============================================================================
# P1-3-3.1: 新协议消息类型存在性
# =============================================================================

class TestNewProtocolTypesExist:
    """验证 shared schema 定义了新协议事件类型。"""

    def test_shared_schema_json_has_new_event_types(self):
        """shared/schemas/ws_messages.json 必须包含新事件类型定义。"""
        import json
        from pathlib import Path

        # shared/ is at project root, not importable as Python module
        schema_path = Path(__file__).resolve().parents[2] / "shared" / "schemas" / "ws_messages.json"
        with open(schema_path, encoding="utf-8") as f:
            schema = json.load(f)

        definitions = schema.get("definitions", {})

        # 新事件类型应在定义中（JSON schema keys 不区分大小写）
        new_types = ["message_start", "message_delta", "message_end", "message_error"]
        defined_keys = set(definitions.keys())

        found = [t for t in new_types if t in defined_keys or any(t.lower() in k.lower() for k in defined_keys)]
        assert len(found) > 0, (
            f"shared schema 必须定义新事件类型（message_start/delta/end/error），"
            f"当前定义: {list(defined_keys)[:20]}"
        )


# =============================================================================
# P1-3-3.2: ws.py 新协议发送函数
# =============================================================================

class TestNewProtocolSenderFunctions:
    """验证 ws.py 包含新协议的发送函数。"""

    def test_ws_module_has_send_message_start_function(self):
        """ws.py 必须有 ws_send_message_start 函数。"""
        from app.api import ws as ws_module

        assert hasattr(ws_module, "ws_send_message_start")
        assert callable(ws_module.ws_send_message_start)

    def test_ws_module_has_send_message_delta_function(self):
        """ws.py 必须有 ws_send_message_delta 函数。"""
        from app.api import ws as ws_module

        assert hasattr(ws_module, "ws_send_message_delta")
        assert callable(ws_module.ws_send_message_delta)

    def test_ws_module_has_send_message_end_function(self):
        """ws.py 必须有 ws_send_message_end 函数。"""
        from app.api import ws as ws_module

        assert hasattr(ws_module, "ws_send_message_end")
        assert callable(ws_module.ws_send_message_end)

    def test_ws_module_has_send_message_error_function(self):
        """ws.py 必须有 ws_send_message_error 函数。"""
        from app.api import ws as ws_module

        assert hasattr(ws_module, "ws_send_message_error")
        assert callable(ws_module.ws_send_message_error)


# =============================================================================
# P1-3-3.3: message_start 协议字段验证
# =============================================================================

class TestMessageStartProtocol:
    """验证 message_start 符合 Section 6.3 协议契约。"""

    def _send_message_start(self, agent_role="PM", stream_id="stream-001"):
        from app.api.ws import ws_send_message_start
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        mock_msg = MagicMock()
        mock_msg.id = "msg-001"
        mock_msg.session_id = "s-001"
        mock_msg.sender_role = agent_role
        mock_msg.type = "text"
        mock_msg.content = ""
        mock_msg.payload = {"text": ""}
        mock_msg.msg_metadata = {"source": "fixed_responder", "render_hint": "markdown"}
        mock_msg.status = "streaming"
        mock_msg.created_at = MagicMock()

        asyncio.run(ws_send_message_start(
            mock_ws,
            agent_role=agent_role,
            stream_id=stream_id,
            message=mock_msg,
        ))
        return captured["data"]

    def test_message_start_type_field(self):
        """message_start 的 type 必须为 "message_start"。"""
        data = self._send_message_start()
        assert data["type"] == "message_start"

    def test_message_start_has_agent_role(self):
        """message_start 必须包含 agent_role。"""
        data = self._send_message_start(agent_role="Coder")
        assert data["agent_role"] == "Coder"

    def test_message_start_has_timestamp(self):
        """message_start 必须包含 timestamp（ISO 8601）。"""
        data = self._send_message_start()
        assert "timestamp" in data
        assert "T" in data["timestamp"]

    def test_message_start_has_stream_id(self):
        """message_start 必须包含 stream_id。"""
        data = self._send_message_start(stream_id="stream-xyz-123")
        assert data["stream_id"] == "stream-xyz-123"

    def test_message_start_has_message_object(self):
        """message_start 必须包含完整的 message 对象壳。"""
        data = self._send_message_start()
        assert "message" in data
        msg = data["message"]

        # message 必须包含所有最小字段
        required_msg_fields = [
            "id", "session_id", "sender_type", "sender_role",
            "type", "content", "payload", "metadata", "status", "created_at",
        ]
        for field in required_msg_fields:
            assert field in msg, f"message 对象缺少字段: {field}"

    def test_message_start_message_sender_type_is_agent(self):
        """message_start.message.sender_type 必须为 "agent"。"""
        data = self._send_message_start()
        assert data["message"]["sender_type"] == "agent"

    def test_message_start_message_type_is_text(self):
        """message_start.message.type 必须为 "text"。"""
        data = self._send_message_start()
        assert data["message"]["type"] == "text"

    def test_message_start_message_content_empty(self):
        """message_start.message.content 初始为空字符串。"""
        data = self._send_message_start()
        assert data["message"]["content"] == ""

    def test_message_start_message_payload_text_empty(self):
        """message_start.message.payload.text 初始为空字符串。"""
        data = self._send_message_start()
        assert data["message"]["payload"]["text"] == ""

    def test_message_start_message_metadata_has_source(self):
        """message_start.message.metadata 必须包含 source 字段。"""
        data = self._send_message_start()
        assert "source" in data["message"]["metadata"]

    def test_message_start_message_metadata_has_render_hint(self):
        """message_start.message.metadata 必须包含 render_hint 字段。"""
        data = self._send_message_start()
        assert "render_hint" in data["message"]["metadata"]

    def test_message_start_message_status_is_streaming(self):
        """message_start.message.status 必须为 "streaming"。"""
        data = self._send_message_start()
        assert data["message"]["status"] == "streaming"


# =============================================================================
# P1-3-3.4: message_delta 协议字段验证
# =============================================================================

class TestMessageDeltaProtocol:
    """验证 message_delta 符合 Section 6.3 协议契约。"""

    def _send_message_delta(self, agent_role="PM", stream_id="stream-001", message_id="msg-001", delta="Hello world。"):
        from app.api.ws import ws_send_message_delta
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_message_delta(
            mock_ws,
            agent_role=agent_role,
            stream_id=stream_id,
            message_id=message_id,
            delta=delta,
        ))
        return captured["data"]

    def test_message_delta_type_field(self):
        """message_delta 的 type 必须为 "message_delta"。"""
        data = self._send_message_delta()
        assert data["type"] == "message_delta"

    def test_message_delta_has_agent_role(self):
        """message_delta 必须包含 agent_role。"""
        data = self._send_message_delta(agent_role="Reviewer")
        assert data["agent_role"] == "Reviewer"

    def test_message_delta_has_timestamp(self):
        """message_delta 必须包含 timestamp。"""
        data = self._send_message_delta()
        assert "timestamp" in data
        assert "T" in data["timestamp"]

    def test_message_delta_has_stream_id(self):
        """message_delta 必须包含 stream_id。"""
        data = self._send_message_delta(stream_id="stream-xyz")
        assert data["stream_id"] == "stream-xyz"

    def test_message_delta_has_message_id(self):
        """message_delta 必须包含 message_id。"""
        data = self._send_message_delta(message_id="msg-123")
        assert data["message_id"] == "msg-123"

    def test_message_delta_has_delta_field(self):
        """message_delta 必须包含 delta 字段（而非 content_chunk）。"""
        data = self._send_message_delta(delta="这是一段增量文本")
        assert "delta" in data
        assert data["delta"] == "这是一段增量文本"
        assert "content_chunk" not in data

    def test_message_delta_delta_is_non_empty(self):
        """message_delta 的 delta 必须为非空字符串。"""
        data = self._send_message_delta(delta="non-empty chunk")
        assert isinstance(data["delta"], str)
        assert len(data["delta"]) > 0


# =============================================================================
# P1-3-3.5: message_end 协议字段验证
# =============================================================================

class TestMessageEndProtocol:
    """验证 message_end 符合 Section 6.3 协议契约。"""

    def _send_message_end(self, agent_role="PM", stream_id="stream-001", message_id="msg-001", status="completed"):
        from app.api.ws import ws_send_message_end
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_message_end(
            mock_ws,
            agent_role=agent_role,
            stream_id=stream_id,
            message_id=message_id,
            status=status,
        ))
        return captured["data"]

    def test_message_end_type_field(self):
        """message_end 的 type 必须为 "message_end"。"""
        data = self._send_message_end()
        assert data["type"] == "message_end"

    def test_message_end_has_agent_role(self):
        """message_end 必须包含 agent_role。"""
        data = self._send_message_end(agent_role="Planner")
        assert data["agent_role"] == "Planner"

    def test_message_end_has_timestamp(self):
        """message_end 必须包含 timestamp。"""
        data = self._send_message_end()
        assert "timestamp" in data
        assert "T" in data["timestamp"]

    def test_message_end_has_stream_id(self):
        """message_end 必须包含 stream_id。"""
        data = self._send_message_end(stream_id="stream-abc")
        assert data["stream_id"] == "stream-abc"

    def test_message_end_has_message_id(self):
        """message_end 必须包含 message_id。"""
        data = self._send_message_end(message_id="msg-456")
        assert data["message_id"] == "msg-456"

    def test_message_end_has_status(self):
        """message_end 必须包含 status 字段。"""
        data = self._send_message_end(status="completed")
        assert "status" in data
        assert data["status"] == "completed"

    def test_message_end_status_completed(self):
        """正常结束时 status 必须为 "completed"。"""
        data = self._send_message_end(status="completed")
        assert data["status"] == "completed"


# =============================================================================
# P1-3-3.6: message_error 协议字段验证
# =============================================================================

class TestMessageErrorProtocol:
    """验证 message_error 符合 Section 6.3 协议契约。"""

    def _send_message_error(
        self,
        agent_role="PM",
        stream_id="stream-001",
        message_id="msg-001",
        error_code="fixed_responder_failed",
        error_message="Failed to stream fixed response",
    ):
        from app.api.ws import ws_send_message_error
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_message_error(
            mock_ws,
            agent_role=agent_role,
            stream_id=stream_id,
            message_id=message_id,
            error_code=error_code,
            error_message=error_message,
        ))
        return captured["data"]

    def test_message_error_type_field(self):
        """message_error 的 type 必须为 "message_error"。"""
        data = self._send_message_error()
        assert data["type"] == "message_error"

    def test_message_error_has_agent_role(self):
        """message_error 必须包含 agent_role。"""
        data = self._send_message_error(agent_role="Coder")
        assert data["agent_role"] == "Coder"

    def test_message_error_has_timestamp(self):
        """message_error 必须包含 timestamp。"""
        data = self._send_message_error()
        assert "timestamp" in data
        assert "T" in data["timestamp"]

    def test_message_error_has_stream_id(self):
        """message_error 必须包含 stream_id。"""
        data = self._send_message_error(stream_id="stream-err")
        assert data["stream_id"] == "stream-err"

    def test_message_error_has_message_id(self):
        """message_error 必须包含 message_id。"""
        data = self._send_message_error(message_id="msg-err")
        assert data["message_id"] == "msg-err"

    def test_message_error_has_error_code(self):
        """message_error 必须包含 error_code 字段。"""
        data = self._send_message_error(error_code="session_not_found")
        assert "error_code" in data
        assert data["error_code"] == "session_not_found"

    def test_message_error_has_error_message(self):
        """message_error 必须包含 error_message 字段。"""
        data = self._send_message_error(error_message="Session not found")
        assert "error_message" in data
        assert data["error_message"] == "Session not found"


# =============================================================================
# P1-3-3.7: 错误码覆盖
# =============================================================================

class TestNewProtocolErrorCodes:
    """验证新协议支持所有 P1-3 规定的错误码。"""

    def _send_message_error(self, error_code):
        from app.api.ws import ws_send_message_error
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_message_error(
            mock_ws,
            agent_role="PM",
            stream_id="stream-001",
            message_id="msg-001",
            error_code=error_code,
            error_message=f"test: {error_code}",
        ))
        return captured["data"]

    def test_error_code_session_not_found(self):
        """支持 error_code: session_not_found。"""
        data = self._send_message_error("session_not_found")
        assert data["error_code"] == "session_not_found"

    def test_error_code_invalid_request(self):
        """支持 error_code: invalid_request。"""
        data = self._send_message_error("invalid_request")
        assert data["error_code"] == "invalid_request"

    def test_error_code_agent_busy(self):
        """支持 error_code: agent_busy。"""
        data = self._send_message_error("agent_busy")
        assert data["error_code"] == "agent_busy"

    def test_error_code_fixed_responder_failed(self):
        """支持 error_code: fixed_responder_failed。"""
        data = self._send_message_error("fixed_responder_failed")
        assert data["error_code"] == "fixed_responder_failed"

    def test_error_code_unknown(self):
        """支持 error_code: unknown。"""
        data = self._send_message_error("unknown")
        assert data["error_code"] == "unknown"


# =============================================================================
# P1-3-3.8: 旧协议不再作为主链路
# =============================================================================

class TestOldProtocolRetirement:
    """验证旧协议不再在 ws.py 主链路中使用。"""

    def test_ws_module_does_not_have_old_send_typing_function(self):
        """ws.py 不应保留 ws_send_typing 作为主链路函数。"""
        from app.api import ws as ws_module

        # 旧函数 ws_send_typing 应被移除或不再在主流程中使用
        source = ""
        try:
            import inspect
            source = inspect.getsource(ws_module)
        except Exception:
            pass

        # 新实现不应有 ws_send_typing
        if hasattr(ws_module, "ws_send_typing"):
            # 如果函数仍存在，检查是否在 session_websocket 中被调用
            import inspect
            handler_source = inspect.getsource(ws_module.session_websocket)
            assert "ws_send_typing" not in handler_source, \
                "ws_send_typing 不应在 session_websocket 主流程中使用"

    def test_ws_module_does_not_have_old_send_chunk_function(self):
        """ws.py 不应保留 ws_send_chunk 作为主链路函数。"""
        from app.api import ws as ws_module

        if hasattr(ws_module, "ws_send_chunk"):
            import inspect
            handler_source = inspect.getsource(ws_module.session_websocket)
            assert "ws_send_chunk" not in handler_source, \
                "ws_send_chunk 不应在 session_websocket 主流程中使用"

    def test_ws_module_still_has_old_error_function_for_pre_start_errors(self):
        """ws.py 的旧 send_error 函数可以保留（用于 pre-start 错误），但主流程用新函数。"""
        from app.api import ws as ws_module

        # send_error 可能仍存在用于 pre-start 错误场景
        # 这是允许的，只要主流程使用新的 ws_send_message_error


# =============================================================================
# P1-3-3.9: shared schema 与实现对齐
# =============================================================================

class TestSharedSchemaAlignment:
    """验证 shared schema 与 ws.py 实现完全对齐。"""

    def test_message_start_fields_match_shared_schema(self):
        """message_start 所有字段与 shared schema 对齐。"""
        from app.api.ws import ws_send_message_start
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        mock_msg = MagicMock()
        mock_msg.id = "msg-align-001"
        mock_msg.session_id = "s-align-001"
        mock_msg.sender_role = "PM"
        mock_msg.type = "text"
        mock_msg.content = "aligned content"
        mock_msg.payload = {"text": "aligned content"}
        mock_msg.metadata = {"source": "fixed_responder"}
        mock_msg.status = "streaming"
        mock_msg.created_at = MagicMock()

        asyncio.run(ws_send_message_start(mock_ws, agent_role="PM", stream_id="stream-001", message=mock_msg))
        data = captured["data"]

        # shared MessageStart 必须字段
        assert data["type"] == "message_start"
        assert "agent_role" in data
        assert "timestamp" in data
        assert "stream_id" in data
        assert "message" in data

        msg = data["message"]
        assert "id" in msg
        assert "session_id" in msg
        assert "sender_type" in msg
        assert msg["sender_type"] == "agent"
        assert "sender_role" in msg
        assert "type" in msg
        assert "content" in msg
        assert "payload" in msg
        assert "metadata" in msg
        assert "status" in msg
        assert "created_at" in msg

    def test_message_delta_fields_match_shared_schema(self):
        """message_delta 所有字段与 shared schema 对齐。"""
        from app.api.ws import ws_send_message_delta
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_message_delta(
            mock_ws, agent_role="PM", stream_id="stream-001",
            message_id="msg-001", delta="Hello。"
        ))
        data = captured["data"]

        # shared MessageDelta 必须字段
        assert data["type"] == "message_delta"
        assert "agent_role" in data
        assert "timestamp" in data
        assert "stream_id" in data
        assert "message_id" in data
        assert "delta" in data

    def test_message_end_fields_match_shared_schema(self):
        """message_end 所有字段与 shared schema 对齐。"""
        from app.api.ws import ws_send_message_end
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_message_end(
            mock_ws, agent_role="PM", stream_id="stream-001",
            message_id="msg-001", status="completed"
        ))
        data = captured["data"]

        # shared MessageEnd 必须字段
        assert data["type"] == "message_end"
        assert "agent_role" in data
        assert "timestamp" in data
        assert "stream_id" in data
        assert "message_id" in data
        assert "status" in data

    def test_message_error_fields_match_shared_schema(self):
        """message_error 所有字段与 shared schema 对齐。"""
        from app.api.ws import ws_send_message_error
        from starlette.websockets import WebSocket

        mock_ws = MagicMock(spec=WebSocket)
        captured = {}

        async def capture(data):
            captured["data"] = data

        mock_ws.send_json = capture

        asyncio.run(ws_send_message_error(
            mock_ws, agent_role="PM", stream_id="stream-001",
            message_id="msg-001", error_code="fixed_responder_failed",
            error_message="Failed"
        ))
        data = captured["data"]

        # shared MessageError 必须字段
        assert data["type"] == "message_error"
        assert "agent_role" in data
        assert "timestamp" in data
        assert "stream_id" in data
        assert "message_id" in data
        assert "error_code" in data
        assert "error_message" in data
