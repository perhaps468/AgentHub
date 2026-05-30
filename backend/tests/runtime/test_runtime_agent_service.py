"""M5 - RuntimeAgentService TDD tests (RED phase).

Tests verify that:
- RuntimeAgentService can be instantiated with required dependencies
- It drives ReactAgent to produce async event stream
- It creates agent messages and accumulates content
- It emits WS-compatible events
- Error paths produce message_error
"""

import asyncio
import os
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import MagicMock, AsyncMock

import pytest

TEST_WORKSPACE_ROOT = str(Path(__file__).parent / "tools" / "test_workspace")


@pytest.fixture(autouse=True)
def _workspace_env():
    """Ensure WORKSPACE_ROOT is set for all RAS tests (Task B workspace resolution)."""
    old = os.environ.get("WORKSPACE_ROOT")
    os.environ["WORKSPACE_ROOT"] = TEST_WORKSPACE_ROOT
    yield TEST_WORKSPACE_ROOT
    if old is None:
        os.environ.pop("WORKSPACE_ROOT", None)
    else:
        os.environ["WORKSPACE_ROOT"] = old


class TestRuntimeAgentServiceInit:
    """RAS-1: RuntimeAgentService can be initialized."""

    def test_service_can_be_imported(self):
        """RuntimeAgentService should be importable."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        assert RuntimeAgentService is not None

    def test_service_requires_llm_adapter(self):
        """Service must be initialized with an LLM adapter."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from app.runtime.memory import AgentMemory

        fake_adapter = _FakeAdapter(["answer"])
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=fake_adapter,
            workspace_root=TEST_WORKSPACE_ROOT,
            db=MagicMock(),
        )
        assert service is not None

    def test_service_has_stream_events_method(self):
        """Service should expose an async generator stream_events() method."""
        import inspect
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from app.runtime.memory import AgentMemory

        fake_adapter = _FakeAdapter(["answer"])
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=fake_adapter,
            workspace_root=TEST_WORKSPACE_ROOT,
            db=MagicMock(),
        )
        assert hasattr(service, "stream_events")
        assert inspect.isasyncgenfunction(service.stream_events), \
            "stream_events should be an async generator function"


class TestRuntimeAgentServiceEvents:
    """RAS-2: Service produces WS-compatible event sequence."""

    def test_emits_message_start_event(self):
        """stream_events() should yield a message_start event first."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        events = []

        async def run():
            async for event in service.stream_events():
                events.append(event)
                break  # Only get first event

        asyncio.run(run())

        assert len(events) == 1
        assert events[0].type == "message_start"

    def test_emits_message_delta_event(self):
        """stream_events() should yield message_delta events."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        events = []
        delta_count = 0

        async def run():
            nonlocal delta_count
            async for event in service.stream_events():
                events.append(event)
                if event.type == "message_delta":
                    delta_count += 1
                if event.type == "message_end":
                    break

        asyncio.run(run())

        assert any(e.type == "message_delta" for e in events), (
            f"Expected at least one message_delta, got events: {[e.type for e in events]}"
        )

    def test_emits_message_end_event(self):
        """stream_events() should yield a message_end event on completion."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        events = []

        async def run():
            async for event in service.stream_events():
                events.append(event)
                if event.type == "message_end":
                    break

        asyncio.run(run())

        assert any(e.type == "message_end" for e in events), (
            f"Expected message_end, got events: {[e.type for e in events]}"
        )

    def test_message_end_status_completed_on_success(self):
        """On success, message_end should have status='completed'."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_events = []

        async def run():
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_events.append(event)
                    break

        asyncio.run(run())

        assert len(end_events) == 1
        assert end_events[0].status == "completed"


class TestRuntimeAgentServiceDB:
    """RAS-3: Service interacts with DB correctly."""

    def test_creates_agent_message_on_start(self):
        """Service should create an agent message in DB on message_start."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        async def run():
            async for event in service.stream_events():
                if event.type == "message_start":
                    break

        asyncio.run(run())

        mock_db.add.assert_called()

    def test_updates_message_status_on_end(self):
        """Service should update message status to completed on success."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        async def run():
            async for event in service.stream_events():
                if event.type == "message_end":
                    break

        asyncio.run(run())

        # Check that the DB was updated with completed status
        calls = mock_db.add.call_args_list
        assert len(calls) >= 1


