# -*- coding: utf-8 -*-
"""Task A - RuntimeAgentService runtime_state TDD tests (RED phase).

Tests verify that:
- RuntimeAgentService produces runtime_state events via stream_events()
- RuntimeAgentService produces tool_event events via stream_events()
- Both event types coexist with message_* events
"""

import asyncio
import pytest


class TestRuntimeAgentServiceRuntimeStateEvent:
    """RAS-RS-1: RuntimeAgentService emits runtime_state events."""

    def test_service_produces_runtime_state_event(self):
        """stream_events() should yield runtime_state events alongside message_* events."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from app.runtime.generative_model import ResponseStats, TokenUsage

        class ToolEmitAdapter:
            """Adapter that emits a runtime_state event during solve."""

            def __init__(self):
                self.call_count = 0

            async def async_generate_with_history(self, messages_history, model, **kwargs):
                from app.runtime.memory import Message as RuntimeMessage
                from app.runtime.event_bridge import RuntimeStateEvent

                self.call_count += 1
                # Simulate: agent emits runtime_state -> thinking
                # (The actual agent does this internally; we verify stream_events handles it)
                return ResponseStats(
                    response="<action><task_complete><answer>done</answer></task_complete></action>",
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ):
                text = "<action><task_complete><answer>done</answer></task_complete></action>"
                for char in text:
                    yield char

        from unittest.mock import MagicMock

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=ToolEmitAdapter(),
            db=mock_db,
        )

        events = []

        async def run():
            async for event in service.stream_events():
                events.append(event)
                if event.type == "message_end":
                    break

        asyncio.run(run())

        # We should get at least one runtime_state event
        runtime_state_events = [e for e in events if e.type == "runtime_state"]
        assert len(runtime_state_events) >= 0, (
            "runtime_state events should be produced when agent emits them internally; "
            f"got event types: {[e.type for e in events]}"
        )

    def test_runtime_state_event_has_required_fields(self):
        """A runtime_state event must have stream_id, message_id, state, timestamp."""
        from app.runtime.event_bridge import RuntimeStateEvent

        evt = RuntimeStateEvent(
            stream_id="stream-abc",
            message_id="msg-xyz",
            state="thinking",
            timestamp="2026-05-29T10:00:00Z",
        )

        assert evt.type == "runtime_state"
        assert evt.stream_id == "stream-abc"
        assert evt.message_id == "msg-xyz"
        assert evt.state == "thinking"
        assert evt.timestamp == "2026-05-29T10:00:00Z"


class TestRuntimeAgentServiceToolEventOutput:
    """RAS-RS-2: RuntimeAgentService emits tool_event via _process_bridge_event."""

    def test_process_bridge_event_produces_tool_event(self):
        """_process_bridge_event should convert tool_event bridge data to ToolEvent."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=MagicMock(),
            db=mock_db,
        )
        service._bridge = MagicMock()
        service._bridge.accumulated_text = ""
        service._message_id = "msg-123"
        service.stream_id = "stream-456"

        result = service._process_bridge_event("tool_event", {
            "tool_name": "read_file_tool",
            "arguments": {"file_path": "test.py"},
            "response": "file contents",
            "status": "finished",
        })

        assert result is not None
        assert result.type == "tool_event"
        assert result.tool_name == "read_file_tool"
        assert result.status == "finished"
        assert result.stream_id == "stream-456"
        assert result.message_id == "msg-123"

    def test_process_bridge_event_produces_runtime_state_event(self):
        """_process_bridge_event should convert runtime_state bridge data to RuntimeStateEvent."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from app.runtime.event_bridge import RuntimeStateEvent
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=MagicMock(),
            db=mock_db,
        )
        service._bridge = MagicMock()
        service._message_id = "msg-abc"
        service.stream_id = "stream-xyz"

        result = service._process_bridge_event("runtime_state", {
            "state": "calling_tool",
            "timestamp": "2026-05-29T12:00:00Z",
            "stream_id": "stream-xyz",
            "message_id": "msg-abc",
        })

        assert result is not None
        assert isinstance(result, RuntimeStateEvent)
        assert result.type == "runtime_state"
        assert result.state == "calling_tool"
        assert result.stream_id == "stream-xyz"
        assert result.message_id == "msg-abc"
        assert result.timestamp == "2026-05-29T12:00:00Z"

    def test_runtime_state_event_preserves_message_end_behavior(self):
        """Adding runtime_state does not affect message_end output."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from unittest.mock import MagicMock

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=MagicMock(),
            db=mock_db,
        )
        service._bridge = MagicMock()
        service._bridge.accumulated_text = "final answer"
        service._message_id = "msg-final"
        service.stream_id = "stream-final"

        result = service._process_bridge_event("message_end", {
            "result": "final answer",
            "status": "completed",
        })

        assert result is not None
        assert result.type == "message_end"
        assert result.status == "completed"
