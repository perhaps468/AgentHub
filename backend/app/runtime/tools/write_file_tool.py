"""Tool for writing new files with content.

M6: Returns PendingChange instead of direct file write.
Uses WorkspaceGuard for path boundary validation.
"""

import os
from pathlib import Path
from typing import Optional

from app.runtime.pending_change import ChangeOperation, ChangeStatus, PendingChange
from app.runtime.tools.tool import Tool, ToolArgument
from app.runtime.workspace import WorkspaceGuard


class WriteFileTool(Tool):
    """Tool for writing new files with specified content.

    M6 behaviour:
    - Validates workspace boundary before any file access
    - Returns PendingChange (preview) instead of writing directly
    - Computes unified_diff for display
    - Rejects empty or whitespace-only content
    """

    name: str = "write_file"
    description: str = (
        "Writes content to a new file at the specified path. "
        "The file must not exist or will be overwritten. "
        "Returns a preview of the change; the change is not applied until explicitly confirmed."
    )
    # C-2: Set to False - confirmation happens via apply_change tool, not validation prompt
    need_validation: bool = False

    _workspace_root: Optional[Path] = None

    arguments: list[ToolArgument] = [
        ToolArgument(
            name="path",
            arg_type="string",
            description="The path of the file to write.",
            required=True,
            example="./src/new_module.py",
        ),
        ToolArgument(
            name="content",
            arg_type="string",
            description="The content to write to the file.",
            required=True,
            example="def hello():\n    print('Hello, World!')\n",
        ),
    ]

    def __init__(self, workspace_root: Optional[Path | str] = None):
        super().__init__()
        self._workspace_root = Path(workspace_root) if workspace_root else None

    @property
    def _guard(self) -> WorkspaceGuard:
        if self._workspace_root:
            resolved_root = self._workspace_root.expanduser()
            if not resolved_root.is_absolute():
                resolved_root = resolved_root.resolve()
            return WorkspaceGuard(resolved_root)
        ws_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
        return WorkspaceGuard(ws_root)

    def execute(self, path: str, content: str) -> PendingChange:
        """Compute a file write preview, returning PendingChange instead of writing.

        M6: This method never writes to disk. It returns a PendingChange with
        unified_diff computed for display.
        """
        # Validate presence
        if not path or not path.strip():
            return PendingChange.make_error("", "File path cannot be empty")

        # Validate content
        stripped = content.strip() if content else ""
        if not stripped:
            return PendingChange.make_error(path, "File content cannot be empty")

        # Validate workspace boundary
        try:
            resolved_path = self._guard.resolve_write_path(path)
        except Exception as e:
            return PendingChange.make_error(path, f"Workspace access denied: {e}")

        resolved_str = str(resolved_path)

        # Validate parent directory exists and is writable
        parent = resolved_path.parent
        if not parent.exists():
            return PendingChange.make_error(
                resolved_str,
                f"Parent directory does not exist: '{parent}'",
            )

        # Determine operation
        file_exists = resolved_path.exists()

        # Read original content for diff generation
        original_content: Optional[str] = None
        if file_exists:
            try:
                original_content = resolved_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return PendingChange.make_error(
                    resolved_str,
                    f"File must be UTF-8 encoded: '{resolved_str}'",
                )
            except Exception as e:
                return PendingChange.make_error(
                    resolved_str,
                    f"Failed to read existing file: {e}",
                )

        # Return PendingChange with preview
        # C-2: Auto-register PendingChange for confirmed apply flow
        from app.runtime.tools.apply_change_tool import ApplyChangeTool

        if file_exists:
            pc = PendingChange.make_update(
                path=resolved_str,
                original_content=original_content,
                proposed_content=content,
            )
            ApplyChangeTool.register_change(pc)
            return pc
        else:
            pc = PendingChange.make_create(
                path=resolved_str,
                proposed_content=content,
            )
            ApplyChangeTool.register_change(pc)
            return pc