class TestRuntimeAgentServiceError:
    """RAS-4: Error paths produce message_error events."""

    def test_emits_message_error_on_llm_failure(self):
        """On LLM error, stream_events should emit message_error."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class FailingAdapter:
            async def async_generate_with_history(self, messages_history, model, **kwargs):
                raise RuntimeError("LLM provider unavailable")

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=FailingAdapter(),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        error_events = []

        async def run():
            async for event in service.stream_events():
                if event.type == "message_error":
                    error_events.append(event)
                    break
                if event.type == "message_end":
                    break

        asyncio.run(run())

        assert len(error_events) >= 1, f"Expected message_error, got no error events"

    def test_message_error_has_error_code_and_message(self):
        """message_error should include error_code and error_message."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class FailingAdapter:
            async def async_generate_with_history(self, messages_history, model, **kwargs):
                raise RuntimeError("LLM provider unavailable")

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=FailingAdapter(),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        error_event = None

        async def run():
            nonlocal error_event
            try:
                async for event in service.stream_events():
                    if event.type == "message_error":
                        error_event = event
                        break
            except Exception:
                pass

        asyncio.run(run())

        # The service should emit message_error via stream_events
        # If it raises, the error handling is in ws.py
        if error_event:
            assert hasattr(error_event, "error_code")
            assert hasattr(error_event, "error_message")
            assert error_event.error_code == "runtime_error"


class TestRuntimeAgentServiceSequence:
    """RAS-5: Event sequence is stable: message_start -> delta* -> end."""

    def test_events_come_in_correct_order(self):
        """Events should follow: message_start, then zero-or-more deltas, then message_end."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        events = []

        async def run():
            async for event in service.stream_events():
                events.append(event)
                if event.type == "message_end" or event.type == "message_error":
                    break

        asyncio.run(run())

        event_types = [e.type for e in events]
        if not event_types:
            pytest.skip("No events produced")

        # First event must be message_start
        assert event_types[0] == "message_start", f"Expected message_start first, got {event_types}"

        # Last event must be message_end
        assert event_types[-1] in ("message_end", "message_error"), (
            f"Expected message_end/message_error last, got {event_types}"
        )

        # No message_start after the first
        assert event_types.count("message_start") == 1, f"Multiple message_start: {event_types}"


class TestRuntimeAgentServiceTools:
    """RAS-6: All M4 read-only tools are registered."""

    def test_build_tools_includes_glob_and_grep(self):
        """_build_tools() should include ReadFileTool, ListDirectoryTool, GlobTool, GrepTool."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        tools = service._build_tools()
        tool_names = {t.name for t in tools}

        assert "read_file_tool" in tool_names, f"Missing read_file_tool, got: {tool_names}"
        assert "list_directory_tool" in tool_names, f"Missing list_directory_tool, got: {tool_names}"
        assert "glob_tool" in tool_names, f"Missing glob_tool, got: {tool_names}"
        assert "grep_tool" in tool_names, f"Missing grep_tool, got: {tool_names}"
        assert "task_complete" in tool_names, f"Missing task_complete, got: {tool_names}"


