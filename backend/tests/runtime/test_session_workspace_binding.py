# -*- coding: utf-8 -*-
"""P3 - Session-Workspace binding tests — RED phase.

Tests verify that:
- ChatSession model has workspace_id field
- Session can be created with workspace_id
- workspace_id is persisted and queryable
- Session without workspace has workspace_id=None
- workspace_id is nullable for non-dev sessions
- Session query returns workspace binding info

Note: ChatSession already has workspace_id field in current implementation.
Tests check the existing functionality and expected behavior.
"""

from datetime import datetime

import pytest


class TestSessionModelWorkspaceId:
    """SWB-1: ChatSession model has workspace_id field."""

    def test_session_model_has_workspace_id(self):
        """ChatSession model must have a workspace_id field."""
        from app.models.session import ChatSession

        assert hasattr(ChatSession, "workspace_id"), (
            "ChatSession model must have workspace_id field for session->workspace binding"
        )

    def test_session_workspace_id_is_nullable(self):
        """workspace_id must be nullable (not all sessions are dev sessions)."""
        from app.models.session import ChatSession

        col = ChatSession.workspace_id
        assert col is not None
        assert col.nullable is True


class TestSessionWorkspaceBindingCreate:
    """SWB-2: Session can be created with workspace_id."""

    def test_session_can_bind_workspace(self):
        """Can create a ChatSession with workspace_id set."""
        from app.models.session import ChatSession

        session = ChatSession(
            id="session-123",
            owner_id="user-456",
            title="Dev Session",
            mode="single",
            workspace_id="workspace-789",
        )

        assert session.workspace_id == "workspace-789"
        assert session.owner_id == "user-456"

    def test_session_workspace_id_is_string(self):
        """workspace_id field type is string."""
        from app.models.session import ChatSession

        session = ChatSession(
            id="session-test",
            owner_id="user-1",
            mode="single",
            workspace_id="ws-bound-001",
        )

        assert isinstance(session.workspace_id, str)
        assert session.workspace_id == "ws-bound-001"


class TestSessionWorkspacePersistence:
    """SWB-3: workspace_id is persisted and queryable."""

    def test_session_workspace_binding_persists(self):
        """workspace_id assigned to a session persists through the model."""
        from app.models.session import ChatSession

        session = ChatSession(
            id="persist-test-session",
            owner_id="user-persist",
            mode="single",
            workspace_id="ws-persist-123",
        )

        assert session.workspace_id == "ws-persist-123"

    def test_session_can_update_workspace_id(self):
        """workspace_id can be updated after creation."""
        from app.models.session import ChatSession

        session = ChatSession(
            id="update-ws-test",
            owner_id="user-1",
            mode="single",
            workspace_id=None,
        )

        session.workspace_id = "ws-newly-assigned"
        assert session.workspace_id == "ws-newly-assigned"


class TestSessionWithoutWorkspace:
    """SWB-4: Session without workspace has workspace_id=None."""

    def test_session_without_workspace_has_null(self):
        """Session created without workspace_id should have workspace_id=None."""
        from app.models.session import ChatSession

        session = ChatSession(
            id="no-ws-session",
            owner_id="user-1",
            mode="single",
        )

        assert session.workspace_id is None

    def test_session_workspace_id_nullable(self):
        """workspace_id can be None for non-dev sessions."""
        from app.models.session import ChatSession

        session = ChatSession(
            id="non-dev-session",
            owner_id="user-1",
            mode="group",
        )

        assert session.workspace_id is None


class TestSessionWorkspaceRelationship:
    """SWB-5: Session query returns workspace binding info."""

    def test_session_workspace_id_relationship(self):
        """Session object exposes workspace_id for relationship queries."""
        from app.models.session import ChatSession

        session = ChatSession(
            id="rel-test-session",
            owner_id="user-rel",
            mode="single",
            workspace_id="ws-relationship-001",
        )

        assert hasattr(session, "workspace_id")
        assert session.workspace_id == "ws-relationship-001"

    def test_session_with_null_workspace_id_queryable(self):
        """Session with workspace_id=None is distinguishable from bound session."""
        from app.models.session import ChatSession

        bound_session = ChatSession(
            id="bound-session",
            owner_id="user-1",
            mode="single",
            workspace_id="ws-bound",
        )

        unbound_session = ChatSession(
            id="unbound-session",
            owner_id="user-1",
            mode="single",
        )

        assert bound_session.workspace_id is not None
        assert unbound_session.workspace_id is None
        assert bound_session.workspace_id != unbound_session.workspace_id


class TestSessionSchemaWorkspaceId:
    """SWB-6: Session schemas support workspace_id."""

    def test_session_create_schema_has_workspace_id(self):
        """SessionCreate schema accepts workspace_id."""
        from app.schemas.session import SessionCreate

        payload = SessionCreate(
            title="Dev Session",
            mode="single",
            workspace_id="ws-schema-test",
        )

        assert payload.workspace_id == "ws-schema-test"

    def test_session_create_schema_workspace_id_required(self):
        """Task B+C-1: SessionCreate schema REQUIRES workspace_id (not nullable)."""
        from app.schemas.session import SessionCreate
        from pydantic import ValidationError

        # Should fail because workspace_id is now required
        with pytest.raises(ValidationError) as exc_info:
            SessionCreate(
                title="Non-dev Session",
                mode="single",
            )
        errors = exc_info.value.errors()
        assert any("workspace_id" in str(e).lower() for e in errors)

    def test_session_response_schema_has_workspace_id(self):
        """SessionResponse schema includes workspace_id and workspace object."""
        from app.schemas.session import SessionResponse, WorkspaceSummary
        from datetime import datetime, timezone

        response = SessionResponse(
            id="session-resp",
            owner_id="user-resp",
            title="Test Session",
            mode="single",
            is_pinned=False,
            is_archived=False,
            workspace_id="ws-in-resp",
            workspace=WorkspaceSummary(
                id="ws-in-resp",
                name="MyProject",
                root_path="D:/code/MyProject",
            ),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert response.workspace_id == "ws-in-resp"
        assert response.workspace is not None
        assert response.workspace.id == "ws-in-resp"

    def test_session_update_schema_allows_workspace_id(self):
        """SessionUpdate schema allows workspace_id changes."""
        from app.schemas.session import SessionUpdate

        update = SessionUpdate(workspace_id="ws-new")
        assert update.workspace_id == "ws-new"
