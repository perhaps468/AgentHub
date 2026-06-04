# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger
from app.observability.audit_paths import get_group_chat_audit_log_path


# 全局事件序列计数器，用于保证跨stream的事件按顺序排列
_global_event_sequence: int = 0
_sequence_lock = threading.Lock()


def _get_next_sequence() -> int:
    """获取下一个全局事件序列号（线程安全）"""
    global _global_event_sequence
    with _sequence_lock:
        _global_event_sequence += 1
        return _global_event_sequence


def reset_event_sequence() -> None:
    """重置全局事件序列计数器（用于新session开始时）"""
    global _global_event_sequence
    with _sequence_lock:
        _global_event_sequence = 0


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _truncate_text(value: str | None, limit: int = 2000) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit] + f"... [truncated {len(text) - limit} chars]"


def _compact_value(value: Any, *, text_limit: int = 1000) -> Any:
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate_text(value, text_limit)
    if isinstance(value, dict):
        return {
            str(key): _compact_value(item, text_limit=text_limit)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_compact_value(item, text_limit=text_limit) for item in value[:20]]
    return _truncate_text(str(value), text_limit)


class GroupChatAuditRecorder:
    _instance: "GroupChatAuditRecorder | None" = None
    _lock = threading.Lock()

    def __init__(
        self,
        enabled: bool = True,
        log_path: str | None = None,
    ) -> None:
        self._enabled = enabled
        self._log_path = log_path or get_group_chat_audit_log_path()
        self._file_lock = threading.Lock()
        if self._enabled:
            self._ensure_directory()

    @classmethod
    def get_instance(
        cls,
        enabled: bool = True,
        log_path: str | None = None,
    ) -> "GroupChatAuditRecorder":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(enabled=enabled, log_path=log_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        with cls._lock:
            cls._instance = None

    def _ensure_directory(self) -> None:
        try:
            Path(self._log_path).parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning(f"Failed to create group chat audit directory: {exc}")

    def record(self, event_type: str, **data: Any) -> None:
        if not self._enabled:
            return
        event = {
            "timestamp": _utcnow_iso(),
            "event_type": event_type,
            "sequence": _get_next_sequence(),
            **{key: _compact_value(value) for key, value in data.items() if value is not None},
        }
        try:
            self._write_event(event)
        except Exception as exc:
            logger.warning(f"Failed to record group chat audit event: {exc}")

    def _write_event(self, event: dict[str, Any]) -> None:
        with self._file_lock:
            with open(self._log_path, "a", encoding="utf-8", newline="") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def record_user_message(
        self,
        *,
        session_id: str,
        message_id: str,
        content: str,
        mode: str,
    ) -> None:
        self.record(
            "user_message",
            session_id=session_id,
            message_id=message_id,
            mode=mode,
            content=content,
        )

    def record_run_created(
        self,
        *,
        session_id: str,
        run_id: str,
        trigger_message_id: str,
        planner_agent_id: str,
        planner_role: str,
        summary: str | None,
        tasks: list[dict[str, Any]],
    ) -> None:
        self.record(
            "orchestration_run_created",
            session_id=session_id,
            run_id=run_id,
            trigger_message_id=trigger_message_id,
            planner_agent_id=planner_agent_id,
            planner_role=planner_role,
            summary=summary,
            task_count=len(tasks),
            tasks=tasks,
        )

    def record_plan_published(
        self,
        *,
        session_id: str,
        run_id: str,
        planner_agent_id: str,
        planner_role: str,
        plan_message_id: str,
        summary: str,
    ) -> None:
        self.record(
            "orchestration_plan_published",
            session_id=session_id,
            run_id=run_id,
            planner_agent_id=planner_agent_id,
            planner_role=planner_role,
            message_id=plan_message_id,
            summary=summary,
        )

    def record_group_response(
        self,
        *,
        session_id: str,
        stream_id: str,
        agent_role: str,
        final_content: str,
        source: str,
    ) -> None:
        self.record(
            "group_response",
            session_id=session_id,
            stream_id=stream_id,
            agent_role=agent_role,
            final_content=final_content,
            source=source,
        )

    def record_task_started(
        self,
        *,
        session_id: str,
        run_id: str,
        task_id: str,
        stream_id: str,
        agent_id: str,
        agent_role: str,
        title: str,
        goal: str,
        input_payload: dict[str, Any],
        user_request: str | None,
        planner_summary: str | None,
    ) -> None:
        self.record(
            "task_started",
            session_id=session_id,
            run_id=run_id,
            task_id=task_id,
            stream_id=stream_id,
            agent_id=agent_id,
            agent_role=agent_role,
            title=title,
            goal=goal,
            input_payload=input_payload,
            user_request=user_request,
            planner_summary=planner_summary,
        )

    def record_task_status_changed(
        self,
        *,
        session_id: str,
        run_id: str,
        task_id: str,
        agent_id: str,
        from_status: str,
        to_status: str,
        stream_id: str | None = None,
        title: str | None = None,
        result_payload: dict[str, Any] | None = None,
        error_payload: dict[str, Any] | None = None,
        final_output: str | None = None,
        change_id: str | None = None,
    ) -> None:
        self.record(
            "task_status_changed",
            session_id=session_id,
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
            stream_id=stream_id,
            title=title,
            from_status=from_status,
            to_status=to_status,
            result_payload=result_payload,
            error_payload=error_payload,
            final_output=final_output,
            change_id=change_id,
        )

    def record_pending_change_decision(
        self,
        *,
        session_id: str,
        run_id: str | None,
        task_id: str | None,
        agent_id: str | None,
        change_id: str,
        decision: str,
        path: str,
        operation: str,
        status: str,
        message: str,
    ) -> None:
        self.record(
            "pending_change_decision",
            session_id=session_id,
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
            change_id=change_id,
            decision=decision,
            path=path,
            operation=operation,
            status=status,
            message=message,
        )

    def record_run_finished(
        self,
        *,
        session_id: str,
        run_id: str,
        status: str,
        summary: str | None,
        tasks: list[dict[str, Any]],
    ) -> None:
        self.record(
            "orchestration_run_finished",
            session_id=session_id,
            run_id=run_id,
            status=status,
            summary=summary,
            tasks=tasks,
        )

    def record_fallback_decision(
        self,
        *,
        session_id: str,
        run_id: str | None,
        planner_agent_id: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """记录fallback触发决策

        Args:
            session_id: session ID
            run_id: run ID（如果有）
            planner_agent_id: 主agent ID
            reason: fallback原因（如 "planner_parse_failed", "planner_validation_failed", "planner_llm_failed"）
            details: 额外详情
        """
        self.record(
            "fallback_decision",
            session_id=session_id,
            run_id=run_id,
            planner_agent_id=planner_agent_id,
            reason=reason,
            details=details,
        )

    def record_fallback_task_allocation(
        self,
        *,
        session_id: str,
        run_id: str,
        planner_agent_id: str,
        user_request: str,
        planned_tasks: list[dict[str, Any]],
        agent_ids: list[str],
    ) -> None:
        """记录fallback任务分配详情

        Args:
            session_id: session ID
            run_id: run ID
            planner_agent_id: 主agent ID
            user_request: 用户原始请求
            planned_tasks: 计划的任务列表
            agent_ids: 可用的agent ID列表
        """
        self.record(
            "fallback_task_allocation",
            session_id=session_id,
            run_id=run_id,
            planner_agent_id=planner_agent_id,
            user_request=user_request,
            task_count=len(planned_tasks),
            planned_tasks=[
                {
                    "sequence": task.get("sequence"),
                    "title": task.get("title"),
                    "assigned_agent_id": task.get("assigned_agent_id"),
                }
                for task in planned_tasks
            ],
            available_agents=agent_ids,
        )


def get_group_chat_audit_recorder() -> GroupChatAuditRecorder:
    enabled = os.getenv("GROUP_CHAT_AUDIT_ENABLED", "1") not in {"0", "false", "False"}
    log_path = os.getenv("GROUP_CHAT_AUDIT_LOG_PATH") or get_group_chat_audit_log_path()
    return GroupChatAuditRecorder.get_instance(enabled=enabled, log_path=log_path)
