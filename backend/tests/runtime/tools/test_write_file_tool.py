"""Tests for WriteFileTool — RED phase.

M6 tests verify:
- Tool produces PendingChange structure
- Workspace boundary enforced
- File content validation (non-empty, size limits)
- Preview mode: original file unchanged
- File creation with valid content
"""

from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "test_workspace"


class TestWriteFileToolImport:
    """Verify WriteFileTool is importable."""

    def test_imports(self):
        """WriteFileTool should be importable."""
        from app.runtime.tools.write_file_tool import WriteFileTool

        assert WriteFileTool is not None

    def test_has_name(self):
        """Tool should have the correct name."""
        from app.runtime.tools.write_file_tool import WriteFileTool

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        assert tool.name == "write_file"

    def test_returns_pending_change(self):
        """execute() should return PendingChange."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "new_file_m6.txt"),
            content="hello write file tool",
        )

        assert isinstance(result, PendingChange), (
            f"execute() must return PendingChange, got {type(result).__name__}: {result}"
        )


class TestWriteFileToolWorkspaceBoundary:
    """WS-1: WriteFileTool enforces workspace boundary."""

    def test_rejects_absolute_path_outside_workspace(self):
        """Tool should reject absolute paths outside workspace."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path="/tmp/evil_write.txt",
            content="malicious content",
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "workspace" in result.error.lower() or "outside" in result.error.lower()

    def test_rejects_parent_traversal(self):
        """Tool should reject paths with '..' that escape workspace."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / ".." / "outside_write.txt"),
            content="malicious",
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "workspace" in result.error.lower() or "outside" in result.error.lower()


class TestWriteFileToolContentValidation:
    """WS-2: Content validation."""

    def test_non_empty_content_success(self):
        """Non-empty content should succeed with PendingChange."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "new_write_test.txt"),
            content="print('hello world')",
        )

        assert isinstance(result, PendingChange)
        assert result.is_success(), f"Expected success, got: {result.error}"
        assert result.operation.value in ("update", "create")

    def test_empty_content_returns_error(self):
        """Empty content should return error."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "empty_file_test.txt"),
            content="",
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "empty" in result.error.lower() or "content" in result.error.lower()

    def test_whitespace_only_returns_error(self):
        """Whitespace-only content should return error."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "whitespace_test.txt"),
            content="   \n\t  ",
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()

    def test_nonexistent_parent_returns_error(self):
        """Non-existent parent directory should return error."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "nonexistent_parent_xyz" / "file.txt"),
            content="content",
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "directory" in result.error.lower() or "exist" in result.error.lower()


class TestWriteFileToolPreviewMode:
    """WS-3: Tool should compute preview, not directly write files."""

    def test_original_file_unchanged_after_execute(self):
        """The actual file on disk must not change after execute()."""
        from app.runtime.tools.write_file_tool import WriteFileTool

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        target = TEST_WORKSPACE_ROOT / "subdir" / "new_preview_test.txt"
        original_exists = target.exists()

        tool.execute(path=str(target), content="new content for preview test")

        if original_exists:
            assert target.read_text(encoding="utf-8") != "new content for preview test"
        else:
            assert not target.exists(), (
                "File was created! WriteFileTool should only produce preview in M6."
            )

    def test_result_has_proposed_content(self):
        """Successful result should contain proposed content."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        content = "def foo():\n    return 42\n"
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "proposed_content_test.txt"),
            content=content,
        )

        assert isinstance(result, PendingChange)
        assert result.is_success()
        assert result.proposed_content == content

    def test_result_status_is_preview(self):
        """Result status should always be 'preview' in M6."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange, ChangeStatus

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "status_preview_test.txt"),
            content="content",
        )

        assert isinstance(result, PendingChange)
        assert result.status == ChangeStatus.PREVIEW, (
            f"Expected status=preview, got {result.status}"
        )
