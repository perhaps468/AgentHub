"""Tool for finding files matching a glob pattern within the workspace.

T6: workspace_root is injected internally by ToolManager, not required from the model.
"""

import os
from pathlib import Path

from loguru import logger

from app.runtime.tools.tool import Tool, ToolArgument
from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard


class GlobTool(Tool):
    """Finds files matching a glob pattern within the workspace."""

    name: str = "glob_tool"
    description: str = (
        "Finds files matching a glob pattern within the workspace root. "
        "Supports standard glob patterns including ** for recursive matching."
    )
    arguments: list = [
        ToolArgument(
            name="pattern",
            arg_type="string",
            description="Glob pattern to match files (e.g. '**/*.py', 'src/**/*.ts')",
            required=True,
            example="**/*.py",
        ),
        ToolArgument(
            name="workspace_root",
            arg_type="string",
            description="The root path of the workspace (injected internally)",
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

    def get_injectable_properties_in_execution(self) -> dict:
        """T6: inject workspace_root internally from the tool instance."""
        if self._workspace_root:
            return {"workspace_root": self._workspace_root}
        return {}

    def execute(self, pattern: str, workspace_root: str | None = None) -> str:
        """Find files matching a glob pattern within the workspace."""
        # T6: use injected workspace_root if not provided
        ws = workspace_root or self._workspace_root
        if not ws:
            return f"Error: workspace_root is not configured."
        try:
            guard = WorkspaceGuard(ws)

            if os.path.isabs(pattern):
                resolved = guard.resolve_path(pattern)
                if not guard.is_within_workspace(resolved):
                    return f"Error: pattern resolves to path outside workspace: {pattern}"
                base = resolved.parent
                pattern_part = resolved.name
            else:
                base = guard.root
                pattern_part = pattern

            if ".." in pattern_part.replace("\\", "/").split("/"):
                potential_escape = (guard.root / pattern_part).resolve()
                if not guard.is_within_workspace(potential_escape):
                    return f"Error: pattern escapes workspace boundary: {pattern}"

            matches = list(base.glob(pattern_part))

            safe_matches = []
            for match in matches:
                if guard.is_within_workspace(match):
                    safe_matches.append(match)

            safe_matches.sort(key=lambda x: (str(x.parent), x.name))

            if not safe_matches:
                return "No files found matching pattern."

            lines = []
            for match in safe_matches:
                rel = match.relative_to(guard.root)
                if match.is_dir():
                    lines.append(f"{rel}/")
                else:
                    lines.append(str(rel))

            return "\n".join(lines)

        except WorkspaceAccessError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error in glob: {str(e)}")
            return f"Error: {e}"
