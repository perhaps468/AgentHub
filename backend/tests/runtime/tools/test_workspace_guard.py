"""Tests for workspace guard — RED (module does not exist yet)."""

import os
import sys
from pathlib import Path

import pytest

TEST_ROOT = Path(__file__).parent.parent.parent.parent.parent / "tests" / "runtime" / "tools"
TEST_WORKSPACE_ROOT = TEST_ROOT / "test_workspace"


class TestWorkspaceGuardImport:
    """Verify workspace module can be imported."""

    def test_workspace_module_importable(self):
        """Workspace module should be importable from app.runtime.workspace."""
        from app.runtime.workspace import WorkspaceGuard

        assert WorkspaceGuard is not None


class TestWorkspaceGuardInit:
    """Verify WorkspaceGuard initialization."""

    def test_init_with_absolute_path(self):
        """WorkspaceGuard should accept an absolute path as root."""
        from app.runtime.workspace import WorkspaceGuard

        root = TEST_WORKSPACE_ROOT.resolve()
        guard = WorkspaceGuard(root=root)

        assert guard.root == root.resolve()

    def test_init_resolves_relative_path(self):
        """WorkspaceGuard should resolve relative paths to absolute."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        assert guard.root.is_absolute()

    def test_init_strips_trailing_slash(self):
        """WorkspaceGuard should normalize trailing slash."""
        from app.runtime.workspace import WorkspaceGuard

        root_with_slash = Path(str(TEST_WORKSPACE_ROOT) + os.sep)
        guard = WorkspaceGuard(root=root_with_slash)

        assert str(guard.root).rstrip(os.sep) == str(guard.root).rstrip(os.sep)


class TestResolvePath:
    """Verify path resolution logic."""

    def test_resolve_absolute_path(self):
        """resolve_path should return the same absolute path."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        abs_path = (TEST_WORKSPACE_ROOT / "subdir" / "file.txt").resolve()

        resolved = guard.resolve_path(str(abs_path))

        assert resolved == abs_path

    def test_resolve_relative_path(self):
        """resolve_path should resolve relative path against workspace root."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        resolved = guard.resolve_path("subdir/file.txt")

        expected = (TEST_WORKSPACE_ROOT / "subdir" / "file.txt").resolve()
        assert resolved == expected

    def test_resolve_expands_tilde(self):
        """resolve_path should expand tilde in paths."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        resolved = guard.resolve_path("~/somefile.txt")

        assert "~" not in str(resolved)
        assert resolved.is_absolute()


class TestIsWithinWorkspace:
    """Verify workspace boundary checks."""

    def test_file_within_workspace(self):
        """is_within_workspace should return True for paths inside workspace."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        file_path = (TEST_WORKSPACE_ROOT / "subdir" / "file.txt").resolve()

        assert guard.is_within_workspace(file_path) is True

    def test_file_outside_workspace(self):
        """is_within_workspace should return False for paths outside workspace."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        outside_path = Path(os.path.expanduser("~") or "/tmp").resolve()

        result = guard.is_within_workspace(outside_path)
        assert result is False

    def test_parent_traversal_rejected(self):
        """is_within_workspace should return False when '..' escapes workspace."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        escaped = (TEST_WORKSPACE_ROOT / "subdir" / ".." / ".." / "outside.txt").resolve()

        assert guard.is_within_workspace(escaped) is False

    @pytest.mark.skipif(sys.platform == "win32", reason="symlink requires admin on Windows")
    def test_symlink_escape_rejected(self):
        """is_within_workspace should return False for symlink pointing outside."""
        import os

        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        safe_path = TEST_WORKSPACE_ROOT / "subdir" / "safe.txt"
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        safe_path.write_text("safe")

        symlink_path = TEST_WORKSPACE_ROOT / "link_to_outside"
        target_path = TEST_WORKSPACE_ROOT.parent / "outside_test_dir"
        target_path.mkdir(exist_ok=True)

        try:
            if symlink_path.exists() or symlink_path.is_symlink():
                symlink_path.unlink()
            symlink_path.symlink_to(target_path, target_is_directory=True)
            escaped = symlink_path.resolve()

            assert guard.is_within_workspace(escaped) is False
        finally:
            if symlink_path.is_symlink():
                symlink_path.unlink()
            if target_path.exists():
                target_path.rmdir()


class TestEnsureWithinWorkspace:
    """Verify safe path enforcement."""

    def test_ensure_within_accepts_inside_path(self):
        """ensure_within_workspace should return path unchanged when inside workspace."""
        from app.runtime.workspace import WorkspaceGuard
        from app.runtime.workspace import WorkspaceAccessError

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        inside = (TEST_WORKSPACE_ROOT / "subdir" / "file.txt").resolve()

        result = guard.ensure_within_workspace(inside)

        assert result == inside

    def test_ensure_within_rejects_outside_path(self):
        """ensure_within_workspace should raise WorkspaceAccessError for outside paths."""
        from app.runtime.workspace import WorkspaceGuard
        from app.runtime.workspace import WorkspaceAccessError

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        outside = Path(os.path.expanduser("~") or "/tmp").resolve()

        with pytest.raises(WorkspaceAccessError):
            guard.ensure_within_workspace(outside)

    def test_ensure_within_rejects_parent_traversal(self):
        """ensure_within_workspace should reject paths that escape via '..'."""
        from app.runtime.workspace import WorkspaceGuard
        from app.runtime.workspace import WorkspaceAccessError

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        escaped = (TEST_WORKSPACE_ROOT / ".." / "outside.txt").resolve()

        with pytest.raises(WorkspaceAccessError):
            guard.ensure_within_workspace(escaped)


class TestWorkspaceAccessError:
    """Verify error type."""

    def test_error_has_meaningful_message(self):
        """WorkspaceAccessError should include the offending path in the message."""
        from app.runtime.workspace import WorkspaceGuard, WorkspaceAccessError

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        outside = Path(os.path.expanduser("~") or "/tmp").resolve()

        try:
            guard.ensure_within_workspace(outside)
            pytest.fail("Expected WorkspaceAccessError")
        except WorkspaceAccessError as e:
            assert str(outside) in str(e)
            assert "workspace" in str(e).lower()
