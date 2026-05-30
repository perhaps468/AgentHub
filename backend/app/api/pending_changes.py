# -*- coding: utf-8 -*-
"""Task C-2: Pending Change apply API endpoints.

Provides REST API for confirming/rejecting pending file changes.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import CurrentUser
from app.runtime.tools.apply_change_tool import ApplyChangeTool
from app.runtime.pending_change import ChangeStatus

router = APIRouter(prefix="/api/pending-changes", tags=["pending-changes"])


class ApplyChangeRequest(BaseModel):
    change_id: str
    session_id: str | None = None  # Task C-4: 用于 WebSocket 事件推送


class ApplyChangeResponse(BaseModel):
    success: bool
    change_id: str
    message: str
    status: str = "applied"  # Task C-4: applied, rejected, failed
    event: dict | None = None  # Task 2: formal apply_result event payload


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/apply", response_model=ApplyChangeResponse)
def apply_pending_change(
    request: ApplyChangeRequest,
    current_user: CurrentUser,
    db=Depends(get_db),
) -> ApplyChangeResponse:
    """Apply a pending change by its change_id.

    Task C-2: This endpoint allows the frontend to confirm a pending change
    after the user reviews the diff preview.

    Args:
        change_id: The unique identifier of the pending change to apply.

    Returns:
        ApplyChangeResponse indicating success or failure.
    """
    change_id = request.change_id.strip()
    if not change_id:
        raise HTTPException(status_code=400, detail="change_id cannot be empty")

    # Retrieve the pending change
    pending = ApplyChangeTool.get_change(change_id)
    if pending is None:
        raise HTTPException(
            status_code=404,
            detail=f"No pending change found with change_id='{change_id}'. "
            "The change may have already been applied or the ID is invalid."
        )

    if pending.status == ChangeStatus.APPLIED:
        event = {
            "type": "apply_result",
            "change_id": change_id,
            "success": False,
            "status": "applied",
            "message": f"Change '{change_id}' has already been applied.",
            "timestamp": _utcnow_iso(),
        }
        return ApplyChangeResponse(
            success=False,
            change_id=change_id,
            message=f"Change '{change_id}' has already been applied.",
            status="applied",
            event=event,
        )

    if pending.status == ChangeStatus.REJECTED:
        event = {
            "type": "apply_result",
            "change_id": change_id,
            "success": False,
            "status": "rejected",
            "message": f"Change '{change_id}' was previously rejected.",
            "timestamp": _utcnow_iso(),
        }
        return ApplyChangeResponse(
            success=False,
            change_id=change_id,
            message=f"Change '{change_id}' was previously rejected.",
            status="rejected",
            event=event,
        )

    # Attempt to apply the change
    success = pending.apply()

    if success:
        event = {
            "type": "apply_result",
            "change_id": change_id,
            "success": True,
            "status": "applied",
            "message": f"Successfully applied {pending.operation.value.upper()} {pending.path}",
            "timestamp": _utcnow_iso(),
        }
        # Remove from registry after successful apply
        # Note: ApplyChangeTool.execute() handles registry cleanup
        return ApplyChangeResponse(
            success=True,
            change_id=change_id,
            message=f"Successfully applied {pending.operation.value.upper()} {pending.path}",
            status="applied",
            event=event,
        )
    else:
        # Transition to REJECTED status
        pending.status = ChangeStatus.REJECTED
        event = {
            "type": "apply_result",
            "change_id": change_id,
            "success": False,
            "status": "rejected",
            "message": f"Apply failed: {pending.error}. The file may have been modified after preview.",
            "timestamp": _utcnow_iso(),
        }
        return ApplyChangeResponse(
            success=False,
            change_id=change_id,
            message=f"Apply failed: {pending.error}. The file may have been modified after preview.",
            status="rejected",
            event=event,
        )
