# -*- coding: utf-8 -*-
"""Observability module for LLM tracing and audit.

This module provides structured audit logging for LLM requests, responses,
streaming events, tool calls, and runtime state changes.
"""

from app.observability.audit_recorder import AuditRecorder, get_audit_recorder
from app.observability.audit_models import (
    AuditContext,
    BaseAuditEvent,
    LlmRequestAuditEvent,
    LlmResponseAuditEvent,
    LlmStreamDeltaAuditEvent,
    LlmStreamCompleteAuditEvent,
    LlmErrorAuditEvent,
    RuntimeSessionStartAuditEvent,
    RuntimeStateAuditEvent,
    ToolCallStartAuditEvent,
    ToolCallFinishAuditEvent,
    ChangePreviewAuditEvent,
    ApplyResultAuditEvent,
    CommandResultAuditEvent,
    PreviewResultAuditEvent,
    RepairStateAuditEvent,
    MessageEndAuditEvent,
    MessageErrorAuditEvent,
)

__all__ = [
    "AuditRecorder",
    "get_audit_recorder",
    "AuditContext",
    "BaseAuditEvent",
    "LlmRequestAuditEvent",
    "LlmResponseAuditEvent",
    "LlmStreamDeltaAuditEvent",
    "LlmStreamCompleteAuditEvent",
    "LlmErrorAuditEvent",
    "RuntimeSessionStartAuditEvent",
    "RuntimeStateAuditEvent",
    "ToolCallStartAuditEvent",
    "ToolCallFinishAuditEvent",
    "ChangePreviewAuditEvent",
    "ApplyResultAuditEvent",
    "CommandResultAuditEvent",
    "PreviewResultAuditEvent",
    "RepairStateAuditEvent",
    "MessageEndAuditEvent",
    "MessageErrorAuditEvent",
]
