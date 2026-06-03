# -*- coding: utf-8 -*-
"""Session API endpoints.

Task B+C-1: Session creation requires workspace_id.
Session responses include workspace details for frontend display.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models.agent import Agent
from app.models.message import Message
from app.models.session import ChatSession
from app.models.session_member import SessionMember
from app.models.workspace import Workspace
from app.schemas.common import Page
from app.schemas.message import MessageResponse
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate, WorkspaceSummary
from app.schemas.session_member import MemberResponse

PRIMARY_AGENT_ID = "primary_pm_agent"

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _get_workspace_summary(db: Session, workspace_id: str | None) -> WorkspaceSummary | None:
    """Get workspace summary for a workspace_id."""
    if workspace_id is None:
        return None
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        return None
    return WorkspaceSummary(
        id=ws.id,
        name=ws.name,
        root_path=ws.root_path,
    )


def _get_members_for_session(db: Session, session_id: str) -> list[MemberResponse]:
    """Get members for a session."""
    members = db.query(SessionMember).filter(
        SessionMember.session_id == session_id
    ).all()
    return [
        MemberResponse(
            id=m.id,
            session_id=m.session_id,
            member_type=m.member_type,
            member_id=m.member_id,
            is_primary=m.is_primary,
            health_status=m.health_status,
            created_at=m.created_at.isoformat(),
        )
        for m in members
    ]


def _session_to_response(db: Session, session: ChatSession) -> SessionResponse:
    """Convert a ChatSession to SessionResponse with workspace info."""
    return SessionResponse(
        id=session.id,
        owner_id=session.owner_id,
        workspace_id=session.workspace_id,
        agent_id=session.agent_id,
        title=session.title,
        mode=session.mode,
        is_pinned=session.is_pinned,
        is_archived=session.is_archived,
        created_at=session.created_at,
        updated_at=session.updated_at,
        workspace=_get_workspace_summary(db, session.workspace_id),
        members=_get_members_for_session(db, session.id),
    )


def get_session_or_404(db: Session, session_id: str) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def get_session_with_ownership_check(db: Session, session_id: str, current_user: CurrentUser) -> ChatSession:
    session = get_session_or_404(db, session_id)
    if session.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden: session does not belong to current user")
    return session


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, current_user: CurrentUser, db: Session = Depends(get_db)) -> SessionResponse:
    # Task B+C-1: Validate workspace_id exists and belongs to current user
    owner = str(current_user.id)
    ws = db.get(Workspace, payload.workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if ws.owner_id != owner:
        raise HTTPException(status_code=403, detail="Workspace does not belong to current user")

    if payload.agent_id is not None:
        agent = db.get(Agent, payload.agent_id)
        if agent is None:
            raise HTTPException(status_code=404, detail="Agent not found")
        if not agent.is_builtin and agent.owner_id != owner:
            raise HTTPException(status_code=403, detail="Agent does not belong to current user")

    session = ChatSession(
        owner_id=owner,
        title=payload.title,
        mode=payload.mode,
        workspace_id=payload.workspace_id,
        agent_id=payload.agent_id,
    )
    db.add(session)
    db.flush()  # flush to get session.id for member creation

    # P6-3: Group mode — auto-add primary agent and participant agents as members
    if payload.mode == "group":
        participant_ids = list(payload.participant_agent_ids or [])
        # Always include primary agent, deduplicate
        member_ids = set(participant_ids)
        member_ids.discard(PRIMARY_AGENT_ID)

        # Validate all participant agents exist
        for agent_id in member_ids:
            ag = db.get(Agent, agent_id)
            if ag is None:
                raise HTTPException(status_code=404, detail=f"Agent not found: {agent_id}")
            if not ag.is_builtin and ag.owner_id != owner:
                raise HTTPException(status_code=403, detail=f"Agent does not belong to current user: {agent_id}")

        # Add primary agent as primary member
        db.add(SessionMember(
            session_id=session.id,
            member_type="agent",
            member_id=PRIMARY_AGENT_ID,
            is_primary=True,
            health_status="connected",
        ))

        # Add participant agents as non-primary members
        for agent_id in member_ids:
            db.add(SessionMember(
                session_id=session.id,
                member_type="agent",
                member_id=agent_id,
                is_primary=False,
                health_status="connected",
            ))

    db.commit()
    db.refresh(session)
    return _session_to_response(db, session)


@router.get("", response_model=Page[SessionResponse])
def list_sessions(
    current_user: CurrentUser,
    include_archived: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[SessionResponse]:
    filters = [ChatSession.owner_id == str(current_user.id)]
    if not include_archived:
        filters.append(ChatSession.is_archived.is_(False))

    total = db.scalar(select(func.count()).select_from(ChatSession).where(*filters)) or 0
    items = db.scalars(
        select(ChatSession)
        .where(*filters)
        .order_by(ChatSession.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=[_session_to_response(db, session) for session in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, current_user: CurrentUser, db: Session = Depends(get_db)) -> SessionResponse:
    session = get_session_with_ownership_check(db, session_id, current_user)
    return _session_to_response(db, session)


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    payload: SessionUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> SessionResponse:
    session = get_session_with_ownership_check(db, session_id, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(session, field, value)
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_to_response(db, session)


@router.delete("/{session_id}")
def archive_session_alias(session_id: str, current_user: CurrentUser, db: Session = Depends(get_db)) -> dict:
    session = get_session_with_ownership_check(db, session_id, current_user)
    session.is_archived = True
    db.add(session)
    db.commit()
    return {
        "archived": True,
        "mode": "archive_alias",
        "session_id": session_id,
    }


@router.get("/{session_id}/messages", response_model=Page[MessageResponse])
def list_messages(
    session_id: str,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[MessageResponse]:
    get_session_with_ownership_check(db, session_id, current_user)
    total = db.scalar(select(func.count()).select_from(Message).where(
        Message.session_id == session_id,
        Message.status != "streaming",
    )) or 0
    items = db.scalars(
        select(Message)
        .where(Message.session_id == session_id, Message.status != "streaming")
        .order_by(Message.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )


# M6: Active Run Recovery Endpoint
class ActiveRunRecoveryResponse(BaseModel):
    """Response model for active run recovery endpoint."""
    run: Optional[dict] = None
    tasks: list[dict] = []
    pending_changes: list[dict] = []


from app.models.orchestration import OrchestrationRun as OrchRun
from app.models.orchestration import OrchestrationTask as OrchTask
from app.models.pending_change import PendingChangeModel


@router.get("/{session_id}/active-run", response_model=ActiveRunRecoveryResponse)
def get_active_run(
    session_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ActiveRunRecoveryResponse:
    """Get active run with tasks and pending changes for UI state recovery.

    M6: This endpoint provides the minimum data needed for frontend to render
    the orchestration execution view after page refresh or session re-entry.

    Returns:
        - run: Active run data (or None if no active run)
        - tasks: List of tasks with all UI fields
        - pending_changes: List of pending changes for this session

    Raises:
        HTTPException 404: If session not found.
        HTTPException 403: If user doesn't own the session.
    """
    # Check session ownership
    get_session_with_ownership_check(db, session_id, current_user)

    # Get latest active run for this session
    from sqlalchemy import desc
    run = db.scalars(
        select(OrchRun)
        .options(selectinload(OrchRun.tasks))
        .where(
            OrchRun.session_id == session_id,
            OrchRun.status.in_(['planned', 'running', 'waiting_confirmation'])
        )
        .order_by(desc(OrchRun.created_at))
        .limit(1)
    ).first()

    if run is None:
        return ActiveRunRecoveryResponse(run=None, tasks=[], pending_changes=[])

    # Build run response
    run_data = {
        'id': run.id,
        'session_id': run.session_id,
        'trigger_message_id': run.trigger_message_id,
        'planner_agent_id': run.planner_agent_id,
        'status': run.status,
        'summary': run.summary,
        'created_at': run.created_at.isoformat() if run.created_at else None,
        'updated_at': run.updated_at.isoformat() if run.updated_at else None,
    }

    # Build tasks response
    tasks_data = []
    for task in run.tasks:
        tasks_data.append({
            'id': task.id,
            'run_id': task.run_id,
            'parent_task_id': task.parent_task_id,
            'sequence': task.sequence,
            'assigned_agent_id': task.assigned_agent_id,
            'kind': task.kind,
            'title': task.title,
            'goal': task.goal,
            'input_payload': task.input_payload,
            'result_payload': task.result_payload,
            'error_payload': task.error_payload,
            'status': task.status,
        })

    # Get pending changes for this session/run
    pending_changes = (
        db.query(PendingChangeModel)
        .filter(
            PendingChangeModel.session_id == session_id,
            PendingChangeModel.status == 'pending_confirmation'
        )
        .all()
    )

    pending_changes_data = []
    for pc in pending_changes:
        pending_changes_data.append({
            'change_id': pc.change_id,
            'session_id': pc.session_id,
            'message_id': pc.message_id,
            'stream_id': pc.stream_id,
            'run_id': pc.run_id,
            'task_id': pc.task_id,
            'agent_id': pc.agent_id,
            'batch_id': pc.batch_id,
            'operation': pc.operation,
            'path': pc.path,
            'unified_diff': pc.unified_diff,
            'original_content': pc.original_content,
            'proposed_content': pc.proposed_content,
            'status': pc.status,
            'created_at': pc.created_at.isoformat() if pc.created_at else None,
            'applied_at': pc.applied_at.isoformat() if pc.applied_at else None,
        })

    return ActiveRunRecoveryResponse(
        run=run_data,
        tasks=tasks_data,
        pending_changes=pending_changes_data,
    )
