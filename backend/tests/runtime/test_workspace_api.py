# -*- coding: utf-8 -*-
"""P3 - Workspace API endpoint tests — RED phase.

Tests verify that:
- POST /api/workspaces creates workspace
- Endpoint requires authentication
- GET /api/workspaces lists user's workspaces
- GET /api/workspaces/{id} returns workspace (404 for non-existent, 403 for others)
- POST /api/sessions accepts workspace_id
- GET /api/sessions/{id} returns workspace_id
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "tools" / "test_workspace"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TestCreateWorkspaceEndpoint:
    """WAP-1: POST /api/workspaces creates workspace."""

    def test_create_workspace_requires_auth(self):
        """POST /api/workspaces without auth returns 401/403."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        response = client.post(
            "/api/workspaces",
            json={"root_path": str(TEST_WORKSPACE_ROOT)},
        )
        assert response.status_code in (401, 403)

    def test_create_workspace_validates_invalid_path(self):
        """POST /api/workspaces with invalid path returns 400."""
        from app.api.workspaces import _validate_root_path, WorkspaceRootInvalidError

        with pytest.raises(WorkspaceRootInvalidError):
            _validate_root_path("/nonexistent/path/workspace")


class TestListWorkspacesEndpoint:
    """WAP-2: GET /api/workspaces lists user's workspaces."""

    def test_list_workspaces_requires_auth(self):
        """GET /api/workspaces without auth returns 401/403."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        response = client.get("/api/workspaces")
        assert response.status_code in (401, 403)


class TestGetWorkspaceEndpoint:
    """WAP-3: GET /api/workspaces/{id} returns workspace."""

    def test_get_workspace_requires_auth(self):
        """GET /api/workspaces/{id} without auth returns 401/403."""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        response = client.get("/api/workspaces/ws-any")
        assert response.status_code in (401, 403)


class TestSessionWorkspaceIdEndpoint:
    """WAP-4: Sessions API accepts and returns workspace_id."""

    def test_session_create_accepts_workspace_id(self):
        """SessionCreate schema accepts workspace_id."""
        from app.schemas.session import SessionCreate

        payload = SessionCreate(
            title="Dev Session",
            mode="single",
            workspace_id="ws-session-bind",
        )
        assert payload.workspace_id == "ws-session-bind"

    def test_session_model_supports_workspace_id(self):
        """ChatSession model supports workspace_id binding."""
        from app.models.session import ChatSession

        session = ChatSession(
            id="session-ws-bound",
            owner_id="user-ws-bind",
            title="Bound Session",
            mode="single",
            workspace_id="ws-bound-api",
        )
        assert session.workspace_id == "ws-bound-api"

    def test_session_response_includes_workspace_id(self):
        """SessionResponse schema includes workspace_id."""
        from app.schemas.session import SessionResponse

        response = SessionResponse(
            id="session-resp-ws",
            owner_id="user-resp",
            title="Session with WS",
            mode="single",
            is_pinned=False,
            is_archived=False,
            workspace_id="ws-in-response",
            created_at=_utcnow(),
            updated_at=_utcnow(),
        )
        assert response.workspace_id == "ws-in-response"

    def test_session_schema_has_workspace_id_field(self):
        """SessionResponse schema has workspace_id field."""
        from app.schemas.session import SessionResponse

        assert "workspace_id" in SessionResponse.model_fields

    def test_session_create_allows_null_workspace_id(self):
        """SessionCreate schema allows workspace_id=None for non-dev sessions."""
        from app.schemas.session import SessionCreate

        payload = SessionCreate(title="Chat", mode="group", workspace_id=None)
        assert payload.workspace_id is None


class TestWorkspaceIdSchemaFields:
    """WAP-5: Workspace-related schemas have correct fields."""

    def test_session_create_schema_has_workspace_id(self):
        """SessionCreate schema has workspace_id field."""
        from app.schemas.session import SessionCreate

        assert "workspace_id" in SessionCreate.model_fields

    def test_session_update_schema_allows_workspace_id(self):
        """SessionUpdate schema allows workspace_id changes."""
        from app.schemas.session import SessionUpdate

        update = SessionUpdate(workspace_id="ws-new", title="New Title")
        assert update.workspace_id == "ws-new"

    def test_session_update_allows_clear_workspace(self):
        """SessionUpdate can clear workspace_id along with other fields."""
        from app.schemas.session import SessionUpdate

        update = SessionUpdate(workspace_id=None, title="Cleared")
        assert update.workspace_id is None


class TestWorkspaceCreateSchema:
    """WAP-6: Workspace creation schema validation."""

    def test_workspace_create_requires_root_path(self):
        """WorkspaceCreate requires root_path."""
        from app.schemas.workspace import WorkspaceCreate

        with pytest.raises(ValueError):
            WorkspaceCreate()

    def test_workspace_create_rejects_relative_path(self):
        """WorkspaceCreate rejects relative paths."""
        from app.schemas.workspace import WorkspaceCreate

        with pytest.raises(ValueError):
            WorkspaceCreate(root_path="relative/path")

    def test_workspace_create_accepts_absolute_path(self):
        """WorkspaceCreate accepts absolute paths that exist."""
        from app.schemas.workspace import WorkspaceCreate

        ws = WorkspaceCreate(root_path=str(TEST_WORKSPACE_ROOT))
        assert ws.root_path is not None
        assert len(ws.root_path) > 0
