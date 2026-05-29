"""Tool for searching text patterns within files in the workspace.

T6: workspace_root is injected internally by ToolManager, not required from the model.
"""

import os
import re
from pathlib import Path
from typing import Optional

from loguru import logger

from app.runtime.tools.tool import Tool, ToolArgument
from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard


class GrepTool(Tool):
    """Searches for text patterns within files in the workspace."""

    name: str = "grep_tool"
    description: str = (
        "Searches for a text pattern within files in the workspace. "
        "Supports regex patterns. Searches all text files by default, "
        "or scope to a specific file/directory within the workspace."
    )
    arguments: list = [
        ToolArgument(
            name="pattern",
            arg_type="string",
            description="Text or regex pattern to search for",
            required=True,
            example="def hello",
        ),
        ToolArgument(
            name="path",
            arg_type="string",
            description="File path or directory to search within (relative to workspace root). "
                        "If omitted, searches all files in the workspace.",
            required=False,
            default="",
            example="src/",
        ),
        ToolArgument(
            name="max_results",
            arg_type="int",
            description="Maximum number of matching lines to return",
            required=False,
            default="50",
            example="50",
        ),
        ToolArgument(
            name="workspace_root",
            arg_type="string",
            description="The root path of the workspace (injected internally)",
            required=False,
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

    def get_injectable_properties_in_execution(self) -> dict:
        """T6: inject workspace_root internally from the tool instance."""
        if self._workspace_root:
            return {"workspace_root": self._workspace_root}
        return {}

    def _search_file(
        self,
        file_path: Path,
        pattern: str,
        max_results: int,
        guard: WorkspaceGuard,
    ) -> list[str]:
        """Search a single file for pattern matches."""
        results: list[str] = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for line_no, line in enumerate(f, 1):
                    if re.search(pattern, line):
                        rel = file_path.relative_to(guard.root)
                        results.append(f"{rel}:{line_no}:{line.rstrip()}")
                        if len(results) >= max_results:
                            break
        except (UnicodeDecodeError, OSError) as e:
            logger.debug(f"Skipping binary/unreadable file {file_path}: {e}")
        return results

    def _search_directory(
        self,
        dir_path: Path,
        pattern: str,
        max_results: int,
        guard: WorkspaceGuard,
    ) -> list[str]:
        """Recursively search a directory for pattern matches."""
        results: list[str] = []
        try:
            for candidate in dir_path.rglob("*"):
                if len(results) >= max_results:
                    break
                if not candidate.is_file():
                    continue
                if candidate.name.startswith("."):
                    continue
                file_results = self._search_file(candidate, pattern, max_results - len(results), guard)
                results.extend(file_results)
        except PermissionError:
            logger.debug(f"Permission denied accessing {dir_path}")
        return results

    def execute(
        self,
        pattern: str,
        workspace_root: str | None = None,
        path: str = "",
        max_results: str = "50",
    ) -> str:
        """Search for a pattern within the workspace."""
        # T6: use injected workspace_root if not provided
        ws = workspace_root or self._workspace_root
        if not ws:
            return f"Error: workspace_root is not configured."
        try:
            guard = WorkspaceGuard(ws)
            search_scope = guard.resolve_path(path) if path else guard.root

            if not guard.is_within_workspace(search_scope):
                return f"Error: search path is outside workspace: {path}"

            max_results_int = int(max_results)
            if max_results_int <= 0:
                return "Error: max_results must be a positive integer"

            if search_scope.is_file():
                results = self._search_file(search_scope, pattern, max_results_int, guard)
            elif search_scope.is_dir():
                results = self._search_directory(search_scope, pattern, max_results_int, guard)
            else:
                return f"Error: search path does not exist: {path}"

            if not results:
                return "No matches found."

            return "\n".join(results)

        except WorkspaceAccessError as e:
            return f"Error: {e}"
        except re.error as e:
            return f"Error: invalid regex pattern '{pattern}': {e}"
        except Exception as e:
            logger.error(f"Error in grep: {str(e)}")
            return f"Error: {e}"
