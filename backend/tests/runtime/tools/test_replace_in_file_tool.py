"""Tests for ReplaceInFileTool — RED phase.

M6 tests verify:
- Tool produces PendingChange structure (not direct file write)
- Workspace boundary enforced
- SEARCH/REPLACE block parsing works
- Stable error messages for mismatches
- Preview diff is computed but not applied
"""

import os
import tempfile
from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "test_workspace"


class TestReplaceInFileToolImport:
    """Verify ReplaceInFileTool is importable."""

    def test_imports(self):
        """ReplaceInFileTool should be importable."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool

        assert ReplaceInFileTool is not None

    def test_has_name(self):
        """Tool should have the correct name."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        assert tool.name == "replace_in_file_tool"

    def test_has_pending_change_in_return_type(self):
        """execute() should return a PendingChange-like structure, not raw text."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        # Pass a valid workspace
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "old\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        # Result should be a PendingChange, not a plain string about writing files
        assert isinstance(result, PendingChange), (
            f"execute() must return PendingChange, got {type(result).__name__}: {result}"
        )


class TestReplaceInFileToolWorkspaceBoundary:
    """WS-1: ReplaceInFileTool enforces workspace boundary."""

    def test_rejects_absolute_path_outside_workspace(self):
        """Tool should reject absolute paths outside workspace."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path="/tmp/evil_file.txt",
            diff=(
                "<<<<<<< SEARCH\n"
                "old\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "workspace" in result.error.lower() or "outside" in result.error.lower()

    def test_rejects_parent_traversal(self):
        """Tool should reject paths with '..' that escape workspace."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / ".." / "outside.txt"),
            diff=(
                "<<<<<<< SEARCH\n"
                "old\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "workspace" in result.error.lower() or "outside" in result.error.lower()

    def test_rejects_empty_path(self):
        """Tool should reject empty path."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path="",
            diff=(
                "<<<<<<< SEARCH\n"
                "old\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()


class TestReplaceInFileToolSearchReplace:
    """WS-2: SEARCH/REPLACE block parsing."""

    def test_exact_match_returns_proposed_content(self):
        """When SEARCH matches, result should contain proposed content."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "pass\n"
                "=======\n"
                "print('modified')\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_success(), f"Expected success, got error: {result.error}"
        assert result.operation.value == "update"
        assert result.original_content is not None
        assert result.proposed_content is not None
        assert "modified" in result.proposed_content

    def test_nonexistent_file_returns_error(self):
        """Non-existent file should return error, not create it."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "nonexistent_m6_test.txt"),
            diff=(
                "<<<<<<< SEARCH\n"
                "old\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "not found" in result.error.lower() or "not exist" in result.error.lower()

    def test_search_not_found_returns_error(self):
        """SEARCH block not found should return stable error."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "THIS_STRING_DEFINITELY_DOES_NOT_EXIST_IN_THE_FILE_12345\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "no matching" in result.error.lower() or "not found" in result.error.lower()

    def test_multiple_blocks_all_resolved(self):
        """Multiple SEARCH/REPLACE blocks should all be resolved."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "pass\n"
                "=======\n"
                "first\n"
                ">>>>>>> REPLACE\n"
                "<<<<<<< SEARCH\n"
                "# comment\n"
                "=======\n"
                "# changed\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_success(), f"Expected success, got: {result.error}"

    def test_empty_diff_returns_error(self):
        """Empty diff should return error."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff="",
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()


class TestReplaceInFileToolPreviewMode:
    """WS-3: Tool should compute preview, not directly write files."""

    def test_original_file_unchanged_after_execute(self):
        """The actual file on disk must not change after execute()."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)

        # Read original
        target = TEST_WORKSPACE_ROOT / "subdir" / "code.py"
        original_content = target.read_text(encoding="utf-8")

        # Execute
        tool.execute(
            path=str(target),
            diff=(
                "<<<<<<< SEARCH\n"
                "pass\n"
                "=======\n"
                "print('modified by test')\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        # File on disk must be unchanged
        after_content = target.read_text(encoding="utf-8")
        assert after_content == original_content, (
            "File on disk was modified! ReplaceInFileTool should only produce preview."
        )

    def test_result_has_unified_diff(self):
        """Successful result should contain a unified diff string."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "pass\n"
                "=======\n"
                "print('diff test')\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_success()
        assert result.unified_diff, "Result should contain unified_diff for display"

    def test_result_status_is_preview(self):
        """Result status should always be 'preview' in M6."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange
        from app.runtime.pending_change import ChangeStatus

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "pass\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.status == ChangeStatus.PREVIEW, (
            f"Expected status=preview, got {result.status}"
        )
