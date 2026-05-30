"""Tests for GlobTool — RED (module does not exist yet)."""

from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "test_workspace"


class TestGlobToolImport:
    """Verify GlobTool is importable."""

    def test_imports_glob_tool(self):
        """GlobTool should be importable."""
        from app.runtime.tools.glob_tool import GlobTool

        assert GlobTool is not None

    def test_has_name(self):
        """GlobTool should have a name attribute."""
        from app.runtime.tools.glob_tool import GlobTool

        tool = GlobTool()
        assert tool.name == "glob_tool"

    def test_has_pattern_argument(self):
        """GlobTool should define a pattern argument."""
        from app.runtime.tools.glob_tool import GlobTool

        tool = GlobTool()
        arg_names = [a.name for a in tool.arguments]
        assert "pattern" in arg_names


class TestGlobToolExecution:
    """Verify GlobTool execution with workspace guard."""

    def test_finds_files_matching_pattern(self):
        """GlobTool should find files matching the given pattern inside workspace."""
        from app.runtime.tools.glob_tool import GlobTool

        tool = GlobTool()
        result = tool.execute(pattern="**/*.py", workspace_root=TEST_WORKSPACE_ROOT)

        assert "code.py" in result
        assert "Error" not in result

    def test_finds_files_in_subdirectory(self):
        """GlobTool should find files in subdirectories."""
        from app.runtime.tools.glob_tool import GlobTool

        tool = GlobTool()
        result = tool.execute(pattern="**/*.txt", workspace_root=TEST_WORKSPACE_ROOT)

        assert "test.txt" in result or "deep.txt" in result

    def test_rejects_pattern_outside_workspace_absolute(self):
        """GlobTool should reject absolute paths outside workspace."""
        from app.runtime.tools.glob_tool import GlobTool

        tool = GlobTool()
        result = tool.execute(
            pattern="/tmp/**/*.txt",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" in result or "workspace" in result.lower()

    def test_rejects_pattern_with_parent_traversal(self):
        """GlobTool should reject patterns with '..' that escape workspace."""
        from app.runtime.tools.glob_tool import GlobTool

        tool = GlobTool()
        result = tool.execute(
            pattern="../**/*.py",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" in result or "workspace" in result.lower()

    def test_returns_empty_for_no_matches(self):
        """GlobTool should return empty result when no files match."""
        from app.runtime.tools.glob_tool import GlobTool

        tool = GlobTool()
        result = tool.execute(
            pattern="**/*.nonexistent_extension_xyz",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" not in result


class TestGlobToolIntegration:
    """Integration: GlobTool via ToolManager."""

    def test_tool_manager_can_execute_glob(self):
        """ToolManager should be able to execute GlobTool with workspace guard."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.glob_tool import GlobTool

        tool = GlobTool()
        tm = ToolManager(tools={"glob_tool": tool})

        result = tm.execute("glob_tool", pattern="**/*.py", workspace_root=TEST_WORKSPACE_ROOT)

        assert "code.py" in result
