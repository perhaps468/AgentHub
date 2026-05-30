# -*- coding: utf-8 -*-
"""T1: Session history injection tests.

Tests that RuntimeAgentService injects session DB messages into agent memory
so that multi-turn conversations have full context.
"""

import pytest


class TestSessionHistoryMapping:
    """T1: Mapping rules from DB Message to runtime Message."""

    def test_human_role_maps_to_user(self):
        """human sender_type -> user role."""
        from app.runtime.runtime_agent_service import _db_message_to_runtime_message
        db_msg = type("obj", (object,), {
            "sender_type": "human",
            "content": "hello",
            "type": "text",
            "status": "completed",
            "payload": {},
        })()
        rt_msg = _db_message_to_runtime_message(db_msg)
        assert rt_msg.role == "user"
        assert rt_msg.content == "hello"

    def test_agent_role_maps_to_assistant(self):
        """agent sender_type -> assistant role."""
        from app.runtime.runtime_agent_service import _db_message_to_runtime_message
        db_msg = type("obj", (object,), {
            "sender_type": "agent",
            "content": "hi there",
            "type": "text",
            "status": "completed",
            "payload": {},
        })()
        rt_msg = _db_message_to_runtime_message(db_msg)
        assert rt_msg.role == "assistant"

    def test_non_text_type_filtered(self):
        """Non-text type messages (image, etc.) are excluded."""
        from app.runtime.runtime_agent_service import _db_message_to_runtime_message
        db_msg = type("obj", (object,), {
            "sender_type": "human",
            "content": "image data",
            "type": "image",
            "status": "completed",
            "payload": {},
        })()
        result = _db_message_to_runtime_message(db_msg)
        assert result is None

    def test_empty_content_filtered(self):
        """Messages with empty content are excluded."""
        from app.runtime.runtime_agent_service import _db_message_to_runtime_message
        db_msg = type("obj", (object,), {
            "sender_type": "human",
            "content": "",
            "type": "text",
            "status": "completed",
            "payload": {},
        })()
        result = _db_message_to_runtime_message(db_msg)
        assert result is None

    def test_streaming_status_included(self):
        """Agent messages with streaming status are included (they have content)."""
        from app.runtime.runtime_agent_service import _db_message_to_runtime_message
        db_msg = type("obj", (object,), {
            "sender_type": "agent",
            "content": "thinking...",
            "type": "text",
            "status": "streaming",
            "payload": {},
        })()
        rt_msg = _db_message_to_runtime_message(db_msg)
        assert rt_msg is not None
        assert rt_msg.role == "assistant"

    def test_payload_text_used_when_content_empty(self):
        """When content is empty but payload.text exists, use payload text."""
        from app.runtime.runtime_agent_service import _db_message_to_runtime_message
        db_msg = type("obj", (object,), {
            "sender_type": "human",
            "content": "",
            "type": "text",
            "status": "completed",
            "payload": {"text": "hello from payload"},
        })()
        rt_msg = _db_message_to_runtime_message(db_msg)
        assert rt_msg is not None
        assert rt_msg.content == "hello from payload"

    def test_unknown_sender_type_excluded(self):
        """Unknown sender_type is excluded."""
        from app.runtime.runtime_agent_service import _db_message_to_runtime_message
        db_msg = type("obj", (object,), {
            "sender_type": "system",
            "content": "system message",
            "type": "text",
            "status": "completed",
            "payload": {},
        })()
        result = _db_message_to_runtime_message(db_msg)
        assert result is None


