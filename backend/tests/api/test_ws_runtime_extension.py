# -*- coding: utf-8 -*-
"""Task A - WS tool_event + runtime_state forwarding TDD tests (RED phase).

Tests verify that:
- ws.py has ws_send_tool_event and ws_send_runtime_state helper functions
- session_websocket handler forwards tool_event and runtime_state from RuntimeAgentService
- ws.py remains backward-compatible with existing message_* protocol
"""

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator
from unittest.mock import MagicMock, patch
import pytest


class TestWSRuntimeExtensionHelpers:
    """WS-RE-1: ws.py exports ws_send_tool_event and ws_send_runtime_state."""

    def test_ws_send_tool_event_exists(self):
        """ws_send_tool_event should be importable from app.api.ws."""
        from app.api import ws as ws_module

        assert hasattr(ws_module, "ws_send_tool_event"), (
            "ws_send_tool_event not found in app.api.ws"
        )
        assert callable(ws_module.ws_send_tool_event)

    def test_ws_send_runtime_state_exists(self):
        """ws_send_runtime_state should be importable from app.api.ws."""
        from app.api import ws as ws_module

        assert hasattr(ws_module, "ws_send_runtime_state"), (
            "ws_send_runtime_state not found in app.api.ws"
        )
        assert callable(ws_module.ws_send_runtime_state)

    def test_ws_send_tool_event_sends_correct_payload(self):
        """ws_send_tool_event should send a JSON payload with tool_event type."""
        from app.api.ws import ws_send_tool_event

        class _WS:
            def __init__(self):
                self.sent = None

            async def send_json(self, data):
                self.sent = data

        ws = _WS()
        asyncio.run(ws_send_tool_event(
            ws,
            tool_name="read_file_tool",
            arguments={"file_path": "test.py"},
            response="file contents",
            status="finished",
            stream_id="stream-abc",
            message_id="msg-xyz",
        ))

        assert ws.sent is not None
        assert ws.sent["type"] == "tool_event"
        assert ws.sent["tool_name"] == "read_file_tool"
        assert ws.sent["status"] == "finished"
        assert ws.sent["stream_id"] == "stream-abc"
        assert ws.sent["message_id"] == "msg-xyz"
        assert ws.sent["arguments"] == {"file_path": "test.py"}
        assert ws.sent["response"] == "file contents"
        assert "timestamp" in ws.sent

    def test_ws_send_runtime_state_sends_correct_payload(self):
        """ws_send_runtime_state should send a JSON payload with runtime_state type."""
        from app.api.ws import ws_send_runtime_state

        class _WS:
            def __init__(self):
                self.sent = None

            async def send_json(self, data):
                self.sent = data

        ws = _WS()
        asyncio.run(ws_send_runtime_state(
            ws,
            stream_id="stream-abc",
            message_id="msg-xyz",
            state="thinking",
            timestamp="2026-05-29T10:00:00Z",
        ))

        assert ws.sent is not None
        assert ws.sent["type"] == "runtime_state"
        assert ws.sent["state"] == "thinking"
        assert ws.sent["stream_id"] == "stream-abc"
        assert ws.sent["message_id"] == "msg-xyz"
        assert ws.sent["timestamp"] == "2026-05-29T10:00:00Z"


