from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.orchestration import OrchestrationRun, OrchestrationTask


class OrchestrationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_run(
        self,
        *,
        session_id: str,
        trigger_message_id: str,
        planner_agent_id: str,
        summary: str | None = None,
        status: str = "planned",
    ) -> OrchestrationRun:
        run = OrchestrationRun(
            session_id=session_id,
            trigger_message_id=trigger_message_id,
            planner_agent_id=planner_agent_id,
            summary=summary,
            status=status,
        )
        self.db.add(run)
        self.db.flush()
        self.db.refresh(run)
        return run

    def create_tasks(self, run_id: str, tasks: list[dict]) -> list[OrchestrationTask]:
        created: list[OrchestrationTask] = []
        for task_data in tasks:
            task = OrchestrationTask(run_id=run_id, **task_data)
            self.db.add(task)
            created.append(task)
        self.db.flush()
        return created

    def get_run(self, run_id: str) -> OrchestrationRun | None:
        return self.db.scalar(
            select(OrchestrationRun)
            .options(selectinload(OrchestrationRun.tasks))
            .where(OrchestrationRun.id == run_id)
        )

    def get_latest_run_for_session(self, session_id: str) -> OrchestrationRun | None:
        return self.db.scalar(
            select(OrchestrationRun)
            .options(selectinload(OrchestrationRun.tasks))
            .where(OrchestrationRun.session_id == session_id)
            .order_by(OrchestrationRun.created_at.desc(), OrchestrationRun.updated_at.desc())
            .limit(1)
        )

    def update_run_status(self, run_id: str, status: str) -> OrchestrationRun | None:
        """Update run status.

        M2: Used to transition run from 'planned' to 'running' when tasks start.
        """
        run = self.db.get(OrchestrationRun, run_id)
        if run is None:
            return None
        run.status = status
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
