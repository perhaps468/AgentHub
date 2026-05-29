"""Tool for reading a file and returning its content.

All reads are scoped to the workspace root via WorkspaceGuard.
T6: workspace_root is injected internally by ToolManager, not required from the model.
"""

import os
from pathlib import Path

from app.runtime.tools.tool import Tool, ToolArgument
from app.runtime.utils.read_file import read_file
from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard

MAX_LINES = 3000


class ReadFileTool(Tool):
    """Tool for reading a local file within the workspace and returning its content."""

    name: str = "read_file_tool"
    description: str = (
        f"Reads a local file content and returns its content. "
        f"Scoped to workspace root. "
        f"Truncated to {MAX_LINES} first lines.\n"
        "Don't use on HTML files and large files."
    )
    arguments: list = [
        ToolArgument(
            name="file_path",
            arg_type="string",
            description="The path to the file to read (relative or absolute within workspace).",
            required=True,
            example="src/main.py",
        ),
        ToolArgument(
            name="workspace_root",
            arg_type="string",
            description="The root path of the workspace (injected internally).",
            required=False,
            example="/path/to/project",
        ),
    ]
    _workspace_root: str | None = None

    def __init__(self, workspace_root: str | None = None, **kwargs):
        super().__init__(**kwargs)
        if workspace_root:
            self._workspace_root = str(Path(workspace_root).resolve())
        elif self._workspace_root is None:
            env_root = os.environ.get("WORKSPACE_ROOT", "")
            if env_root:
                self._workspace_root = str(Path(env_root).resolve())

    def model_post_init(self, __context) -> None:
        pass

    def _truncate_content(self, content: str) -> str:
        """Truncate the content to the first MAX_LINES lines."""
        lines = content.splitlines()
        truncated_lines = lines[:MAX_LINES]
        truncated_content = "\n".join(truncated_lines)
        if len(lines) > MAX_LINES:
            truncated_content += f"\n\n[The content is too long. Truncated at {MAX_LINES} lines.]"
        return truncated_content

    def get_injectable_properties_in_execution(self) -> dict:
        """T6: inject workspace_root internally from the tool instance."""
        if self._workspace_root:
            return {"workspace_root": self._workspace_root}
        return {}

    def execute(self, file_path: str, workspace_root: str | None = None) -> str:
        """Reads a local file within the workspace and returns its content."""
        # T6: use injected workspace_root if not provided as argument
        ws = workspace_root or self._workspace_root
        if not ws:
            return f"Error: workspace_root is not configured. Set WORKSPACE_ROOT env var or pass workspace_root to the tool constructor."
        try:
            guard = WorkspaceGuard(ws)
            resolved = guard.resolve_path(file_path)
            guard.ensure_within_workspace(resolved)
            content = read_file(str(resolved))
            truncated_content = self._truncate_content(content)
            return truncated_content
        except WorkspaceAccessError as e:
            return f"Error: {e}"
        except FileNotFoundError:
            return f"Error: file not found: {file_path}"
        except Exception as e:
            return f"Error reading file {file_path}: {str(e)}"
