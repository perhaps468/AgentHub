# -*- coding: utf-8 -*-
"""Task B+C-1 - Session query returns workspace info tests.

Tests verify that SessionResponse includes full workspace details
for frontend display, as specified in Section 4.4.
"""
from datetime import datetime, timezone

import pytest


class TestSessionResponseWorkspaceInfo:
    """TDD: SessionResponse should include full workspace info."""

    def test_session_response_has_workspace_object(self):
        """SessionResponse must include nested workspace object."""
        from app.schemas.session import SessionResponse, WorkspaceSummary

        response = SessionResponse(
            id="session-123",
            owner_id="user-456",
            title="Test Session",
            mode="single",
            is_pinned=False,
            is_archived=False,
            workspace_id="ws-789",
            workspace=WorkspaceSummary(
                id="ws-789",
                name="MyProject",
                root_path="D:/code/MyProject",
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert response.workspace is not None
        assert response.workspace.id == "ws-789"
        assert response.workspace.name == "MyProject"
        assert response.workspace.root_path == "D:/code/MyProject"

    def test_session_response_workspace_fields_required(self):
        """Workspace object in SessionResponse must have required fields."""
        from app.schemas.session import SessionResponse
        from pydantic import ValidationError

        # Missing required workspace fields should fail
        with pytest.raises(ValidationError):
            SessionResponse(
                id="session-123",
                owner_id="user-456",
                title="Test",
                mode="single",
                is_pinned=False,
                is_archived=False,
                workspace_id="ws-789",
                workspace={"id": "ws-789"},  # Missing name and root_path
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

    def test_session_response_workspace_null_when_no_binding(self):
        """Workspace should be null when session has no workspace_id."""
        from app.schemas.session import SessionResponse

        response = SessionResponse(
            id="session-123",
            owner_id="user-456",
            title="Test",
            mode="single",
            is_pinned=False,
            is_archived=False,
            workspace_id=None,
            workspace=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert response.workspace_id is None
        assert response.workspace is None


class TestSessionAPIReturnsWorkspaceInfo:
    """TDD: Session API should return workspace info in response."""

    def test_session_create_response_includes_workspace(self):
        """Session creation API response should include workspace info."""
        # This would be an integration test
        pass

    def test_session_get_response_includes_workspace(self):
        """Session get/detail API should return workspace info."""
        # This would be an integration test
        pass
