# -*- coding: utf-8 -*-
"""Audit event models for LLM tracing.

This module defines structured event models for audit logging.
All events share common fields for correlation via trace_id.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return str(uuid.uuid4())


@dataclass
class AuditContext:
    """Context for correlating audit events within a single request/response cycle.

    This context is created at the start of a runtime session and passed
    through all layers (provider, runtime, tool execution) to enable
    correlation of events via trace_id.
    """

    trace_id: str = field(default_factory=_generate_trace_id)
    session_id: str = ""
    stream_id: str = ""
    message_id: str = ""
    agent_role: str = ""
    provider: str = "qwen"
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary for embedding in events."""
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "stream_id": self.stream_id,
            "message_id": self.message_id,
            "agent_role": self.agent_role,
            "provider": self.provider,
            "model": self.model,
        }


@dataclass
class BaseAuditEvent:
    """Base class for all audit events.

    All events share common fields:
    - timestamp: ISO 8601 timestamp
    - event_type: Type identifier for the event
    - source: Source module (provider, runtime, tool, etc.)
    - trace context: trace_id, session_id, stream_id, message_id, agent_role
    """

    timestamp: str = field(default_factory=_utcnow_iso)
    event_type: str = ""
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert event to JSON-serializable dictionary."""
        raise NotImplementedError("Subclasses must implement to_dict()")

    def _base_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        """Build base dictionary with common fields."""
        result: dict[str, Any] = {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source": self.source,
        }
        if context:
            result.update(context.to_dict())
        return result


@dataclass
class LlmRequestAuditEvent(BaseAuditEvent):
    """Audit event for LLM requests.

    Records the complete request sent to the LLM provider.

    Fields:
        provider: LLM provider name (e.g., 'qwen', 'openai')
        model: Model identifier
        request_kind: Type of request ('chat', 'chat_with_messages', 'stream_chat', 'stream_chat_with_messages')
        messages: List of messages sent to the LLM
        base_url: API endpoint URL
        stream: Whether streaming was enabled
    """

    provider: str = ""
    model: str = ""
    request_kind: str = ""
    messages: list[dict[str, str]] = field(default_factory=list)
    base_url: str = ""
    stream: bool = False

    def __post_init__(self) -> None:
        self.event_type = "llm_request"
        self.source = "provider"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "provider": self.provider,
            "model": self.model,
            "request_kind": self.request_kind,
            "messages": self.messages,
            "base_url": self.base_url,
            "stream": self.stream,
        })
        return result


@dataclass
class LlmResponseAuditEvent(BaseAuditEvent):
    """Audit event for non-streaming LLM responses.

    Records the complete response from the LLM.

    Fields:
        full_text: Complete response text
        usage: Token usage statistics (if available)
        finish_reason: Reason for completion (if available)
    """

    full_text: str = ""
    usage: dict[str, int] | None = None
    finish_reason: str | None = None

    def __post_init__(self) -> None:
        self.event_type = "llm_response"
        self.source = "provider"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "full_text": self.full_text,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
        })
        return result


@dataclass
class LlmStreamDeltaAuditEvent(BaseAuditEvent):
    """Audit event for streaming LLM token deltas.

    Records each token received during streaming.

    Fields:
        delta_text: Text delta received
        sequence_index: Index of this delta in the stream
    """

    delta_text: str = ""
    sequence_index: int = 0

    def __post_init__(self) -> None:
        self.event_type = "llm_stream_delta"
        self.source = "provider"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "delta_text": self.delta_text,
            "sequence_index": self.sequence_index,
        })
        return result


@dataclass
class LlmStreamCompleteAuditEvent(BaseAuditEvent):
    """Audit event for streaming completion.

    Records the final aggregated response after streaming completes.

    Fields:
        final_text: Complete aggregated text
        usage: Token usage statistics (if available)
        finish_reason: Reason for completion (if available)
    """

    final_text: str = ""
    usage: dict[str, int] | None = None
    finish_reason: str | None = None

    def __post_init__(self) -> None:
        self.event_type = "llm_stream_complete"
        self.source = "provider"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "final_text": self.final_text,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
        })
        return result


@dataclass
class LlmErrorAuditEvent(BaseAuditEvent):
    """Audit event for LLM errors.

    Records errors encountered during LLM calls.

    Fields:
        error_type: Type of error (e.g., 'ProviderRequestError', 'ProviderResponseInvalidError')
        error_message: Human-readable error message
        status_code: HTTP status code (if applicable)
    """

    error_type: str = ""
    error_message: str = ""
    status_code: int | None = None

    def __post_init__(self) -> None:
        self.event_type = "llm_error"
        self.source = "provider"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "error_type": self.error_type,
            "error_message": self.error_message,
            "status_code": self.status_code,
        })
        return result


@dataclass
class RuntimeSessionStartAuditEvent(BaseAuditEvent):
    """Audit event for runtime session start.

    Records the beginning of a runtime execution session.

    Fields:
        user_message: User's input message
        workspace_root: Root path of the workspace
        agent_role: Role of the agent (e.g., 'PM', 'Developer')
        model: Model being used
    """

    user_message: str = ""
    workspace_root: str = ""
    agent_role: str = ""
    model: str = ""

    def __post_init__(self) -> None:
        self.event_type = "runtime_session_start"
        self.source = "runtime"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "user_message": self.user_message,
            "workspace_root": self.workspace_root,
            "agent_role": self.agent_role,
            "model": self.model,
        })
        return result


@dataclass
class RuntimeStateAuditEvent(BaseAuditEvent):
    """Audit event for runtime state changes.

    Records state transitions during agent execution.

    Fields:
        state: New runtime state (e.g., 'thinking', 'calling_tool', 'responding', 'finished', 'error')
    """

    state: str = ""

    def __post_init__(self) -> None:
        self.event_type = "runtime_state"
        self.source = "runtime"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result["state"] = self.state
        return result


@dataclass
class ToolCallStartAuditEvent(BaseAuditEvent):
    """Audit event for tool call start.

    Records the beginning of a tool execution.

    Fields:
        tool_name: Name of the tool being executed
        arguments: Tool arguments provided by the model
    """

    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.event_type = "tool_call_start"
        self.source = "tool"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        })
        return result


@dataclass
class ToolCallFinishAuditEvent(BaseAuditEvent):
    """Audit event for tool call completion.

    Records the result of a tool execution.

    Fields:
        tool_name: Name of the tool that was executed
        arguments: Tool arguments that were used
        response: Tool's execution result
    """

    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    response: str = ""

    def __post_init__(self) -> None:
        self.event_type = "tool_call_finish"
        self.source = "tool"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "response": self.response,
        })
        return result


@dataclass
class ChangePreviewAuditEvent(BaseAuditEvent):
    """Audit event for pending change previews.

    Records file changes that require user confirmation.

    Fields:
        change_id: Unique identifier for this change
        operation: Type of operation ('create', 'update', 'delete')
        path: Absolute path of the target file
        unified_diff: Human-readable unified diff string
        status: Current status of the change
    """

    change_id: str = ""
    operation: str = "create"
    path: str = ""
    unified_diff: str = ""
    status: str = "pending_confirmation"

    def __post_init__(self) -> None:
        self.event_type = "change_preview"
        self.source = "runtime"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "change_id": self.change_id,
            "operation": self.operation,
            "path": self.path,
            "unified_diff": self.unified_diff,
            "status": self.status,
        })
        return result


@dataclass
class ApplyResultAuditEvent(BaseAuditEvent):
    """Audit event for apply operation results.

    Records the result of applying or rejecting a pending change.

    Fields:
        change_id: Unique identifier of the change
        success: Whether the apply was successful
        status: Result status ('applied', 'rejected', 'failed')
        message: Human-readable result message
    """

    change_id: str = ""
    success: bool = True
    status: str = "applied"
    message: str = ""

    def __post_init__(self) -> None:
        self.event_type = "apply_result"
        self.source = "runtime"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "change_id": self.change_id,
            "success": self.success,
            "status": self.status,
            "message": self.message,
        })
        return result


@dataclass
class CommandResultAuditEvent(BaseAuditEvent):
    """Audit event for command execution results.

    Records the output of shell command executions.

    Fields:
        command: The executed command string
        cwd: Working directory where command was executed
        stdout: Standard output from the command
        stderr: Standard error from the command
        exit_code: Process exit code
        success: Whether the command succeeded
        timed_out: Whether the command timed out
    """

    command: str = ""
    cwd: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    success: bool = True
    timed_out: bool = False

    def __post_init__(self) -> None:
        self.event_type = "command_result"
        self.source = "tool"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "command": self.command,
            "cwd": self.cwd,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "success": self.success,
            "timed_out": self.timed_out,
        })
        return result


@dataclass
class PreviewResultAuditEvent(BaseAuditEvent):
    """Audit event for preview results.

    Records the completion status of preview generation.

    Fields:
        preview_id: Unique identifier for this preview
        workspace_id: Workspace where preview was generated
        preview_url: URL to access the preview
        status: Preview status ('ready', 'generating', 'error', 'cancelled')
    """

    preview_id: str = ""
    workspace_id: str = ""
    preview_url: str = ""
    status: str = "ready"

    def __post_init__(self) -> None:
        self.event_type = "preview_result"
        self.source = "runtime"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "preview_id": self.preview_id,
            "workspace_id": self.workspace_id,
            "preview_url": self.preview_url,
            "status": self.status,
        })
        return result


@dataclass
class RepairStateAuditEvent(BaseAuditEvent):
    """Audit event for self-repair state changes.

    Records self-repair attempts and outcomes.

    Fields:
        state: Current repair state
        attempt: Current attempt number
        max_attempts: Maximum number of attempts allowed
        message: Human-readable state message
    """

    state: str = ""
    attempt: int = 0
    max_attempts: int = 0
    message: str = ""

    def __post_init__(self) -> None:
        self.event_type = "repair_state"
        self.source = "runtime"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "state": self.state,
            "attempt": self.attempt,
            "max_attempts": self.max_attempts,
            "message": self.message,
        })
        return result


@dataclass
class MessageEndAuditEvent(BaseAuditEvent):
    """Audit event for message completion.

    Records the end of an agent message.

    Fields:
        final_content: Final content of the message
        status: Completion status ('completed', 'failed')
    """

    final_content: str = ""
    status: str = "completed"

    def __post_init__(self) -> None:
        self.event_type = "message_end"
        self.source = "runtime"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "final_content": self.final_content,
            "status": self.status,
        })
        return result


@dataclass
class MessageErrorAuditEvent(BaseAuditEvent):
    """Audit event for message errors.

    Records errors during message processing.

    Fields:
        error_code: Machine-readable error code
        error_message: Human-readable error message
    """

    error_code: str = ""
    error_message: str = ""

    def __post_init__(self) -> None:
        self.event_type = "message_error"
        self.source = "runtime"

    def to_dict(self, context: AuditContext | None = None) -> dict[str, Any]:
        result = self._base_dict(context)
        result.update({
            "error_code": self.error_code,
            "error_message": self.error_message,
        })
        return result
