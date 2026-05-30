"""Tests for ListDirectoryTool with workspace guard — RED (guard integration not yet implemented)."""

from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "test_workspace"


class TestListDirectoryToolImport:
    """Verify ListDirectoryTool is importable."""

    def test_imports_list_directory_tool(self):
        """ListDirectoryTool should be importable."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        assert ListDirectoryTool is not None

    def test_has_name(self):
        """ListDirectoryTool should have a name attribute."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool()
        assert tool.name == "list_directory_tool"

    def test_has_directory_path_argument(self):
        """ListDirectoryTool should define a directory_path argument."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool()
        arg_names = [a.name for a in tool.arguments]
        assert "directory_path" in arg_names


class TestListDirectoryToolExecution:
    """Verify ListDirectoryTool execution with workspace guard."""

    def test_lists_directory_within_workspace_relative_path(self):
        """ListDirectoryTool should list directory inside workspace using relative path."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool()
        result = tool.execute(
            directory_path="subdir",
            recursive="false",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "nested" in result or "deep.txt" in result
        assert "Error" not in result

    def test_lists_directory_within_workspace_absolute_path(self):
        """ListDirectoryTool should list directory inside workspace using absolute path."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool()
        abs_path = str((TEST_WORKSPACE_ROOT / "subdir").resolve())
        result = tool.execute(
            directory_path=abs_path,
            recursive="false",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" not in result

    def test_rejects_directory_outside_workspace_absolute_path(self):
        """ListDirectoryTool should reject paths outside workspace (absolute)."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool()
        result = tool.execute(
            directory_path="/tmp",
            recursive="false",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" in result or "workspace" in result.lower()

    def test_rejects_parent_traversal(self):
        """ListDirectoryTool should reject paths with '..' that escape workspace."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool()
        result = tool.execute(
            directory_path="..",
            recursive="false",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" in result or "workspace" in result.lower()

    def test_returns_error_for_nonexistent_directory(self):
        """ListDirectoryTool should return a controlled error for missing directories."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool()
        result = tool.execute(
            directory_path="nonexistent_dir_xyz",
            recursive="false",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" in result or "does not exist" in result.lower() or "not found" in result.lower()

    def test_respects_recursive_parameter(self):
        """ListDirectoryTool should respect the recursive parameter."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool()
        result = tool.execute(
            directory_path="subdir",
            recursive="true",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "deep.txt" in result


class TestListDirectoryToolIntegration:
    """Integration: ListDirectoryTool via ToolManager."""

    def test_tool_manager_can_execute_list_directory(self):
        """ToolManager should be able to execute ListDirectoryTool with workspace guard."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool()
        tm = ToolManager(tools={"list_directory_tool": tool})

        result = tm.execute(
            "list_directory_tool",
            directory_path="subdir",
            recursive="false",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" not in result
