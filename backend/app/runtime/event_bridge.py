"""M5 - Runtime-to-WebSocket event bridge.

Maps runtime internal events to WS protocol events.

Runtime events (from Agent._emit_event):
- session_start         -> message_start (via callback)
- task_think_end        -> message_delta (via callback, accumulates text)
- task_solve_end        -> message_end (via callback)
- error_max_iterations  -> message_error
- runtime_error         -> message_error (via callback)

WS events match the types defined in FixedAgentResponder so that ws.py
can consume both responder types through the same send helper functions.
"""

from typing import Any, Callable


class MessageStartEvent:
    """WS event: agent message started."""

    def __init__(self, agent_role: str, stream_id: str, message) -> None:
        self.type = "message_start"
        self.agent_role = agent_role
        self.stream_id = stream_id
        self.message = message


class MessageDeltaEvent:
    """WS event: text delta."""

    def __init__(self, agent_role: str, stream_id: str, message_id: str, delta: str) -> None:
        self.type = "message_delta"
        self.agent_role = agent_role
        self.stream_id = stream_id
        self.message_id = message_id
        self.delta = delta


class MessageEndEvent:
    """WS event: agent message ended."""

    def __init__(
        self,
        agent_role: str,
        stream_id: str,
        message_id: str,
        status: str,
        final_content: str | None = None,
    ) -> None:
        self.type = "message_end"
        self.agent_role = agent_role
        self.stream_id = stream_id
        self.message_id = message_id
        self.status = status
        self.final_content = final_content


class MessageErrorEvent:
    """WS event: error during agent processing."""

    def __init__(
        self,
        agent_role: str,
        stream_id: str,
        message_id: str,
        error_code: str,
        error_message: str,
    ) -> None:
        self.type = "message_error"
        self.agent_role = agent_role
        self.stream_id = stream_id
        self.message_id = message_id
        self.error_code = error_code
        self.error_message = error_message


class ToolEvent:
    """T4 - WS event: structured tool execution notification.

    Surface this to the frontend so users can see what the agent is doing
    (tool started / finished) as structured events, not just the final
    text summary.

    Attributes:
        tool_name: Name of the tool being executed.
        arguments: Tool arguments provided by the model.
        response: Tool's execution result.
        status: "started" or "finished".
        stream_id: Session stream identifier.
    """

    def __init__(
        self,
        tool_name: str,
        arguments: dict | None = None,
        response: str | None = None,
        status: str = "started",
        stream_id: str = "",
        message_id: str = "",
        agent_role: str = "",
    ) -> None:
        self.type = "tool_event"
        self.tool_name = tool_name
        self.arguments = arguments or {}
        self.response = response
        self.status = status  # "started" | "finished"
        self.stream_id = stream_id
        self.message_id = message_id
        self.agent_role = agent_role


class RuntimeStateEvent:
    """Task A - WS event: runtime execution state change notification.

    Notifies the frontend when the agent moves between execution phases
    (thinking, calling_tool, observing, responding, finished, error).
    This enables runtime process visibility and minimal replay.

    Attributes:
        stream_id: Session stream identifier.
        message_id: Message identifier.
        state: One of thinking / calling_tool / observing / responding / finished / error.
        timestamp: ISO8601 timestamp.
    """

    def __init__(
        self,
        stream_id: str = "",
        message_id: str = "",
        state: str = "thinking",
        timestamp: str = "",
    ) -> None:
        self.type = "runtime_state"
        self.stream_id = stream_id
        self.message_id = message_id
        self.state = state
        self.timestamp = timestamp


class ChangePreviewEvent:
    """Task C-2 - WS event: pending change preview notification.

    Notifies the frontend when a file write/replace produces a PendingChange.
    This enables the frontend to display the diff and provide a confirm button.

    Attributes:
        stream_id: Session stream identifier.
        message_id: Message identifier.
        change_id: Unique identifier for this pending change.
        operation: The type of change (create / update / delete).
        path: Absolute path of the target file.
        unified_diff: Human-readable unified diff string.
        status: Always "pending_confirmation" for preview changes.
        timestamp: ISO8601 timestamp.
        agent_role: The role of the agent sending this change preview.
    """

    def __init__(
        self,
        stream_id: str = "",
        message_id: str = "",
        change_id: str = "",
        operation: str = "create",
        path: str = "",
        unified_diff: str = "",
        status: str = "pending_confirmation",
        timestamp: str = "",
        agent_role: str = "PM",
    ) -> None:
        self.type = "change_preview"
        self.stream_id = stream_id
        self.message_id = message_id
        self.change_id = change_id
        self.operation = operation
        self.path = path
        self.unified_diff = unified_diff
        self.status = status
        self.timestamp = timestamp
        self.agent_role = agent_role

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "stream_id": self.stream_id,
            "message_id": self.message_id,
            "change_id": self.change_id,
            "operation": self.operation,
            "path": self.path,
            "unified_diff": self.unified_diff,
            "status": self.status,
            "timestamp": self.timestamp,
            "agent_role": self.agent_role,
        }