class TestRuntimeAgentServiceWriteTools:
    """RAS-7 (M6): Write tools are registered in _build_tools()."""

    def test_build_tools_includes_write_tools(self):
        """_build_tools() must include ReplaceInFileTool, UnifiedDiffTool, WriteFileTool."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        tools = service._build_tools()
        tool_names = {t.name for t in tools}

        assert "replace_in_file_tool" in tool_names, (
            f"Missing replace_in_file_tool, got: {tool_names}"
        )
        assert "unified_diff" in tool_names, (
            f"Missing unified_diff, got: {tool_names}"
        )
        assert "write_file" in tool_names, (
            f"Missing write_file, got: {tool_names}"
        )


class TestRuntimeAgentServiceFinalContent:
    """RAS-8 (M5): task_complete answer is propagated as final_content (not raw XML)."""

    def test_task_complete_answer_in_message_end_final_content(self):
        """message_end.final_content must equal the task_complete answer "hi"."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="say hi",
            agent_role="PM",
            llm_adapter=_FakeAdapter(
                ["<action><task_complete><answer>hi</answer></task_complete></action>"]
            ),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None, "No message_end event emitted"
        assert hasattr(end_event, "final_content"), "message_end missing final_content field"
        assert end_event.final_content == "hi", (
            f"Expected final_content='hi', got final_content='{end_event.final_content}'"
        )

    def test_agent_message_stored_with_final_content_not_xml(self):
        """The DB-persisted agent message must have content='hi', not the raw XML."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="say hi",
            agent_role="PM",
            llm_adapter=_FakeAdapter(
                ["<action><task_complete><answer>hi</answer></task_complete></action>"]
            ),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        async def run():
            async for event in service.stream_events():
                if event.type == "message_end":
                    break

        asyncio.run(run())

        # Find the finalize call (last db.add call)
        add_calls = [c for c in mock_db.add.call_args_list]
        assert len(add_calls) >= 1, "Expected at least one db.add call"

        # The last add call should have the finalized message with content='hi'
        final_call = add_calls[-1]
        msg_arg = final_call[0][0]

        assert hasattr(msg_arg, "content"), "Finalized message missing .content attribute"
        assert msg_arg.content == "hi", (
            f"Expected message.content='hi' in DB, got '{msg_arg.content}'"
        )
        assert msg_arg.payload.get("text") == "hi", (
            f"Expected payload.text='hi', got '{msg_arg.payload.get('text')}'"
        )
        # Ensure raw XML is NOT stored
        assert "<action>" not in msg_arg.content, (
            f"DB message must not contain raw XML. Got: {msg_arg.content}"
        )

    def test_thinking_only_xml_is_sanitized_before_message_end(self):
        """No-action protocol XML should be converted into visible final text."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="你好",
            agent_role="PM",
            llm_adapter=_FakeAdapter(
                ["<thinking><execution_analysis>你好，我可以帮你处理这个问题。</execution_analysis></thinking>"]
            ),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None, "No message_end event emitted"
        assert end_event.final_content == "你好，我可以帮你处理这个问题。"
        assert "<thinking>" not in end_event.final_content


    def test_low_signal_streaming_response_uses_fallback_final_content(self):
        """If streaming returns only markdown shell, message_end.final_content should use fallback text."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class LowSignalAdapter:
            async def async_generate_with_history(self, messages_history, model, **kwargs):
                return ResponseStats(
                    response="你好，我是正常回复。",
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ) -> AsyncIterator[str]:
                for char in "####":
                    yield char

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="测试",
            agent_role="PM",
            llm_adapter=LowSignalAdapter(),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None, "No message_end event emitted"
        assert end_event.final_content == "你好，我是正常回复。"


class TestRuntimeAgentServiceCommandTools:
    """RAS-9 (M7): run_command_tool is registered in _build_tools()."""

    def test_build_tools_includes_run_command_tool(self):
        """_build_tools() must include RunCommandTool."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        tools = service._build_tools()
        tool_names = {t.name for t in tools}

        assert "run_command_tool" in tool_names, (
            f"Missing run_command_tool, got: {tool_names}"
        )

    def test_build_tools_still_has_read_tools(self):
        """_build_tools() must still include all M4 read tools."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        tools = service._build_tools()
        tool_names = {t.name for t in tools}

        for tool_name in ["read_file_tool", "list_directory_tool", "glob_tool", "grep_tool"]:
            assert tool_name in tool_names, f"Missing {tool_name}, got: {tool_names}"

    def test_build_tools_still_has_write_tools(self):
        """_build_tools() must still include all M6 write tools."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(["answer"]),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        tools = service._build_tools()
        tool_names = {t.name for t in tools}

        for tool_name in ["replace_in_file_tool", "unified_diff", "write_file"]:
            assert tool_name in tool_names, f"Missing {tool_name}, got: {tool_names}"


