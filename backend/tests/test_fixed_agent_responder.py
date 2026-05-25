"""P1-3-2 FixedAgentResponder TDD 测试。

本测试文件驱动 FixedAgentResponder 的实现：

设计契约（P1-3 task spec Section 6.4）:
- 输入: session_id, user_message, agent_role, db, stream_id
- 输出: 异步生成 message_start -> message_delta* -> message_end 或 message_error
- 行为:
  1. 根据固定模板生成 deterministic 文本
  2. 文本切分为若干固定片段，按顺序输出
  3. 默认输出来源写入 metadata.source = "fixed_responder"
  4. 不调用真实 provider，不读取真实模型配置，不消费历史上下文

本测试文件使用 TDD 红色优先策略：
1. 先写期望行为的断言（describe it ... expect）
2. 运行测试确认失败（当前模块不存在）
3. 实现代码使测试通过
"""

import asyncio
import uuid
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# 辅助: Mock WebSocket（复用于 ws.py test pattern）
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
        from starlette.websockets import WebSocketDisconnect
        if not self.received_messages:
            raise WebSocketDisconnect(code=1000)
        return self.received_messages.pop(0)

    def queue_message(self, msg: dict) -> None:
        self.received_messages.append(msg)


# ---------------------------------------------------------------------------
# 辅助: 内存数据库
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


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder 模块存在性
# ---------------------------------------------------------------------------

class TestFixedAgentResponderModule:
    """TDD Step 1: 验证 FixedAgentResponder 模块存在且可导入。"""

    def test_module_can_be_imported(self):
        """FixedAgentResponder 必须可从 app.services.fixed_agent_responder 导入。"""
        from app.services.fixed_agent_responder import FixedAgentResponder  # noqa: F401

    def test_class_exists(self):
        """FixedAgentResponder 类必须存在。"""
        from app.services.fixed_agent_responder import FixedAgentResponder
        assert FixedAgentResponder is not None


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder 初始化参数
# ---------------------------------------------------------------------------

