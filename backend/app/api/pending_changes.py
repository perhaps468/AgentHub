# -*- coding: utf-8 -*-
"""Task C-2/C-4/CE: Pending Change API endpoints.

Provides REST API for:
- GET /api/pending-changes?session_id=... - List pending changes by session
- GET /api/pending-changes/{change_id} - Get single pending change by ID
- POST /api/pending-changes/apply - Apply a pending change (existing)

Also pushes apply_result events via WebSocket for frontend state sync.
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc

from app.core.database import get_db, Session as DBSession
from app.core.security import CurrentUser
from app.models.message import Message
from app.models.pending_change import PendingChangeModel
from app.models.session import ChatSession
from app.observability.group_chat_audit import get_group_chat_audit_recorder
from app.runtime.tools.apply_change_tool import ApplyChangeTool
from app.runtime.pending_change import ChangeStatus

router = APIRouter(prefix="/api/pending-changes", tags=["pending-changes"])
_GROUP_CHAT_AUDIT = get_group_chat_audit_recorder()


class ApplyChangeRequest(BaseModel):
    change_id: str
    session_id: str | None = None  # 用于 WebSocket 事件推送


class ApplyChangeResponse(BaseModel):
    success: bool
    change_id: str
    message: str
    status: str = "applied"  # applied, rejected, failed
    ws_pushed: bool = False  # 是否成功推送到 WebSocket
    # M4: Task-aware fields for frontend state sync
    run_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None


class PendingChangeResponse(BaseModel):
    """Response model for pending change query."""
    change_id: str
    session_id: str
    message_id: str | None
    stream_id: str | None
    run_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None
    batch_id: str | None = None
    path: str
    operation: str
    unified_diff: str
    original_content: str | None
    proposed_content: str | None
    status: str
    created_at: str | None
    applied_at: str | None


class PendingChangeListResponse(BaseModel):
    """Response model for listing pending changes."""
    items: list[PendingChangeResponse]
    total: int
    session_id: str


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_owned_session_or_404(
    db: DBSession,
    session_id: str,
    current_user: CurrentUser,
) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    return session


def _get_owned_pending_change_or_404(
    db: DBSession,
    change_id: str,
    current_user: CurrentUser,
) -> PendingChangeModel:
    change = db.query(PendingChangeModel).filter_by(change_id=change_id).first()
    if change is None:
        raise HTTPException(
            status_code=404,
            detail=f"Pending change with change_id='{change_id}' not found.",
        )
    _get_owned_session_or_404(db, change.session_id, current_user)
    return change


async def _push_apply_result(
    session_id: str,
    change_id: str,
    success: bool,
    status: str,
    message: str,
    run_id: str | None = None,
    task_id: str | None = None,
    agent_id: str | None = None,
) -> bool:
    """向 WebSocket 会话推送 apply_result 事件。

    使用异步方式推送，避免阻塞 REST 请求。

    M4: Added task-aware fields for precise frontend state sync.
    """
    if not session_id:
        return False

    try:
        from app.api.ws import ws_send_apply_result
        return await ws_send_apply_result(
            session_id=session_id,
            change_id=change_id,
            success=success,
            status=status,
            message=message,
            run_id=run_id,
            task_id=task_id,
            agent_id=agent_id,
        )
    except Exception:
        return False


async def _push_orchestration_summary_message(
    session_id: str,
    run_id: str | None,
    db: DBSession,
) -> bool:
    if not session_id or not run_id:
        return False

    try:
        from app.api.ws import get_ws_connection_manager, ws_send_message_end, ws_send_message_start
    except Exception:
        return False

    conn = get_ws_connection_manager().get_connection(session_id)
    if conn is None:
        return False

    run_messages = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .all()
    )
    summary_message = next(
        (
            item for item in run_messages
            if (item.msg_metadata or {}).get("run_id") == run_id
            and (item.msg_metadata or {}).get("is_orchestration_summary") is True
        ),
        None,
    )
    if summary_message is None:
        return False

    websocket, _ = conn
    stream_id = f"run-summary-{run_id}"
    await ws_send_message_start(
        websocket,
        agent_role=summary_message.sender_role or "PM",
        stream_id=stream_id,
        message=summary_message,
        run_id=run_id,
        agent_id=(summary_message.msg_metadata or {}).get("agent_id"),
    )
    await ws_send_message_end(
        websocket,
        agent_role=summary_message.sender_role or "PM",
        stream_id=stream_id,
        message_id=summary_message.id,
        status="completed",
        final_content=summary_message.content,
        run_id=run_id,
        agent_id=(summary_message.msg_metadata or {}).get("agent_id"),
    )
    return True


def _update_task_status_on_apply(db: DBSession, db_change, change_id: str) -> None:
    """M4: Update associated task status to completed when apply succeeds.

    Args:
        db: Database session
        db_change: The pending change that was applied
        change_id: The change ID
    """
    if not db_change.task_id:
        return

    try:
        from app.models.orchestration import OrchestrationTask
        from app.services.orchestration_executor import OrchestrationExecutor

        task = db.get(OrchestrationTask, db_change.task_id)
        if task is not None and task.status == "waiting_confirmation":
            executor = OrchestrationExecutor(db)
            executor.update_task_status(
                db_change.task_id,
                "completed",
                result_payload={"change_id": change_id, "applied": True}
            )
            # M5: Try to finalize run after task completion
            _try_finalize_run(db, db_change.run_id)
    except Exception:
        pass


def _update_task_status_on_reject(db: DBSession, db_change, change_id: str) -> None:
    """M4: Update associated task status to rejected when user rejects.

    Args:
        db: Database session
        db_change: The pending change that was rejected
        change_id: The change ID
    """
    if not db_change.task_id:
        return

    try:
        from app.models.orchestration import OrchestrationTask
        from app.services.orchestration_executor import OrchestrationExecutor

        task = db.get(OrchestrationTask, db_change.task_id)
        if task is not None and task.status == "waiting_confirmation":
            executor = OrchestrationExecutor(db)
            executor.update_task_status(
                db_change.task_id,
                "rejected",
                result_payload={"change_id": change_id, "rejected": True}
            )
            # M5: Try to finalize run after task completion
            _try_finalize_run(db, db_change.run_id)
    except Exception:
        pass


def _try_finalize_run(db: DBSession, run_id: str | None) -> None:
    """M5: Try to finalize run if all tasks are in terminal states.

    Args:
        db: Database session
        run_id: The run ID to finalize
    """
    if not run_id:
        return

    try:
        from app.services.orchestration_executor import OrchestrationExecutor
        executor = OrchestrationExecutor(db)
        if hasattr(executor, 'finalize_run'):
            executor.finalize_run(run_id)
        elif hasattr(executor, 'aggregate_run'):
            executor.aggregate_run(run_id)
    except Exception:
        pass


@router.get("", response_model=PendingChangeListResponse)
async def get_pending_changes(
    session_id: Annotated[str, Query(description="Session ID to query pending changes for")],
    current_user: CurrentUser,
    db: DBSession = Depends(get_db),
) -> PendingChangeListResponse:
    """Get all pending changes for a session.

    Task CE: This endpoint enables frontend to recover pending changes
    after page refresh or WebSocket reconnect.

    Args:
        session_id: The session ID to query pending changes for.
        current_user: Authenticated user (required).

    Returns:
        PendingChangeListResponse containing all pending changes for the session.
    """
    _get_owned_session_or_404(db, session_id, current_user)
    changes = (
        db.query(PendingChangeModel)
        .filter_by(session_id=session_id)
        .order_by(desc(PendingChangeModel.created_at))
        .all()
    )

    items = []
    for change in changes:
        response = change.to_api_response()
        items.append(PendingChangeResponse(**response))

    return PendingChangeListResponse(
        items=items,
        total=len(items),
        session_id=session_id,
    )


@router.get("/{change_id}", response_model=PendingChangeResponse)
async def get_pending_change_by_id(
    change_id: str,
    current_user: CurrentUser,
    db: DBSession = Depends(get_db),
) -> PendingChangeResponse:
    """Get a single pending change by its change_id.

    Task CE: This endpoint allows frontend to fetch details of a specific
    pending change for recovery or display.

    Args:
        change_id: The unique identifier of the pending change.
        current_user: Authenticated user (required).

    Returns:
        PendingChangeResponse with full pending change details.

    Raises:
        HTTPException 404: If the pending change is not found.
    """
    change = _get_owned_pending_change_or_404(db, change_id, current_user)
    response = change.to_api_response()
    return PendingChangeResponse(**response)


@router.post("/apply", response_model=ApplyChangeResponse)
async def apply_pending_change(
    request: ApplyChangeRequest,
    current_user: CurrentUser,
    db=Depends(get_db),
) -> ApplyChangeResponse:
    """Apply a pending change by its change_id.

    Task C-2/C-4: This endpoint allows the frontend to confirm a pending change
    after the user reviews the diff preview. After applying, it pushes the
    result back to the frontend via WebSocket for state synchronization.

    Args:
        change_id: The unique identifier of the pending change to apply.
        session_id: Optional session ID for WebSocket push.

    Returns:
        ApplyChangeResponse indicating success or failure.
    """
    change_id = request.change_id.strip()
    if not change_id:
        raise HTTPException(status_code=400, detail="change_id cannot be empty")

    db_change = _get_owned_pending_change_or_404(db, change_id, current_user)

    # Retrieve the pending change from memory registry first. If this is a page
    # refresh / reconnect recovery flow, reconstruct it from the persisted DB row.
    pending = ApplyChangeTool.get_change(change_id)
    if pending is None and db_change.status == "pending_confirmation":
        pending = db_change.to_runtime()
        ApplyChangeTool.register_change(pending)

    session_id = request.session_id

    if db_change.status == "applied" or pending.status == ChangeStatus.APPLIED:
        result = ApplyChangeResponse(
            success=False,
            change_id=change_id,
            message=f"Change '{change_id}' has already been applied.",
            status="applied",
            run_id=db_change.run_id,
            task_id=db_change.task_id,
            agent_id=db_change.agent_id,
        )
        # 推送 WebSocket 事件
        if session_id:
            result.ws_pushed = await _push_apply_result(
                session_id, change_id, False, "applied",
                f"Change '{change_id}' has already been applied.",
                run_id=db_change.run_id,
                task_id=db_change.task_id,
                agent_id=db_change.agent_id,
            )
        return result

    if db_change.status in {"rejected", "failed"} or pending.status == ChangeStatus.REJECTED:
        result = ApplyChangeResponse(
            success=False,
            change_id=change_id,
            message=f"Change '{change_id}' was previously rejected.",
            status="rejected",
            run_id=db_change.run_id,
            task_id=db_change.task_id,
            agent_id=db_change.agent_id,
        )
        if session_id:
            result.ws_pushed = await _push_apply_result(
                session_id, change_id, False, "rejected",
                f"Change '{change_id}' was previously rejected.",
                run_id=db_change.run_id,
                task_id=db_change.task_id,
                agent_id=db_change.agent_id,
            )
        return result

    # Attempt to apply the change
    success = pending.apply()

    if success:
        db_change.status = "applied"
        db_change.applied_at = datetime.now(timezone.utc)
        db.add(db_change)

        # M4: Update associated task status to completed
        _update_task_status_on_apply(db, db_change, change_id)

        db.commit()
        result = ApplyChangeResponse(
            success=True,
            change_id=change_id,
            message=f"Successfully applied {pending.operation.value.upper()} {pending.path}",
            status="applied",
            run_id=db_change.run_id,
            task_id=db_change.task_id,
            agent_id=db_change.agent_id,
        )
        # 成功后从 registry 移除
        _GROUP_CHAT_AUDIT.record_pending_change_decision(
            session_id=db_change.session_id,
            run_id=db_change.run_id,
            task_id=db_change.task_id,
            agent_id=db_change.agent_id,
            change_id=change_id,
            decision="apply",
            path=db_change.path,
            operation=db_change.operation,
            status="applied",
            message=result.message,
        )
        ApplyChangeTool.clear_change(change_id)
        if session_id:
            result.ws_pushed = await _push_apply_result(
                session_id, change_id, True, "applied",
                f"Successfully applied {pending.operation.value.upper()} {pending.path}",
                run_id=db_change.run_id,
                task_id=db_change.task_id,
                agent_id=db_change.agent_id,
            )
            if db_change.run_id:
                result.ws_pushed = await _push_orchestration_summary_message(session_id, db_change.run_id, db) or result.ws_pushed
        return result
    else:
        # Transition to REJECTED status
        pending.status = ChangeStatus.REJECTED
        db_change.status = "rejected"
        db.add(db_change)
        db.commit()
        result = ApplyChangeResponse(
            success=False,
            change_id=change_id,
            message=f"Apply failed: {pending.error}. The file may have been modified after preview.",
            status="rejected",
            run_id=db_change.run_id,
            task_id=db_change.task_id,
            agent_id=db_change.agent_id,
        )
        _GROUP_CHAT_AUDIT.record_pending_change_decision(
            session_id=db_change.session_id,
            run_id=db_change.run_id,
            task_id=db_change.task_id,
            agent_id=db_change.agent_id,
            change_id=change_id,
            decision="apply_failed",
            path=db_change.path,
            operation=db_change.operation,
            status="rejected",
            message=result.message,
        )
        if session_id:
            result.ws_pushed = await _push_apply_result(
                session_id, change_id, False, "rejected",
                f"Apply failed: {pending.error}. The file may have been modified after preview.",
                run_id=db_change.run_id,
                task_id=db_change.task_id,
                agent_id=db_change.agent_id,
            )
        return result


@router.post("/reject", response_model=ApplyChangeResponse)
async def reject_pending_change(
    request: ApplyChangeRequest,
    current_user: CurrentUser,
    db=Depends(get_db),
) -> ApplyChangeResponse:
    """Reject (cancel) a pending change by its change_id.

    This endpoint allows the frontend to cancel a pending change after the
    user reviews the diff preview. It updates the DB status to 'rejected'
    and pushes the result back via WebSocket for state synchronization.

    Args:
        change_id: The unique identifier of the pending change to reject.
        session_id: Optional session ID for WebSocket push.

    Returns:
        ApplyChangeResponse indicating success or failure.
    """
    change_id = request.change_id.strip()
    if not change_id:
        raise HTTPException(status_code=400, detail="change_id cannot be empty")

    db_change = _get_owned_pending_change_or_404(db, change_id, current_user)

    session_id = request.session_id

    if db_change.status == "rejected":
        result = ApplyChangeResponse(
            success=False,
            change_id=change_id,
            message=f"Change '{change_id}' has already been rejected.",
            status="rejected",
            run_id=db_change.run_id,
            task_id=db_change.task_id,
            agent_id=db_change.agent_id,
        )
        if session_id:
            result.ws_pushed = await _push_apply_result(
                session_id, change_id, False, "rejected",
                f"Change '{change_id}' has already been rejected.",
                run_id=db_change.run_id,
                task_id=db_change.task_id,
                agent_id=db_change.agent_id,
            )
        return result

    if db_change.status == "applied":
        result = ApplyChangeResponse(
            success=False,
            change_id=change_id,
            message=f"Change '{change_id}' has already been applied and cannot be rejected.",
            status="applied",
            run_id=db_change.run_id,
            task_id=db_change.task_id,
            agent_id=db_change.agent_id,
        )
        if session_id:
            result.ws_pushed = await _push_apply_result(
                session_id, change_id, False, "applied",
                f"Change '{change_id}' has already been applied and cannot be rejected.",
                run_id=db_change.run_id,
                task_id=db_change.task_id,
                agent_id=db_change.agent_id,
            )
        return result

    # Mark as rejected in DB
    db_change.status = "rejected"
    db_change.applied_at = datetime.now(timezone.utc)
    db.add(db_change)

    # M4: Update associated task status to rejected
    _update_task_status_on_reject(db, db_change, change_id)

    db.commit()

    # Also mark in memory registry if present
    pending = ApplyChangeTool.get_change(change_id)
    if pending is not None:
        pending.status = ChangeStatus.REJECTED
    ApplyChangeTool.clear_change(change_id)

    result = ApplyChangeResponse(
        success=True,
        change_id=change_id,
        message=f"Change '{change_id}' has been rejected.",
        status="rejected",
        run_id=db_change.run_id,
        task_id=db_change.task_id,
        agent_id=db_change.agent_id,
    )
    _GROUP_CHAT_AUDIT.record_pending_change_decision(
        session_id=db_change.session_id,
        run_id=db_change.run_id,
        task_id=db_change.task_id,
        agent_id=db_change.agent_id,
        change_id=change_id,
        decision="reject",
        path=db_change.path,
        operation=db_change.operation,
        status="rejected",
        message=result.message,
    )
    if session_id:
        result.ws_pushed = await _push_apply_result(
            session_id, change_id, True, "rejected",
            f"Change '{change_id}' has been rejected by user.",
            run_id=db_change.run_id,
            task_id=db_change.task_id,
            agent_id=db_change.agent_id,
        )
        if db_change.run_id:
            result.ws_pushed = await _push_orchestration_summary_message(session_id, db_change.run_id, db) or result.ws_pushed
    return result