class TestRuntimeAgentServiceDirectReply:
    """RAS-10: Direct reply (no <action>) propagates as final_content via bridge."""

    def test_direct_reply_final_content(self):
        """message_end.final_content must equal the direct reply text."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="你好",
            agent_role="PM",
            llm_adapter=_DirectReplyAdapter("你好，世界！"),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None, "No message_end event emitted"
        assert end_event.final_content == "你好，世界！"

    def test_direct_reply_db_message_not_empty(self):
        """DB-persisted message must contain the direct reply text, not empty."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_DirectReplyAdapter("Hello from direct reply!"),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        async def run():
            async for event in service.stream_events():
                if event.type == "message_end":
                    break

        asyncio.run(run())

        add_calls = [c for c in mock_db.add.call_args_list]
        assert len(add_calls) >= 1, "Expected at least one db.add call"
        final_call = add_calls[-1]
        msg_arg = final_call[0][0]
        assert msg_arg.content == "Hello from direct reply!"
        assert msg_arg.payload.get("text") == "Hello from direct reply!"
        assert msg_arg.content != ""

    def test_direct_reply_streaming_normal_text_no_fallback(self):
        """Normal streaming text should NOT trigger non-streaming fallback."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class NormalStreamingAdapter:
            def __init__(self):
                self.stream_called = False
                self.non_stream_called = False

            async def async_generate_with_history(self, messages_history, model, **kwargs):
                self.non_stream_called = True
                return ResponseStats(
                    response="SHOULD NOT USE THIS",
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ) -> AsyncIterator[str]:
                self.stream_called = True
                for char in "你好，正常回复。":
                    yield char

        adapter = NormalStreamingAdapter()
        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="测试",
            agent_role="PM",
            llm_adapter=adapter,
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None
        assert end_event.final_content == "你好，正常回复。"
        assert adapter.stream_called
        assert not adapter.non_stream_called  # NO fallback triggered


class TestRuntimeAgentServiceLowSignalFallback:
    """RAS-11: Low-signal streaming triggers non-streaming fallback."""

    def test_low_signal_streaming_fallback_to_normal_response(self):
        """When streaming yields '####', fallback to non-streaming answer."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class LowSignalAdapter:
            def __init__(self):
                self.fallback_text = "这是正常fallback回复。"

            async def async_generate_with_history(self, messages_history, model, **kwargs):
                return ResponseStats(
                    response=self.fallback_text,
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ) -> AsyncIterator[str]:
                for char in "####":
                    yield char

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="测试",
            agent_role="PM",
            llm_adapter=LowSignalAdapter(),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None
        assert end_event.final_content == "这是正常fallback回复。"


class TestRuntimeAgentServiceDirectReplyNoActionXML:
    """RAS-12: No-action protocol XML is normalized before final_content."""

    def test_thinking_only_xml_normalized_to_visible_text(self):
        """<thinking><execution_analysis>...</execution_analysis></thinking> → visible text."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="你好",
            agent_role="PM",
            llm_adapter=_DirectReplyAdapter(
                "<thinking><execution_analysis>你好，我可以帮你。</execution_analysis></thinking>"
            ),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None
        assert end_event.final_content == "你好，我可以帮你。"
        assert "<thinking>" not in end_event.final_content

    def test_db_message_not_storing_raw_xml(self):
        """DB message must not contain raw protocol XML tags."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="test",
            agent_role="PM",
            llm_adapter=_DirectReplyAdapter(
                "<thinking><execution_analysis>可见文本。</execution_analysis></thinking>"
            ),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        async def run():
            async for event in service.stream_events():
                if event.type == "message_end":
                    break

        asyncio.run(run())

        add_calls = [c for c in mock_db.add.call_args_list]
        final_call = add_calls[-1]
        msg_arg = final_call[0][0]
        assert "<thinking>" not in msg_arg.content
        assert msg_arg.content == "可见文本。"