class TestWSRuntimeExtensionForwarding:
    """WS-RE-2: session_websocket forwards tool_event + runtime_state from RuntimeAgentService."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Configure in-memory DB and isolate InFlightGuard."""
        from app.core import database
        from app.api.ws import _InFlightGuard, set_guard

        database.configure_database("sqlite+pysqlite:///:memory:", create_schema=True)
        set_guard(_InFlightGuard())
        yield
        database.Base.metadata.drop_all(bind=database.engine)
        set_guard(_InFlightGuard())

    @pytest.fixture
    def _e2e_env(self):
        """Create session and token in same db session."""
        from app.core.database import SessionLocal
        from app.models.session import ChatSession
        from app.core.security import create_access_token

        db = SessionLocal()
        session = ChatSession(owner_id="1", title="Test", mode="single")
        db.add(session)
        db.commit()
        db.refresh(session)
        token = create_access_token(user_id=1, username="dev_user")
        return session.id, db, token

    def _build_fake_runtime_service_with_tool_and_state(self, session_id):
        """Fake RuntimeAgentService that emits tool_event and runtime_state."""
        from typing import AsyncIterator

        class _FakeRuntimeService:
            def __init__(self, **kwargs):
                self._session_id = kwargs.get("session_id", "fake")

            async def stream_events(self) -> AsyncIterator:
                # message_start
                class _Msg:
                    id = "e2e-fake-msg-id"
                    session_id = self._session_id
                    sender_type = "agent"
                    sender_role = "PM"
                    type = "text"
                    content = ""
                    payload = {"text": ""}
                    msg_metadata = {}
                    status = "streaming"
                    created_at = datetime.now(timezone.utc)

                class _StartEvent:
                    type = "message_start"
                    agent_role = "PM"
                    stream_id = "e2e-stream-id"
                    message = _Msg()

                yield _StartEvent()

                # runtime_state: thinking
                class _ThinkingStateEvent:
                    type = "runtime_state"
                    stream_id = "e2e-stream-id"
                    message_id = "e2e-fake-msg-id"
                    state = "thinking"
                    timestamp = "2026-05-29T10:00:00Z"

                yield _ThinkingStateEvent()

                # tool_event: started
                class _ToolStartEvent:
                    type = "tool_event"
                    tool_name = "read_file_tool"
                    arguments = {"file_path": "test.py"}
                    response = None
                    status = "started"
                    stream_id = "e2e-stream-id"
                    message_id = "e2e-fake-msg-id"

                yield _ToolStartEvent()

                # tool_event: finished
                class _ToolEndEvent:
                    type = "tool_event"
                    tool_name = "read_file_tool"
                    arguments = {"file_path": "test.py"}
                    response = "file contents"
                    status = "finished"
                    stream_id = "e2e-stream-id"
                    message_id = "e2e-fake-msg-id"

                yield _ToolEndEvent()

                # runtime_state: responding
                class _RespondingStateEvent:
                    type = "runtime_state"
                    stream_id = "e2e-stream-id"
                    message_id = "e2e-fake-msg-id"
                    state = "responding"
                    timestamp = "2026-05-29T10:00:01Z"

                yield _RespondingStateEvent()

                # message_end
                class _EndEvent:
                    type = "message_end"
                    agent_role = "PM"
                    stream_id = "e2e-stream-id"
                    message_id = "e2e-fake-msg-id"
                    status = "completed"
                    final_content = "done"

                yield _EndEvent()

        return _FakeRuntimeService(session_id=session_id)

    def _run_ws_with_fake_service(self, session_id, token, db, fake_service):
        """Run session_websocket with a patched RuntimeAgentService."""
        from app.api.ws import session_websocket

        ws = _MockWebSocketForWS(token=token)
        ws.queue_message({"action": "send_message", "session_id": session_id, "content": "hello"})

        with patch("app.runtime.runtime_agent_service.RuntimeAgentService", return_value=fake_service), \
             patch("app.api.ws.runtime_use_runtime_agent", return_value=True), \
             patch("app.api.ws.SessionLocal", return_value=db):
            asyncio.run(session_websocket(ws, session_id))

        return ws.sent_messages

    def test_runtime_path_forwards_tool_event_to_websocket(self, _e2e_env):
        """RuntimeAgentService tool_event must be forwarded to the WebSocket client."""
        session_id, db, token = _e2e_env
        try:
            fake_service = self._build_fake_runtime_service_with_tool_and_state(session_id)
            msgs = self._run_ws_with_fake_service(session_id, token, db, fake_service)

            tool_events = [m for m in msgs if m.get("type") == "tool_event"]
            assert len(tool_events) >= 2, (
                f"Expected >=2 tool_event (started + finished), got: {[m.get('type') for m in msgs]}"
            )

            # Check started event
            start_tool = next((m for m in tool_events if m.get("status") == "started"), None)
            assert start_tool is not None, "Missing tool_event with status=started"
            assert start_tool["tool_name"] == "read_file_tool"
            assert start_tool["arguments"] == {"file_path": "test.py"}

            # Check finished event
            end_tool = next((m for m in tool_events if m.get("status") == "finished"), None)
            assert end_tool is not None, "Missing tool_event with status=finished"
            assert end_tool["tool_name"] == "read_file_tool"
            assert end_tool["response"] == "file contents"
        finally:
            db.close()

    def test_runtime_path_forwards_runtime_state_to_websocket(self, _e2e_env):
        """RuntimeAgentService runtime_state must be forwarded to the WebSocket client."""
        session_id, db, token = _e2e_env
        try:
            fake_service = self._build_fake_runtime_service_with_tool_and_state(session_id)
            msgs = self._run_ws_with_fake_service(session_id, token, db, fake_service)

            runtime_states = [m for m in msgs if m.get("type") == "runtime_state"]
            assert len(runtime_states) >= 2, (
                f"Expected >=2 runtime_state, got: {[m.get('type') for m in msgs]}"
            )

            # Check thinking state
            thinking = next((m for m in runtime_states if m.get("state") == "thinking"), None)
            assert thinking is not None, "Missing runtime_state with state=thinking"
            assert thinking["stream_id"] == "e2e-stream-id"

            # Check responding state
            responding = next((m for m in runtime_states if m.get("state") == "responding"), None)
            assert responding is not None, "Missing runtime_state with state=responding"
        finally:
            db.close()

    def test_runtime_state_and_tool_event_coexist_with_message_events(self, _e2e_env):
        """tool_event + runtime_state must coexist with message_start/delta/end in same stream."""
        session_id, db, token = _e2e_env
        try:
            fake_service = self._build_fake_runtime_service_with_tool_and_state(session_id)
            msgs = self._run_ws_with_fake_service(session_id, token, db, fake_service)

            event_types = [m.get("type") for m in msgs]

            # Must have standard message events
            assert "message_start" in event_types, "Missing message_start"
            assert "message_end" in event_types, "Missing message_end"

            # Must have runtime extension events
            assert "tool_event" in event_types, "Missing tool_event"
            assert "runtime_state" in event_types, "Missing runtime_state"

            # message_start must be first
            assert event_types[0] == "message_start"
            # message_end must be last
            assert event_types[-1] == "message_end"
        finally:
            db.close()


# --------------------------------------------------------------------------
# Mock WebSocket（reused from test_ws_runtime_agent.py）
# --------------------------------------------------------------------------


class _MockWebSocketForWS:
    """Supports session_websocket query_params and close(reason=)."""

    def __init__(self, token=None):
        self.accepted = False
        self.closed = False
        self.close_code: int | None = None
        self.sent_messages: list[dict] = []
        self.received_messages: list[dict] = []
        self.query_params = {"x-token": token} if token else {}

    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000, **kwargs) -> None:
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
