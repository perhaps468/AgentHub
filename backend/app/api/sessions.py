from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models.message import Message
from app.models.session import ChatSession
from app.schemas.common import Page
from app.schemas.message import MessageResponse
from app.schemas.session import SessionCreate, SessionResponse, SessionUpdate

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


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
def create_session(payload: SessionCreate, current_user: CurrentUser, db: Session = Depends(get_db)) -> ChatSession:
    session = ChatSession(
        owner_id=str(current_user.id),
        title=payload.title,
        mode=payload.mode,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


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
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(session_id: str, current_user: CurrentUser, db: Session = Depends(get_db)) -> ChatSession:
    return get_session_with_ownership_check(db, session_id, current_user)


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: str,
    payload: SessionUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ChatSession:
    session = get_session_with_ownership_check(db, session_id, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(session, field, value)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


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
        .order_by(Message.created_at.asc())
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
