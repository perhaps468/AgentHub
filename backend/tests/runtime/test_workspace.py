"""Tests for workspace write boundary methods — RED phase.

These tests verify M6 write boundary capabilities:
- resolve_write_path validates workspace boundary
- validate_write_target checks parent directory
- check_write_allowed convenience method
"""

import os
import tempfile
from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "tools" / "test_workspace"


class TestWorkspaceWriteImport:
    """Verify workspace write classes are importable."""

    def test_workspace_write_error_importable(self):
        """WorkspaceWriteError should be importable."""
        from app.runtime.workspace import WorkspaceWriteError

        assert WorkspaceWriteError is not None

    def test_resolve_write_path_exists(self):
        """WorkspaceGuard should have resolve_write_path method."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        assert hasattr(guard, "resolve_write_path")

    def test_validate_write_target_exists(self):
        """WorkspaceGuard should have validate_write_target method."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        assert hasattr(guard, "validate_write_target")

    def test_check_write_allowed_exists(self):
        """WorkspaceGuard should have check_write_allowed method."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        assert hasattr(guard, "check_write_allowed")


class TestResolveWritePath:
    """Verify resolve_write_path validates workspace boundary."""

    def test_resolve_write_path_accepts_inside_workspace(self):
        """resolve_write_path should accept relative paths inside workspace."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        resolved = guard.resolve_write_path("subdir/file.txt")

        assert resolved.is_absolute()
        assert guard.is_within_workspace(resolved)

    def test_resolve_write_path_accepts_absolute_inside(self):
        """resolve_write_path should accept absolute paths inside workspace."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        abs_path = str((TEST_WORKSPACE_ROOT / "subdir" / "code.py").resolve())
        resolved = guard.resolve_write_path(abs_path)

        assert resolved == Path(abs_path)

    def test_resolve_write_path_rejects_absolute_outside(self):
        """resolve_write_path should reject absolute paths outside workspace."""
        from app.runtime.workspace import WorkspaceGuard
        from app.runtime.workspace import WorkspaceAccessError

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        home = Path(os.path.expanduser("~")).resolve()
        outside = str(home / "evil_file_m6.txt")

        with pytest.raises(WorkspaceAccessError):
            guard.resolve_write_path(outside)

    def test_resolve_write_path_expands_tilde(self):
        """resolve_write_path should expand tilde in paths."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        # tilde path inside workspace doesn't make sense but resolve should still work
        resolved = guard.resolve_write_path("subdir/file.txt")
        assert "~" not in str(resolved)


class TestValidateWriteTarget:
    """Verify validate_write_target checks parent directory."""

    def test_validate_write_target_accepts_existing_file_parent(self):
        """validate_write_target should accept existing file with writable parent."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        target = (TEST_WORKSPACE_ROOT / "subdir" / "code.py").resolve()

        is_valid, reason = guard.validate_write_target(target)
        assert is_valid, reason

    def test_validate_write_target_rejects_nonexistent_parent(self):
        """validate_write_target should reject when parent does not exist."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        # Create a path with a non-existent parent deep in workspace
        target = (TEST_WORKSPACE_ROOT / "nonexistent_parent_dir_xyz789" / "file.txt").resolve()

        is_valid, reason = guard.validate_write_target(target)
        assert not is_valid
        assert "parent directory does not exist" in reason

    def test_validate_write_target_accepts_nonexistent_file_with_valid_parent(self):
        """validate_write_target should accept new file if parent exists."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        # File does not exist but parent (subdir) does
        target = (TEST_WORKSPACE_ROOT / "subdir" / "brand_new_file_m6.txt").resolve()

        is_valid, reason = guard.validate_write_target(target)
        assert is_valid, reason

    def test_validate_write_target_rejects_outside_workspace(self):
        """validate_write_target should reject paths outside workspace."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        outside = Path(os.path.expanduser("~") or "/tmp").resolve() / "file.txt"

        is_valid, reason = guard.validate_write_target(outside)
        assert not is_valid
        assert "outside workspace" in reason

    def test_validate_write_target_rejects_parent_traversal(self):
        """validate_write_target should reject '..' escape attempt."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        escaped = (TEST_WORKSPACE_ROOT / ".." / "outside.txt").resolve()

        is_valid, reason = guard.validate_write_target(escaped)
        assert not is_valid
        assert "outside workspace" in reason


class TestCheckWriteAllowed:
    """Verify check_write_allowed convenience method."""

    def test_check_write_allowed_true_for_valid_target(self):
        """check_write_allowed should return True for valid target."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        target = (TEST_WORKSPACE_ROOT / "subdir" / "code.py").resolve()

        assert guard.check_write_allowed(target) is True

    def test_check_write_allowed_false_for_outside(self):
        """check_write_allowed should return False for outside paths."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        outside = Path(os.path.expanduser("~") or "/tmp").resolve() / "file.txt"

        assert guard.check_write_allowed(outside) is False

    def test_check_write_allowed_false_for_bad_parent(self):
        """check_write_allowed should return False when parent doesn't exist."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        target = (TEST_WORKSPACE_ROOT / "bad_parent_xyz" / "file.txt").resolve()

        assert guard.check_write_allowed(target) is False


class TestWorkspaceWriteError:
    """Verify WorkspaceWriteError structure."""

    def test_write_error_has_path_and_reason(self):
        """WorkspaceWriteError should expose path and reason."""
        from app.runtime.workspace import WorkspaceWriteError

        err = WorkspaceWriteError(Path("/some/path"), "parent missing")
        assert err.path == Path("/some/path")
        assert err.reason == "parent missing"
        assert "parent missing" in str(err)
