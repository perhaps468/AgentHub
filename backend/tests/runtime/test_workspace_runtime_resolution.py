# -*- coding: utf-8 -*-
"""P3 - Workspace resolution from session tests — RED phase.

Tests verify that:
- WorkspaceService resolves workspace from session binding
- Falls back to WORKSPACE_ROOT env when no session binding
- Fails when session has no workspace_id
- Fails when bound workspace doesn't exist
- Fails when workspace doesn't belong to session owner
- Fails when workspace root path is invalid/inaccessible
- Tools receive correct workspace_root

Note: These tests focus on the WorkspaceService and the workspace resolution logic.
The RAS integration tests document expected behavior.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "tools" / "test_workspace"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TestWorkspaceServiceResolution:
    """WRR-1: WorkspaceService resolves workspace from session binding."""

    def test_get_workspace_returns_bound_workspace(self):
        """WorkspaceService.get_workspace returns workspace by id."""
        from app.services.workspace import WorkspaceService

        mock_ws = MagicMock(
            id="ws-bound-123",
            owner_id="user-123",
            root_path=str(TEST_WORKSPACE_ROOT.resolve()),
        )
        mock_db = MagicMock()
        mock_db.get.return_value = mock_ws

        service = WorkspaceService(db=mock_db)
        ws = service.get_workspace("ws-bound-123")

        assert ws is not None
        assert ws.id == "ws-bound-123"

    def test_get_workspace_returns_nonexistent_error(self):
        """WorkspaceService.get_workspace raises WorkspaceNotFoundError when not found."""
        from app.services.workspace import WorkspaceService, WorkspaceNotFoundError

        mock_db = MagicMock()
        mock_db.get.return_value = None

        service = WorkspaceService(db=mock_db)

        with pytest.raises(WorkspaceNotFoundError):
            service.get_workspace("nonexistent-ws")

    def test_get_workspace_checks_ownership(self):
        """WorkspaceService.get_workspace raises WorkspaceAccessDeniedError when owner mismatch."""
        from app.services.workspace import WorkspaceService, WorkspaceAccessDeniedError

        mock_ws = MagicMock(
            id="ws-owned",
            owner_id="rightful-owner",
            root_path=str(TEST_WORKSPACE_ROOT.resolve()),
        )
        mock_db = MagicMock()
        mock_db.get.return_value = mock_ws

        service = WorkspaceService(db=mock_db)

        with pytest.raises(WorkspaceAccessDeniedError):
            service.get_workspace("ws-owned", owner_id="intruder")

    def test_list_user_workspaces_returns_only_own(self):
        """list_user_workspaces returns only workspaces owned by the user."""
        from app.services.workspace import WorkspaceService

        mock_workspaces = [
            MagicMock(id="ws-1", owner_id="user-1", root_path="/ws/1"),
            MagicMock(id="ws-2", owner_id="user-1", root_path="/ws/2"),
        ]
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_workspaces

        service = WorkspaceService(db=mock_db)
        workspaces = service.list_user_workspaces("user-1")

        assert len(workspaces) == 2
        assert all(ws.owner_id == "user-1" for ws in workspaces)


class TestWorkspaceServiceValidation:
    """WRR-2: Workspace root path validation."""

    def test_validate_root_path_rejects_nonexistent(self):
        """_validate_root_path rejects non-existent paths."""
        from app.services.workspace import WorkspaceService, InvalidWorkspacePathError

        mock_db = MagicMock()
        service = WorkspaceService(db=mock_db)

        with pytest.raises(InvalidWorkspacePathError):
            service._validate_root_path("/nonexistent/path/workspace")

    def test_validate_root_path_rejects_file(self):
        """_validate_root_path rejects file paths."""
        from app.services.workspace import WorkspaceService, InvalidWorkspacePathError

        mock_db = MagicMock()
        service = WorkspaceService(db=mock_db)

        with pytest.raises(InvalidWorkspacePathError):
            service._validate_root_path(__file__)

    def test_validate_root_path_accepts_directory(self):
        """_validate_root_path accepts valid directories."""
        from app.services.workspace import WorkspaceService

        mock_db = MagicMock()
        service = WorkspaceService(db=mock_db)

        # Test workspace directory exists
        service._validate_root_path(str(TEST_WORKSPACE_ROOT.resolve()))


class TestWorkspaceResolutionEnvFallback:
    """WRR-3: RAS falls back to WORKSPACE_ROOT env when no session binding."""

    def test_ras_resolves_from_env_when_no_session(self):
        """RuntimeAgentService falls back to WORKSPACE_ROOT env var."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        env_path = str(TEST_WORKSPACE_ROOT.resolve())

        # When session doesn't exist in DB and no explicit workspace_root,
        # RAS falls back to WORKSPACE_ROOT env
        mock_db = MagicMock()
        mock_db.get.return_value = None  # Session not found

        with patch.dict(os.environ, {"WORKSPACE_ROOT": env_path}):
            service = RuntimeAgentService(
                session_id="non-existent-session",
                user_message="hello",
                agent_role="PM",
                llm_adapter=_FakeAdapter(),
                db=mock_db,
                workspace_root=None,
            )

            # RAS should have resolved from env
            assert service.workspace_root == env_path

    def test_ras_prefers_explicit_over_env(self):
        """Explicit workspace_root takes precedence over WORKSPACE_ROOT env."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        explicit_path = str(TEST_WORKSPACE_ROOT.resolve())
        env_path = str((TEST_WORKSPACE_ROOT.parent / "env_ws").resolve())

        mock_db = MagicMock()
        mock_db.get.return_value = None

        with patch.dict(os.environ, {"WORKSPACE_ROOT": env_path}):
            service = RuntimeAgentService(
                session_id="session-explicit",
                user_message="hello",
                agent_role="PM",
                llm_adapter=_FakeAdapter(),
                db=mock_db,
                workspace_root=explicit_path,
            )

            assert service.workspace_root == explicit_path
            assert service.workspace_root != env_path


class TestWorkspaceResolutionBoundSession:
    """WRR-4: RAS resolves workspace from bound session."""

    def test_ras_resolves_from_bound_session(self):
        """RAS resolves workspace from session's workspace_id binding."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from app.models.session import ChatSession
        from app.services.workspace import WorkspaceService

        ws_path = str(TEST_WORKSPACE_ROOT.resolve())

        # Mock session with workspace binding
        mock_session = MagicMock(spec=ChatSession)
        mock_session.workspace_id = "ws-bound-session"
        mock_session.owner_id = "user-bound"

        # Mock workspace
        mock_ws = MagicMock(
            id="ws-bound-session",
            owner_id="user-bound",
            root_path=ws_path,
        )

        mock_db = MagicMock()

        def get_side_effect(model_class, key):
            if model_class.__name__ == "ChatSession" and key == "session-bound":
                return mock_session
            return None

        mock_db.get.side_effect = get_side_effect

        with patch.object(WorkspaceService, "get_workspace", return_value=mock_ws):
            service = RuntimeAgentService(
                session_id="session-bound",
                user_message="hello",
                agent_role="PM",
                llm_adapter=_FakeAdapter(),
                db=mock_db,
                workspace_root=None,
            )

            # RAS should resolve workspace from bound session
            assert service.workspace_root == ws_path


