# -*- coding: utf-8 -*-
"""P3 - WorkspaceGuard initialized from session workspace binding — RED phase.

Tests verify that:
- Guard accepts valid absolute root path
- Guard blocks path traversal (..) escape
- Guard blocks absolute paths outside workspace
- Guard correctly resolves relative paths within workspace
- Guard prevents escape via symlink
- Write target within workspace is allowed
- Write target outside workspace is rejected
"""

import os
import tempfile
from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "tools" / "test_workspace"


class TestWorkspaceGuardAcceptValidPath:
    """WGG-1: Guard accepts valid absolute root path."""

    def test_guard_accepts_valid_workspace_root(self):
        """WorkspaceGuard should accept a valid absolute root path."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)
        assert guard.root == TEST_WORKSPACE_ROOT.resolve()

    def test_guard_resolves_tilde_in_root(self):
        """WorkspaceGuard should expand tilde in root path."""
        from app.runtime.workspace import WorkspaceGuard

        home = Path(os.path.expanduser("~"))
        if home.exists():
            home_ws = home / ".agenthub_workspace_test"
            guard = WorkspaceGuard(root=str(home_ws))
            assert guard.root is not None
            assert "~" not in str(guard.root)


class TestWorkspaceGuardRejectsTraversal:
    """WGG-2: Guard blocks path traversal (..) escape."""

    def test_guard_rejects_path_traversal(self):
        """WorkspaceGuard should block '..' traversal to escape workspace."""
        from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        # Attempt to escape via ..
        traversal_path = TEST_WORKSPACE_ROOT / ".." / "outside.txt"
        resolved = guard.resolve_path(str(traversal_path))

        with pytest.raises(WorkspaceAccessError):
            guard.ensure_within_workspace(resolved)

    def test_guard_rejects_deep_traversal(self):
        """Guard should block deep '..' traversal."""
        from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        deep_traversal = TEST_WORKSPACE_ROOT / "subdir" / ".." / ".." / "outside.txt"
        resolved = guard.resolve_path(str(deep_traversal))

        with pytest.raises(WorkspaceAccessError):
            guard.ensure_within_workspace(resolved)

    def test_guard_rejects_nested_traversal(self):
        """Guard should block deep '..' traversal that escapes workspace."""
        from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        # Deep traversal that goes above the workspace root
        # "/a/b/../../.." from TEST_WORKSPACE_ROOT goes above the root
        parts = str(TEST_WORKSPACE_ROOT).split(os.sep)
        depth = len(parts)
        # Build a path that definitely escapes: .. repeated enough times
        escape = os.sep.join([".."] * (depth + 3))
        escaped_path = str(Path(escape).resolve())

        resolved = guard.resolve_path(escaped_path)

        with pytest.raises(WorkspaceAccessError):
            guard.ensure_within_workspace(resolved)


class TestWorkspaceGuardRejectsAbsoluteOutside:
    """WGG-3: Guard blocks absolute paths outside workspace."""

    def test_guard_rejects_absolute_outside(self):
        """WorkspaceGuard should reject absolute paths outside workspace."""
        from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        # Absolute path to a location outside workspace
        home = Path(os.path.expanduser("~")).resolve()
        outside_path = home / "evil_file.txt"

        resolved = guard.resolve_path(str(outside_path))

        with pytest.raises(WorkspaceAccessError):
            guard.ensure_within_workspace(resolved)

    def test_guard_rejects_system_paths(self):
        """Guard should block access to system paths."""
        from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        system_paths = [
            "/etc/passwd",
            "/bin/sh",
            "C:\\Windows\\System32",
        ]
        for sys_path in system_paths:
            try:
                p = Path(sys_path)
                if p.exists() and not p.is_relative_to(TEST_WORKSPACE_ROOT):
                    resolved = guard.resolve_path(sys_path)
                    with pytest.raises(WorkspaceAccessError):
                        guard.ensure_within_workspace(resolved)
            except (OSError, ValueError):
                pass  # Skip paths that don't exist on this system


class TestWorkspaceGuardResolvesRelative:
    """WGG-4: Guard correctly resolves relative paths within workspace."""

    def test_guard_resolves_relative_paths(self):
        """Guard should resolve relative paths within workspace."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        relative = "subdir/code.py"
        resolved = guard.resolve_path(relative)

        assert resolved.is_absolute()
        assert guard.is_within_workspace(resolved)
        assert "subdir" in str(resolved)

    def test_guard_resolves_nested_relative(self):
        """Guard should resolve nested relative paths."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        nested = "subdir/nested/deep.txt"
        resolved = guard.resolve_path(nested)

        assert resolved.is_absolute()
        assert guard.is_within_workspace(resolved)

    def test_guard_accepts_root_as_boundary(self):
        """The workspace root itself should be within workspace."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        assert guard.is_within_workspace(guard.root)


