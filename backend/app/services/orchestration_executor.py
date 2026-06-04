# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass
from typing import Any, AsyncGenerator

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.message import Message
from app.models.orchestration import OrchestrationRun, OrchestrationTask
from app.models.pending_change import PendingChangeModel
from app.models.session_member import SessionMember
from app.observability.group_chat_audit import get_group_chat_audit_recorder
from app.runtime.memory import Message as RuntimeMessage
from app.runtime.runtime_agent_service import RuntimeAgentService
from app.schemas.common import to_iso_z
from app.services.agent_runtime import get_provider_for_agent
from app.services.fixed_agent_responder import FixedAgentResponder


@dataclass
class TaskContext:
    task_id: str
    run_id: str
    session_id: str
    agent_id: str
    agent_role: str
    agent_name: str
    goal: str
    title: str
    input_payload: dict[str, Any]
    user_request: str | None = None
    planner_summary: str | None = None


class OrchestrationExecutor:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._group_chat_audit = get_group_chat_audit_recorder()

    def _generate_stream_id(self, task_id: str) -> str:
        return str(uuid.uuid4())

    def get_task(self, task_id: str) -> OrchestrationTask | None:
        return self.db.get(OrchestrationTask, task_id)

    def get_run(self, run_id: str) -> OrchestrationRun | None:
        return self.db.get(OrchestrationRun, run_id)

    def get_agent(self, agent_id: str) -> Agent | None:
        return self.db.get(Agent, agent_id)

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result_payload: dict | None = None,
        error_payload: dict | None = None,
    ) -> OrchestrationTask | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        previous_status = task.status

        task.status = status
        if result_payload is not None:
            task.result_payload = result_payload
        if error_payload is not None:
            task.error_payload = error_payload

        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self._group_chat_audit.record_task_status_changed(
            session_id=task.run.session_id if task.run is not None else "",
            run_id=task.run_id,
            task_id=task.id,
            agent_id=task.assigned_agent_id,
            stream_id=((task.result_payload or {}).get("stream_id") if isinstance(task.result_payload, dict) else None),
            title=task.title,
            from_status=previous_status,
            to_status=status,
            result_payload=result_payload,
            error_payload=error_payload,
            final_output=((result_payload or {}).get("final_content") if isinstance(result_payload, dict) else None),
            change_id=((result_payload or {}).get("change_id") if isinstance(result_payload, dict) else None),
        )
        return task

    def build_task_context(self, task_id: str) -> TaskContext | None:
        task = self.get_task(task_id)
        if task is None or task.run is None:
            return None

        run = task.run
        trigger_message = self.db.get(Message, run.trigger_message_id) if run.trigger_message_id else None
        agent = self.get_agent(task.assigned_agent_id)
        agent_role = getattr(agent, "role", None) or task.assigned_agent_id

        return TaskContext(
            task_id=task.id,
            run_id=task.run_id,
            session_id=run.session_id,
            agent_id=task.assigned_agent_id,
            agent_role=agent_role,
            agent_name=getattr(agent, "name", None) or task.assigned_agent_id,
            goal=task.goal,
            title=task.title,
            input_payload=task.input_payload or {},
            user_request=trigger_message.content if trigger_message is not None else None,
            planner_summary=run.summary,
        )

    def build_task_start_event(
        self,
        task_id: str,
        stream_id: str | None = None,
    ) -> dict[str, Any] | None:
        task = self.get_task(task_id)
        if task is None:
            return None

        return {
            "type": "task_start",
            "run_id": task.run_id,
            "task_id": task.id,
            "agent_id": task.assigned_agent_id,
            "stream_id": stream_id or self._generate_stream_id(task_id),
            "title": task.title,
            "goal": task.goal,
            "kind": task.kind,
            "timestamp": _utcnow_iso(),
        }

    def build_task_end_event(
        self,
        task_id: str,
        status: str,
        stream_id: str,
        result: dict | None = None,
    ) -> dict[str, Any] | None:
        task = self.get_task(task_id)
        if task is None:
            return None

        return {
            "type": "task_end",
            "run_id": task.run_id,
            "task_id": task.id,
            "agent_id": task.assigned_agent_id,
            "stream_id": stream_id,
            "status": status,
            "result": result,
            "timestamp": _utcnow_iso(),
        }

    def build_task_error_event(
        self,
        task_id: str,
        stream_id: str,
        error_code: str,
        error_message: str,
    ) -> dict[str, Any] | None:
        task = self.get_task(task_id)
        if task is None:
            return None

        return {
            "type": "task_error",
            "run_id": task.run_id,
            "task_id": task.id,
            "agent_id": task.assigned_agent_id,
            "stream_id": stream_id,
            "error_code": error_code,
            "error_message": error_message,
            "timestamp": _utcnow_iso(),
        }

    def build_task_history(self, task_id: str) -> list[RuntimeMessage]:
        context = self.build_task_context(task_id)
        if context is None:
            return []

        history: list[RuntimeMessage] = []
        if context.user_request:
            history.append(RuntimeMessage(role="user", content=context.user_request))

        if context.planner_summary:
            history.append(RuntimeMessage(role="assistant", content=f"Planner summary: {context.planner_summary}"))

        history.append(
            RuntimeMessage(
                role="user",
                content=(
                    f"Task title: {context.title}\n"
                    f"Task goal: {context.goal}\n"
                    f"Task input: {context.input_payload}"
                ),
            )
        )

        prior_messages = (
            self.db.query(Message)
            .filter(Message.session_id == context.session_id)
            .order_by(Message.created_at.asc())
            .all()
        )
        for message in prior_messages:
            metadata = message.msg_metadata or {}
            if metadata.get("task_id") != task_id:
                continue
            if message.sender_type not in ("human", "agent"):
                continue
            content = message.content or message.payload.get("text", "")
            if not content:
                continue
            history.append(
                RuntimeMessage(
                    role="assistant" if message.sender_type == "agent" else "user",
                    content=content,
                )
            )

        return history

    async def execute_task(
        self,
        task_id: str,
        stream_id: str | None = None,
    ) -> dict[str, Any]:
        task = self.get_task(task_id)
        if task is None:
            return {"status": "failed", "error": f"Task {task_id} not found"}

        active_stream_id = stream_id or self._generate_stream_id(task_id)
        context = self.build_task_context(task_id)
        if context is not None:
            self._group_chat_audit.record_task_started(
                session_id=context.session_id,
                run_id=context.run_id,
                task_id=context.task_id,
                stream_id=active_stream_id,
                agent_id=context.agent_id,
                agent_role=context.agent_role,
                title=context.title,
                goal=context.goal,
                input_payload=context.input_payload,
                user_request=context.user_request,
                planner_summary=context.planner_summary,
            )
        self.update_task_status(task_id, "running", result_payload={"stream_id": active_stream_id})

        try:
            result = await self._execute_runtime(task, active_stream_id)
            refreshed_task = self.get_task(task_id)
            if refreshed_task is not None and refreshed_task.status != "waiting_confirmation":
                self.update_task_status(
                    task_id,
                    "completed",
                    result_payload={"stream_id": active_stream_id, **result},
                )
                refreshed_task = self.get_task(task_id)
            return {
                "status": refreshed_task.status if refreshed_task is not None else "completed",
                "task_id": task_id,
                "stream_id": active_stream_id,
                "result": result,
            }
        except Exception as exc:
            error_payload = {
                "stream_id": active_stream_id,
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
            self.update_task_status(task_id, "failed", error_payload=error_payload)
            return {
                "status": "failed",
                "task_id": task_id,
                "stream_id": active_stream_id,
                "error": str(exc),
            }

    async def stream_task_events(
        self,
        task_id: str,
        stream_id: str,
    ) -> AsyncGenerator[Any, None]:
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")

        context = self.build_task_context(task_id)
        if context is None:
            raise ValueError(f"Could not build context for task {task_id}")

        self._group_chat_audit.record_task_started(
            session_id=context.session_id,
            run_id=context.run_id,
            task_id=context.task_id,
            stream_id=stream_id,
            agent_id=context.agent_id,
            agent_role=context.agent_role,
            title=context.title,
            goal=context.goal,
            input_payload=context.input_payload,
            user_request=context.user_request,
            planner_summary=context.planner_summary,
        )
        self.update_task_status(task_id, "running", result_payload={"stream_id": stream_id})

        try:
            event_source = self._build_event_source(task, context, stream_id)
            last_message_id = ""
            final_content: str | None = None

            async for event in event_source:
                self._enrich_event(event, task, stream_id)
                if hasattr(event, "message") and getattr(event.message, "msg_metadata", None) is not None:
                    self._merge_message_metadata(event.message, task, stream_id)
                if getattr(event, "message_id", None):
                    last_message_id = event.message_id
                if getattr(event, "type", None) == "message_end":
                    final_content = getattr(event, "final_content", None)
                yield event

            result_payload = {"stream_id": stream_id}
            if last_message_id:
                result_payload["message_id"] = last_message_id
            if final_content is not None:
                result_payload["final_content"] = final_content

            refreshed_task = self.get_task(task_id)
            if refreshed_task is not None and refreshed_task.status == "waiting_confirmation":
                self.update_task_status(task_id, "waiting_confirmation", result_payload=result_payload)
            else:
                self.update_task_status(task_id, "completed", result_payload=result_payload)
        except Exception as exc:
            self.update_task_status(
                task_id,
                "failed",
                error_payload={
                    "stream_id": stream_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise

    async def _execute_runtime(
        self,
        task: OrchestrationTask,
        stream_id: str,
    ) -> dict[str, Any]:
        events = []
        async for event in self.stream_task_events(task.id, stream_id):
            events.append(event)

        message_end = next(
            (event for event in reversed(events) if getattr(event, "type", None) == "message_end"),
            None,
        )
        final_content = getattr(message_end, "final_content", None) if message_end is not None else None
        return {
            "executed": True,
            "stream_id": stream_id,
            "final_content": final_content,
        }

    async def execute_tasks_parallel(self, task_ids: list[str]) -> list[dict[str, Any]]:
        coroutines = [self.execute_task(task_id) for task_id in task_ids]
        results = await asyncio.gather(*coroutines, return_exceptions=True)

        processed_results = []
        for index, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "status": "failed",
                    "task_id": task_ids[index],
                    "error": str(result),
                })
            else:
                processed_results.append(result)
        return processed_results

    async def execute_run(self, run_id: str) -> list[dict[str, Any]]:
        run = self.get_run(run_id)
        if run is None:
            return [{"status": "failed", "error": f"Run {run_id} not found"}]

        planned_tasks = [task for task in run.tasks if task.status == "planned"]
        if not planned_tasks:
            return [{"status": "skipped", "reason": "No planned tasks"}]

        return await self.execute_tasks_parallel([task.id for task in planned_tasks])

    def _build_event_source(
        self,
        task: OrchestrationTask,
        context: TaskContext,
        stream_id: str,
    ):
        agent = self.get_agent(task.assigned_agent_id)
        if agent is None:
            raise ValueError(f"Assigned agent {task.assigned_agent_id} not found")

        prompt = context.goal
        if task.input_payload:
            prompt = f"{context.goal}\n\nTask input:\n{task.input_payload}"

        if runtime_use_runtime_agent():
            try:
                from app.runtime.llm_adapter import LLMAdapter

                provider = get_provider_for_agent(agent)
                llm_adapter = LLMAdapter(provider=provider)
                return RuntimeAgentService(
                    session_id=context.session_id,
                    user_message=prompt,
                    agent_role=context.agent_role,
                    llm_adapter=llm_adapter,
                    db=self.db,
                    stream_id=stream_id,
                    session_history=self.build_task_history(task.id),
                    run_id=context.run_id,
                    task_id=context.task_id,
                    task_agent_id=context.agent_id,
                ).stream_events()
            except Exception:
                pass

        return FixedAgentResponder(
            session_id=context.session_id,
            user_message=prompt,
            agent_role=context.agent_role,
            db=self.db,
            stream_id=stream_id,
        ).stream_events()

    def _enrich_event(self, event: Any, task: OrchestrationTask, stream_id: str) -> None:
        setattr(event, "run_id", task.run_id)
        setattr(event, "task_id", task.id)
        setattr(event, "agent_id", task.assigned_agent_id)
        setattr(event, "stream_id", stream_id)

    def _merge_message_metadata(self, message: Message, task: OrchestrationTask, stream_id: str) -> None:
        metadata = dict(message.msg_metadata or {})
        metadata.update({
            "run_id": task.run_id,
            "task_id": task.id,
            "agent_id": task.assigned_agent_id,
            "stream_id": stream_id,
        })
        message.msg_metadata = metadata
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

    def finalize_run(self, run_id: str) -> OrchestrationRun | None:
        run = self.get_run(run_id)
        if run is None:
            return None

        tasks = run.tasks
        if not tasks:
            return run

        terminal_states = {"completed", "rejected", "cancelled", "failed"}
        if not all(task.status in terminal_states for task in tasks):
            return run

        task_statuses = [task.status for task in tasks]
        has_completed = "completed" in task_statuses
        has_failed = "failed" in task_statuses

        if all(status == "completed" for status in task_statuses):
            new_status = "completed"
        elif all(status in {"rejected", "cancelled"} for status in task_statuses):
            new_status = "cancelled"
        elif not has_completed and has_failed:
            new_status = "failed"
        elif has_completed and any(status in {"rejected", "cancelled", "failed"} for status in task_statuses):
            new_status = "partial"
        else:
            new_status = "partial"

        if run.status != new_status:
            run.status = new_status
            self.db.add(run)
            self.db.commit()
            self.db.refresh(run)

        self._generate_run_summary(run)
        self._generate_host_completion_message(run)
        refreshed_run = self.get_run(run_id)
        if refreshed_run is not None:
            self._group_chat_audit.record_run_finished(
                session_id=refreshed_run.session_id,
                run_id=refreshed_run.id,
                status=refreshed_run.status,
                summary=refreshed_run.summary,
                tasks=[
                    {
                        "task_id": task.id,
                        "sequence": task.sequence,
                        "title": task.title,
                        "agent_id": task.assigned_agent_id,
                        "status": task.status,
                    }
                    for task in refreshed_run.tasks
                ],
        )
        return run

    def _generate_host_completion_message(self, run: OrchestrationRun) -> None:
        if run.status != "completed":
            return

        existing = next(
            (
                message
                for message in self.db.query(Message)
                .filter(Message.session_id == run.session_id)
                .order_by(Message.created_at.asc())
                .all()
                if (message.msg_metadata or {}).get("run_id") == run.id
                and (message.msg_metadata or {}).get("is_host_completion") is True
            ),
            None,
        )
        if existing is not None:
            return

        primary_member = (
            self.db.query(SessionMember)
            .filter(
                SessionMember.session_id == run.session_id,
                SessionMember.member_type == "agent",
                SessionMember.is_primary == True,  # noqa: E712
            )
            .first()
        )
        host_agent = self.get_agent(primary_member.member_id) if primary_member is not None else self.get_agent(run.planner_agent_id)
        host_role = getattr(host_agent, "role", None) or "PM"

        message = Message(
            session_id=run.session_id,
            sender_type="agent",
            sender_role=host_role,
            content="全部任务完成。",
            type="text",
            status="completed",
            payload={"run_status": run.status, "run_id": run.id},
            msg_metadata={
                "run_id": run.id,
                "is_host_completion": True,
                "agent_id": getattr(host_agent, "id", None) or run.planner_agent_id,
            },
        )
        self.db.add(message)
        self.db.commit()

    def _generate_run_summary(self, run: OrchestrationRun) -> None:
        existing = self.db.query(Message).filter(
            Message.session_id == run.session_id,
            Message.msg_metadata["run_id"].as_string() == run.id,
        ).all()
        for message in existing:
            metadata = message.msg_metadata or {}
            if metadata.get("is_orchestration_summary") is True:
                return

        primary_member = (
            self.db.query(SessionMember)
            .filter(
                SessionMember.session_id == run.session_id,
                SessionMember.member_type == "agent",
                SessionMember.is_primary == True,
            )
            .first()
        )
        host_agent = self.get_agent(primary_member.member_id) if primary_member is not None else self.get_agent(run.planner_agent_id)
        host_role = getattr(host_agent, "role", None) or "PM"

        status_text_map = {
            "completed": "全部任务完成",
            "partial": "部分任务完成",
            "cancelled": "任务已取消",
            "failed": "任务执行失败",
        }
        status_text = status_text_map.get(run.status, f"任务状态: {run.status}")
        task_summaries = [
            f"- {task.title}: {self._get_task_result_text(task)}"
            for task in sorted(run.tasks, key=lambda t: t.sequence)
        ]
        summary_content = f"{status_text}\n\n" + "\n".join(task_summaries)

        summary_message = Message(
            session_id=run.session_id,
            sender_type="agent",
            sender_role=host_role,
            content=summary_content,
            type="text",
            status="completed",
            payload={"run_status": run.status, "task_count": len(run.tasks)},
            msg_metadata={
                "run_id": run.id,
                "is_orchestration_summary": True,
                "agent_id": getattr(host_agent, "id", None) or run.planner_agent_id,
            },
        )
        self.db.add(summary_message)
        self.db.commit()

    def _get_task_result_text(self, task: OrchestrationTask) -> str:
        if task.status == "completed":
            if task.result_payload:
                path = task.result_payload.get("path", "") or self._get_task_change_path(task)
                if path:
                    return f"已完成 ({path})"
            return "已完成"
        if task.status == "rejected":
            return "已拒绝"
        if task.status == "cancelled":
            return "已取消"
        if task.status == "failed":
            error = task.error_payload.get("error", "未知错误") if task.error_payload else "未知错误"
            return f"失败 ({error})"
        return f"状态: {task.status}"

    def _get_task_change_path(self, task: OrchestrationTask) -> str:
        change = (
            self.db.query(PendingChangeModel)
            .filter(PendingChangeModel.task_id == task.id)
            .order_by(PendingChangeModel.created_at.desc())
            .first()
        )
        return change.path if change is not None else ""


def runtime_use_runtime_agent() -> bool:
    return os.getenv("RUNTIME_USE_RUNTIME_AGENT", "0") in ("1", "true", "True")


def _utcnow_iso() -> str:
    from app.models.session import utcnow

    return to_iso_z(utcnow())
