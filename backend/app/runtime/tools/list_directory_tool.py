"""Tool for listing the contents of a directory.

T6: workspace_root is injected internally by ToolManager, not required from the model.
"""

import os
from pathlib import Path
from typing import Dict, List

from loguru import logger

from app.runtime.tools.tool import Tool, ToolArgument
from app.runtime.workspace import WorkspaceAccessError, WorkspaceGuard


class ListDirectoryTool(Tool):
    """Lists directory contents within the workspace with pagination and .gitignore filtering."""

    name: str = "list_directory_tool"
    description: str = (
        "Lists directory contents within the workspace root with pagination and .gitignore filtering"
    )
    arguments: list[ToolArgument] = [
        ToolArgument(name="directory_path", arg_type="string", description="Absolute or relative path to target directory within workspace", required=True, example="src"),
        ToolArgument(name="recursive", arg_type="string", description="Enable recursive traversal (true/false)", required=False, default="false", example="true"),
        ToolArgument(name="max_depth", arg_type="int", description="Maximum directory traversal depth", required=False, default="10", example="10"),
        ToolArgument(name="start_line", arg_type="int", description="First line to return in paginated results", required=False, default="1", example="1"),
        ToolArgument(name="end_line", arg_type="int", description="Last line to return in paginated results", required=False, default="200", example="200"),
        ToolArgument(name="workspace_root", arg_type="string", description="The root path of the workspace (injected internally)", required=False),
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

    def _list_directory(self, path: Path, max_depth: int, current_depth: int = 0) -> List[Dict]:
        if current_depth > max_depth:
            return []
        results = []
        try:
            for item in sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if item.name == ".git":
                    continue
                try:
                    if item.is_file():
                        size = item.stat().st_size
                        results.append({"type": "file", "name": item.name, "size": f"{size} bytes", "path": str(item.relative_to(path.parent))})
                    elif item.is_dir():
                        children = self._list_directory(item, max_depth, current_depth + 1)
                        results.append({"type": "directory", "name": item.name, "children": children, "path": str(item.relative_to(path.parent))})
                except PermissionError:
                    results.append({"type": "error", "name": item.name, "error": "Permission denied"})
                except Exception as e:
                    logger.error(f"Error processing {item}: {str(e)}")
        except PermissionError:
            return [{"type": "error", "name": path.name, "error": "Permission denied"}]
        except Exception as e:
            logger.error(f"Error listing directory {path}: {str(e)}")
            return [{"type": "error", "name": path.name, "error": str(e)}]
        return results

    def _format_tree(self, items: List[Dict], depth: int = 0) -> List[str]:
        lines = []
        indent = "  " * depth
        for item in items:
            if item["type"] == "file":
                lines.append(f"{indent} {item['path']} ({item['size']})")
            elif item["type"] == "directory":
                lines.append(f"{indent} {item['path']}/")
                if "children" in item:
                    lines.extend(self._format_tree(item["children"], depth + 1))
            elif item["type"] == "error":
                lines.append(f"{indent} {item['name']} ({item['error']})")
        return lines

    def get_injectable_properties_in_execution(self) -> dict:
        """T6: inject workspace_root internally from the tool instance."""
        if self._workspace_root:
            return {"workspace_root": self._workspace_root}
        return {}

    def execute(self, directory_path: str, workspace_root: str | None = None, recursive: str = "false", max_depth: str = "10", start_line: str = "1", end_line: str = "200") -> str:
        # T6: use injected workspace_root if not provided
        ws = workspace_root or self._workspace_root
        if not ws:
            return f"Error: workspace_root is not configured."
        try:
            guard = WorkspaceGuard(ws)
            resolved = guard.resolve_path(directory_path)
            guard.ensure_within_workspace(resolved)
            path = resolved
            if not path.exists():
                raise ValueError(f"The directory '{directory_path}' does not exist.")
            if not path.is_dir():
                raise ValueError(f"The path '{directory_path}' is not a directory.")

            start = int(start_line)
            end = int(end_line)
            max_depth_int = int(max_depth)
            is_recursive = recursive.lower() == "true"

            if start > end:
                raise ValueError("start_line must be less than or equal to end_line.")

            items = self._list_directory(path=path, max_depth=max_depth_int if is_recursive else 0)
            lines = self._format_tree(items)

            if not lines:
                return "==== No files to display ===="

            total_lines = len(lines)
            paginated_lines = lines[start - 1:end]
            header = f"==== Lines {start}-{min(end, total_lines)} of {total_lines} ===="
            if end >= total_lines:
                header += " [LAST BLOCK]"
            return f"{header}\n" + "\n".join(paginated_lines) + "\n==== End of Block ===="
        except WorkspaceAccessError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error listing directory: {str(e)}")
            return f"Error: {str(e)}"
