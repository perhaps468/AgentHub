# -*- coding: utf-8 -*-
"""Audit recorder for LLM tracing.

This module provides a singleton AuditRecorder that writes structured
audit events to JSONL files. Audit recording is non-blocking and
fault-tolerant - failures do not affect the main business flow.
"""

import json
import os
import threading
from contextvars import ContextVar
from pathlib import Path
import re
from typing import Any

from loguru import logger

from app.observability.audit_models import (
    AuditContext,
    BaseAuditEvent,
)


# Thread-local context for trace propagation
_audit_context_var: ContextVar[AuditContext | None] = ContextVar(
    "audit_context", default=None
)


class AuditRecorder:
    """Singleton audit recorder that writes events to JSONL files.

    The recorder is thread-safe and non-blocking. File write errors
    are caught and logged but do not propagate, ensuring audit
    failures do not affect the main business flow.

    Usage::

        # Get the singleton instance
        recorder = get_audit_recorder()

        # Set audit context (typically done at session start)
        context = AuditContext(
            trace_id="...",
            session_id="...",
            stream_id="...",
            message_id="...",
            agent_role="PM",
            provider="qwen",
            model="qwen-plus",
        )
        recorder.set_context(context)

        # Record events
        event = LlmRequestAuditEvent(...)
        recorder.record(event)

        # Or use convenience methods
        recorder.record_llm_request(...)
        recorder.record_llm_response(...)
    """

    _instance: "AuditRecorder | None" = None
    _lock = threading.Lock()

    def __init__(
        self,
        enabled: bool = True,
        log_path: str = "backend/.audit/llm_traces.jsonl",
        full_content: bool = True,
    ) -> None:
        """Initialize the audit recorder.

        Args:
            enabled: Whether audit recording is enabled
            log_path: Path to the JSONL log file
            full_content: Whether to record full content (vs. truncated)
        """
        self._enabled = enabled
        self._log_path = log_path
        self._full_content = full_content
        self._file_lock = threading.Lock()

        if self._enabled:
            self._ensure_directory()

    @classmethod
    def get_instance(
        cls,
        enabled: bool = True,
        log_path: str = "backend/.audit/llm_traces.jsonl",
        full_content: bool = True,
    ) -> "AuditRecorder":
        """Get or create the singleton instance.

        Args:
            enabled: Whether audit recording is enabled
            log_path: Path to the JSONL log file
            full_content: Whether to record full content (vs. truncated)

        Returns:
            The singleton AuditRecorder instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(
                        enabled=enabled,
                        log_path=log_path,
                        full_content=full_content,
                    )
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        with cls._lock:
            cls._instance = None

    def _ensure_directory(self) -> None:
        """Ensure the log directory exists."""
        try:
            log_dir = Path(self._log_path).parent
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create audit log directory: {e}")

    def set_context(self, context: AuditContext | None) -> None:
        """Set the current audit context for the current async task.

        The context is stored in a context variable, making it available
        across async boundaries within the same task.

        Args:
            context: The audit context to set, or None to clear
        """
        _audit_context_var.set(context)

    def get_context(self) -> AuditContext | None:
        """Get the current audit context from the context variable.

        Returns:
            The current audit context, or None if not set
        """
        return _audit_context_var.get()

    def record(self, event: BaseAuditEvent, context: AuditContext | None = None) -> None:
        """Record an audit event to the JSONL file.

        This method is non-blocking and fault-tolerant. Write failures
        are caught and logged but do not propagate.

        Args:
            event: The audit event to record
            context: Optional audit context (uses current context if not provided)
        """
        if not self._enabled:
            return

        # Use provided context, current context, or None
        audit_context = context or self.get_context()

        try:
            event_dict = event.to_dict(context=audit_context)
            self._write_event(event_dict)
        except Exception as e:
            # Non-blocking: log error but don't propagate
            logger.warning(f"Failed to record audit event: {e}")

    def record_raw(self, event_type: str, data: dict[str, Any]) -> None:
        """Record a raw audit event dictionary.

        Args:
            event_type: Type identifier for the event
            data: Event data dictionary
        """
        if not self._enabled:
            return

        try:
            audit_context = self.get_context()
            event_dict: dict[str, Any] = {
                "timestamp": data.get("timestamp", ""),
                "event_type": event_type,
                "source": data.get("source", "unknown"),
            }
            if audit_context:
                event_dict.update(audit_context.to_dict())
            event_dict.update(data)
            self._write_event(event_dict)
        except Exception as e:
            logger.warning(f"Failed to record raw audit event: {e}")

    def _write_event(self, event_dict: dict[str, Any]) -> None:
        """Write an event dictionary to the JSONL file.

        Args:
            event_dict: The event data to write
        """
        with self._file_lock:
            try:
                with open(
                    self._log_path,
                    "a",
                    encoding="utf-8",
                    newline="",
                ) as f:
                    json_line = json.dumps(event_dict, ensure_ascii=False)
                    f.write(json_line + "\n")
            except Exception as e:
                logger.warning(f"Failed to write audit event to file: {e}")

    def _sanitize_llm_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Remove verbose prompt scaffolding from audit logs.

        We keep the message roles for traceability, but redact:
        - full system prompts
        - runtime tool definitions / protocols
        - repeated observation scaffolding
        """
        sanitized: list[dict[str, str]] = []
        for message in messages:
            role = str(message.get("role", ""))
            content = self._sanitize_llm_message_content(role, message.get("content", ""))
            sanitized.append({
                "role": role,
                "content": content,
            })
        return sanitized

    def _sanitize_llm_message_content(self, role: str, content: Any) -> str:
        text = str(content or "").strip()
        if not text:
            return ""

        if role == "system":
            return "[omitted system prompt]"

        lowered = text.lower()
        if (
            "to accomplish this task, you have access to these tools" in lowered
            or "## tool protocol" in lowered
            or "## response requirements" in lowered
            or "available tools:" in lowered
            or "runtime tool reference" in lowered
        ):
            if role == "assistant":
                return "[omitted runtime tool instructions]"
            extracted_task = self._extract_task_text(text)
            return extracted_task or "[omitted runtime continuation prompt]"

        if "## your task to solve:" in lowered or "<task>" in lowered:
            extracted_task = self._extract_task_text(text)
            if extracted_task:
                return extracted_task

        if text.startswith("# Analysis and Next Action Decision Point"):
            extracted_task = self._extract_analysis_task(text)
            return extracted_task or "[omitted runtime continuation prompt]"

        return text

    def _extract_task_text(self, text: str) -> str:
        task_match = re.search(r"<task>\s*(.*?)\s*</task>", text, flags=re.DOTALL)
        if task_match:
            return task_match.group(1).strip()

        marker = "## Your task to solve:"
        if marker in text:
            tail = text.split(marker, 1)[1].strip()
            lines = [line.strip() for line in tail.splitlines() if line.strip()]
            if lines:
                return lines[0]
        return ""

    def _extract_analysis_task(self, text: str) -> str:
        summary_match = re.search(
            r"## Global Task summary:\s*```(.*?)```",
            text,
            flags=re.DOTALL,
        )
        if summary_match:
            return summary_match.group(1).strip()
        return ""

    # Convenience methods for common event types

    def record_llm_request(
        self,
        provider: str,
        model: str,
        request_kind: str,
        messages: list[dict[str, str]],
        base_url: str,
        stream: bool = False,
        context: AuditContext | None = None,
    ) -> None:
        """Record an LLM request event."""
        from app.observability.audit_models import LlmRequestAuditEvent

        event = LlmRequestAuditEvent(
            provider=provider,
            model=model,
            request_kind=request_kind,
            messages=self._sanitize_llm_messages(messages),
            base_url=base_url,
            stream=stream,
        )
        self.record(event, context)

    def record_llm_response(
        self,
        full_text: str,
        usage: dict[str, int] | None = None,
        finish_reason: str | None = None,
        context: AuditContext | None = None,
    ) -> None:
        """Record a non-streaming LLM response event."""
        from app.observability.audit_models import LlmResponseAuditEvent

        event = LlmResponseAuditEvent(
            full_text=full_text,
            usage=usage,
            finish_reason=finish_reason,
        )
        self.record(event, context)

    def record_llm_stream_delta(
        self,
        delta_text: str,
        sequence_index: int = 0,
        context: AuditContext | None = None,
    ) -> None:
        """Record a streaming LLM delta event."""
        from app.observability.audit_models import LlmStreamDeltaAuditEvent

        event = LlmStreamDeltaAuditEvent(
            delta_text=delta_text,
            sequence_index=sequence_index,
        )
        self.record(event, context)

    def record_llm_stream_complete(
        self,
        final_text: str,
        usage: dict[str, int] | None = None,
        finish_reason: str | None = None,
        context: AuditContext | None = None,
    ) -> None:
        """Record a streaming completion event."""
        from app.observability.audit_models import LlmStreamCompleteAuditEvent

        event = LlmStreamCompleteAuditEvent(
            final_text=final_text,
            usage=usage,
            finish_reason=finish_reason,
        )
        self.record(event, context)

    def record_llm_error(
        self,
        error_type: str,
        error_message: str,
        status_code: int | None = None,
        context: AuditContext | None = None,
    ) -> None:
        """Record an LLM error event."""
        from app.observability.audit_models import LlmErrorAuditEvent

        event = LlmErrorAuditEvent(
            error_type=error_type,
            error_message=error_message,
            status_code=status_code,
        )
        self.record(event, context)

    def record_runtime_session_start(
        self,
        user_message: str,
        workspace_root: str,
        agent_role: str,
        model: str,
        context: AuditContext | None = None,
    ) -> None:
        """Record a runtime session start event."""
        from app.observability.audit_models import RuntimeSessionStartAuditEvent

        event = RuntimeSessionStartAuditEvent(
            user_message=user_message,
            workspace_root=workspace_root,
            agent_role=agent_role,
            model=model,
        )
        self.record(event, context)

    def record_runtime_state(
        self,
        state: str,
        context: AuditContext | None = None,
    ) -> None:
        """Record a runtime state event."""
        from app.observability.audit_models import RuntimeStateAuditEvent

        event = RuntimeStateAuditEvent(state=state)
        self.record(event, context)

    def record_tool_call_start(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        context: AuditContext | None = None,
    ) -> None:
        """Record a tool call start event."""
        from app.observability.audit_models import ToolCallStartAuditEvent

        event = ToolCallStartAuditEvent(
            tool_name=tool_name,
            arguments=arguments,
        )
        self.record(event, context)

    def record_tool_call_finish(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        response: str,
        context: AuditContext | None = None,
    ) -> None:
        """Record a tool call finish event."""
        from app.observability.audit_models import ToolCallFinishAuditEvent

        event = ToolCallFinishAuditEvent(
            tool_name=tool_name,
            arguments=arguments,
            response=response,
        )
        self.record(event, context)

    def record_change_preview(
        self,
        change_id: str,
        operation: str,
        path: str,
        unified_diff: str,
        status: str,
        context: AuditContext | None = None,
    ) -> None:
        """Record a change preview event."""
        from app.observability.audit_models import ChangePreviewAuditEvent

        event = ChangePreviewAuditEvent(
            change_id=change_id,
            operation=operation,
            path=path,
            unified_diff=unified_diff,
            status=status,
        )
        self.record(event, context)

    def record_apply_result(
        self,
        change_id: str,
        success: bool,
        status: str,
        message: str,
        context: AuditContext | None = None,
    ) -> None:
        """Record an apply result event."""
        from app.observability.audit_models import ApplyResultAuditEvent

        event = ApplyResultAuditEvent(
            change_id=change_id,
            success=success,
            status=status,
            message=message,
        )
        self.record(event, context)

    def record_command_result(
        self,
        command: str,
        cwd: str,
        stdout: str,
        stderr: str,
        exit_code: int,
        success: bool,
        timed_out: bool,
        context: AuditContext | None = None,
    ) -> None:
        """Record a command result event."""
        from app.observability.audit_models import CommandResultAuditEvent

        event = CommandResultAuditEvent(
            command=command,
            cwd=cwd,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            success=success,
            timed_out=timed_out,
        )
        self.record(event, context)

    def record_preview_result(
        self,
        preview_id: str,
        workspace_id: str,
        preview_url: str,
        status: str,
        context: AuditContext | None = None,
    ) -> None:
        """Record a preview result event."""
        from app.observability.audit_models import PreviewResultAuditEvent

        event = PreviewResultAuditEvent(
            preview_id=preview_id,
            workspace_id=workspace_id,
            preview_url=preview_url,
            status=status,
        )
        self.record(event, context)

    def record_repair_state(
        self,
        state: str,
        attempt: int,
        max_attempts: int,
        message: str,
        context: AuditContext | None = None,
    ) -> None:
        """Record a repair state event."""
        from app.observability.audit_models import RepairStateAuditEvent

        event = RepairStateAuditEvent(
            state=state,
            attempt=attempt,
            max_attempts=max_attempts,
            message=message,
        )
        self.record(event, context)

    def record_message_end(
        self,
        final_content: str,
        status: str,
        context: AuditContext | None = None,
    ) -> None:
        """Record a message end event."""
        from app.observability.audit_models import MessageEndAuditEvent

        event = MessageEndAuditEvent(
            final_content=final_content,
            status=status,
        )
        self.record(event, context)

    def record_message_error(
        self,
        error_code: str,
        error_message: str,
        context: AuditContext | None = None,
    ) -> None:
        """Record a message error event."""
        from app.observability.audit_models import MessageErrorAuditEvent

        event = MessageErrorAuditEvent(
            error_code=error_code,
            error_message=error_message,
        )
        self.record(event, context)


def get_audit_recorder(
    enabled: bool = True,
    log_path: str = "backend/.audit/llm_traces.jsonl",
    full_content: bool = True,
) -> AuditRecorder:
    """Get the global AuditRecorder singleton.

    Args:
        enabled: Whether audit recording is enabled
        log_path: Path to the JSONL log file
        full_content: Whether to record full content

    Returns:
        The singleton AuditRecorder instance
    """
    return AuditRecorder.get_instance(
        enabled=enabled,
        log_path=log_path,
        full_content=full_content,
    )