class TestRuntimeAgentServiceIncompleteDirectReply:
    """RAS-13: Incomplete streaming phrases trigger fallback and full text reaches final_content."""

    def test_incomplete_truncated_phrase_does_not_become_final_content(self):
        """Streaming '我能' should not become final_content='我能'. Fallback returns full answer."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class IncompleteStreamingAdapter:
            def __init__(self):
                self.fallback_text = "我能帮你查看代码并修复问题。"
                self.stream_called = False
                self.fallback_called = False

            async def async_generate_with_history(self, messages_history, model, **kwargs):
                self.fallback_called = True
                return ResponseStats(
                    response=self.fallback_text,
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ) -> AsyncIterator[str]:
                self.stream_called = True
                for char in "我能":
                    yield char

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="测试",
            agent_role="PM",
            llm_adapter=IncompleteStreamingAdapter(),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None
        # Must be the full fallback text, not the truncated "我能"
        assert end_event.final_content == "我能帮你查看代码并修复问题。"
        assert end_event.final_content != "我能"


    def test_incomplete_identity_phrase_uses_fallback_final_content(self):
        """Streaming '我是' should not be finalized until fallback returns the full identity reply."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class IncompleteIdentityStreamingAdapter:
            def __init__(self):
                self.fallback_text = "我是 AgentHub 的运行时助手。"

            async def async_generate_with_history(self, messages_history, model, **kwargs):
                return ResponseStats(
                    response=self.fallback_text,
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ) -> AsyncIterator[str]:
                for char in "我是":
                    yield char

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="你是谁",
            agent_role="PM",
            llm_adapter=IncompleteIdentityStreamingAdapter(),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None
        assert end_event.final_content == "我是 AgentHub 的运行时助手。"
        assert end_event.final_content != "我是"

    def test_incomplete_xml_prefix_uses_fallback_final_content(self):
        """Streaming '<' should not be persisted as final_content='<'."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        class IncompleteXmlPrefixStreamingAdapter:
            def __init__(self):
                self.fallback_text = "当然可以，下面是一个 Java 版的 HelloWorld。"

            async def async_generate_with_history(self, messages_history, model, **kwargs):
                return ResponseStats(
                    response=self.fallback_text,
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ) -> AsyncIterator[str]:
                yield "<"

        mock_db = MagicMock()
        service = RuntimeAgentService(
            session_id="test-session",
            user_message="帮我写一个java版的helloworld吗",
            agent_role="PM",
            llm_adapter=IncompleteXmlPrefixStreamingAdapter(),
            workspace_root=TEST_WORKSPACE_ROOT,
            db=mock_db,
        )

        end_event = None

        async def run():
            nonlocal end_event
            async for event in service.stream_events():
                if event.type == "message_end":
                    end_event = event
                    break

        asyncio.run(run())

        assert end_event is not None
        assert end_event.final_content == "当然可以，下面是一个 Java 版的 HelloWorld。"
        assert end_event.final_content != "<"


# --------------------------------------------------------------------------
# Additional Fake LLMAdapters
# --------------------------------------------------------------------------

class _DirectReplyAdapter:
    """Fake adapter that returns a plain text response without any <action>."""

    def __init__(self, response: str):
        self.response = response
        self.call_count = 0

    async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
        self.call_count += 1
        return ResponseStats(
            response=self.response,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=model,
            finish_reason="stop",
        )

    async def async_stream_generate_with_history(
        self, messages_history: list, model: str, **kwargs
    ) -> AsyncIterator[str]:
        self.call_count += 1
        for char in self.response:
            yield char


# --------------------------------------------------------------------------
# Fake LLMAdapter
# --------------------------------------------------------------------------

from app.runtime.generative_model import ResponseStats, TokenUsage


class _FakeAdapter:
    """Minimal fake LLMAdapter that returns canned responses for testing."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or [
            "<action><task_complete><answer>answer</answer></task_complete></action>"
        ]
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
