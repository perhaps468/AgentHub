# -*- coding: utf-8 -*-
"""Task A - RuntimeStateEvent TDD tests (RED phase).

Tests verify that:
- RuntimeStateEvent class exists and has required fields per spec §7.4
- EventBridge maps internal runtime state events to RuntimeStateEvent
- RuntimeStateEvent is forwarded via on_runtime_state callback
- Existing tool_event behavior is preserved
"""

import pytest


class TestRuntimeStateEventClass:
    """RSE-1: RuntimeStateEvent class has spec-compliant fields."""

    def test_runtime_state_event_class_exists(self):
        """RuntimeStateEvent should be importable from event_bridge."""
        from app.runtime.event_bridge import RuntimeStateEvent

        assert RuntimeStateEvent is not None

    def test_runtime_state_event_has_required_fields(self):
        """RuntimeStateEvent must have type, stream_id, message_id, state, timestamp."""
        from app.runtime.event_bridge import RuntimeStateEvent

        evt = RuntimeStateEvent(
            stream_id="stream-123",
            message_id="msg-456",
            state="thinking",
            timestamp="2026-05-29T10:00:00Z",
        )

        assert evt.type == "runtime_state"
        assert evt.stream_id == "stream-123"
        assert evt.message_id == "msg-456"
        assert evt.state == "thinking"
        assert evt.timestamp == "2026-05-29T10:00:00Z"

    def test_runtime_state_event_type_fixed_to_runtime_state(self):
        """RuntimeStateEvent.type must always be 'runtime_state'."""
        from app.runtime.event_bridge import RuntimeStateEvent

        evt = RuntimeStateEvent(stream_id="s1", message_id="m1", state="calling_tool", timestamp="2026-01-01T00:00:00Z")
        assert evt.type == "runtime_state"

    def test_runtime_state_event_default_state_values(self):
        """RuntimeStateEvent should accept valid state values: thinking/calling_tool/observing/responding/finished/error."""
        from app.runtime.event_bridge import RuntimeStateEvent

        for state in ("thinking", "calling_tool", "observing", "responding", "finished", "error"):
            evt = RuntimeStateEvent(stream_id="s", message_id="m", state=state, timestamp="2026-01-01T00:00:00Z")
            assert evt.state == state


class TestEventBridgeRuntimeStateCallback:
    """RSE-2: EventBridge routes runtime_state events to on_runtime_state callback."""

    def test_event_bridge_accepts_on_runtime_state_callback(self):
        """EventBridge.__init__ must accept on_runtime_state parameter."""
        from app.runtime.event_bridge import EventBridge

        received = []

        def on_state(**kwargs):
            received.append(kwargs)

        bridge = EventBridge(on_runtime_state=on_state)
        assert hasattr(bridge, "_on_runtime_state")

    def test_event_bridge_emits_runtime_state_event(self):
        """A 'runtime_state' internal event produces a RuntimeStateEvent via callback."""
        from app.runtime.event_bridge import EventBridge, RuntimeStateEvent

        received = []

        def on_state(**kwargs):
            received.append(kwargs)

        bridge = EventBridge(
            on_runtime_state=on_state,
            stream_id="stream-abc",
            message_id="msg-xyz",
        )

        bridge.emit("runtime_state", {
            "state": "thinking",
            "timestamp": "2026-05-29T10:00:00Z",
        })

        assert len(received) == 1
        assert received[0]["state"] == "thinking"
        assert received[0]["stream_id"] == "stream-abc"
        assert received[0]["message_id"] == "msg-xyz"
        assert received[0]["timestamp"] == "2026-05-29T10:00:00Z"

    def test_runtime_state_without_callback_is_silently_ignored(self):
        """When on_runtime_state is None, runtime_state events do not raise."""
        from app.runtime.event_bridge import EventBridge

        bridge = EventBridge(on_runtime_state=None)
        # Should not raise
        bridge.emit("runtime_state", {"state": "thinking", "timestamp": "2026-05-29T10:00:00Z"})

    def test_runtime_state_maps_all_valid_states(self):
        """All valid runtime states produce correct callback data."""
        from app.runtime.event_bridge import EventBridge

        received = []

        def on_state(**kwargs):
            received.append(kwargs)

        bridge = EventBridge(on_runtime_state=on_state, stream_id="s1", message_id="m1")

        for state in ("thinking", "calling_tool", "observing", "responding", "finished", "error"):
            bridge.emit("runtime_state", {"state": state, "timestamp": "2026-01-01T00:00:00Z"})

        assert len(received) == 6
        states = [r["state"] for r in received]
        assert states == ["thinking", "calling_tool", "observing", "responding", "finished", "error"]


class TestEventBridgePreservesExistingBehavior:
    """RSE-3: Adding runtime_state does not break existing behavior."""

    def test_tool_event_still_works_after_runtime_state_added(self):
        """tool_execution_start still routes to on_tool_event."""
        from app.runtime.event_bridge import EventBridge

        tool_received = []

        def on_tool(**kwargs):
            tool_received.append(kwargs)

        bridge = EventBridge(on_tool_event=on_tool, on_runtime_state=lambda **_: None)

        bridge.emit("tool_execution_start", {
            "tool_name": "read_file_tool",
            "arguments": {"file_path": "test.py"},
        })

        assert len(tool_received) == 1
        assert tool_received[0]["tool_name"] == "read_file_tool"
        assert tool_received[0]["status"] == "started"

    def test_message_delta_still_works_after_runtime_state_added(self):
        """model_delta events still accumulate and trigger on_message_delta."""
        from app.runtime.event_bridge import EventBridge

        deltas = []

        def on_delta(**kw):
            deltas.append(kw.get("delta"))

        bridge = EventBridge(
            on_message_delta=on_delta,
            on_runtime_state=lambda **_: None,
        )

        bridge.emit("model_delta", {"delta": "Hello"})
        bridge.emit("model_delta", {"delta": " world"})

        assert deltas == ["Hello", " world"]
        assert bridge.accumulated_text == "Hello world"

    def test_message_end_still_works_after_runtime_state_added(self):
        """task_solve_end still maps to message_end."""
        from app.runtime.event_bridge import EventBridge

        end_events = []

        def on_end(**kw):
            end_events.append(kw)

        bridge = EventBridge(on_message_end=on_end, on_runtime_state=lambda **_: None)
        bridge.emit("task_solve_end", {"result": "answer", "tracked_files": []})

        assert len(end_events) == 1
        assert end_events[0]["status"] == "completed"
        assert end_events[0]["result"] == "answer"
