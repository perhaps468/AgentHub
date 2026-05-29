"""M5 - Runtime Agent Service.

Drives ReactAgent and bridges runtime events to WS-compatible event stream.

Responsibilities:
- Create ReactAgent with LLMAdapter and EventBridge
- Run agent.solve_task() asynchronously
- Yield WS-compatible events (message_start, message_delta, message_end, message_error)
- Create and update agent messages in DB
- Handle error paths gracefully

Event sequence:
  message_start -> message_delta* -> message_end
or:
  message_start? -> message_error

This service is the bridge between the pure-runtime Agent and the
DB/WebSocket layer of ws.py.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.session import utcnow
from app.runtime.event_bridge import (
    EventBridge,
    MessageDeltaEvent,
    MessageEndEvent,
    MessageErrorEvent,
    MessageStartEvent,
    ToolEvent,  # T4: structured tool events
)
from app.runtime.memory import AgentMemory, Message as RuntimeMessage


def _db_message_to_runtime_message(db_msg) -> RuntimeMessage | None:
    """Map a DB Message to a runtime Message.

    Role mapping:
      human -> user
      agent -> assistant

    Filtering:
      - Only sender_type in (human, agent) are included
      - Only type == "text" messages are included
      - Empty content (after payload fallback) messages are excluded
      - System sender_type is excluded (system messages are injected by the
        agent from its own system prompt, not from DB)
    """
    sender_type = getattr(db_msg, "sender_type", None)
    if sender_type not in ("human", "agent"):
        return None

    role_map = {"human": "user", "agent": "assistant"}
    role = role_map[sender_type]

    content = getattr(db_msg, "content", "") or ""
    msg_type = getattr(db_msg, "type", "text")

    if msg_type != "text":
        return None

    # Fall back to payload.text when content is empty
    if not content:
        payload = getattr(db_msg, "payload", {}) or {}
        content = payload.get("text", "") if isinstance(payload, dict) else ""

    if not content:
        return None

    return RuntimeMessage(role=role, content=content)


def load_session_history(db: Session, session_id: str) -> list[RuntimeMessage]:
    """Load completed text messages from the session DB and convert to runtime Messages.

    Returns messages in chronological order (oldest first) as required by
    the LLM message-history format.

    Filtering rules:
      - Only sender_type in (human, agent) are included
      - Only type == "text" messages are included
      - Empty content (after payload fallback) messages are excluded
    """
    messages = (
        db.query(Message)
        .filter_by(session_id=session_id)
        .order_by(Message.created_at)
        .all()
    )
    result = []
    for db_msg in messages:
        rt_msg = _db_message_to_runtime_message(db_msg)
        if rt_msg is not None:
            result.append(rt_msg)
    return result


def _iso_now() -> str:
    return utcnow().isoformat().replace("+00:00", "Z")


class RuntimeAgentService:
    """Bridges ReactAgent to WS-compatible event stream.

    Usage::

        service = RuntimeAgentService(
            session_id=session_id,
            user_message=content,
            agent_role=agent.role,
            llm_adapter=llm_adapter,
            db=db,
            stream_id=stream_id,
        )
        async for event in service.stream_events():
            # event.type in ("message_start", "message_delta", "message_end", "message_error")
            ...
    """

    def __init__(
        self,
        session_id: str,
        user_message: str,
        agent_role: str,
        llm_adapter,  # LLMAdapter instance
        db: Session,
        stream_id: str | None = None,
        workspace_root: str | None = None,
        session_history: list[RuntimeMessage] | None = None,
    ) -> None:
        self.session_id = session_id
        self.user_message = user_message
        self.agent_role = agent_role
        self.llm_adapter = llm_adapter
        self.db = db
        self.stream_id = stream_id or str(uuid.uuid4())
        self.workspace_root = workspace_root
        # T1: pre-loaded session history to inject into agent memory
        self._session_history: list[RuntimeMessage] = session_history or []

        self._agent = None  # Initialized lazily in stream_events
        self._bridge = None  # Initialized lazily in stream_events
        self._event_queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        self._done = False

        self._agent_message: Message | None = None
        self._message_id: str = ""
        self._accumulated_content: str = ""
        self._error_emitted: bool = False  # prevent double-yielding error events

    async def stream_events(self) -> AsyncIterator[
        MessageStartEvent | MessageDeltaEvent | MessageEndEvent | MessageErrorEvent | ToolEvent  # T4: +ToolEvent
    ]:
        """Drive the agent and yield WS-compatible events.

        Lifecycle:
        1. Create agent message in DB -> yield message_start
        2. Run agent (events flow through bridge -> queue)
        3. On completion -> update message status -> yield message_end
        4. On error -> yield message_error
        """
        loop = asyncio.get_running_loop()
        done_future: asyncio.Future = asyncio.get_running_loop().create_future()

        self._bridge = EventBridge(
            on_message_start=self._on_message_start,
            on_message_delta=self._on_message_delta,
            on_message_end=self._on_message_end,
            on_message_error=self._on_message_error,
            on_model_delta=self._on_model_delta,  # T2: token-level streaming
            on_tool_event=self._on_tool_event,  # T4: structured tool events
            agent_role=self.agent_role,
            stream_id=self.stream_id,
        )
        self._bridge._message_id = self._message_id

        # We run the agent in a separate task so we can concurrently
        # drain the bridge's queue. The bridge calls `_on_*` callbacks
        # which push events into the queue.
        agent_task = asyncio.create_task(
            self._run_agent_in_background(done_future)
        )

        try:
            # Yield message_start first
            msg = self._create_agent_message()
            self._agent_message = msg
            self._message_id = msg.id

            # Update bridge with message_id so delta/end events have it
            self._bridge._message_id = msg.id

            yield MessageStartEvent(
                agent_role=self.agent_role,
                stream_id=self.stream_id,
                message=msg,
            )

            # Drain event queue until agent is done
            while not self._done:
                try:
                    event_type, data = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=30.0,
                    )
                    ws_event = self._process_bridge_event(event_type, data)
                    if ws_event:
                        yield ws_event
                except asyncio.TimeoutError:
                    # Check if agent task is still running
                    if agent_task.done():
                        self._done = True
                        break

            # Signal agent task we are done consuming
            done_future.set_result(None)

            # Drain any remaining events from queue
            while not self._event_queue.empty():
                try:
                    event_type, data = self._event_queue.get_nowait()
                    ws_event = self._process_bridge_event(event_type, data)
                    if ws_event:
                        yield ws_event
                except asyncio.QueueEmpty:
                    break

        except Exception as exc:
            done_future.set_result(None)
            agent_task.cancel()
            # Only yield error if agent didn't already emit one via _run_agent_in_background
            if not self._error_emitted:
                yield MessageErrorEvent(
                    agent_role=self.agent_role,
                    stream_id=self.stream_id,
                    message_id=self._message_id,
                    error_code="runtime_service_error",
                    error_message=str(exc),
                )
                self._mark_message_failed()
        finally:
            # Ensure agent task is cleaned up
            if not agent_task.done():
                agent_task.cancel()
                try:
                    await agent_task
                except asyncio.CancelledError:
                    pass

    def _on_message_start(self, **kwargs) -> None:
        self._event_queue.put_nowait(("message_start", kwargs))

    def _on_message_delta(self, **kwargs) -> None:
        self._accumulated_content += kwargs.get("delta", "")
        self._event_queue.put_nowait(("message_delta", kwargs))

    # T2: Real streaming: accumulate each token delta
    def _on_model_delta(self, **kwargs) -> None:
        delta = kwargs.get("delta", "")
        self._accumulated_content += delta
        self._event_queue.put_nowait(("message_delta", kwargs))

    def _on_message_end(self, **kwargs) -> None:
        self._event_queue.put_nowait(("message_end", kwargs))

    def _on_message_error(self, **kwargs) -> None:
        self._event_queue.put_nowait(("message_error", kwargs))

    def _on_tool_event(self, **kwargs) -> None:
        """Handle structured tool events from EventBridge (T4)."""
        self._event_queue.put_nowait(("tool_event", kwargs))

    async def _run_agent_in_background(self, done_future: asyncio.Future) -> None:
        """Run agent.solve_task() and propagate errors to event queue."""
        try:
            agent = self._build_agent()
            result = await agent.async_solve_task(
                self.user_message,
                max_iterations=30,
                streaming=True,  # T2: enable real token-level streaming
                clear_memory=False,  # T1: keep pre-populated session history
            )
            # Result is returned but already emitted via bridge events.
            # However, if the result is an error string, emit a message_error
            # since async_solve_task catches LLM errors internally and returns
            # "Error: ..." instead of raising.
            if isinstance(result, str) and result.startswith("Error:"):
                self._error_emitted = True
                self._event_queue.put_nowait((
                    "message_error",
                    {
                        "error_code": "runtime_error",
                        "error_message": result,
                        "event_type": "runtime_error",
                    },
                ))
            return result
        except Exception as exc:
            # Propagate runtime errors as message_error
            self._error_emitted = True
            self._event_queue.put_nowait((
                "message_error",
                {
                    "error_code": "runtime_error",
                    "error_message": str(exc),
                    "event_type": "runtime_error",
                },
            ))
            self._done = True
            raise
        finally:
            self._done = True

    def _build_agent(self):
        """Build ReactAgent with EventBridge as event_emitter and pre-populated memory."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory
        from app.runtime.prompts import system_prompt
        from app.runtime.tool_manager import ToolManager
        from app.runtime.utils import get_environment

        # Build tools list with workspace_root
        tools = self._build_tools()
        tool_manager = ToolManager(tools={tool.name: tool for tool in tools})
        environment = get_environment()
        tools_markdown = tool_manager.to_markdown()

        # T1: Pre-populate memory with session history + system prompt.
        # The system prompt goes FIRST (as required by LLM message-history format).
        # The agent's __init__ won't re-add it because we handle it here.
        memory = AgentMemory()
        system_prompt_text = system_prompt(
            tools=tools_markdown,
            environment=environment,
            expertise="General AI assistant with coding and problem-solving capabilities",
            agent_mode="react",
        )
        memory.add(RuntimeMessage(role="system", content=system_prompt_text))
        for msg in self._session_history:
            memory.add(msg)

        configured_model = getattr(getattr(self.llm_adapter, "provider", None), "_model", "")
        if configured_model:
            from loguru import logger
            logger.debug(
                "RuntimeAgentService building agent with provider model='{}', session_history_count={}",
                configured_model,
                len(self._session_history),
            )

        agent = Agent(
            model_name="",
            llm_adapter=self.llm_adapter,
            memory=memory,
            tools=tools,
            event_emitter=self._bridge,
            max_iterations=30,
        )
        return agent

    def _build_tools(self) -> list:
        """Build tool list with workspace_root injected from environment or config."""
        from app.runtime.tools.task_complete_tool import TaskCompleteTool
        from app.runtime.tools.read_file_tool import ReadFileTool
        from app.runtime.tools.list_directory_tool import ListDirectoryTool
        from app.runtime.tools.glob_tool import GlobTool
        from app.runtime.tools.grep_tool import GrepTool
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.tools.run_command_tool import RunCommandTool

        tools = []

        ws_root = self.workspace_root
        if ws_root is None:
            import os
            ws_root = os.environ.get("WORKSPACE_ROOT", "")

        for tool_cls, extra_kwargs in [
            (ReadFileTool, {"workspace_root": ws_root}),
            (ListDirectoryTool, {"workspace_root": ws_root}),
            (GlobTool, {"workspace_root": ws_root}),
            (GrepTool, {"workspace_root": ws_root}),
            (ReplaceInFileTool, {"workspace_root": ws_root}),
            (UnifiedDiffTool, {"workspace_root": ws_root}),
            (WriteFileTool, {"workspace_root": ws_root}),
            (RunCommandTool, {"workspace_root": ws_root}),
            (TaskCompleteTool, {}),
        ]:
            try:
                tools.append(tool_cls(**extra_kwargs))
            except TypeError:
                try:
                    tools.append(tool_cls())
                except TypeError:
                    pass

        return tools

    def _process_bridge_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> MessageDeltaEvent | MessageEndEvent | MessageErrorEvent | ToolEvent | None:  # T4: +ToolEvent
        """Convert bridge event data to WS event, update DB in-place."""
        if event_type == "message_start":
            return None
        elif event_type == "message_delta":
            self._update_agent_message()
            return MessageDeltaEvent(
                agent_role=self.agent_role,
                stream_id=self.stream_id,
                message_id=self._message_id,
                delta=data.get("delta", ""),
            )
        elif event_type == "message_end":
            result = data.get("result", "")
            # Prefer bridge's accumulated_text (which accumulates model deltas via
            # _emit_model_delta and task_complete responses via the fix above)
            accumulated = data.get("accumulated_text", "")
            if not accumulated and self._bridge is not None:
                accumulated = self._bridge.accumulated_text
            # Detect error strings returned by agent when LLM fails
            if isinstance(result, str) and result.startswith("Error:"):
                self._finalize_agent_message("failed")
                return MessageErrorEvent(
                    agent_role=self.agent_role,
                    stream_id=self.stream_id,
                    message_id=self._message_id,
                    error_code="runtime_error",
                    error_message=result,
                )
            # Also check accumulated text for error prefix
            if isinstance(accumulated, str) and accumulated.startswith("Error:"):
                self._finalize_agent_message("failed")
                return MessageErrorEvent(
                    agent_role=self.agent_role,
                    stream_id=self.stream_id,
                    message_id=self._message_id,
                    error_code="runtime_error",
                    error_message=accumulated,
                )
            # Use task_solve_end.result as final content (avoids leaking ReAct/XML).
            # result is the authoritative answer from the agent (e.g., task_complete answer).
            # Prefer result over accumulated (accumulated may be empty in streaming path
            # since async_solve_task returns before the WS consumer processes deltas).
            final_text = result if result else accumulated
            from loguru import logger
            if accumulated and "<action>" in accumulated:
                logger.debug(
                    "RuntimeAgentService response classified as action_call, final_content preview: {}",
                    str(final_text)[:500].replace("\n", "\\n"),
                )
            else:
                logger.debug(
                    "RuntimeAgentService response classified as direct_reply, final_content preview: {}",
                    str(final_text)[:500].replace("\n", "\\n"),
                )
            self._finalize_agent_message("completed", final_content=final_text)
            return MessageEndEvent(
                agent_role=self.agent_role,
                stream_id=self.stream_id,
                message_id=self._message_id,
                status="completed",
                final_content=final_text,
            )
        elif event_type == "message_error":
            self._mark_message_failed()
            return MessageErrorEvent(
                agent_role=self.agent_role,
                stream_id=self.stream_id,
                message_id=self._message_id,
                error_code=data.get("error_code", "runtime_error"),
                error_message=data.get("error_message", ""),
            )
        elif event_type == "tool_event":  # T4: structured tool events
            return ToolEvent(
                tool_name=data.get("tool_name", "unknown"),
                arguments=data.get("arguments", {}),
                response=data.get("response", ""),
                status=data.get("status", "started"),
                stream_id=self.stream_id,
                message_id=self._message_id,
            )
        return None

    def _create_agent_message(self) -> Message:
        """Create and persist initial agent message in DB."""
        msg = Message(
            session_id=self.session_id,
            sender_type="agent",
            sender_role=self.agent_role,
            content="",
            type="text",
            status="streaming",
            payload={"text": ""},
            msg_metadata={
                "source": "runtime_agent_service",
                "stream_id": self.stream_id,
                "render_hint": "markdown",
            },
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        self._message_id = msg.id
        return msg

    def _update_agent_message(self) -> None:
        """Update agent message with accumulated content."""
        if self._agent_message is None:
            return
        self._agent_message.content = self._accumulated_content
        self._agent_message.payload = {"text": self._accumulated_content}
        self.db.add(self._agent_message)
        self.db.commit()

    def _finalize_agent_message(self, status: str, final_content: str | None = None) -> None:
        """Finalize agent message with completed status."""
        if self._agent_message is None:
            return
        # Prefer final_content (extracted answer from task_complete) over accumulated XML
        final_text = final_content if final_content is not None else self._accumulated_content
        self._agent_message.content = final_text
        self._agent_message.payload = {"text": final_text}
        self._agent_message.status = status
        self.db.add(self._agent_message)
        self.db.commit()

    def _mark_message_failed(self) -> None:
        """Mark agent message as failed."""
        if self._agent_message is None:
            return
        self._agent_message.status = "failed"
        self.db.add(self._agent_message)
        self.db.commit()
