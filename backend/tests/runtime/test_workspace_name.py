# -*- coding: utf-8 -*-
"""Task B+C-1 - Workspace name field tests.

Tests verify:
1. Workspace model has a name field
2. Workspace name is derived from root_path or explicitly set
3. Workspace API returns name for frontend display
4. SessionResponse includes workspace details (id, name, root_path)
"""
from datetime import datetime, timezone

import pytest


class TestWorkspaceModelName:
    """TDD: Workspace model should have a name field."""

    def test_workspace_model_has_name_field(self):
        """Workspace model must have a 'name' field."""
        from app.models.workspace import Workspace

        assert hasattr(Workspace, "name"), \
            "Workspace model must have 'name' field for display purposes"

    def test_workspace_name_defaults_to_folder_name(self):
        """Workspace name should default to the folder name from root_path."""
        from app.models.workspace import Workspace

        ws = Workspace(
            owner_id="user-1",
            root_path="D:/code/MyProject",
        )

        # Name should be derived from root_path
        assert ws.name == "MyProject"

    def test_workspace_name_can_be_explicitly_set(self):
        """Workspace name can be explicitly set."""
        from app.models.workspace import Workspace

        ws = Workspace(
            owner_id="user-1",
            root_path="D:/code/MyProject",
            name="Custom Name",
        )

        assert ws.name == "Custom Name"


class TestWorkspaceSchemaName:
    """TDD: Workspace schemas support name field."""

    def test_workspace_create_schema_has_name(self):
        """WorkspaceCreate schema should accept name."""
        from app.schemas.workspace import WorkspaceCreate

        payload = WorkspaceCreate(
            root_path="D:/code/TestProject",
            name="Test Workspace",
        )

        assert payload.name == "Test Workspace"

    def test_workspace_create_schema_name_optional(self):
        """WorkspaceCreate schema name should be optional (auto-derived if not provided)."""
        from app.schemas.workspace import WorkspaceCreate

        payload = WorkspaceCreate(
            root_path="D:/code/TestProject",
        )

        # name is auto-derived from root_path when not provided
        assert payload.name == "TestProject"

    def test_workspace_response_schema_has_name(self):
        """WorkspaceResponse schema should include name."""
        from app.schemas.workspace import WorkspaceResponse

        response = WorkspaceResponse(
            id="ws-123",
            owner_id="user-456",
            root_path="D:/code/TestProject",
            name="Test Workspace",
            created_at=datetime.now(timezone.utc),
        )

        assert response.name == "Test Workspace"


class TestSessionResponseWithWorkspaceDetails:
    """TDD: SessionResponse should include full workspace details."""

    def test_session_response_with_workspace_object(self):
        """SessionResponse should include nested workspace object."""
        from datetime import datetime, timezone
        from app.schemas.session import SessionResponse

        # Current implementation only has workspace_id
        # According to spec 4.4, should have workspace: {id, name, root_path}
        response = SessionResponse(
            id="session-123",
            owner_id="user-456",
            title="Test",
            mode="single",
            is_pinned=False,
            is_archived=False,
            workspace_id="ws-789",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        assert response.workspace_id == "ws-789"
        # TODO: Should have workspace field with full details
