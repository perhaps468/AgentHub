# -*- coding: utf-8 -*-
"""P3 - Workspace model tests — RED phase.

Tests verify that:
- Workspace model can be imported from app.models.workspace
- Workspace model has required fields: id, owner_id, root_path, created_at
- Workspace model can be instantiated with required fields
- Field types are correct
"""

from datetime import datetime

import pytest


class TestWorkspaceModelImport:
    """WSM-1: Workspace model is importable."""

    def test_workspace_model_importable(self):
        """Workspace model should be importable from app.models.workspace."""
        from app.models.workspace import Workspace

        assert Workspace is not None

    def test_workspace_model_from_database_base(self):
        """Workspace model should inherit from database Base."""
        from app.models.workspace import Workspace

        # Workspace should be a SQLAlchemy model (has __tablename__)
        assert hasattr(Workspace, "__tablename__")
        assert Workspace.__tablename__ == "workspaces"


class TestWorkspaceModelFields:
    """WSM-2: Workspace model has required fields."""

    def test_workspace_model_has_required_fields(self):
        """Workspace model must have id, owner_id, root_path, created_at fields."""
        from app.models.workspace import Workspace

        required_fields = ["id", "owner_id", "root_path", "created_at"]
        for field in required_fields:
            assert hasattr(Workspace, field), f"Workspace missing required field: {field}"

    def test_workspace_model_id_is_string(self):
        """id field should be a string type."""
        from app.models.workspace import Workspace

        # Check via column type inspection
        id_col = Workspace.id
        # String columns are mapped_column with String type
        assert id_col is not None

    def test_workspace_model_owner_id_is_string(self):
        """owner_id field should be a string type."""
        from app.models.workspace import Workspace

        owner_id_col = Workspace.owner_id
        assert owner_id_col is not None

    def test_workspace_model_root_path_is_string(self):
        """root_path field should be a string type."""
        from app.models.workspace import Workspace

        root_path_col = Workspace.root_path
        assert root_path_col is not None

    def test_workspace_model_created_at_is_datetime(self):
        """created_at field should be a datetime type."""
        from app.models.workspace import Workspace

        created_at_col = Workspace.created_at
        assert created_at_col is not None

    def test_workspace_model_id_is_primary_key(self):
        """id field should be the primary key."""
        from app.models.workspace import Workspace

        # Primary key columns have primary_key=True
        assert Workspace.id.primary_key is True


class TestWorkspaceModelInstantiation:
    """WSM-3: Workspace model can be instantiated."""

    def test_workspace_model_can_be_instantiated(self):
        """Workspace can be created with required fields."""
        from app.models.workspace import Workspace

        ws = Workspace(
            id="test-workspace-id-123",
            owner_id="user-456",
            root_path="/tmp/test_workspace",
            created_at=datetime.utcnow(),
        )

        assert ws.id == "test-workspace-id-123"
        assert ws.owner_id == "user-456"
        assert ws.root_path == "/tmp/test_workspace"
        assert isinstance(ws.created_at, datetime)

    def test_workspace_model_id_is_string(self):
        """Instantiated workspace id field is a string."""
        from app.models.workspace import Workspace

        ws = Workspace(
            id="ws-abc-123",
            owner_id="user-1",
            root_path="/workspace/test",
            created_at=datetime.utcnow(),
        )

        assert isinstance(ws.id, str)

    def test_workspace_model_owner_id_is_string(self):
        """Instantiated workspace owner_id field is a string."""
        from app.models.workspace import Workspace

        ws = Workspace(
            id="ws-abc-123",
            owner_id="owner-xyz",
            root_path="/workspace/test",
            created_at=datetime.utcnow(),
        )

        assert isinstance(ws.owner_id, str)

    def test_workspace_model_root_path_is_string(self):
        """Instantiated workspace root_path field is a string."""
        from app.models.workspace import Workspace

        ws = Workspace(
            id="ws-abc-123",
            owner_id="user-1",
            root_path="/workspace/myproject",
            created_at=datetime.utcnow(),
        )

        assert isinstance(ws.root_path, str)

    def test_workspace_model_created_at_is_datetime(self):
        """Instantiated workspace created_at field is a datetime."""
        from app.models.workspace import Workspace

        now = datetime.utcnow()
        ws = Workspace(
            id="ws-abc-123",
            owner_id="user-1",
            root_path="/workspace/test",
            created_at=now,
        )

        assert isinstance(ws.created_at, datetime)


class TestWorkspaceModelOptionalFields:
    """WSM-4: Workspace model may have optional fields."""

    def test_workspace_model_may_have_name_field(self):
        """Workspace may have an optional name field."""
        from app.models.workspace import Workspace

        # name is optional - workspace can be created without it
        ws = Workspace(
            id="ws-no-name",
            owner_id="user-1",
            root_path="/workspace/test",
            created_at=datetime.utcnow(),
        )
        # Should not raise - name is optional
        assert ws.id == "ws-no-name"

    def test_workspace_model_may_have_description_field(self):
        """Workspace may have an optional description field."""
        from app.models.workspace import Workspace

        ws = Workspace(
            id="ws-no-desc",
            owner_id="user-1",
            root_path="/workspace/test",
            created_at=datetime.utcnow(),
        )
        # Should not raise - description is optional
        assert ws.id == "ws-no-desc"