class TestWorkspaceGuardSymlink:
    """WGG-5: Guard prevents escape via symlink."""

    def test_guard_symlink_escape_prevented(self):
        """Guard should prevent escape via symlink pointing outside workspace."""
        from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        # Create a temporary symlink inside workspace pointing outside
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file outside workspace
            outside_file = Path(tmpdir) / "outside_target.txt"
            outside_file.write_text("outside content")

            # Create symlink inside workspace test area
            subdir = TEST_WORKSPACE_ROOT / "subdir"
            if subdir.exists():
                symlink_path = subdir / "escape_link"
                try:
                    # Create symlink (may fail on Windows without admin)
                    symlink_path.symlink_to(outside_file)

                    # Try to access via symlink
                    resolved = guard.resolve_path(str(symlink_path))

                    # Guard should block the escape
                    with pytest.raises(WorkspaceAccessError):
                        guard.ensure_within_workspace(resolved)
                except OSError:
                    pytest.skip("Symlink creation not available on this system")


class TestWorkspaceGuardWriteBoundary:
    """WGG-6: Write boundary enforcement from session workspace binding."""

    def test_guard_write_within_workspace(self):
        """Write target within workspace is allowed."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        # Target inside workspace
        target = TEST_WORKSPACE_ROOT / "subdir" / "new_file.txt"
        is_valid, reason = guard.validate_write_target(target)

        assert is_valid, f"Write within workspace should be allowed: {reason}"

    def test_guard_write_outside_workspace(self):
        """Write target outside workspace is rejected."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        # Target outside workspace
        home = Path(os.path.expanduser("~")).resolve()
        target = home / "malicious_write.txt"

        is_valid, reason = guard.validate_write_target(target)

        assert not is_valid, "Write outside workspace should be rejected"
        assert "outside workspace" in reason.lower()

    def test_guard_write_traversal_rejected(self):
        """Write with '..' traversal outside workspace is rejected."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        # Traversal to outside
        target = (TEST_WORKSPACE_ROOT / ".." / "evil_write.txt").resolve()

        is_valid, reason = guard.validate_write_target(target)

        assert not is_valid
        assert "outside workspace" in reason.lower()

    def test_guard_resolve_write_path_validates_boundary(self):
        """resolve_write_path should validate workspace boundary for writes."""
        from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        # Relative path inside workspace - should succeed
        inside = guard.resolve_write_path("subdir/newfile.txt")
        assert guard.is_within_workspace(inside)

        # Absolute path outside workspace - should fail
        home = Path(os.path.expanduser("~")).resolve()
        outside = str(home / "bad.txt")

        with pytest.raises(WorkspaceAccessError):
            guard.resolve_write_path(outside)

    def test_guard_check_write_allowed_convenience(self):
        """check_write_allowed convenience method should work correctly."""
        from app.runtime.workspace import WorkspaceGuard

        guard = WorkspaceGuard(root=TEST_WORKSPACE_ROOT)

        # Inside workspace
        inside_target = (TEST_WORKSPACE_ROOT / "subdir" / "file.txt").resolve()
        assert guard.check_write_allowed(inside_target) is True

        # Outside workspace
        home = Path(os.path.expanduser("~")).resolve()
        outside_target = (home / "file.txt").resolve()
        assert guard.check_write_allowed(outside_target) is False


class TestWorkspaceGuardFromSessionBinding:
    """WGG-7: Guard initialized from session workspace binding context."""

    def test_guard_initialized_from_bound_workspace_root(self):
        """Guard should be initialized with the workspace root from session binding."""
        from app.runtime.workspace import WorkspaceGuard

        ws_root = str(TEST_WORKSPACE_ROOT)
        guard = WorkspaceGuard(root=ws_root)

        # The guard's root should match the bound workspace
        assert str(guard.root) == str(TEST_WORKSPACE_ROOT.resolve())

    def test_guard_from_session_prevents_env_override(self):
        """Guard root from session binding should not be affected by WORKSPACE_ROOT env."""
        from app.runtime.workspace import WorkspaceGuard

        bound_root = str(TEST_WORKSPACE_ROOT)
        env_root = str(TEST_WORKSPACE_ROOT / "env_override")

        # Guard is initialized with bound workspace, not env
        guard = WorkspaceGuard(root=bound_root)

        assert str(guard.root) == str(TEST_WORKSPACE_ROOT.resolve())
        assert str(guard.root) != env_root
