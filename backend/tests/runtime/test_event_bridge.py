"""M5 - EventBridge TDD tests (RED phase).

Tests verify that:
- Runtime internal events map correctly to WS protocol events
- Success path produces message_start -> message_delta* -> message_end
- Error path produces message_error
- Event ordering is stable
- Bridge is usable as Agent.event_emitter
"""

import asyncio
from unittest.mock import MagicMock

import pytest


class TestEventBridgeBasic:
    """EB-1: EventBridge can be used as an Agent.event_emitter."""

    def test_event_bridge_exists(self):
        """EventBridge class should be importable."""
        from app.runtime.event_bridge import EventBridge

        bridge = EventBridge(on_message_start=lambda *a, **k: None)
        assert bridge is not None

    def test_bridge_has_emit_method(self):
        """EventBridge should have an emit() method compatible with Agent."""
        from app.runtime.event_bridge import EventBridge

        bridge = EventBridge(on_message_start=lambda *a, **k: None)
        assert hasattr(bridge, "emit")
        assert callable(bridge.emit)

    def test_bridge_is_accepted_as_agent_event_emitter(self):
        """EventBridge can be passed as event_emitter to Agent."""
        from app.runtime.event_bridge import EventBridge
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        bridge = EventBridge(on_message_start=lambda *a, **k: None)
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=_FakeAdapter(["answer"]),
            memory=AgentMemory(),
            tools=[],
            event_emitter=bridge,
        )
        assert agent is not None


class TestEventBridgeMapping:
    """EB-2: Runtime events map to WS events correctly."""

    def test_session_start_triggers_message_start(self):
        """session_start event should emit message_start callback."""
        from app.runtime.event_bridge import EventBridge

        emitted: list[dict] = []

        def capture_start(**kwargs):
            emitted.append(kwargs)

        bridge = EventBridge(on_message_start=capture_start)
        bridge.emit("session_start", {"iteration": 1})

        assert len(emitted) == 1
        assert emitted[0]["event_type"] == "session_start"
        assert "message" in emitted[0]

    def test_task_think_end_triggers_message_delta(self):
        """task_think_end event should emit message_delta callback."""
        from app.runtime.event_bridge import EventBridge

        emitted: list[dict] = []

        def capture_delta(**kwargs):
            emitted.append(kwargs)

        bridge = EventBridge(on_message_delta=capture_delta)
        bridge.emit("task_think_end", {"response": "Hello world"})

        assert len(emitted) == 1
        assert emitted[0]["event_type"] == "task_think_end"
        assert "delta" in emitted[0]

    def test_task_complete_triggers_message_end(self):
        """task_solve_end event should emit message_end callback."""
        from app.runtime.event_bridge import EventBridge

        emitted: list[dict] = []

        def capture_end(**kwargs):
            emitted.append(kwargs)

        bridge = EventBridge(on_message_end=capture_end)
        bridge.emit(
            "task_solve_end",
            {"result": "final answer", "message": "done", "tracked_files": []},
        )

        assert len(emitted) == 1
        assert emitted[0]["event_type"] == "task_solve_end"
        assert "status" in emitted[0]
        assert emitted[0]["status"] == "completed"

    def test_runtime_error_triggers_message_error(self):
        """Any exception event should emit message_error callback."""
        from app.runtime.event_bridge import EventBridge

        emitted: list[dict] = []

        def capture_error(**kwargs):
            emitted.append(kwargs)

        bridge = EventBridge(on_message_error=capture_error)
        bridge.emit("runtime_error", {"error": "something went wrong"})

        assert len(emitted) == 1
        assert emitted[0]["event_type"] == "runtime_error"
        assert "error_code" in emitted[0]

    def test_tool_events_do_not_emit_ws_events(self):
        """tool_execution_start/end should not emit WS events by default."""
        from app.runtime.event_bridge import EventBridge

        start_emitted: list = []
        end_emitted: list = []

        bridge = EventBridge(
            on_message_start=lambda **k: start_emitted.append(k),
            on_message_delta=lambda **k: None,
            on_message_end=lambda **k: end_emitted.append(k),
        )
        bridge.emit("tool_execution_start", {"tool_name": "read_file"})
        bridge.emit("tool_execution_end", {"tool_name": "read_file", "response": "ok"})

        assert len(start_emitted) == 0
        assert len(end_emitted) == 0


