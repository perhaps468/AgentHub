# -*- coding: utf-8 -*-
"""T6: workspace_root internal injection tests.

Tests that file/workspace tools do NOT require workspace_root as a model-visible parameter,
and that the runtime injects it internally.
"""

import pytest


class TestWorkspaceRootNotInModelSchema:
    """T6: workspace_root is NOT exposed to the model (hidden in markdown, optional in schema)."""

    def test_read_file_tool_markdown_no_workspace_root(self):
        """ReadFileTool markdown does not expose workspace_root to the model."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        tool = ReadFileTool(workspace_root="/tmp")
        markdown = tool.to_markdown()
        # workspace_root must not appear in the model-visible markdown
        assert "workspace_root" not in markdown

    def test_list_directory_tool_markdown_no_workspace_root(self):
        """ListDirectoryTool markdown does not expose workspace_root."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tool = ListDirectoryTool(workspace_root="/tmp")
        markdown = tool.to_markdown()
        assert "workspace_root" not in markdown

    def test_glob_tool_markdown_no_workspace_root(self):
        """GlobTool markdown does not expose workspace_root."""
        from app.runtime.tools.glob_tool import GlobTool

        tool = GlobTool(workspace_root="/tmp")
        markdown = tool.to_markdown()
        assert "workspace_root" not in markdown

    def test_grep_tool_markdown_no_workspace_root(self):
        """GrepTool markdown does not expose workspace_root."""
        from app.runtime.tools.grep_tool import GrepTool

        tool = GrepTool(workspace_root="/tmp")
        markdown = tool.to_markdown()
        assert "workspace_root" not in markdown


class TestWorkspaceRootInternalInjection:
    """T6: workspace_root is injected internally by the runtime."""

    def test_read_file_uses_injected_workspace_root(self):
        """ReadFileTool reads from internally injected workspace_root."""
        from app.runtime.tools.read_file_tool import ReadFileTool
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w", encoding="utf-8") as f:
                f.write("hello from injected workspace")

            # Initialize with injected workspace_root
            tool = ReadFileTool(workspace_root=tmpdir)

            # Model calls without workspace_root
            result = tool.execute(file_path="test.txt")

            assert "hello from injected workspace" in result
            # Should NOT contain "Error" about missing workspace_root
            assert "workspace_root" not in result.lower()

    def test_list_directory_uses_injected_workspace_root(self):
        """ListDirectoryTool uses internally injected workspace_root."""
        from app.runtime.tools.list_directory_tool import ListDirectoryTool
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "subdir"))
            open(os.path.join(tmpdir, "file.txt"), "w", encoding="utf-8").close()

            tool = ListDirectoryTool(workspace_root=tmpdir)

            # Model calls without workspace_root
            result = tool.execute(directory_path=".", workspace_root=None)

            assert "file.txt" in result or "subdir" in result
            assert "Error" not in result or "workspace_root" not in result

    def test_glob_uses_injected_workspace_root(self):
        """GlobTool uses internally injected workspace_root."""
        from app.runtime.tools.glob_tool import GlobTool
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            open(os.path.join(tmpdir, "foo.py"), "w", encoding="utf-8").close()
            open(os.path.join(tmpdir, "bar.txt"), "w", encoding="utf-8").close()

            tool = GlobTool(workspace_root=tmpdir)

            # Model calls without workspace_root
            result = tool.execute(pattern="*.py", workspace_root=None)

            assert "foo.py" in result
            assert "Error" not in result or "workspace_root" not in result

    def test_grep_uses_injected_workspace_root(self):
        """GrepTool uses internally injected workspace_root."""
        from app.runtime.tools.grep_tool import GrepTool
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "sample.py"), "w", encoding="utf-8") as f:
                f.write("def hello(): pass")

            tool = GrepTool(workspace_root=tmpdir)

            # Model calls without workspace_root
            result = tool.execute(pattern="def hello", path="sample.py", workspace_root=None)

            assert "def hello" in result
            assert "Error" not in result or "workspace_root" not in result


class TestToolManagerValidation:
    """T6: ToolManager validation works without workspace_root."""

    def test_tool_manager_validates_without_workspace_root(self):
        """ToolManager.validate_and_convert_arguments works without workspace_root."""
        from app.runtime.tools.read_file_tool import ReadFileTool
        from app.runtime.tool_manager import ToolManager
        import os

        tool = ReadFileTool(workspace_root="/tmp")
        tm = ToolManager()
        tm.add(tool)

        # Validate with only file_path (no workspace_root) — should NOT raise
        converted = tm.validate_and_convert_arguments(
            "read_file_tool",
            {"file_path": "test.txt"}
        )

        # T6: workspace_root is injected internally, so it IS in the execution args
        assert "file_path" in converted
        # After injection, workspace_root is in execution dict (injected from tool instance)
        assert "workspace_root" in converted
        # On Windows, the resolved path may differ from "/tmp"
        assert len(converted["workspace_root"]) > 0

    def test_tool_markdown_no_workspace_root(self):
        """Tool.to_markdown() does not include workspace_root parameter."""
        from app.runtime.tools.read_file_tool import ReadFileTool

        # Initialize with workspace_root so it's injected (required for T6 behavior)
        tool = ReadFileTool(workspace_root="/tmp")
        markdown = tool.to_markdown()

        # workspace_root should not appear in the markdown the model sees
        assert "workspace_root" not in markdown
