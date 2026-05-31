# -*- coding: utf-8 -*-
"""Session API endpoints.

Task B+C-1: Session creation requires workspace_id.
Session responses include workspace details for frontend display.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models.message import Message
from app.models.session import ChatSession
from app.models.workspace import Workspace
from app.schemas.common import Page
from app.schemas.message import MessageResponse
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate, WorkspaceSummary

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


def _session_to_response(db: Session, session: ChatSession) -> SessionResponse:
    """Convert a ChatSession to SessionResponse with workspace info."""
    return SessionResponse(
        id=session.id,
        owner_id=session.owner_id,
        workspace_id=session.workspace_id,
        title=session.title,
        mode=session.mode,
        is_pinned=session.is_pinned,
        is_archived=session.is_archived,
        created_at=session.created_at,
        updated_at=session.updated_at,
        workspace=_get_workspace_summary(db, session.workspace_id),
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

    session = ChatSession(
        owner_id=owner,
        title=payload.title,
        mode=payload.mode,
        workspace_id=payload.workspace_id,
    )
    db.add(session)
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
