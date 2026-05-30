"""Tests for ToolManager — verifying tool registration and execution."""

import pytest


class TestToolManagerRegistration:
    """Verify ToolManager registration methods."""

    def test_add_single_tool(self):
        """ToolManager should be able to add a single tool."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.task_complete_tool import TaskCompleteTool

        tm = ToolManager()
        tool = TaskCompleteTool()
        tm.add(tool)

        assert tool.name in tm.list()

    def test_add_list_of_tools(self):
        """ToolManager should be able to add a list of tools."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.task_complete_tool import TaskCompleteTool
        from app.runtime.tools.read_file_tool import ReadFileTool

        tm = ToolManager()
        tm.add_list([TaskCompleteTool(), ReadFileTool()])

        assert "task_complete" in tm.list()
        assert "read_file_tool" in tm.list()

    def test_remove_tool(self):
        """ToolManager should be able to remove a tool."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.task_complete_tool import TaskCompleteTool

        tm = ToolManager()
        tool = TaskCompleteTool()
        tm.add(tool)
        tm.remove(tool.name)

        assert tool.name not in tm.list()

    def test_list_returns_tool_names(self):
        """ToolManager.list() should return a list of tool names."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.task_complete_tool import TaskCompleteTool

        tm = ToolManager()
        tm.add(TaskCompleteTool())

        names = tm.list()
        assert isinstance(names, list)
        assert "task_complete" in names

    def test_tool_names_returns_list(self):
        """ToolManager.tool_names() should return list of names."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.task_complete_tool import TaskCompleteTool

        tm = ToolManager()
        tm.add(TaskCompleteTool())

        names = tm.tool_names()
        assert isinstance(names, list)
        assert "task_complete" in names


class TestToolManagerGet:
    """Verify ToolManager.get() behavior."""

    def test_get_existing_tool(self):
        """get() should return the tool if it exists."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.task_complete_tool import TaskCompleteTool

        tm = ToolManager()
        tool = TaskCompleteTool()
        tm.add(tool)

        retrieved = tm.get("task_complete")
        assert retrieved is not None
        assert retrieved.name == "task_complete"

    def test_get_nonexistent_tool_returns_none(self):
        """get() should return None for non-existent tool (not raise KeyError)."""
        from app.runtime.tool_manager import ToolManager

        tm = ToolManager()
        result = tm.get("nonexistent_tool_xyz")

        assert result is None


class TestToolManagerExecute:
    """Verify ToolManager.execute() behavior."""

    def test_execute_task_complete(self):
        """execute() should successfully run task_complete tool."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.task_complete_tool import TaskCompleteTool

        tm = ToolManager()
        tm.add(TaskCompleteTool())
        result = tm.execute("task_complete", answer="test answer")

        assert "test answer" in result

    def test_execute_nonexistent_tool_raises(self):
        """execute() should raise when tool does not exist."""
        from app.runtime.tool_manager import ToolManager

        tm = ToolManager()

        with pytest.raises(KeyError):
            tm.execute("nonexistent_tool_xyz")


class TestToolManagerValidation:
    """Verify argument validation."""

    def test_validate_required_argument_missing(self):
        """validate_and_convert_arguments should raise when required argument is missing."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.read_file_tool import ReadFileTool

        tm = ToolManager()
        tm.add(ReadFileTool())

        with pytest.raises(ValueError, match="required"):
            tm.validate_and_convert_arguments("read_file_tool", {})

    def test_validate_optional_argument_uses_default(self):
        """validate_and_convert_arguments should use default for optional arguments."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.read_file_tool import ReadFileTool

        tm = ToolManager()
        tm.add(ReadFileTool())
        validated = tm.validate_and_convert_arguments(
            "read_file_tool",
            {"file_path": "test.txt", "workspace_root": "/tmp"},
        )

        assert "file_path" in validated

    def test_validate_type_conversion_int(self):
        """validate_and_convert_arguments should convert int type arguments."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tm = ToolManager()
        tm.add(ListDirectoryTool())
        validated = tm.validate_and_convert_arguments(
            "list_directory_tool",
            {"directory_path": ".", "max_depth": "5", "workspace_root": "/tmp"},
        )

        assert validated["max_depth"] == 5
        assert isinstance(validated["max_depth"], int)

    def test_validate_type_conversion_bool(self):
        """validate_and_convert_arguments should convert bool type arguments."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.list_directory_tool import ListDirectoryTool

        tm = ToolManager()
        tm.add(ListDirectoryTool())
        validated = tm.validate_and_convert_arguments(
            "list_directory_tool",
            {"directory_path": ".", "recursive": "true", "workspace_root": "/tmp"},
        )

        assert validated["recursive"] == "true"


class TestToolManagerToMarkdown:
    """Verify markdown generation."""

    def test_to_markdown_contains_tool_name(self):
        """to_markdown() should include tool names."""
        from app.runtime.tool_manager import ToolManager
        from app.runtime.tools.task_complete_tool import TaskCompleteTool

        tm = ToolManager()
        tm.add(TaskCompleteTool())
        md = tm.to_markdown()

        assert "task_complete" in md
