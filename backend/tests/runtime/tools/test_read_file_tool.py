"""Tests for ReadFileTool with workspace guard — RED (guard integration not yet implemented)."""

from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "test_workspace"


class TestReadFileToolImport:
    """Verify ReadFileTool is importable and has expected structure."""

    def test_imports_read_file_tool(self):
        """ReadFileTool should be importable."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        assert ReadFileTool is not None

    def test_has_name(self):
        """ReadFileTool should have a name attribute."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        assert tool.name == "read_file_tool"

    def test_has_file_path_argument(self):
        """ReadFileTool should define a file_path argument."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        arg_names = [a.name for a in tool.arguments]
        assert "file_path" in arg_names


class TestReadFileToolExecution:
    """Verify ReadFileTool execution with workspace guard."""

    def test_reads_file_within_workspace_relative_path(self):
        """ReadFileTool should read files inside workspace using relative path."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        result = tool.execute(file_path="test.txt", workspace_root=TEST_WORKSPACE_ROOT)

        assert "test content" in result
        assert "Error" not in result

    def test_reads_file_within_workspace_absolute_path(self):
        """ReadFileTool should read files inside workspace using absolute path."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        abs_path = str((TEST_WORKSPACE_ROOT / "test.txt").resolve())
        result = tool.execute(file_path=abs_path, workspace_root=TEST_WORKSPACE_ROOT)

        assert "test content" in result
        assert "Error" not in result

    def test_rejects_file_outside_workspace_absolute_path(self):
        """ReadFileTool should reject file paths outside workspace (absolute)."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        outside_path = "/tmp/outside_workspace_file.txt"
        result = tool.execute(file_path=outside_path, workspace_root=TEST_WORKSPACE_ROOT)

        assert "Error" in result or "workspace" in result.lower()
        assert "test content" not in result

    def test_rejects_parent_traversal(self):
        """ReadFileTool should reject paths with '..' that escape workspace."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        escaped_path = str((TEST_WORKSPACE_ROOT / ".." / "outside_file.txt").resolve())
        result = tool.execute(file_path=escaped_path, workspace_root=TEST_WORKSPACE_ROOT)

        assert "Error" in result or "workspace" in result.lower()

    def test_returns_error_for_nonexistent_file(self):
        """ReadFileTool should return a controlled error for missing files."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        result = tool.execute(file_path="nonexistent_file_xyz.txt", workspace_root=TEST_WORKSPACE_ROOT)

        assert "Error" in result or "not found" in result.lower() or "does not exist" in result.lower()

    def test_truncates_large_files(self):
        """ReadFileTool should truncate content to MAX_LINES (3000 lines)."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        result = tool.execute(file_path="test.txt", workspace_root=TEST_WORKSPACE_ROOT)

        lines = result.splitlines()
        assert len(lines) <= 3000 + 1


class TestReadFileToolIntegration:
    """Integration: ReadFileTool via ToolManager."""

    def test_tool_manager_can_execute_read_file(self):
        """ToolManager should be able to execute ReadFileTool with workspace guard."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        tm = ToolManager(tools={"read_file_tool": tool})

        result = tm.execute(
            "read_file_tool",
            file_path="test.txt",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "test content" in result
        assert "Error" not in result

    def test_tool_manager_rejects_outside_workspace(self):
        """ToolManager.execute should propagate workspace rejection from ReadFileTool."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool()
        tm = ToolManager(tools={"read_file_tool": tool})

        result = tm.execute(
            "read_file_tool",
            file_path="/tmp/some_other_file.txt",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" in result or "workspace" in result.lower()
