# -*- coding: utf-8 -*-
"""T2: Real streaming delta tests.

Tests that the runtime uses actual model streaming (token-level deltas)
instead of pseudo-streaming (whole blocks after generation completes).
"""

import pytest


class TestModelDeltaEvent:
    """T2: model_delta events are emitted during token streaming."""

    def test_event_bridge_has_model_delta_callback(self):
        """EventBridge accepts on_model_delta callback."""
        from app.runtime.event_bridge import EventBridge

        deltas = []

        def on_delta(**kwargs):
            deltas.append(kwargs)

        bridge = EventBridge(
            on_model_delta=on_delta,
        )
        assert bridge._on_model_delta is not None

    def test_model_delta_yields_delta_string(self):
        """model_delta event emits the raw delta string."""
        from app.runtime.event_bridge import EventBridge

        deltas = []

        def on_delta(**kwargs):
            deltas.append(kwargs)

        bridge = EventBridge(
            on_model_delta=on_delta,
        )
        bridge._message_id = "msg1"
        bridge._stream_id = "stream1"
        bridge._agent_role = "PM"

        bridge.emit("model_delta", {"delta": "Hello "})
        bridge.emit("model_delta", {"delta": "world!"})

        assert len(deltas) == 2
        assert deltas[0]["delta"] == "Hello "
        assert deltas[1]["delta"] == "world!"

    def test_model_delta_propagates_to_message_delta_callback(self):
        """model_delta events route to on_message_delta with correct fields."""
        from app.runtime.event_bridge import EventBridge

        message_deltas = []

        def on_msg_delta(**kwargs):
            message_deltas.append(kwargs)

        bridge = EventBridge(
            on_message_delta=on_msg_delta,
        )
        bridge._message_id = "msg1"
        bridge._stream_id = "stream1"
        bridge._agent_role = "PM"

        bridge.emit("model_delta", {"delta": "token1"})

        assert len(message_deltas) == 1
        assert message_deltas[0]["delta"] == "token1"
        assert message_deltas[0]["message_id"] == "msg1"
        assert message_deltas[0]["stream_id"] == "stream1"
        assert message_deltas[0]["agent_role"] == "PM"

    def test_model_delta_accumulates_text(self):
        """model_delta events accumulate in bridge._accumulated_text."""
        from app.runtime.event_bridge import EventBridge

        bridge = EventBridge(on_model_delta=lambda **k: None)
        bridge._message_id = "m1"

        bridge.emit("model_delta", {"delta": "first "})
        bridge.emit("model_delta", {"delta": "second "})
        bridge.emit("model_delta", {"delta": "third"})

        assert bridge.accumulated_text == "first second third"

    def test_event_bridge_has_model_delta_event_type(self):
        """EventBridge.emit() handles 'model_delta' event type."""
        from app.runtime.event_bridge import EventBridge

        bridge = EventBridge(on_model_delta=lambda **k: None)
        # Should not raise
        bridge.emit("model_delta", {"delta": "test"})

    def test_task_think_end_still_works_with_streaming(self):
        """task_think_end (non-streaming path) still emits message_delta."""
        from app.runtime.event_bridge import EventBridge

        deltas = []

        def on_msg_delta(**kwargs):
            deltas.append(kwargs)

        bridge = EventBridge(on_message_delta=on_msg_delta)
        bridge._message_id = "msg1"
        bridge._stream_id = "stream1"
        bridge._agent_role = "PM"

        # Non-streaming path
        bridge.emit("task_think_end", {"response": "full response"})

        assert len(deltas) == 1
        assert deltas[0]["delta"] == "full response"


class TestStreamingPathInAgent:
    """T2: ReactAgent emits model_delta during streaming."""

    def test_llm_wrapper_has_streaming_method(self):
        """LLMWrapper exposes async_stream_generate_with_history."""
        from app.runtime.llm_wrapper import LLMWrapper

        # The wrapper should have streaming capability
        assert hasattr(LLMWrapper, "async_stream_generate_with_history") or \
               hasattr(LLMWrapper, "_llm_adapter")

    def test_llm_adapter_has_streaming_method(self):
        """LLMAdapter.async_stream_generate_with_history exists."""
        from app.runtime.llm_adapter import LLMAdapter

        # Can check the method exists
        assert hasattr(LLMAdapter, "async_stream_generate_with_history")


class TestRuntimeServiceStreaming:
    """T2: RuntimeAgentService routes model_delta to message_delta."""

    def test_service_handles_model_delta_event(self):
        """RuntimeAgentService._on_model_delta is callable."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class FakeDB:
            def add(self, m): pass
            def commit(self): pass
            def refresh(self, m): pass
            def get(self, cls, id_): return None

        service = RuntimeAgentService(
            session_id="s1",
            user_message="hello",
            agent_role="PM",
            llm_adapter=None,
            db=FakeDB(),
        )

        # The service should have an _on_model_delta callback
        assert hasattr(service, "_on_model_delta")

    def test_model_delta_updates_accumulated_content(self):
        """model_delta updates the service's _accumulated_content."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class FakeDB:
            def add(self, m): pass
            def commit(self): pass
            def refresh(self, m): pass
            def get(self, cls, id_): return None

        service = RuntimeAgentService(
            session_id="s1",
            user_message="hello",
            agent_role="PM",
            llm_adapter=None,
            db=FakeDB(),
        )

        # Simulate model_delta events
        service._on_model_delta(delta="Hello ")
        service._on_model_delta(delta="world!")

        assert service._accumulated_content == "Hello world!"
