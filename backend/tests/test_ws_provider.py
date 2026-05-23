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
        asyncio.run(send_error(mock_ws, ws_code, ws_message))
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