class TestEventBridgeAccumulator:
    """EB-3: Bridge accumulates text deltas."""

    def test_multiple_think_end_accumulates_deltas(self):
        """Multiple task_think_end events should produce multiple delta calls."""
        from app.runtime.event_bridge import EventBridge

        deltas: list[str] = []

        def capture_delta(**kwargs):
            deltas.append(kwargs.get("delta", ""))

        bridge = EventBridge(on_message_delta=capture_delta)
        bridge.emit("task_think_end", {"response": "First response"})
        bridge.emit("task_think_end", {"response": "Second response"})

        assert len(deltas) == 2

    def test_accumulated_text_reported_on_end(self):
        """On message_end, accumulated text should be available."""
        from app.runtime.event_bridge import EventBridge

        end_data: list[dict] = []

        def capture_end(**kwargs):
            end_data.append(kwargs)

        bridge = EventBridge(on_message_end=capture_end)
        bridge.emit("task_think_end", {"response": "Hello "})
        bridge.emit("task_think_end", {"response": "World"})

        bridge.emit(
            "task_solve_end",
            {"result": "Hello World", "message": "done", "tracked_files": []},
        )

        assert len(end_data) == 1
        assert "final_text" in end_data[0] or "accumulated_text" in end_data[0]


class TestEventBridgeWSProtocol:
    """EB-4: Bridge output is compatible with WS protocol fields."""

    def test_message_start_has_required_fields(self):
        """message_start callback should receive all required WS fields."""
        from app.runtime.event_bridge import EventBridge

        received: dict = {}

        def capture_start(**kwargs):
            received.update(kwargs)

        bridge = EventBridge(on_message_start=capture_start)
        # Set a fake message to simulate what RuntimeAgentService does
        class FakeMessage:
            id = "test-msg-id"
        bridge.set_message(message=FakeMessage(), message_id="test-msg-id")
        bridge.emit("session_start", {"iteration": 1})

        assert "message" in received
        assert "event_type" in received
        assert received["message"] is not None

    def test_message_delta_has_required_fields(self):
        """message_delta callback should receive all required WS fields."""
        from app.runtime.event_bridge import EventBridge

        received: dict = {}

        def capture_delta(**kwargs):
            received.update(kwargs)

        bridge = EventBridge(on_message_delta=capture_delta)
        bridge.emit("task_think_end", {"response": "partial"})

        assert "delta" in received
        assert "event_type" in received

    def test_message_end_has_required_fields(self):
        """message_end callback should receive all required WS fields."""
        from app.runtime.event_bridge import EventBridge

        received: dict = {}

        def capture_end(**kwargs):
            received.update(kwargs)

        bridge = EventBridge(on_message_end=capture_end)
        bridge.emit(
            "task_solve_end",
            {"result": "final", "message": "done", "tracked_files": []},
        )

        assert "status" in received
        assert "event_type" in received
        assert received["status"] in ("completed", "failed")

    def test_message_error_has_required_fields(self):
        """message_error callback should receive all required WS fields."""
        from app.runtime.event_bridge import EventBridge

        received: dict = {}

        def capture_error(**kwargs):
            received.update(kwargs)

        bridge = EventBridge(on_message_error=capture_error)
        bridge.emit("runtime_error", {"error": "boom"})

        assert "error_code" in received
        assert "error_message" in received
        assert "event_type" in received


# --------------------------------------------------------------------------
# Fake LLMAdapter for tests that need a full Agent
# --------------------------------------------------------------------------

from typing import AsyncIterator

from app.runtime.generative_model import ResponseStats, TokenUsage


class _FakeAdapter:
    """Minimal fake LLMAdapter for event bridge tests."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or ["<action><task_complete><answer>answer</answer></task_complete></action>"]
        self.call_count = 0

    async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
        idx = min(self.call_count, len(self.responses) - 1)
        text = self.responses[idx]
        self.call_count += 1
        return ResponseStats(
            response=text,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=model,
            finish_reason="stop",
        )

    async def async_stream_generate_with_history(
        self, messages_history: list, model: str, **kwargs
    ) -> AsyncIterator[str]:
        idx = min(self.call_count, len(self.responses) - 1)
        text = self.responses[idx]
        self.call_count += 1
        for char in text:
            yield char
