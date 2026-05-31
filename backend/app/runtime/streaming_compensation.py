# -*- coding: utf-8 -*-
"""Task CE: Streaming Failure Compensation.

This module provides compensation logic for streaming failures during agent execution.
When streaming starts but then fails, this module attempts a non-streaming fallback
to ensure the user always gets a complete response or a clear error.

From migration doc section 5.4:
- If streaming started but upstream failed, try non-streaming compensation once
- Only attempt within the same round, avoid infinite loops
- Record failure type for observability

Design principle: Never let connection close be the only way to end
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class StreamingFailureType(str, Enum):
    """Types of streaming failures."""
    UPSTREAM_TIMEOUT = "upstream_timeout"
    NETWORK_RESET = "network_reset"
    INVALID_STREAM_PAYLOAD = "invalid_stream_payload"
    UNKNOWN = "unknown"


@dataclass
class CompensationResult:
    """Result of a compensation attempt."""
    success: bool
    final_content: Optional[str] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class FailureRecord:
    """Record of a streaming failure for logging and observability."""
    failure_type: StreamingFailureType
    error_message: str
    stream_id: Optional[str] = None
    session_id: Optional[str] = None
    compensation_attempted: bool = False
    compensation_success: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization."""
        return {
            "failure_type": self.failure_type.value,
            "error_message": self.error_message,
            "stream_id": self.stream_id,
            "session_id": self.session_id,
            "compensation_attempted": self.compensation_attempted,
            "compensation_success": self.compensation_success,
            "timestamp": self.timestamp.isoformat(),
        }


def detect_failure_type(error_message: str) -> StreamingFailureType:
    """Detect the type of streaming failure from error message.

    Args:
        error_message: The error message to analyze.

    Returns:
        StreamingFailureType enum value.
    """
    error_lower = error_message.lower()

    # Upstream timeout patterns
    timeout_patterns = [
        "timeout",
        "timed out",
        "request timeout",
        "upstream timeout",
        "connection timeout",
        "read timeout",
    ]
    for pattern in timeout_patterns:
        if pattern in error_lower:
            return StreamingFailureType.UPSTREAM_TIMEOUT

    # Network reset patterns
    network_patterns = [
        "connection reset",
        "network error",
        "network unreachable",
        "connection closed",
        "broken pipe",
        "connection aborted",
        "connectionrefused",
        "connectionaborted",
        "eof",
    ]
    for pattern in network_patterns:
        if pattern in error_lower:
            return StreamingFailureType.NETWORK_RESET

    # Invalid stream payload patterns
    payload_patterns = [
        "invalid stream",
        "malformed response",
        "json decode",
        "json decode error",
        "stream parse",
        "unexpected token",
    ]
    for pattern in payload_patterns:
        if pattern in error_lower:
            return StreamingFailureType.INVALID_STREAM_PAYLOAD

    return StreamingFailureType.UNKNOWN


class StreamingCompensator:
    """Handles streaming failure compensation.

    When streaming starts but then fails, this class determines whether
    compensation should be attempted and manages the compensation state.
    """

    def __init__(self, max_attempts: int = 1):
        """Initialize the compensator.

        Args:
            max_attempts: Maximum number of compensation attempts (default 1).
        """
        self.max_attempts = max_attempts
        self._attempts_made = 0

    def should_compensate(
        self,
        has_started_streaming: bool,
        accumulated_content: str,
    ) -> bool:
        """Determine if compensation should be attempted.

        Args:
            has_started_streaming: Whether streaming has started.
            accumulated_content: Content accumulated so far from streaming.

        Returns:
            True if compensation should be attempted.
        """
        if not has_started_streaming:
            return False

        if not accumulated_content or not accumulated_content.strip():
            return False

        if self._attempts_made >= self.max_attempts:
            return False

        return True

    def can_retry(self) -> bool:
        """Check if another compensation attempt is allowed.

        Returns:
            True if max attempts not yet reached.
        """
        return self._attempts_made < self.max_attempts

    def mark_compensation_attempted(self) -> None:
        """Mark that a compensation attempt has been made."""
        self._attempts_made += 1

    def reset(self) -> None:
        """Reset the compensator for a new round."""
        self._attempts_made = 0

    def create_failure_record(
        self,
        failure_type: StreamingFailureType,
        error_message: str,
        stream_id: Optional[str] = None,
        session_id: Optional[str] = None,
        compensation_success: bool = False,
    ) -> FailureRecord:
        """Create a failure record for logging.

        Args:
            failure_type: Type of failure detected.
            error_message: Error message from the failure.
            stream_id: Associated stream ID.
            session_id: Associated session ID.
            compensation_success: Whether compensation succeeded.

        Returns:
            FailureRecord instance.
        """
        return FailureRecord(
            failure_type=failure_type,
            error_message=error_message,
            stream_id=stream_id,
            session_id=session_id,
            compensation_attempted=self._attempts_made > 0,
            compensation_success=compensation_success,
        )
