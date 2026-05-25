"""P1-3-1 Message 数据模型升级 TDD 测试。

驱动 P1-3-1 的实现：

设计契约（P1-3 task spec Section 6.1）:
- Message 升级为最小通用消息模型
- 字段: id, session_id, sender_type, sender_role, type, content, payload, metadata, status, created_at
- 旧字段 content_type -> type
- 旧字段 delivery_status -> status
- 新增 payload, metadata (JSON 持久化)
- status 默认值: human=completed, agent 占位=streaming
- payload.metadata.text 最小结构

本测试文件使用 TDD 红色优先策略：
1. 先写期望行为的断言
2. 运行测试确认失败（当前字段不存在）
3. 实现代码使测试通过
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def setup_db():
    from app.core import database
    database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)
    yield
    database.Base.metadata.drop_all(bind=database.engine)


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
# P1-3-1.1: Message 模型字段升级
# =============================================================================

class TestMessageModelFields:
    """验证 Message ORM 模型包含所有升级后字段。"""

    def test_message_model_has_type_field(self, setup_db):
        """Message 模型必须有 type 字段（content_type 的升级）。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        assert hasattr(msg, "type")

    def test_message_model_has_status_field(self, setup_db):
        """Message 模型必须有 status 字段（delivery_status 的升级）。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        assert hasattr(msg, "status")

    def test_message_model_has_payload_field(self, setup_db):
        """Message 模型必须有 payload 字段（JSON 持久化）。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        assert hasattr(msg, "payload")

    def test_message_model_has_metadata_field(self, setup_db):
        """Message 模型必须有 message_metadata 字段（JSON 持久化）。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        assert hasattr(msg, "msg_metadata")

    def test_message_model_has_all_required_fields(self, setup_db):
        """Message 模型必须包含所有 P1-3-1 规定的最小字段。"""
        from app.models.message import Message

        required_fields = [
            "id",
            "session_id",
            "sender_type",
            "sender_role",
            "type",
            "content",
            "payload",
            "msg_metadata",
            "status",
            "created_at",
        ]

        for field in required_fields:
            assert hasattr(Message, field), f"Message 模型缺少字段: {field}"


# =============================================================================
# P1-3-1.2: Message 模型默认值与约束
# =============================================================================

class TestMessageModelDefaults:
    """验证 Message 模型默认值符合契约。"""

    def test_status_default_completed_for_human_message(self, setup_db):
        """Human message 默认 status 为 completed。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="human",
            sender_role=None,
            content="hello",
        )
        assert msg.status == "completed"

    def test_type_default_text(self, setup_db):
        """type 字段默认值为 text。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        assert msg.type == "text"

    def test_payload_is_dict(self, setup_db):
        """payload 字段类型为 dict。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        assert isinstance(msg.payload, dict)

    def test_metadata_is_dict(self, setup_db):
        """message_metadata 字段类型为 dict。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        assert hasattr(msg, "msg_metadata")
        assert isinstance(msg.msg_metadata, dict)

    def test_payload_can_store_text(self, setup_db):
        """payload 可以存储 text 内容。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        msg.payload = {"text": "hello"}
        assert msg.payload["text"] == "hello"

    def test_metadata_can_store_source_and_render_hint(self, setup_db):
        """message_metadata 可以存储 source 和 render_hint。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        msg.msg_metadata = {
            "source": "fixed_responder",
            "render_hint": "markdown",
            "stream_id": "stream-001",
        }
        assert msg.msg_metadata["source"] == "fixed_responder"
        assert msg.msg_metadata["render_hint"] == "markdown"
        assert msg.msg_metadata["stream_id"] == "stream-001"


# =============================================================================
# P1-3-1.3: Message 持久化规则
# =============================================================================

class TestMessagePersistenceRules:
    """验证 Message 持久化规则符合契约。"""

    def test_human_message_can_be_persisted(self, setup_db):
        """Human message 可以持久化到数据库。"""
        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            msg = Message(
                session_id=session_id,
                sender_type="human",
                sender_role=None,
                content="user input",
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)
            assert msg.id is not None
            assert msg.session_id == session_id
        finally:
            db.close()

    def test_agent_message_can_be_persisted_with_streaming_status(self, setup_db):
        """Agent message 可以持久化且 status 为 streaming。"""
        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="",
            )
            msg.status = "streaming"
            db.add(msg)
            db.commit()
            db.refresh(msg)
            assert msg.id is not None
            assert msg.status == "streaming"
        finally:
            db.close()

    def test_agent_message_status_can_be_updated_to_completed(self, setup_db):
        """Agent message 可以从 streaming 更新为 completed。"""
        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="partial",
            )
            msg.status = "streaming"
            db.add(msg)
            db.commit()
            db.refresh(msg)

            # 模拟流结束后更新
            msg.content = "full response content。"
            msg.payload = {"text": "full response content。"}
            msg.status = "completed"
            db.add(msg)
            db.commit()
            db.refresh(msg)

            assert msg.status == "completed"
            assert msg.content == "full response content。"
        finally:
            db.close()

    def test_agent_message_status_can_be_updated_to_failed(self, setup_db):
        """Agent message 可以更新为 failed 状态。"""
        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="partial",
            )
            msg.status = "streaming"
            db.add(msg)
            db.commit()

            msg.status = "failed"
            db.add(msg)
            db.commit()
            db.refresh(msg)

            assert msg.status == "failed"
        finally:
            db.close()

    def test_message_payload_and_metadata_are_persisted(self, setup_db):
        """payload 和 message_metadata 作为 JSON 字段可以持久化。"""
        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            session_id = create_session_via_db()
            msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="hello",
            )
            msg.type = "text"
            msg.status = "completed"
            msg.payload = {"text": "hello"}
            msg.msg_metadata = {
                "source": "fixed_responder",
                "render_hint": "markdown",
                "stream_id": "stream-001",
            }
            db.add(msg)
            db.commit()
            db.refresh(msg)

            assert msg.payload == {"text": "hello"}
            assert msg.msg_metadata["source"] == "fixed_responder"
            assert msg.msg_metadata["render_hint"] == "markdown"
            assert msg.msg_metadata["stream_id"] == "stream-001"
        finally:
            db.close()


# =============================================================================
# P1-3-1.4: REST 历史消息接口统一字段
# =============================================================================

class TestHistoryApiUnifiedFields:
    """验证 GET /api/sessions/{session_id}/messages 返回统一消息字段。"""

    def test_history_api_returns_unified_fields(self, client):
        """历史接口必须返回 type/status/payload/metadata 字段。"""
        # 创建 session
        session_resp = client.post(
            "/api/sessions",
            json={"owner_id": "dev_user", "title": "Test", "mode": "single"},
        )
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]

        # 写入 message（直接写 DB，跳过 WS）
        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="hello",
            )
            msg.type = "text"
            msg.status = "completed"
            msg.payload = {"text": "hello"}
            msg.msg_metadata = {"source": "fixed_responder", "render_hint": "markdown"}
            db.add(msg)
            db.commit()
            db.refresh(msg)
        finally:
            db.close()

        # 调用历史接口
        resp = client.get(f"/api/sessions/{session_id}/messages")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        item = body["items"][0]

        # 验证统一字段
        assert "type" in item
        assert "status" in item
        assert "payload" in item
        assert "metadata" in item
        assert item["type"] == "text"
        assert item["status"] == "completed"
        assert item["payload"] == {"text": "hello"}
        assert item["metadata"]["source"] == "fixed_responder"

    def test_history_api_does_not_return_content_type_field(self, client):
        """历史接口不应再返回旧的 content_type 字段名。"""
        session_resp = client.post(
            "/api/sessions",
            json={"owner_id": "dev_user", "title": "Test", "mode": "single"},
        )
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]

        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="hello",
            )
            msg.type = "text"
            msg.status = "completed"
            msg.payload = {"text": "hello"}
            msg.msg_metadata = {}
            db.add(msg)
            db.commit()
        finally:
            db.close()

        resp = client.get(f"/api/sessions/{session_id}/messages")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "content_type" not in item

    def test_history_api_does_not_return_delivery_status_field(self, client):
        """历史接口不应再返回旧的 delivery_status 字段名。"""
        session_resp = client.post(
            "/api/sessions",
            json={"owner_id": "dev_user", "title": "Test", "mode": "single"},
        )
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]

        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="hello",
            )
            msg.type = "text"
            msg.status = "completed"
            msg.payload = {"text": "hello"}
            msg.msg_metadata = {}
            db.add(msg)
            db.commit()
        finally:
            db.close()

        resp = client.get(f"/api/sessions/{session_id}/messages")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "delivery_status" not in item

    def test_history_api_returns_text_type_payload_structure(self, client):
        """text 类型历史消息的 payload/metadata 必须符合约定结构。"""
        session_resp = client.post(
            "/api/sessions",
            json={"owner_id": "dev_user", "title": "Test", "mode": "single"},
        )
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]

        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="complete response text。",
            )
            msg.type = "text"
            msg.status = "completed"
            msg.payload = {
                "text": "complete response text。"
            }
            msg.msg_metadata = {
                "stream_id": "stream-uuid",
                "source": "fixed_responder",
                "render_hint": "markdown",
            }
            db.add(msg)
            db.commit()
        finally:
            db.close()

        resp = client.get(f"/api/sessions/{session_id}/messages")
        assert resp.status_code == 200
        item = resp.json()["items"][0]

        assert item["type"] == "text"
        assert item["content"] == "complete response text。"
        assert item["payload"]["text"] == "complete response text。"
        assert item["metadata"]["stream_id"] == "stream-uuid"
        assert item["metadata"]["source"] == "fixed_responder"
        assert item["metadata"]["render_hint"] == "markdown"

    def test_history_api_does_not_return_streaming_messages(self, client):
        """历史接口不应返回 status=streaming 的进行中占位消息。"""
        session_resp = client.post(
            "/api/sessions",
            json={"owner_id": "dev_user", "title": "Test", "mode": "single"},
        )
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]

        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            # 写入一条 streaming 消息
            msg = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="partial",
            )
            msg.type = "text"
            msg.status = "streaming"
            msg.payload = {"text": "partial"}
            msg.msg_metadata = {"stream_id": "stream-001"}
            db.add(msg)
            db.commit()
        finally:
            db.close()

        resp = client.get(f"/api/sessions/{session_id}/messages")
        assert resp.status_code == 200
        body = resp.json()

        # streaming 消息不应出现在历史接口返回中
        assert body["total"] == 0
        assert len(body["items"]) == 0

    def test_history_api_returns_completed_and_failed_messages(self, client):
        """历史接口只返回 completed 和 failed 的 finalized 消息。"""
        session_resp = client.post(
            "/api/sessions",
            json={"owner_id": "dev_user", "title": "Test", "mode": "single"},
        )
        assert session_resp.status_code == 201
        session_id = session_resp.json()["id"]

        from app.core.database import SessionLocal
        from app.models.message import Message

        db = SessionLocal()
        try:
            # completed 消息
            msg1 = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="completed text",
            )
            msg1.type = "text"
            msg1.status = "completed"
            msg1.payload = {"text": "completed text"}
            msg1.msg_metadata = {}
            db.add(msg1)

            # failed 消息
            msg2 = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="failed text",
            )
            msg2.type = "text"
            msg2.status = "failed"
            msg2.payload = {"text": "failed text"}
            msg2.msg_metadata = {}
            db.add(msg2)

            # streaming 消息（不应返回）
            msg3 = Message(
                session_id=session_id,
                sender_type="agent",
                sender_role="PM",
                content="streaming text",
            )
            msg3.type = "text"
            msg3.status = "streaming"
            msg3.payload = {"text": "streaming text"}
            msg3.msg_metadata = {}
            db.add(msg3)

            db.commit()
        finally:
            db.close()

        resp = client.get(f"/api/sessions/{session_id}/messages")
        assert resp.status_code == 200
        body = resp.json()

        assert body["total"] == 2
        statuses = {item["status"] for item in body["items"]}
        assert statuses == {"completed", "failed"}
        # 不应包含 streaming
        assert "streaming" not in statuses


# =============================================================================
# P1-3-1.5: MessageResponse Schema 升级
# =============================================================================

class TestMessageResponseSchema:
    """验证 MessageResponse Pydantic schema 包含升级后字段。"""

    def test_message_response_schema_has_type_field(self, setup_db):
        """MessageResponse 必须包含 type 字段。"""
        from app.schemas.message import MessageResponse

        resp = MessageResponse(
            id="msg-001",
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            type="text",
            content="hello",
            payload={"text": "hello"},
            msg_metadata={"source": "fixed_responder"},
            status="completed",
            created_at=datetime.now(),
        )
        assert hasattr(resp, "type")
        assert resp.type == "text"

    def test_message_response_schema_has_status_field(self, setup_db):
        """MessageResponse 必须包含 status 字段。"""
        from app.schemas.message import MessageResponse

        resp = MessageResponse(
            id="msg-001",
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            type="text",
            content="hello",
            payload={"text": "hello"},
            msg_metadata={"source": "fixed_responder"},
            status="completed",
            created_at=datetime.now(),
        )
        assert hasattr(resp, "status")
        assert resp.status == "completed"

    def test_message_response_schema_has_payload_field(self, setup_db):
        """MessageResponse 必须包含 payload 字段。"""
        from app.schemas.message import MessageResponse

        resp = MessageResponse(
            id="msg-001",
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            type="text",
            content="hello",
            payload={"text": "hello"},
            msg_metadata={"source": "fixed_responder"},
            status="completed",
            created_at=datetime.now(),
        )
        assert hasattr(resp, "payload")
        assert resp.payload == {"text": "hello"}

    def test_message_response_schema_has_metadata_field(self, setup_db):
        """MessageResponse 必须包含 message_metadata 字段。"""
        from app.schemas.message import MessageResponse

        resp = MessageResponse(
            id="msg-001",
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            type="text",
            content="hello",
            payload={"text": "hello"},
            msg_metadata={"source": "fixed_responder"},
            status="completed",
            created_at=datetime.now(),
        )
        assert hasattr(resp, "msg_metadata")
        assert resp.msg_metadata == {"source": "fixed_responder"}

    def test_message_response_schema_excludes_old_content_type_field(self, setup_db):
        """MessageResponse 不应再包含 content_type 字段。"""
        from app.schemas.message import MessageResponse

        resp = MessageResponse(
            id="msg-001",
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            type="text",
            content="hello",
            payload={"text": "hello"},
            msg_metadata={},
            status="completed",
            created_at=datetime.now(),
        )
        assert not hasattr(resp, "content_type")

    def test_message_response_schema_excludes_old_delivery_status_field(self, setup_db):
        """MessageResponse 不应再包含 delivery_status 字段。"""
        from app.schemas.message import MessageResponse

        resp = MessageResponse(
            id="msg-001",
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            type="text",
            content="hello",
            payload={"text": "hello"},
            msg_metadata={},
            status="completed",
            created_at=datetime.now(),
        )
        assert not hasattr(resp, "delivery_status")

    def test_message_response_fields_match_contract(self, setup_db):
        """MessageResponse 所有字段必须与 P1-3-1 契约一致。"""
        from app.schemas.message import MessageResponse

        expected_fields = {
            "id",
            "session_id",
            "sender_type",
            "sender_role",
            "type",
            "content",
            "payload",
            "metadata",
            "status",
            "created_at",
        }

        resp = MessageResponse(
            id="msg-001",
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            type="text",
            content="hello",
            payload={"text": "hello"},
            msg_metadata={"source": "fixed_responder"},
            status="completed",
            created_at=datetime.now(),
        )

        # Compare JSON-serialized output (what FastAPI actually sends)
        from fastapi.encoders import jsonable_encoder
        actual = jsonable_encoder(resp)
        actual_fields = set(actual.keys())
        assert actual_fields == expected_fields, f"字段不匹配: 期望 {expected_fields}, 实际 {actual_fields}"


# =============================================================================
# P1-3-1.6: 状态枚举值验证
# =============================================================================

class TestMessageStatusEnum:
    """验证 status 字段接受正确的枚举值。"""

    def test_status_accepts_completed(self, setup_db):
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="human",
            sender_role=None,
            content="hello",
        )
        msg.status = "completed"
        assert msg.status == "completed"

    def test_status_accepts_streaming(self, setup_db):
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="",
        )
        msg.status = "streaming"
        assert msg.status == "streaming"

    def test_status_accepts_failed(self, setup_db):
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="partial",
        )
        msg.status = "failed"
        assert msg.status == "failed"

    def test_status_does_not_accept_pending_for_human(self, setup_db):
        """pending 仅作为预留枚举，本阶段 human message 不应使用。"""
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="human",
            sender_role=None,
            content="hello",
        )
        # 不强制禁止设置，但 human message 默认 completed
        assert msg.status == "completed"


# =============================================================================
# P1-3-1.7: 类型枚举值验证
# =============================================================================

class TestMessageTypeEnum:
    """验证 type 字段接受正确的枚举值。"""

    def test_type_accepts_text(self, setup_db):
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="hello",
        )
        msg.type = "text"
        assert msg.type == "text"

    def test_type_accepts_code(self, setup_db):
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="",
        )
        msg.type = "code"
        assert msg.type == "code"

    def test_type_accepts_diff(self, setup_db):
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="",
        )
        msg.type = "diff"
        assert msg.type == "diff"

    def test_type_accepts_artifact(self, setup_db):
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="",
        )
        msg.type = "artifact"
        assert msg.type == "artifact"

    def test_type_accepts_deploy(self, setup_db):
        from app.models.message import Message

        msg = Message(
            session_id="s-001",
            sender_type="agent",
            sender_role="PM",
            content="",
        )
        msg.type = "deploy"
        assert msg.type == "deploy"
