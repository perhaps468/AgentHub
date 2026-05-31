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
from app.observability.audit_models import AuditContext
from app.observability.audit_recorder import get_audit_recorder
from app.runtime.context_hygiene import sanitize_history_messages
from app.runtime.event_bridge import (
    EventBridge,
    MessageDeltaEvent,
    MessageEndEvent,
    MessageErrorEvent,
    MessageStartEvent,
    RuntimeStateEvent,  # Task A: runtime state events
    ToolEvent,  # T4: structured tool events
    ChangePreviewEvent,  # Task C-2: pending change preview
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


class WorkspaceNotBoundError(Exception):
    """Raised when a session has no workspace binding and no fallback is available."""
    pass


class WorkspaceNotFoundError(Exception):
    """Raised when the workspace referenced by a session does not exist."""
    pass


class WorkspaceAccessDeniedError(Exception):
    """Raised when the workspace owner doesn't match the session owner."""
    pass


class WorkspaceRootInvalidError(Exception):
    """Raised when the workspace root path is inaccessible or invalid."""

    def __init__(self, root_path: str, reason: str):
        self.root_path = root_path
        self.reason = reason
        super().__init__(f"Invalid workspace root '{root_path}': {reason}")


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
        # T1: pre-loaded session history to inject into agent memory
        self._session_history: list[RuntimeMessage] = session_history or []

        # Task B: Resolve workspace from formal session binding first.
        # Priority: 1) session workspace_id binding, 2) explicit workspace_root param,
        # 3) WORKSPACE_ROOT env var (compatibility fallback).
        self._resolved_workspace_root = self._resolve_workspace_root(workspace_root)
        self.workspace_root = self._resolved_workspace_root

        self._agent = None  # Initialized lazily in stream_events
        self._bridge = None  # Initialized lazily in stream_events
        self._event_queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        self._done = False

        self._agent_message: Message | None = None
        self._message_id: str = ""
        self._accumulated_content: str = ""
        self._error_emitted: bool = False  # prevent double-yielding error events
        self._pending_change_ids: set[str] = set()

        # Audit: Create audit context for this session
        self._audit_context = AuditContext(
            session_id=session_id,
            stream_id=self.stream_id,
            agent_role=agent_role,
            provider="qwen",
            model="",
        )
        # Initialize audit recorder and set context
        self._recorder = get_audit_recorder()

    def _setup_audit_context(self) -> None:
        """Set up audit context before streaming starts."""
        # Update context with resolved workspace root
        self._audit_context.session_id = self.session_id
        self._audit_context.stream_id = self.stream_id
        self._audit_context.agent_role = self.agent_role
        self._audit_context.model = self._get_model_name()
        # Set context in the recorder for propagation
        self._recorder.set_context(self._audit_context)

    def _get_model_name(self) -> str:
        """Get the model name from the LLM adapter."""
        try:
            provider = getattr(self.llm_adapter, "provider", None)
            if provider is not None:
                model = getattr(provider, "_model", "")
                if model:
                    return model
        except Exception:
            pass
        return "qwen-plus"

    def _resolve_workspace_root(self, explicit_root: str | None) -> str:
        """Resolve workspace root from formal session binding, with fallback hierarchy.

        Priority (highest to lowest):
        1. Formal session -> workspace_id binding (checked first, NOT overridden by env)
        2. Explicit workspace_root parameter
        3. WORKSPACE_ROOT environment variable (legacy compatibility fallback)

        Raises:
            WorkspaceNotBoundError: Session has no workspace binding and no fallback.
            WorkspaceNotFoundError: Bound workspace does not exist.
            WorkspaceAccessDeniedError: Workspace owner doesn't match session owner.
            WorkspaceRootInvalidError: Workspace root path is inaccessible.
        """
        import os

        from app.models.session import ChatSession
        from app.services.workspace import WorkspaceService

        # If db.get returns a MagicMock (test scenario), treat it as no session
        session = self.db.get(ChatSession, self.session_id)
        if session is None or not isinstance(session, ChatSession):
            if explicit_root:
                return os.path.abspath(os.path.expanduser(explicit_root))
            env_root = os.environ.get("WORKSPACE_ROOT", "")
            if env_root:
                return os.path.abspath(os.path.expanduser(env_root))
            raise WorkspaceNotBoundError(
                f"No session found for session_id={self.session_id} and no workspace fallback available"
            )

        # Priority 1: Formal session workspace_id binding
        # Guard against MagicMock: workspace_id must be a non-empty string
        workspace_id = getattr(session, "workspace_id", None)
        if workspace_id and isinstance(workspace_id, str):
            ws_service = WorkspaceService(db=self.db)
            ws = ws_service.get_workspace(workspace_id)
            # Owner boundary: session owner and workspace owner must match
            if ws.owner_id != session.owner_id:
                raise WorkspaceAccessDeniedError(
                    ws.id, ws.owner_id, session.owner_id
                )
            from pathlib import Path

            try:
                p = Path(ws.root_path).expanduser().resolve()
            except (OSError, RuntimeError) as e:
                raise WorkspaceRootInvalidError(ws.root_path, str(e))
            if not p.exists():
                raise WorkspaceRootInvalidError(ws.root_path, "workspace root path does not exist")
            if not p.is_dir():
                raise WorkspaceRootInvalidError(ws.root_path, "workspace root path is not a directory")
            return str(p)

        # Priority 2: Explicit workspace_root parameter
        if explicit_root:
            return os.path.abspath(os.path.expanduser(explicit_root))

        # Priority 3: WORKSPACE_ROOT env (legacy fallback - only when session has no workspace_id)
        env_root = os.environ.get("WORKSPACE_ROOT", "")
        if env_root:
            return os.path.abspath(os.path.expanduser(env_root))

        raise WorkspaceNotBoundError(
            f"Session {self.session_id} has no workspace binding and no fallback available. "
            "Create a workspace and bind it to this session, or set WORKSPACE_ROOT."
        )

    async def stream_events(self) -> AsyncIterator[
        MessageStartEvent | MessageDeltaEvent | MessageEndEvent | MessageErrorEvent | ToolEvent | ChangePreviewEvent  # T4: +ToolEvent, C-2: +ChangePreviewEvent
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

        # Audit: Set up audit context and record session start
        self._setup_audit_context()
        self._recorder.record_runtime_session_start(
            user_message=self.user_message,
            workspace_root=self.workspace_root,
            agent_role=self.agent_role,
            model=self._get_model_name(),
            context=self._audit_context,
        )

        self._bridge = EventBridge(
            on_message_start=self._on_message_start,
            on_message_delta=self._on_message_delta,
            on_message_end=self._on_message_end,
            on_message_error=self._on_message_error,
            on_model_delta=self._on_model_delta,  # T2: token-level streaming
            on_tool_event=self._on_tool_event,  # T4: structured tool events
            on_runtime_state=self._on_runtime_state,  # Task A: runtime state events
            on_change_preview=self._on_change_preview,  # Task C-2: pending change preview
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
        # Audit: Record tool events
        status = kwargs.get("status", "started")
        tool_name = kwargs.get("tool_name", "unknown")
        if status == "started":
            self._recorder.record_tool_call_start(
                tool_name=tool_name,
                arguments=kwargs.get("arguments", {}),
                context=self._audit_context,
            )
        else:
            self._recorder.record_tool_call_finish(
                tool_name=tool_name,
                arguments=kwargs.get("arguments", {}),
                response=kwargs.get("response", ""),
                context=self._audit_context,
            )
        self._event_queue.put_nowait(("tool_event", kwargs))

    def _on_runtime_state(self, **kwargs) -> None:
        """Handle runtime state events from EventBridge (Task A)."""
        # Audit: Record runtime state changes
        self._recorder.record_runtime_state(
            state=kwargs.get("state", "thinking"),
            context=self._audit_context,
        )
        self._event_queue.put_nowait(("runtime_state", kwargs))

    def _on_change_preview(self, **kwargs) -> None:
        """Handle pending change preview events from EventBridge (Task C-2)."""
        # Audit: Record change preview events
        self._recorder.record_change_preview(
            change_id=kwargs.get("change_id", ""),
            operation=kwargs.get("operation", "create"),
            path=kwargs.get("path", ""),
            unified_diff=kwargs.get("unified_diff", ""),
            status=kwargs.get("status", "pending_confirmation"),
            context=self._audit_context,
        )
        self._event_queue.put_nowait(("change_preview", kwargs))

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
        tools_markdown = tool_manager.to_prompt_markdown()

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
        for msg in sanitize_history_messages(self._session_history):
            memory.add(msg)

        configured_model = getattr(getattr(self.llm_adapter, "provider", None), "_model", "") or "qwen-plus"
        from loguru import logger
        logger.debug(
            "RuntimeAgentService building agent with provider model='{}', session_history_count={}",
            configured_model,
            len(self._session_history),
        )

        agent = Agent(
            model_name=configured_model,
            llm_adapter=self.llm_adapter,
            memory=memory,
            tools=tools,
            event_emitter=self._bridge,
            max_iterations=30,
        )
        return agent

    def _build_tools(self) -> list:
        """Build tool list with workspace_root resolved from formal session binding.

        All file/command tools receive the same workspace_root, ensuring consistent
        boundary enforcement across the entire tool chain.
        """
        from app.runtime.tools.task_complete_tool import TaskCompleteTool
        from app.runtime.tools.read_file_tool import ReadFileTool
        from app.runtime.tools.list_directory_tool import ListDirectoryTool
        from app.runtime.tools.glob_tool import GlobTool
        from app.runtime.tools.grep_tool import GrepTool
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.tools.run_command_tool import RunCommandTool
        from app.runtime.tools.apply_change_tool import ApplyChangeTool

        tools = []

        ws_root = self.workspace_root

        for tool_cls, extra_kwargs in [
            (ReadFileTool, {"workspace_root": ws_root}),
            (ListDirectoryTool, {"workspace_root": ws_root}),
            (GlobTool, {"workspace_root": ws_root}),
            (GrepTool, {"workspace_root": ws_root}),
            (ReplaceInFileTool, {"workspace_root": ws_root}),
            (UnifiedDiffTool, {"workspace_root": ws_root}),
            (WriteFileTool, {"workspace_root": ws_root}),
            (RunCommandTool, {"workspace_root": ws_root}),
            # T3: apply_change tool for confirmed write flow
            (ApplyChangeTool, {"workspace_root": ws_root}),
            (TaskCompleteTool, {}),
        ]:
            try:
                tool = tool_cls(**extra_kwargs)
            except TypeError:
                try:
                    tool = tool_cls()
                except TypeError:
                    continue
            tools.append(tool)

        return tools

    def _process_bridge_event(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> MessageDeltaEvent | MessageEndEvent | MessageErrorEvent | ToolEvent | RuntimeStateEvent | None:  # T4 + Task A
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
                # Audit: Record message end with error status
                self._recorder.record_message_end(
                    final_content=result,
                    status="failed",
                    context=self._audit_context,
                )
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
                # Audit: Record message end with error status
                self._recorder.record_message_end(
                    final_content=accumulated,
                    status="failed",
                    context=self._audit_context,
                )
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
            # Audit: Record successful message end
            self._recorder.record_message_end(
                final_content=final_text or "",
                status="completed",
                context=self._audit_context,
            )
            return MessageEndEvent(
                agent_role=self.agent_role,
                stream_id=self.stream_id,
                message_id=self._message_id,
                status="completed",
                final_content=final_text,
            )
        elif event_type == "message_error":
            self._mark_message_failed()
            # Audit: Record message error
            self._recorder.record_message_error(
                error_code=data.get("error_code", "runtime_error"),
                error_message=data.get("error_message", ""),
                context=self._audit_context,
            )
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
        elif event_type == "runtime_state":  # Task A: runtime state events
            return RuntimeStateEvent(
                stream_id=self.stream_id,
                message_id=self._message_id,
                state=data.get("state", "thinking"),
                timestamp=data.get("timestamp", ""),
            )
        elif event_type == "change_preview":  # Task C-2: pending change preview
            self._persist_pending_change_preview(data)
            return ChangePreviewEvent(
                stream_id=self.stream_id,
                message_id=self._message_id,
                change_id=data.get("change_id", ""),
                operation=data.get("operation", "create"),
                path=data.get("path", ""),
                unified_diff=data.get("unified_diff", ""),
                status=data.get("status", "pending_confirmation"),
                timestamp=data.get("timestamp", ""),
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
        # Prefer final_content over accumulated: final_content comes from task_complete's
        # answer (which is the authoritative final response), while accumulated holds
        # streaming tokens that may be truncated.
        final_text = final_content if final_content is not None else self._accumulated_content
        self._agent_message.content = final_text
        self._agent_message.payload = {"text": final_text}
        self._agent_message.status = status
        # Task A: Persist runtime replay nodes for minimal replay support
        runtime_nodes = []
        if self._bridge is not None:
            runtime_nodes = list(self._bridge.replay_nodes)
        if runtime_nodes:
            metadata = dict(self._agent_message.msg_metadata or {})
            metadata["runtime_replay"] = runtime_nodes
            metadata["runtime_path"] = "runtime_agent_service"
            if self._pending_change_ids:
                metadata["pending_change_ids"] = sorted(self._pending_change_ids)
                metadata["has_pending_changes"] = True
            self._agent_message.msg_metadata = metadata
        elif self._pending_change_ids:
            metadata = dict(self._agent_message.msg_metadata or {})
            metadata["pending_change_ids"] = sorted(self._pending_change_ids)
            metadata["has_pending_changes"] = True
            self._agent_message.msg_metadata = metadata
        self.db.add(self._agent_message)
        self.db.commit()

    def _mark_message_failed(self) -> None:
        """Mark agent message as failed."""
        if self._agent_message is None:
            return
        self._agent_message.status = "failed"
        self.db.add(self._agent_message)
        self.db.commit()

    def _persist_pending_change_preview(self, data: dict[str, Any]) -> None:
        """Persist a change preview so it can be recovered after refresh/reconnect."""
        from app.models.pending_change import PendingChangeModel

        change_id = data.get("change_id", "")
        if not change_id:
            return

        model = (
            self.db.query(PendingChangeModel)
            .filter_by(change_id=change_id)
            .first()
        )
        if model is None:
            model = PendingChangeModel(
                change_id=change_id,
                session_id=self.session_id,
            )

        model.message_id = data.get("message_id") or self._message_id or model.message_id
        model.stream_id = data.get("stream_id") or self.stream_id or model.stream_id
        model.path = data.get("path", model.path or "")
        model.operation = data.get("operation", model.operation or "create")
        model.unified_diff = data.get("unified_diff", model.unified_diff or "")
        model.status = data.get("status", model.status or "pending_confirmation")
        self.db.add(model)
        self.db.commit()

        self._pending_change_ids.add(change_id)
        self._attach_pending_change_metadata()

    def _attach_pending_change_metadata(self) -> None:
        """Attach pending change references to the in-flight agent message metadata."""
        if self._agent_message is None or not self._pending_change_ids:
            return

        metadata = dict(self._agent_message.msg_metadata or {})
        existing = metadata.get("pending_change_ids", [])
        if not isinstance(existing, list):
            existing = []
        merged = sorted(set(existing) | self._pending_change_ids)
        metadata["pending_change_ids"] = merged
        metadata["has_pending_changes"] = True
        self._agent_message.msg_metadata = metadata
        self.db.add(self._agent_message)
        self.db.commit()
