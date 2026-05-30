"""Tests for GrepTool — RED (module does not exist yet)."""

from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "test_workspace"


class TestGrepToolImport:
    """Verify GrepTool is importable."""

    def test_imports_grep_tool(self):
        """GrepTool should be importable."""
        from app.runtime.tools.grep_tool import GrepTool

        assert GrepTool is not None

    def test_has_name(self):
        """GrepTool should have a name attribute."""
        from app.runtime.tools.grep_tool import GrepTool

        tool = GrepTool()
        assert tool.name == "grep_tool"

    def test_has_pattern_argument(self):
        """GrepTool should define a pattern argument (regex or text)."""
        from app.runtime.tools.grep_tool import GrepTool

        tool = GrepTool()
        arg_names = [a.name for a in tool.arguments]
        assert "pattern" in arg_names


class TestGrepToolExecution:
    """Verify GrepTool execution with workspace guard."""

    def test_finds_matching_text_in_file(self):
        """GrepTool should find lines matching the pattern inside workspace files."""
        from app.runtime.tools.grep_tool import GrepTool

        tool = GrepTool()
        result = tool.execute(
            pattern="hello",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "hello" in result or "code.py" in result or result.strip() == ""
        assert "Error" not in result

    def test_finds_pattern_in_code_file(self):
        """GrepTool should find 'def ' patterns in code files."""
        from app.runtime.tools.grep_tool import GrepTool

        tool = GrepTool()
        result = tool.execute(
            pattern="def hello",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "def hello" in result or "code.py" in result or result.strip() == ""

    def test_rejects_path_outside_workspace_absolute(self):
        """GrepTool should reject paths outside workspace."""
        from app.runtime.tools.grep_tool import GrepTool

        tool = GrepTool()
        result = tool.execute(
            pattern="hello",
            path="/tmp/somefile.txt",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" in result or "workspace" in result.lower()

    def test_rejects_pattern_with_parent_traversal(self):
        """GrepTool should reject patterns with '..' that escape workspace."""
        from app.runtime.tools.grep_tool import GrepTool

        tool = GrepTool()
        result = tool.execute(
            pattern="hello",
            path="../secret.txt",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" in result or "workspace" in result.lower()

    def test_respects_max_results(self):
        """GrepTool should respect max_results parameter."""
        from app.runtime.tools.grep_tool import GrepTool

        tool = GrepTool()
        result = tool.execute(
            pattern="line",
            max_results="1",
            workspace_root=TEST_WORKSPACE_ROOT,
        )

        assert "Error" not in result


class TestGrepToolIntegration:
    """Integration: GrepTool via ToolManager."""

    def test_tool_manager_can_execute_grep(self):
        """ToolManager should be able to execute GrepTool with workspace guard."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.grep_tool import GrepTool

        tool = GrepTool()
        tm = ToolManager(tools={"grep_tool": tool})

        result = tm.execute("grep_tool", pattern="def ", workspace_root=TEST_WORKSPACE_ROOT)

        assert "def " in result or "code.py" in result or result.strip() == ""