# Task C-4: Apply Result Event
class ApplyResultEvent:
    """Task C-4 - WS event: apply result notification.

    Notifies the frontend when a pending change has been applied or rejected.
    This enables the frontend to update the diff card status.

    Attributes:
        change_id: Unique identifier for this pending change.
        success: Whether the apply was successful.
        status: Result status: "applied", "rejected", or "failed".
        message: Human-readable result message.
        timestamp: ISO8601 timestamp.
    """

    def __init__(
        self,
        change_id: str = "",
        success: bool = True,
        status: str = "applied",
        message: str = "",
        timestamp: str = "",
    ) -> None:
        self.type = "apply_result"
        self.change_id = change_id
        self.success = success
        self.status = status
        self.message = message
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "change_id": self.change_id,
            "success": self.success,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp,
        }


# Task C-5: Command Result Event
class CommandResultEvent:
    """Task C-5 - WS event: command execution result notification.

    Notifies the frontend when a command has finished execution.
    This enables the frontend to display command results with stdout/stderr/exit_code.

    Attributes:
        command: The executed command string.
        cwd: Working directory where command was executed.
        stdout: Standard output from the command.
        stderr: Standard error from the command.
        exit_code: Process exit code.
        success: Whether the command succeeded (exit_code == 0).
        timed_out: Whether the command timed out.
        stream_id: Session stream identifier.
        message_id: Message identifier.
        timestamp: ISO8601 timestamp.
    """

    def __init__(
        self,
        command: str = "",
        cwd: str = "",
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        success: bool = True,
        timed_out: bool = False,
        stream_id: str = "",
        message_id: str = "",
        timestamp: str = "",
    ) -> None:
        self.type = "command_result"
        self.command = command
        self.cwd = cwd
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.success = success
        self.timed_out = timed_out
        self.stream_id = stream_id
        self.message_id = message_id
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "command": self.command,
            "cwd": self.cwd,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "success": self.success,
            "timed_out": self.timed_out,
            "stream_id": self.stream_id,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
        }


# Task D-1: Preview Result Event
class PreviewResultEvent:
    """Task D-1 - WS event: preview result notification.

    Notifies the frontend when a preview is ready for display.
    This enables the frontend PreviewPanel to be data-driven.

    Attributes:
        preview_id: Unique identifier for this preview.
        workspace_id: Workspace where preview was generated.
        preview_url: URL to access the preview (optional for local previews).
        status: Preview status: "ready", "generating", "error", "cancelled".
        message_id: Associated message identifier.
        stream_id: Session stream identifier.
        timestamp: ISO8601 timestamp.
    """

    def __init__(
        self,
        preview_id: str = "",
        workspace_id: str = "",
        preview_url: str = "",
        status: str = "ready",
        message_id: str = "",
        stream_id: str = "",
        timestamp: str = "",
    ) -> None:
        self.type = "preview_result"
        self.preview_id = preview_id
        self.workspace_id = workspace_id
        self.preview_url = preview_url
        self.status = status
        self.message_id = message_id
        self.stream_id = stream_id
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "preview_id": self.preview_id,
            "workspace_id": self.workspace_id,
            "preview_url": self.preview_url,
            "status": self.status,
            "message_id": self.message_id,
            "stream_id": self.stream_id,
            "timestamp": self.timestamp,
        }


