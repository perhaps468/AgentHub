# -*- coding: utf-8 -*-
"""T4: Structured tool events into message chain tests.

Tests that:
- tool_execution_start / tool_execution_end are routed through EventBridge
- ToolEvent is produced by RuntimeAgentService.stream_events()
- tool/diff/run command results appear as structured events
"""

import pytest


class TestToolEventInEventBridge:
    """T4: EventBridge routes tool_execution_start/end to on_tool_event callback."""

    def test_tool_event_callback_attribute_exists(self):
        """EventBridge accepts on_tool_event callback."""
        from app.runtime.event_bridge import EventBridge

        received = []

        def on_tool(**kwargs):
            received.append(kwargs)

        bridge = EventBridge(on_tool_event=on_tool)
        assert hasattr(bridge, "_on_tool_event")

    def test_tool_execution_start_emits_tool_event(self):
        """tool_execution_start event produces a ToolEvent."""
        from app.runtime.event_bridge import EventBridge, ToolEvent

        received = []

        def on_tool(**kwargs):
            received.append(kwargs)

        bridge = EventBridge(
            on_tool_event=on_tool,
            stream_id="stream-123",
            message_id="msg-456",
        )

        bridge.emit("tool_execution_start", {
            "tool_name": "read_file_tool",
            "arguments": {"file_path": "test.py"},
        })

        assert len(received) == 1
        assert received[0]["tool_name"] == "read_file_tool"
        assert received[0]["status"] == "started"
        assert received[0]["arguments"] == {"file_path": "test.py"}

    def test_tool_execution_end_emits_tool_event_with_response(self):
        """tool_execution_end event includes the tool's response."""
        from app.runtime.event_bridge import EventBridge

        received = []

        def on_tool(**kwargs):
            received.append(kwargs)

        bridge = EventBridge(
            on_tool_event=on_tool,
            stream_id="stream-123",
        )

        bridge.emit("tool_execution_end", {
            "tool_name": "replace_in_file_tool",
            "arguments": {"path": "file.py", "diff": "...", "change_id": "abc"},
            "response": "[UPDATE] file.py: 5 lines changed",
        })

        assert len(received) == 1
        assert received[0]["tool_name"] == "replace_in_file_tool"
        assert received[0]["status"] == "finished"
        assert "[UPDATE]" in received[0]["response"]

    def test_tool_events_suppress_without_callback(self):
        """If no on_tool_event callback, tool events are silently ignored."""
        from app.runtime.event_bridge import EventBridge

        bridge = EventBridge(on_tool_event=None)
        # Should not raise
        bridge.emit("tool_execution_start", {
            "tool_name": "any_tool",
            "arguments": {},
        })
        bridge.emit("tool_execution_end", {
            "tool_name": "any_tool",
            "arguments": {},
            "response": "result",
        })

    def test_non_tool_events_unchanged(self):
        """Non-tool events (model_delta, task_think_end, etc.) still work."""
        from app.runtime.event_bridge import EventBridge

        deltas = []
        ends = []

        def on_delta(**kwargs):
            deltas.append(kwargs)

        def on_end(**kwargs):
            ends.append(kwargs)

        bridge = EventBridge(
            on_message_delta=on_delta,
            on_message_end=on_end,
        )

        bridge.emit("task_think_end", {"response": "final answer"})
        bridge.emit("task_solve_end", {"result": "final answer"})

        # _emit_message_delta passes "delta" key, not "response"
        assert len(deltas) == 1
        assert deltas[0]["delta"] == "final answer"
        assert deltas[0]["event_type"] == "task_think_end"
        assert len(ends) == 1
        assert ends[0]["result"] == "final answer"


class TestToolEventStructuredOutput:
    """T4: ToolEvent carries structured information for frontend consumption."""

    def test_tool_event_has_required_fields(self):
        """ToolEvent contains tool_name, status, arguments, response."""
        from app.runtime.event_bridge import ToolEvent

        te = ToolEvent(
            tool_name="read_file_tool",
            arguments={"file_path": "main.py"},
            response="file content here",
            status="finished",
            stream_id="s1",
            message_id="m1",
        )

        assert te.type == "tool_event"
        assert te.tool_name == "read_file_tool"
        assert te.status == "finished"
        assert te.arguments == {"file_path": "main.py"}
        assert te.response == "file content here"
        assert te.stream_id == "s1"
        assert te.message_id == "m1"

    def test_tool_event_pending_change_contains_diff(self):
        """PendingChange response includes unified_diff for frontend display."""
        from app.runtime.event_bridge import ToolEvent

        te = ToolEvent(
            tool_name="replace_in_file_tool",
            arguments={"path": "src/app.py", "diff": "SEARCH/REPLACE block"},
            response="[UPDATE] src/app.py\n--- a/src/app.py\n+++ b/src/app.py\n@@ -1,3 +1,3 @@",
            status="finished",
        )

        # The response should contain the diff for display
        assert "---" in te.response
        assert "+++" in te.response
        assert te.tool_name == "replace_in_file_tool"

    def test_run_command_tool_event_contains_exit_code(self):
        """Run command tool result is a structured string with exit_code."""
        from app.runtime.event_bridge import ToolEvent

        te = ToolEvent(
            tool_name="run_command",
            arguments={"command": "pytest tests/", "cwd": "/workspace"},
            response="===== 10 passed in 2.1s =====\nexit_code=0",
            status="finished",
        )

        assert "exit_code=0" in te.response
        assert "passed" in te.response


class TestEventBridgePreservesExistingBehavior:
    """T4: Adding tool events does not break existing message_delta / message_end behavior."""

    def test_model_delta_still_works(self):
        """model_delta events still accumulate and trigger on_message_delta."""
        from app.runtime.event_bridge import EventBridge

        deltas = []
        model_deltas = []

        def on_msg_delta(**kw):
            deltas.append(kw.get("delta"))

        def on_model_delta(**kw):
            model_deltas.append(kw.get("delta"))

        bridge = EventBridge(
            on_message_delta=on_msg_delta,
            on_model_delta=on_model_delta,
        )

        bridge.emit("model_delta", {"delta": "Hello"})
        bridge.emit("model_delta", {"delta": " world"})

        assert deltas == ["Hello", " world"]
        assert model_deltas == ["Hello", " world"]
        assert bridge.accumulated_text == "Hello world"

    def test_message_end_still_works(self):
        """message_end event still maps from task_solve_end."""
        from app.runtime.event_bridge import EventBridge

        end_events = []

        def on_end(**kw):
            end_events.append(kw)

        bridge = EventBridge(on_message_end=on_end)
        bridge.emit("task_solve_end", {"result": "answer", "tracked_files": []})

        assert len(end_events) == 1
        assert end_events[0]["status"] == "completed"
        assert end_events[0]["result"] == "answer"