class TestFixedAgentResponderInit:
    """TDD Step 2: 验证 FixedAgentResponder 构造函数接受正确参数。"""

    def test_constructor_requires_session_id(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            assert responder is not None
            assert hasattr(responder, "session_id")
            assert responder.session_id == session_id
        finally:
            db.close()

    def test_constructor_stores_user_message(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="What is the weather?",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            assert hasattr(responder, "user_message")
            assert responder.user_message == "What is the weather?"
        finally:
            db.close()

    def test_constructor_stores_agent_role(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="Coder",
                db=db,
                stream_id=stream_id,
            )

            assert hasattr(responder, "agent_role")
            assert responder.agent_role == "Coder"
        finally:
            db.close()

    def test_constructor_stores_stream_id(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            assert hasattr(responder, "stream_id")
            assert responder.stream_id == stream_id
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder.stream_events() 方法存在性
# ---------------------------------------------------------------------------

class TestFixedAgentResponderStreamEvents:
    """TDD Step 3: 验证 stream_events() 方法存在且为 async generator。"""

    def test_stream_events_method_exists(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            assert hasattr(responder, "stream_events")
            assert callable(responder.stream_events)
        finally:
            db.close()

    def test_stream_events_is_async_generator(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            import inspect
            gen = responder.stream_events()
            assert asyncio.iscoroutine(gen) or inspect.isasyncgen(gen)
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder 输出协议 - message_start
# ---------------------------------------------------------------------------

class TestFixedAgentResponderMessageStart:
    """TDD Step 4: 验证 stream_events() 输出第一个事件为 message_start。"""

    def test_first_event_is_message_start(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())

            assert len(events) > 0
            first_event = events[0]
            assert hasattr(first_event, "type")
            assert first_event.type == "message_start"
        finally:
            db.close()

    def test_message_start_has_agent_role(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="Coder",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_start = events[0]

            assert hasattr(msg_start, "agent_role")
            assert msg_start.agent_role == "Coder"
        finally:
            db.close()

    def test_message_start_has_timestamp(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_start = events[0]

            assert hasattr(msg_start, "timestamp")
            assert isinstance(msg_start.timestamp, str)
            assert "T" in msg_start.timestamp  # ISO format
        finally:
            db.close()

    def test_message_start_has_stream_id(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_start = events[0]

            assert hasattr(msg_start, "stream_id")
            assert msg_start.stream_id == stream_id
        finally:
            db.close()

    def test_message_start_contains_full_message_object(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                    break  # Only consume first event (message_start), then stop
                return events

            events = asyncio.run(consume())
            msg_start = events[0]

            # message_start must contain full message shell (not just minimum fields)
            # Capture status immediately after message_start - before coroutine finishes
            initial_status = msg_start.message.status

            assert hasattr(msg_start, "message")
            msg = msg_start.message
            assert hasattr(msg, "id")
            assert hasattr(msg, "session_id")
            assert msg.session_id == session_id
            assert hasattr(msg, "sender_type")
            assert msg.sender_type == "agent"
            assert hasattr(msg, "sender_role")
            assert msg.sender_role == "PM"
            assert hasattr(msg, "type")
            assert msg.type == "text"
            assert hasattr(msg, "content")
            assert hasattr(msg, "payload")
            assert hasattr(msg, "metadata")
            assert hasattr(msg, "status")
            assert initial_status == "streaming", f"initial status should be streaming, got {initial_status}"
            assert hasattr(msg, "created_at")
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder 输出协议 - message_delta
# ---------------------------------------------------------------------------

class TestFixedAgentResponderMessageDelta:
    """TDD Step 5: 验证 stream_events() 输出中间事件为 message_delta。"""

    def test_deltas_follow_message_start(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            delta_events = [e for e in events if hasattr(e, "type") and e.type == "message_delta"]

            assert len(delta_events) > 0
            start_idx = next(i for i, e in enumerate(events) if hasattr(e, "type") and e.type == "message_start")
            first_delta_idx = next(i for i, e in enumerate(events) if hasattr(e, "type") and e.type == "message_delta")
            assert first_delta_idx > start_idx
        finally:
            db.close()

    def test_message_delta_has_delta_field(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            delta_events = [e for e in events if hasattr(e, "type") and e.type == "message_delta"]

            for delta in delta_events:
                assert hasattr(delta, "delta")
                assert isinstance(delta.delta, str)
                assert len(delta.delta) > 0
        finally:
            db.close()

    def test_message_delta_has_agent_role(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="Coder",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            delta_events = [e for e in events if hasattr(e, "type") and e.type == "message_delta"]

            for delta in delta_events:
                assert hasattr(delta, "agent_role")
                assert delta.agent_role == "Coder"
        finally:
            db.close()

    def test_message_delta_has_timestamp(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            delta_events = [e for e in events if hasattr(e, "type") and e.type == "message_delta"]

            for delta in delta_events:
                assert hasattr(delta, "timestamp")
                assert "T" in delta.timestamp
        finally:
            db.close()

    def test_message_delta_has_stream_id(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            delta_events = [e for e in events if hasattr(e, "type") and e.type == "message_delta"]

            for delta in delta_events:
                assert hasattr(delta, "stream_id")
                assert delta.stream_id == stream_id
        finally:
            db.close()

    def test_message_delta_has_message_id(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())

            # 从 message_start 获取 message_id
            msg_start = events[0]
            assert hasattr(msg_start, "message")
            expected_msg_id = msg_start.message.id

            delta_events = [e for e in events if hasattr(e, "type") and e.type == "message_delta"]
            for delta in delta_events:
                assert hasattr(delta, "message_id")
                assert delta.message_id == expected_msg_id
        finally:
            db.close()

    def test_deltas_produce_complete_text_when_concatenated(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            delta_events = [e for e in events if hasattr(e, "type") and e.type == "message_delta"]

            # 所有 delta 连接后应产生有效文本
            full_text = "".join(e.delta for e in delta_events)
            assert isinstance(full_text, str)
            assert len(full_text) > 0
            assert "\x00" not in full_text  # 不应包含空字节
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder 输出协议 - message_end
# ---------------------------------------------------------------------------

class TestFixedAgentResponderMessageEnd:
    """TDD Step 6: 验证 stream_events() 输出最后一个事件为 message_end。"""

    def test_last_event_is_message_end(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            assert len(events) > 0
            last_event = events[-1]
            assert hasattr(last_event, "type")
            assert last_event.type == "message_end"
        finally:
            db.close()

    def test_message_end_has_agent_role(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="Reviewer",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_end = events[-1]

            assert hasattr(msg_end, "agent_role")
            assert msg_end.agent_role == "Reviewer"
        finally:
            db.close()

    def test_message_end_has_timestamp(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_end = events[-1]

            assert hasattr(msg_end, "timestamp")
            assert "T" in msg_end.timestamp
        finally:
            db.close()

    def test_message_end_has_stream_id(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_end = events[-1]

            assert hasattr(msg_end, "stream_id")
            assert msg_end.stream_id == stream_id
        finally:
            db.close()

    def test_message_end_has_message_id(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_start = events[0]
            expected_msg_id = msg_start.message.id
            msg_end = events[-1]

            assert hasattr(msg_end, "message_id")
            assert msg_end.message_id == expected_msg_id
        finally:
            db.close()

    def test_message_end_has_status(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_end = events[-1]

            assert hasattr(msg_end, "status")
            assert msg_end.status == "completed"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder 事件序列完整性
# ---------------------------------------------------------------------------

class TestFixedAgentResponderEventSequence:
    """TDD Step 7: 验证完整事件序列: message_start -> message_delta* -> message_end"""

    def test_full_event_sequence(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())

            event_types = [e.type for e in events]

            # 序列: message_start -> message_delta* -> message_end
            assert event_types[0] == "message_start"
            assert event_types[-1] == "message_end"

            delta_count = sum(1 for t in event_types if t == "message_delta")
            assert delta_count > 0

            start_count = sum(1 for t in event_types if t == "message_start")
            end_count = sum(1 for t in event_types if t == "message_end")
            assert start_count == 1
            assert end_count == 1
        finally:
            db.close()

    def test_all_events_share_same_stream_id(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())

            stream_ids = {e.stream_id for e in events}
            assert len(stream_ids) == 1
            assert stream_ids.pop() == stream_id
        finally:
            db.close()

    def test_all_events_share_same_message_id(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())

            msg_start = events[0]
            expected_msg_id = msg_start.message.id

            # message_delta 和 message_end 都应该有 message_id
            delta_and_end = [e for e in events if hasattr(e, "type") and e.type in ("message_delta", "message_end")]
            for e in delta_and_end:
                assert hasattr(e, "message_id")
                assert e.message_id == expected_msg_id
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder 不调用真实 provider
# ---------------------------------------------------------------------------

class TestFixedAgentResponderNoRealProvider:
    """TDD Step 8: 验证 FixedAgentResponder 不调用真实 LLM provider。"""

    def test_does_not_import_or_call_qwen_provider(self, setup_db):
        """FixedAgentResponder 的实现不应导入或调用 QwenProvider / stream_chat。"""
        import inspect
        from app.services.fixed_agent_responder import FixedAgentResponder

        source = inspect.getsource(FixedAgentResponder)

        # 不应包含 provider 相关导入或调用
        assert "QwenProvider" not in source
        assert "get_provider" not in source
        assert "stream_chat" not in source
        assert "QWEN_API_KEY" not in source

    def test_does_not_import_or_call_openai_provider(self, setup_db):
        """不应导入或调用 OpenAI provider。"""
        import inspect
        from app.services.fixed_agent_responder import FixedAgentResponder

        source = inspect.getsource(FixedAgentResponder)

        assert "openai" not in source.lower()

    def test_uses_fixed_template_not_llm_call(self, setup_db):
        """响应内容应来自固定模板，而非 LLM 调用。"""
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder1 = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            stream_id2 = str(uuid.uuid4())
            responder2 = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id2,
            )

            async def consume(responder):
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events1 = asyncio.run(consume(responder1))
            events2 = asyncio.run(consume(responder2))

            # 相同输入应产生相同（或至少 deterministic 的）输出
            text1 = "".join(e.delta for e in events1 if hasattr(e, "type") and e.type == "message_delta")
            text2 = "".join(e.delta for e in events2 if hasattr(e, "type") and e.type == "message_delta")

            # 固定回复器应产生 deterministic 输出
            assert text1 == text2
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder metadata.source = "fixed_responder"
# ---------------------------------------------------------------------------

class TestFixedAgentResponderMetadataSource:
    """TDD Step 9: 验证 metadata.source = "fixed_responder"。"""

    def test_message_metadata_source_is_fixed_responder(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_start = events[0]

            assert hasattr(msg_start, "message")
            assert hasattr(msg_start.message, "msg_metadata")
            assert isinstance(msg_start.message.msg_metadata, dict)
            assert msg_start.message.msg_metadata.get("source") == "fixed_responder"
        finally:
            db.close()


# ---------------------------------------------------------------------------
# 测试: FixedAgentResponder text 类型 payload 最小结构
# ---------------------------------------------------------------------------

class TestFixedAgentResponderPayload:
    """TDD Step 10: 验证 text 类型消息的 payload 最小结构。"""

    def test_message_payload_contains_text(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_start = events[0]

            assert hasattr(msg_start.message, "payload")
            assert isinstance(msg_start.message.payload, dict)
            assert "text" in msg_start.message.payload
        finally:
            db.close()

    def test_message_type_is_text(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())
            msg_start = events[0]

            assert msg_start.message.type == "text"
        finally:
            db.close()

    def test_message_content_matches_payload_text(self, setup_db):
        from app.services.fixed_agent_responder import FixedAgentResponder
        from app.core.database import SessionLocal

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            stream_id = str(uuid.uuid4())

            responder = FixedAgentResponder(
                session_id=session_id,
                user_message="hello",
                agent_role="PM",
                db=db,
                stream_id=stream_id,
            )

            async def consume():
                events = []
                async for event in responder.stream_events():
                    events.append(event)
                return events

            events = asyncio.run(consume())

            # 收集所有 delta
            full_content = "".join(
                e.delta for e in events if hasattr(e, "type") and e.type == "message_delta"
            )

            # payload.text 应等于最终完整内容
            msg_start = events[0]
            assert msg_start.message.payload.get("text") == full_content
            assert msg_start.message.content == full_content
        finally:
            db.close()
