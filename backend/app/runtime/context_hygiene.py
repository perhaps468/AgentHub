"""Utilities for keeping runtime LLM context short and clean."""

from __future__ import annotations

import math
import re

from app.runtime.memory import Message

MAX_WORKING_HISTORY_MESSAGES = 12
MAX_MEMORY_MESSAGE_CHARS = 1600
MAX_PENDING_CHANGE_MEMORY_CHARS = 600

_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_WORD_RE = re.compile(r"[A-Za-z0-9_]+")
_XML_TAG_RE = re.compile(r"</?([A-Za-z_][\w\-]*)[^>]*>")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")
_PREFERRED_TAGS = (
    "answer",
    "execution_analysis",
    "decision_matrix",
    "memory_pad",
    "context_analysis",
    "thinking",
)


def collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def truncate_text(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    head = max(0, limit - 24)
    return f"{text[:head].rstrip()} ...[truncated]"


def estimate_text_tokens(text: str) -> int:
    """Heuristic token estimate that is less wrong for CJK/code/XML than len(text)//4."""
    if not text:
        return 0

    cjk_count = len(_CJK_RE.findall(text))
    word_count = len(_WORD_RE.findall(text))
    punctuation_count = len(re.findall(r"[^\w\s]", text, flags=re.UNICODE))
    whitespace_count = len(re.findall(r"\s", text))
    residual_chars = max(0, len(text) - cjk_count - whitespace_count - sum(len(w) for w in _WORD_RE.findall(text)))

    estimate = (
        cjk_count
        + math.ceil(word_count * 1.3)
        + math.ceil(punctuation_count * 0.35)
        + math.ceil(residual_chars * 0.25)
    )
    return max(1, estimate)


def strip_protocol_markup(text: str) -> str:
    if not isinstance(text, str):
        return str(text)

    stripped = _COMMENT_RE.sub(" ", text)
    stripped = _XML_TAG_RE.sub(lambda match: f" {match.group(1)} ", stripped)
    return collapse_whitespace(stripped)


def extract_preferred_protocol_text(text: str) -> str:
    if not isinstance(text, str):
        return ""

    for tag_name in _PREFERRED_TAGS:
        match = re.search(
            rf"<{tag_name}[^>]*>(.*?)</{tag_name}>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            candidate = strip_protocol_markup(match.group(1))
            if candidate:
                return candidate
    return ""


def summarize_pending_change_memory(text: str) -> str:
    change_id = _search_value(text, "change_id")
    path = _search_value(text, "path")
    operation = _search_value(text, "operation")
    parts = ["[PENDING CHANGE REVIEW REQUIRED]"]
    if change_id:
        parts.append(f"change_id={change_id}")
    if operation:
        parts.append(f"operation={operation}")
    if path:
        parts.append(f"path={path}")
    parts.append("Diff preview is available in the UI.")
    parts.append("Wait for user confirmation before apply_change.")
    return truncate_text(" ".join(parts), MAX_PENDING_CHANGE_MEMORY_CHARS)


def sanitize_memory_content(role: str, content: str, max_chars: int = MAX_MEMORY_MESSAGE_CHARS) -> str:
    if not isinstance(content, str):
        content = str(content)

    text = content.strip()
    if not text:
        return ""

    if "[PENDING CHANGE REVIEW REQUIRED]" in text or "Diff preview:" in text:
        return summarize_pending_change_memory(text)

    if role == "assistant" or "<action>" in text or "<thinking>" in text:
        text = extract_preferred_protocol_text(text) or strip_protocol_markup(text)

    return truncate_text(collapse_whitespace(text), max_chars)


def sanitize_history_messages(
    messages: list[Message],
    max_messages: int = MAX_WORKING_HISTORY_MESSAGES,
    max_chars: int = MAX_MEMORY_MESSAGE_CHARS,
) -> list[Message]:
    sanitized: list[Message] = []
    for message in messages:
        clean = sanitize_memory_content(message.role, message.content, max_chars=max_chars)
        if not clean:
            continue
        sanitized.append(Message(role=message.role, content=clean))

    if len(sanitized) <= max_messages:
        return sanitized

    trimmed = sanitized[-max_messages:]
    if trimmed and trimmed[0].role == "assistant":
        trimmed = trimmed[1:]
    return trimmed


def _search_value(text: str, key: str) -> str:
    match = re.search(rf"{re.escape(key)}=([^\s]+)", text)
    return match.group(1) if match else ""