class TestWorkspaceResolutionFailures:
    """WRR-5: Workspace resolution failure cases."""

    def test_ras_fails_when_session_not_found_and_no_fallback(self):
        """RAS raises WorkspaceNotBoundError when no session and no env fallback."""
        from app.runtime.runtime_agent_service import RuntimeAgentService, WorkspaceNotBoundError

        mock_db = MagicMock()
        mock_db.get.return_value = None

        # Remove WORKSPACE_ROOT from env
        env_backup = os.environ.pop("WORKSPACE_ROOT", None)
        try:
            with pytest.raises(WorkspaceNotBoundError):
                RuntimeAgentService(
                    session_id="orphan-session",
                    user_message="hello",
                    agent_role="PM",
                    llm_adapter=_FakeAdapter(),
                    db=mock_db,
                    workspace_root=None,
                )
        finally:
            if env_backup is not None:
                os.environ["WORKSPACE_ROOT"] = env_backup

    def test_ras_fails_when_workspace_not_found(self):
        """RAS raises WorkspaceNotFoundError when bound workspace doesn't exist."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from app.models.session import ChatSession
        from app.services.workspace import WorkspaceNotFoundError, WorkspaceService

        mock_session = MagicMock(spec=ChatSession)
        mock_session.workspace_id = "ws-missing"
        mock_session.owner_id = "user-1"

        mock_db = MagicMock()
        mock_db.get.side_effect = lambda m, k: mock_session if m.__name__ == "ChatSession" else None

        with patch.object(WorkspaceService, "get_workspace", side_effect=WorkspaceNotFoundError("ws-missing")):
            with pytest.raises(WorkspaceNotFoundError):
                RuntimeAgentService(
                    session_id="session-ws-missing",
                    user_message="hello",
                    agent_role="PM",
                    llm_adapter=_FakeAdapter(),
                    db=mock_db,
                )

    def test_ras_fails_when_owner_mismatch(self):
        """RAS raises WorkspaceAccessDeniedError when workspace owner doesn't match."""
        from app.runtime.runtime_agent_service import RuntimeAgentService
        from app.models.session import ChatSession
        from app.services.workspace import WorkspaceAccessDeniedError, WorkspaceService

        mock_session = MagicMock(spec=ChatSession)
        mock_session.workspace_id = "ws-owned-by-other"
        mock_session.owner_id = "intruder"

        mock_db = MagicMock()
        mock_db.get.side_effect = lambda m, k: mock_session if m.__name__ == "ChatSession" else None

        with patch.object(
            WorkspaceService, "get_workspace",
            side_effect=WorkspaceAccessDeniedError("ws-owned-by-other", "owner", "intruder")
        ):
            with pytest.raises(WorkspaceAccessDeniedError):
                RuntimeAgentService(
                    session_id="session-owner-mismatch",
                    user_message="hello",
                    agent_role="PM",
                    llm_adapter=_FakeAdapter(),
                    db=mock_db,
                )


