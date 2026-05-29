"""Workspace guard for AgentHub runtime.

All read-only and write file tools must pass through this guard to ensure access
is confined to the designated workspace root.

M4 scope (read-only):
- Path boundary control
- Minimal path normalization
- Symlink escape prevention

M6 scope (write boundary additions):
- Unified path resolution for write targets
- Write target validation (parent directory check)
- Preview / pending change path constraint
"""

import os
from pathlib import Path


class WorkspaceAccessError(Exception):
    """Raised when a path access violates workspace boundaries."""

    def __init__(self, path: Path, workspace_root: Path):
        self.path = path
        self.workspace_root = workspace_root
        super().__init__(
            f"Access denied: path '{path}' is outside workspace '{workspace_root}'"
        )


class WorkspaceWriteError(Exception):
    """Raised when a write operation cannot proceed within the workspace."""

    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Write error for '{path}': {reason}")


class WorkspaceGuard:
    """Enforces workspace boundary for file access operations.

    Attributes:
        root: The absolute resolved root path of the workspace.
    """

    def __init__(self, root: Path | str):
        root = Path(root)
        root = root.expanduser()
        self.root = root.resolve()
        self.root = Path(str(self.root).rstrip(os.sep))

    def resolve_path(self, path: str) -> Path:
        """Resolve a path string to an absolute Path object.

        Args:
            path: Absolute path, relative path (resolved against workspace root),
                  or path with tilde expansion.

        Returns:
            The resolved absolute Path.
        """
        p = Path(path).expanduser()
        if p.is_absolute():
            return p.resolve()
        return (self.root / p).resolve()

    def is_within_workspace(self, path: Path) -> bool:
        """Check whether a resolved absolute path is within the workspace boundary.

        Resolves symlinks to prevent escape via symlink traversal.

        Args:
            path: An absolute resolved Path object.

        Returns:
            True if the path is inside or equal to the workspace root.
        """
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError):
            return False
        try:
            resolved.relative_to(self.root)
            return True
        except ValueError:
            return False

    def ensure_within_workspace(self, path: Path) -> Path:
        """Ensure a resolved path is within the workspace, raising if not.

        Args:
            path: An absolute resolved Path object.

        Returns:
            The same path if within workspace.

        Raises:
            WorkspaceAccessError: If the path escapes the workspace boundary.
        """
        if not self.is_within_workspace(path):
            raise WorkspaceAccessError(path, self.root)
        return path

    # ------------------------------------------------------------------
    # M6: Write boundary methods
    # ------------------------------------------------------------------

    def resolve_write_path(self, path: str) -> Path:
        """Resolve a write target path, validating workspace boundary.

        Handles both:
        - Absolute paths (resolved as-is)
        - Paths relative to CWD (resolved from CWD)
        - Paths that already contain workspace prefix (stripped)

        Args:
            path: Absolute path, relative path, or tilde-expanded path.

        Returns:
            The resolved absolute Path, validated to be within workspace.

        Raises:
            WorkspaceAccessError: If the resolved path escapes workspace.
        """
        p = Path(path).expanduser()

        if p.is_absolute():
            resolved = p.resolve()
        else:
            # Try to resolve from CWD first
            from_cwd = p.resolve()

            # Check if it's within workspace when resolved from CWD
            if self.is_within_workspace(from_cwd):
                resolved = from_cwd
            else:
                # Treat as workspace-relative
                resolved = (self.root / p).resolve()

        return self.ensure_within_workspace(resolved)

    def validate_write_target(self, path: Path) -> tuple[bool, str]:
        """Validate whether a write can proceed at the given path.

        Checks:
        1. Path is within workspace boundary
        2. If file exists: parent directory is writable
        3. If file does not exist: parent directory exists and is writable

        Args:
            path: An absolute resolved Path object.

        Returns:
            Tuple of (is_valid, reason). reason is empty string if valid,
            otherwise describes why the write is not allowed.
        """
        if not self.is_within_workspace(path):
            return False, f"path '{path}' is outside workspace '{self.root}'"

        parent = path.parent
        if not parent.exists():
            return False, f"parent directory does not exist: '{parent}'"

        if not os.access(parent, os.W_OK):
            return False, f"parent directory is not writable: '{parent}'"

        return True, ""

    def check_write_allowed(self, path: Path) -> bool:
        """Convenience: return True if writing to path is allowed."""
        valid, _ = self.validate_write_target(path)
        return valid
