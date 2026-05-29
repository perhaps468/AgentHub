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
    ) -> None:
        self.type = "tool_event"
        self.tool_name = tool_name
        self.arguments = arguments or {}
        self.response = response
        self.status = status  # "started" | "finished"
        self.stream_id = stream_id
        self.message_id = message_id


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

        self._agent_role = agent_role
        self._stream_id = stream_id
        self._message_id = message_id
        self._message = None  # Set via set_message() before stream starts

        # Accumulate text across delta events (both model_delta and task_think_end)
        self._accumulated_text: str = ""
        # Track whether message_start has been emitted
        self._message_start_emitted: bool = False

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
        elif event_type in ("error_max_iterations_reached", "runtime_error"):
            self._emit_message_error(event_type, data)
        elif event_type == "task_complete":
            # Agent called task_complete or returned plain text with no tool calls.
            # Forward as task_solve_end so the WS layer receives message_end.
            # task_complete data uses "response" for the answer; task_solve_end uses "result".
            # Extract the answer and pass it as "result" so _emit_message_end works.
            response_text = data.get("response", "")
            if response_text:
                self._accumulated_text += response_text
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
        """Handle token-level model delta from streaming LLM (T2)."""
        delta = data.get("delta", "")
        if not delta:
            return

        # Always accumulate
        self._accumulated_text += delta

        # Route to model_delta callback if provided (T2: streaming path)
        if self._on_model_delta is not None:
            self._on_model_delta(
                event_type="model_delta",
                delta=delta,
                stream_id=self._stream_id,
                agent_role=self._agent_role,
                message_id=self._message_id,
                accumulated_text=self._accumulated_text,
            )

        # Also emit to message_delta so the existing WS path works
        if self._on_message_delta is not None:
            self._on_message_delta(
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
