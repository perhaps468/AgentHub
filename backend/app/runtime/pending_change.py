"""Unified PendingChange / Patch data structure for AgentHub runtime write tools.

M6 scope: All write-related tools (replace_in_file / unified_diff / write_file)
must produce a consistent PendingChange structure so that:
- The agent can display structured diffs to users
- A separate apply path (M7) can consume these structures
- No tool directly overwrites files by default
"""

import difflib
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


class ChangeOperation(str, Enum):
    """The type of change being proposed."""

    CREATE = "create"   # New file
    UPDATE = "update"  # Modify existing file
    DELETE = "delete"  # Remove file
    RENAME = "rename"  # Move/rename file (future use)


class ChangeStatus(str, Enum):
    """The status of a pending change."""

    PREVIEW = "preview"   # Computed but not committed
    PENDING = "pending"   # Committed to apply queue (M7)
    APPLIED = "applied"   # Successfully written (M7)
    REJECTED = "rejected"  # User rejected / apply failed (M7)


@dataclass
class PendingChange:
    """Represents a proposed file change.

    All write tools produce this structure. It is never directly written
    to disk; it is returned to the agent as a structured preview.
    The apply() method is for testing and M7 integration only.

    Attributes:
        change_id: Unique identifier for this change.
        path: Absolute path of the target file (must be within workspace).
        operation: The type of change (create / update / delete).
        original_content: The file's current content (None for new files).
        proposed_content: The proposed new content (None for deletions).
        unified_diff: Human-readable unified diff string (computed on demand).
        status: Current status (always 'preview' in M6).
        error: Error message if the change could not be computed, else None.
        created_at: ISO timestamp when this change was created.
    """

    change_id: str
    path: str
    operation: ChangeOperation
    original_content: Optional[str] = None
    proposed_content: Optional[str] = None
    unified_diff: str = ""
    status: ChangeStatus = ChangeStatus.PREVIEW
    error: Optional[str] = None
    created_at: str = ""
    _diff_computed: bool = field(default=False, repr=False)

    def __post_init__(self):
        if not self.change_id:
            self.change_id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    @property
    def file_path(self) -> str:
        """Alias for path, for compatibility across tool naming conventions."""
        return self.path

    def _compute_diff(self) -> None:
        """Compute unified_diff lazily if not already computed."""
        if self._diff_computed:
            return

        if self.operation == ChangeOperation.DELETE:
            self.unified_diff = ""
        elif self.operation == ChangeOperation.CREATE:
            self.unified_diff = self._make_create_diff()
        elif self.operation == ChangeOperation.UPDATE:
            self.unified_diff = self._make_update_diff()
        else:
            self.unified_diff = ""

        self._diff_computed = True

    def _make_create_diff(self) -> str:
        """Generate unified diff for a new file."""
        if self.proposed_content is None:
            return ""
        path = self.path
        lines = []
        lines.append(f"--- /dev/null")
        lines.append(f"+++ b/{path}")
        line_count = self.proposed_content.count("\n") + (1 if self.proposed_content and not self.proposed_content.endswith("\n") else 0)
        lines.append(f"@@ -0,0 +1,{max(1, line_count)} @@")
        for l in self.proposed_content.splitlines(keepends=True):
            lines.append(f"+{l.rstrip()}")
        return "\n".join(lines)

    def _make_update_diff(self) -> str:
        """Generate unified diff for an updated file."""
        if self.original_content is None or self.proposed_content is None:
            return ""
        path = self.path
        orig_lines = self.original_content.splitlines(keepends=True)
        prop_lines = self.proposed_content.splitlines(keepends=True)

        # Normalize: ensure last line ends with newline for diff
        if orig_lines and not orig_lines[-1].endswith("\n"):
            orig_lines[-1] += "\n"
        if prop_lines and not prop_lines[-1].endswith("\n"):
            prop_lines[-1] += "\n"

        diff = difflib.unified_diff(
            orig_lines,
            prop_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            lineterm="\n",
        )
        result = "".join(diff)
        return result if result else ""

    def is_error(self) -> bool:
        """Return True if this change represents an error."""
        return self.error is not None

    def is_success(self) -> bool:
        """Return True if this change represents a successful computation."""
        return self.error is None

    def summary(self) -> str:
        """Return a one-line summary suitable for the agent."""
        if self.is_error():
            return f"[Error] {self.error}"
        op_map = {
            ChangeOperation.CREATE: "Create",
            ChangeOperation.UPDATE: "Update",
            ChangeOperation.DELETE: "Delete",
            ChangeOperation.RENAME: "Rename",
        }
        return f"{op_map.get(self.operation, 'Change')} {self.path}: status={self.status.value}"

    def to_display_string(self) -> str:
        """Return a human-readable string describing the change.

        This is what the agent returns to the runtime text stream.
        """
        if self.is_error():
            return f"Error computing change for '{self.path}': {self.error}"

        self._compute_diff()
        lines = [f"[{self.operation.value.upper()}] {self.path}"]

        if self.unified_diff:
            lines.append(self.unified_diff)

        return "\n".join(lines)

    def apply(self) -> bool:
        """Apply the pending change to disk.

        This is used for testing and M7 integration only.
        Returns True on success, False on failure.

        The method verifies that the file hasn't changed since preview
        (using content hash) before applying.
        """
        if self.is_error():
            return False

        file_path = Path(self.path)

        # Verify original content hasn't changed
        if self.operation == ChangeOperation.UPDATE:
            if file_path.exists():
                current = file_path.read_text(encoding="utf-8")
                if current != self.original_content:
                    self.error = "File was modified after preview; rejecting apply"
                    return False

        try:
            if self.operation == ChangeOperation.DELETE:
                file_path.unlink(missing_ok=True)
            elif self.operation == ChangeOperation.CREATE:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(self.proposed_content or "", encoding="utf-8")
            elif self.operation == ChangeOperation.UPDATE:
                file_path.write_text(self.proposed_content or "", encoding="utf-8")

            self.status = ChangeStatus.APPLIED
            return True
        except Exception as e:
            self.error = f"Failed to apply change: {e}"
            return False

    @classmethod
    def make_update(
        cls,
        path: str,
        original_content: str,
        proposed_content: str,
        error: Optional[str] = None,
    ) -> "PendingChange":
        """Factory: create an UPDATE PendingChange."""
        obj = cls(
            change_id="",
            path=path,
            operation=ChangeOperation.UPDATE,
            original_content=original_content,
            proposed_content=proposed_content,
            error=error,
        )
        obj._compute_diff()
        return obj

    @classmethod
    def make_create(
        cls,
        path: str,
        proposed_content: str,
        error: Optional[str] = None,
    ) -> "PendingChange":
        """Factory: create a CREATE PendingChange."""
        obj = cls(
            change_id="",
            path=path,
            operation=ChangeOperation.CREATE,
            original_content=None,
            proposed_content=proposed_content,
            error=error,
        )
        obj._compute_diff()
        return obj

    @classmethod
    def make_error(cls, path: str, error: str) -> "PendingChange":
        """Factory: create an error PendingChange."""
        return cls(
            change_id="",
            path=path,
            operation=ChangeOperation.UPDATE,
            error=error,
        )