class TestToolsReceiveWorkspaceRoot:
    """WRR-6: Tools receive correct workspace_root."""

    def test_build_tools_includes_workspace_tools(self):
        """_build_tools includes workspace-scoped tools."""
        from app.runtime.runtime_agent_service import RuntimeAgentService

        ws_path = str(TEST_WORKSPACE_ROOT.resolve())

        # Create RAS with explicit workspace_root, mocking the session not found case
        mock_db = MagicMock()
        mock_db.get.return_value = None  # Session not found - will use explicit workspace_root

        service = RuntimeAgentService(
            session_id="session-tools",
            user_message="hello",
            agent_role="PM",
            llm_adapter=_FakeAdapter(),
            db=mock_db,
            workspace_root=ws_path,
        )

        tools = service._build_tools()
        tool_names = {t.name for t in tools}

        assert "read_file_tool" in tool_names
        assert "write_file" in tool_names
        assert "list_directory_tool" in tool_names
        assert "glob_tool" in tool_names
        assert "grep_tool" in tool_names


# --------------------------------------------------------------------------
# Fake adapter for testing
# --------------------------------------------------------------------------

from app.runtime.generative_model import ResponseStats, TokenUsage


class _FakeAdapter:
    """Minimal fake LLMAdapter that returns canned responses for testing."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or [
            "<action><task_complete><answer>answer</answer></task_complete></action>"
        ]
        self.call_count = 0

    async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
        idx = min(self.call_count, len(self.responses) - 1)
        text = self.responses[idx]
        self.call_count += 1
        return ResponseStats(
            response=text,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=model,
            finish_reason="stop",
        )

    async def async_stream_generate_with_history(
        self, messages_history: list, model: str, **kwargs
    ) -> AsyncIterator[str]:
        idx = min(self.call_count, len(self.responses) - 1)
        text = self.responses[idx]
        self.call_count += 1
        for char in text:
            yield char
