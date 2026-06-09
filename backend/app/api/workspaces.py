# -*- coding: utf-8 -*-
"""Task B - Workspace API endpoints.

Provides CRUD for workspaces with owner boundary enforcement.
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models.session import ChatSession
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


class WorkspaceNotFoundError(Exception):
    pass


class WorkspaceAccessDeniedError(Exception):
    pass


class WorkspaceRootInvalidError(Exception):
    def __init__(self, root_path: str, reason: str):
        self.root_path = root_path
        self.reason = reason
        super().__init__(f"Invalid workspace root '{root_path}': {reason}")


def _validate_root_path(root_path: str) -> None:
    """Validate that root_path is accessible and within allowed boundaries."""
    try:
        p = Path(root_path).expanduser().resolve()
    except (OSError, RuntimeError) as e:
        raise WorkspaceRootInvalidError(root_path, f"cannot resolve path: {e}")

    if not p.exists():
        raise WorkspaceRootInvalidError(root_path, "path does not exist")
    if not p.is_dir():
        raise WorkspaceRootInvalidError(root_path, "path is not a directory")
    if not os.access(p, os.R_OK | os.W_OK):
        raise WorkspaceRootInvalidError(root_path, "path is not readable/writable")


def get_workspace_or_404(db: Session, workspace_id: str) -> Workspace:
    ws = db.get(Workspace, workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


def get_workspace_with_ownership_check(
    db: Session, workspace_id: str, current_user: CurrentUser
) -> Workspace:
    ws = get_workspace_or_404(db, workspace_id)
    if ws.owner_id != str(current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden: workspace does not belong to current user")
    return ws


def resolve_workspace_from_session(
    db: Session, session: ChatSession, current_user: CurrentUser
) -> Workspace | None:
    """Resolve workspace from a session's workspace_id binding.

    Returns the Workspace if bound, None if session has no workspace binding.

    Raises HTTPException on authorization or existence errors.
    """
    if session.workspace_id is None:
        return None

    ws = get_workspace_or_404(db, session.workspace_id)

    # Owner boundary: session owner and workspace owner must match
    if ws.owner_id != session.owner_id:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: session owner does not match workspace owner",
        )

    # Also check against current user for additional safety
    if ws.owner_id != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="Forbidden: workspace does not belong to current user",
        )

    return ws


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Workspace:
    owner = str(current_user.id)

    try:
        _validate_root_path(payload.root_path)
    except WorkspaceRootInvalidError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check for duplicate: same owner + same root_path
    existing = db.scalar(
        select(Workspace).where(
            Workspace.owner_id == owner,
            Workspace.root_path == payload.root_path,
        )
    )
    if existing:
        return existing

    ws = Workspace(
        owner_id=owner,
        root_path=payload.root_path,
        name=payload.name or payload.root_path,
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)
    return ws


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[Workspace]:
    owner = str(current_user.id)
    items = (
        db.scalars(
            select(Workspace)
            .where(Workspace.owner_id == owner)
            .order_by(Workspace.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return list(items)


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(
    workspace_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> Workspace:
    return get_workspace_with_ownership_check(db, workspace_id, current_user)



@router.post(
    "/{workspace_id}/ppt",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "PPT file saved successfully"},
        400: {"description": "Invalid request"},
        403: {"description": "Access denied"},
        404: {"description": "Workspace not found"},
    },
)
def save_ppt_to_workspace(
    workspace_id: str,
    current_user: CurrentUser,
    file_name: str = Query(..., description="PPT file name without extension"),
    file: UploadFile = File(..., description="PPTX file binary"),
    db: Session = Depends(get_db),
) -> dict:
    """Save a PPTX file to the workspace root directory.

    If a file with the same name exists, appends a numeric suffix before saving.
    The file is saved directly under workspace.root_path with the given name.
    """
    ws = get_workspace_with_ownership_check(db, workspace_id, current_user)

    root = Path(ws.root_path).expanduser().resolve()
    if not root.exists():
        raise HTTPException(status_code=400, detail="Workspace root path does not exist")

    safe_name = re.sub(r"[^\w\u4e00-\u9fa5._-]", "_", file_name)
    dest_path = root / f"{safe_name}.pptx"

    if dest_path.exists():
        stem = safe_name
        counter = 1
        while (root / f"{stem}_{counter}.pptx").exists():
            counter += 1
        dest_path = root / f"{stem}_{counter}.pptx"

    with dest_path.open("wb") as dest:
        shutil.copyfileobj(file.file, dest)

    return {
        "saved": True,
        "path": str(dest_path),
        "name": dest_path.name,
    }
