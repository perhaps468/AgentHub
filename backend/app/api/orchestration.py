# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.sessions import get_session_with_ownership_check
from app.core.database import get_db
from app.core.security import CurrentUser
from app.models.orchestration import OrchestrationRun
from app.schemas.orchestration import OrchestrationRunResponse
from app.services.orchestration import OrchestrationService

router = APIRouter(prefix="/api", tags=["orchestration"])


@router.get("/orchestration/runs/{run_id}", response_model=OrchestrationRunResponse)
def get_run(run_id: str, current_user: CurrentUser, db: Session = Depends(get_db)) -> OrchestrationRunResponse:
    run = db.get(OrchestrationRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    get_session_with_ownership_check(db, run.session_id, current_user)
    loaded = OrchestrationService(db).get_run(run_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return OrchestrationRunResponse.model_validate(loaded)


@router.get("/orchestration/sessions/{session_id}/runs/latest", response_model=OrchestrationRunResponse | None)
def get_latest_run(session_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    get_session_with_ownership_check(db, session_id, current_user)
    run = OrchestrationService(db).get_latest_run_for_session(session_id)
    return OrchestrationRunResponse.model_validate(run) if run is not None else None


@router.get("/sessions/{session_id}/runs/latest", response_model=OrchestrationRunResponse | None)
def get_latest_run_via_session(session_id: str, current_user: CurrentUser, db: Session = Depends(get_db)):
    return get_latest_run(session_id=session_id, current_user=current_user, db=db)