class EventBridge:
    """Maps runtime events to WS protocol events.

    Implements the event_emitter interface that Agent expects
    (has emit() method). Routes runtime events to WS-compatible callbacks.

    Usage::

        bridge = EventBridge(
            on_message_start=lambda **k: ...,
            on_message_delta=lambda **k: ...,
            on_message_end=lambda **k: ...,
            on_message_error=lambda **k: ...,
        )
        agent = Agent(llm_adapter=..., event_emitter=bridge, ...)
    """

    def __init__(
        self,
        on_message_start: Callable[..., None] | None = None,
        on_message_delta: Callable[..., None] | None = None,
        on_message_end: Callable[..., None] | None = None,
        on_message_error: Callable[..., None] | None = None,
        on_model_delta: Callable[..., None] | None = None,
        on_tool_event: Callable[..., None] | None = None,  # T4: structured tool events
        on_runtime_state: Callable[..., None] | None = None,  # Task A: runtime state events
        on_change_preview: Callable[..., None] | None = None,  # Task C-2: pending change preview
        agent_role: str = "PM",
        stream_id: str = "",
        message_id: str = "",
    ) -> None:
        self._on_message_start = on_message_start
        self._on_message_delta = on_message_delta
        self._on_message_end = on_message_end
        self._on_message_error = on_message_error
        # T2: separate callback for token-level model deltas
        self._on_model_delta = on_model_delta
        # T4: structured tool events
        self._on_tool_event = on_tool_event
        # Task A: runtime state events
        self._on_runtime_state = on_runtime_state
        # Task C-2: pending change preview events
        self._on_change_preview = on_change_preview

        self._agent_role = agent_role
        self._stream_id = stream_id
        self._message_id = message_id
        self._message = None  # Set via set_message() before stream starts

        # Accumulate text across delta events (both model_delta and task_think_end)
        self._accumulated_text: str = ""
        # Track whether message_start has been emitted
        self._message_start_emitted: bool = False
        # Task A: Runtime replay nodes for minimal replay support
        self._replay_nodes: list[dict[str, Any]] = []

    def set_message(self, message, message_id: str) -> None:
        """Inject message details from RuntimeAgentService before stream starts."""
        self._message = message
        self._message_id = message_id

    def emit(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Receive runtime event and dispatch to appropriate WS callback.

        Called by Agent via Agent._emit_event().

        Event types:
          - session_start       -> _emit_message_start
          - model_delta        -> _emit_model_delta (T2: token-level streaming)
          - task_think_end     -> _emit_message_delta (non-streaming / batch)
          - task_solve_end     -> _emit_message_end
          - tool_execution_start / tool_execution_end -> _emit_tool_event (T4)
          - error_max_iterations_reached, runtime_error -> _emit_message_error
        """
        if data is None:
            data = {}

        if event_type == "session_start":
            self._emit_message_start(data)
        elif event_type == "model_delta":
            # T2: real token-level streaming from LLM
            self._emit_model_delta(data)
        elif event_type == "task_think_end":
            # Non-streaming path: one batch response per turn
            self._emit_message_delta(data)
        elif event_type == "task_solve_end":
            self._emit_message_end(data)
        elif event_type in ("tool_execution_start", "tool_execution_end"):
            # T4: structured tool events routed to WS
            self._emit_tool_event(event_type, data)
        elif event_type == "runtime_state":
            # Task A: runtime state events routed to WS
            self._emit_runtime_state(data)
        elif event_type == "change_preview":
            # Task C-2: pending change preview routed to WS
            self._emit_change_preview(data)
        elif event_type in ("error_max_iterations_reached", "runtime_error"):
            self._emit_message_error(event_type, data)
        elif event_type == "task_complete":
            # Agent called task_complete or returned plain text with no tool calls.
            # Forward as task_solve_end so the WS layer receives message_end.
            # task_complete data uses "response" for the answer; task_solve_end uses "result".
            # Extract the answer and pass it as "result" so _emit_message_end works.
            # Do NOT append to _accumulated_text — it already holds the correct final content
            # (from model_delta streaming + fallback), while "response" may be truncated.
            response_text = data.get("response", "")
            self._emit_message_end({**data, "result": response_text})
        # Other tool_* events (validation, etc.) are silently ignored

    def _emit_message_start(self, data: dict[str, Any]) -> None:
        if not self._on_message_start:
            return
        self._message_start_emitted = True
        self._on_message_start(
            event_type="session_start",
            message=self._message,  # injected by RuntimeAgentService before stream starts
            stream_id=self._stream_id,
            agent_role=self._agent_role,
        )

    def _emit_model_delta(self, data: dict[str, Any]) -> None:
        """Handle token-level model delta from streaming LLM (T2).

        NOTE: Only routes through _on_model_delta, NOT _on_message_delta.
        Routing through both causes double-delivery of each token to the
        frontend, resulting in garbled rendering (e.g. "<<") and duplicate
        content accumulation.
        """
        delta = data.get("delta", "")
        if not delta:
            return

        # Always accumulate
        self._accumulated_text += delta

        # Route to model_delta callback (T2: streaming path)
        if self._on_model_delta is not None:
            self._on_model_delta(
                event_type="model_delta",
                delta=delta,
                stream_id=self._stream_id,
                agent_role=self._agent_role,
                message_id=self._message_id,
                accumulated_text=self._accumulated_text,
            )

    def _emit_message_delta(self, data: dict[str, Any]) -> None:
        """Handle non-streaming (batch) response delta."""
        if not self._on_message_delta:
            return
        response = data.get("response", "")
        if not response:
            return
        self._accumulated_text += response
        self._on_message_delta(
            event_type="task_think_end",
            delta=response,
            stream_id=self._stream_id,
            agent_role=self._agent_role,
            message_id=self._message_id,
            accumulated_text=self._accumulated_text,
        )

    def _emit_tool_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Handle structured tool execution events (T4).

        Emits tool_execution_start and tool_execution_end as structured ToolEvent
        notifications to the WS layer via the on_tool_event callback.
        """
        if self._on_tool_event is None:
            return

        tool_name = data.get("tool_name", "unknown")
        arguments = data.get("arguments", {})
        response = data.get("response", "")

        status = "started" if event_type == "tool_execution_start" else "finished"

        self._on_tool_event(
            event_type=event_type,
            tool_name=tool_name,
            arguments=arguments,
            response=response,
            status=status,
            stream_id=self._stream_id,
            message_id=self._message_id,
        )
        # Task A: Record tool event in replay nodes
        self._push_replay_node({
            "node_type": "tool_event",
            "tool_name": tool_name,
            "tool_status": status,
            "stream_id": self._stream_id,
            "message_id": self._message_id,
            "timestamp": "",
        })

    def _emit_runtime_state(self, data: dict[str, Any]) -> None:
        """Handle runtime state change events (Task A).

        Emits runtime_state events to the WS layer via the on_runtime_state callback,
        notifying the frontend of agent execution phase transitions.
        """
        if self._on_runtime_state is None:
            return

        state = data.get("state", "thinking")
        timestamp = data.get("timestamp", "")

        self._on_runtime_state(
            event_type="runtime_state",
            state=state,
            stream_id=self._stream_id,
            message_id=self._message_id,
            timestamp=timestamp,
        )
        # Task A: Record runtime state in replay nodes
        self._push_replay_node({
            "node_type": "runtime_state",
            "state": state,
            "stream_id": self._stream_id,
            "message_id": self._message_id,
            "timestamp": timestamp,
        })

    def _emit_change_preview(self, data: dict[str, Any]) -> None:
        """Handle pending change preview events (Task C-2).

        Emits change_preview events to the WS layer via the on_change_preview callback,
        notifying the frontend of pending file changes that need user confirmation.
        """
        if self._on_change_preview is None:
            return

        self._on_change_preview(
            event_type="change_preview",
            change_id=data.get("change_id", ""),
            operation=data.get("operation", "create"),
            path=data.get("path", ""),
            unified_diff=data.get("unified_diff", ""),
            status=data.get("status", "pending_confirmation"),
            stream_id=self._stream_id,
            message_id=self._message_id,
            timestamp=data.get("timestamp", ""),
            agent_role=self._agent_role,
        )

    def _emit_message_end(self, data: dict[str, Any]) -> None:
        if not self._on_message_end:
            return
        # Determine status from result
        result = data.get("result", "")
        if result:
            status = "completed"
        else:
            status = "failed"
        self._on_message_end(
            event_type="task_solve_end",
            status=status,
            stream_id=self._stream_id,
            agent_role=self._agent_role,
            message_id=self._message_id,
            accumulated_text=self._accumulated_text,
            result=result,
        )

    def _emit_message_error(self, event_type: str, data: dict[str, Any]) -> None:
        if not self._on_message_error:
            return
        if event_type == "error_max_iterations_reached":
            code = "max_iterations_reached"
            msg = "Maximum iterations reached"
        else:
            code = "runtime_error"
            msg = data.get("error", str(data))
        self._on_message_error(
            event_type=event_type,
            error_code=code,
            error_message=msg,
            stream_id=self._stream_id,
            agent_role=self._agent_role,
            message_id=self._message_id,
        )

    @property
    def accumulated_text(self) -> str:
        """Return accumulated text across delta events."""
        return self._accumulated_text

    # Task A: Runtime replay nodes property
    @property
    def replay_nodes(self) -> list[dict[str, Any]]:
        """Return accumulated runtime replay nodes for minimal replay support."""
        return list(self._replay_nodes)

    def _push_replay_node(self, node: dict[str, Any]) -> None:
        """Add a runtime replay node to the accumulated list."""
        self._replay_nodes.append(node)