class TestLoadSessionHistory:
    """T1: Loading session history from DB."""

    def test_load_session_history_returns_ordered_list(self):
        """load_session_history returns ordered runtime messages."""
        from app.runtime.runtime_agent_service import load_session_history
        from app.models.message import Message

        db_messages = [
            type("obj", (object,), {
                "id": "m1", "sender_type": "human", "content": "first",
                "type": "text", "status": "completed", "payload": {},
            })(),
            type("obj", (object,), {
                "id": "m2", "sender_type": "agent", "content": "first reply",
                "type": "text", "status": "completed", "payload": {},
            })(),
            type("obj", (object,), {
                "id": "m3", "sender_type": "human", "content": "second",
                "type": "text", "status": "completed", "payload": {},
            })(),
        ]

        class MockDB:
            def query(self, cls):
                class Q:
                    def filter_by(self, **k):
                        class Q2:
                            def order_by(self, *a):
                                class Q3:
                                    def all(self):
                                        return db_messages
                                return Q3()
                        return Q2()
                return Q()

        result = load_session_history(MockDB(), "session-123")
        assert len(result) == 3
        assert result[0].role == "user"
        assert result[0].content == "first"
        assert result[1].role == "assistant"
        assert result[1].content == "first reply"
        assert result[2].role == "user"
        assert result[2].content == "second"

    def test_load_session_history_empty_session(self):
        """Empty session returns empty list."""
        from app.runtime.runtime_agent_service import load_session_history

        class MockDB:
            def query(self, cls):
                class Q:
                    def filter_by(self, **k):
                        class Q2:
                            def order_by(self, *a):
                                class Q3:
                                    def all(self):
                                        return []
                                return Q3()
                        return Q2()
                return Q()

        result = load_session_history(MockDB(), "empty-session")
        assert result == []

    def test_load_session_history_skips_non_text(self):
        """Non-text messages are excluded from history."""
        from app.runtime.runtime_agent_service import load_session_history

        db_messages = [
            type("obj", (object,), {
                "id": "m1", "sender_type": "human", "content": "hello",
                "type": "image", "status": "completed", "payload": {},
            })(),
            type("obj", (object,), {
                "id": "m2", "sender_type": "agent", "content": "I see your image",
                "type": "text", "status": "completed", "payload": {},
            })(),
        ]

        class MockDB:
            def query(self, cls):
                class Q:
                    def filter_by(self, **k):
                        class Q2:
                            def order_by(self, *a):
                                class Q3:
                                    def all(self):
                                        return db_messages
                                return Q3()
                        return Q2()
                return Q()

        result = load_session_history(MockDB(), "session-123")
        assert len(result) == 1
        assert result[0].role == "assistant"

    def test_load_session_history_skips_empty_content(self):
        """Messages with empty content are excluded."""
        from app.runtime.runtime_agent_service import load_session_history

        db_messages = [
            type("obj", (object,), {
                "id": "m1", "sender_type": "human", "content": "",
                "type": "text", "status": "completed", "payload": {},
            })(),
            type("obj", (object,), {
                "id": "m2", "sender_type": "agent", "content": "I responded",
                "type": "text", "status": "completed", "payload": {},
            })(),
        ]

        class MockDB:
            def query(self, cls):
                class Q:
                    def filter_by(self, **k):
                        class Q2:
                            def order_by(self, *a):
                                class Q3:
                                    def all(self):
                                        return db_messages
                                return Q3()
                        return Q2()
                return Q()

        result = load_session_history(MockDB(), "session-123")
        assert len(result) == 1
        assert result[0].content == "I responded"


class TestAgentMemoryPrePopulation:
    """T1: Verify agent memory is pre-populated with session history."""

    def test_service_stores_session_history(self):
        """RuntimeAgentService stores session_history in _session_history field."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from app.runtime.memory import AgentMemory, Message as RuntimeMessage

        history = [
            RuntimeMessage(role="user", content="hello"),
            RuntimeMessage(role="assistant", content="hi there"),
        ]

        class FakeDB:
            def add(self, msg):
                pass

            def commit(self):
                pass

            def refresh(self, msg):
                pass

            def get(self, cls, id_):
                return None

        service = RuntimeAgentService(
            session_id="s1",
            user_message="what's next",
            agent_role="PM",
            llm_adapter=None,
            db=FakeDB(),
            session_history=history,
        )

        assert len(service._session_history) == 2
        assert service._session_history[0].content == "hello"
        assert service._session_history[1].content == "hi there"

    def test_service_with_empty_history(self):
        """RuntimeAgentService handles empty session_history."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class FakeDB:
            def add(self, msg):
                pass

            def commit(self):
                pass

            def refresh(self, msg):
                pass

            def get(self, cls, id_):
                return None

        service = RuntimeAgentService(
            session_id="s1",
            user_message="first message",
            agent_role="PM",
            llm_adapter=None,
            db=FakeDB(),
            session_history=None,
        )

        assert service._session_history == []
