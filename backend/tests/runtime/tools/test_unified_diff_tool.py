"""Tests for UnifiedDiffTool — RED phase.

M6 tests verify:
- Tool produces PendingChange structure (not direct file write)
- Workspace boundary enforced
- Valid patch generates preview result
- Invalid patch returns stable error
- Original file unchanged after execute()
"""

import os
from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "test_workspace"


class TestUnifiedDiffToolImport:
    """Verify UnifiedDiffTool is importable."""

    def test_imports(self):
        """UnifiedDiffTool should be importable."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool

        assert UnifiedDiffTool is not None

    def test_has_name(self):
        """Tool should have the correct name."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        assert tool.name == "unified_diff"

    def test_returns_pending_change(self):
        """execute() should return PendingChange, not plain text."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            patch=(
                "--- a/subdir/code.py\n"
                "+++ b/subdir/code.py\n"
                "@@ -1,3 +1,3 @@\n"
                " def hello():\n"
                "-    pass\n"
                "+    print('patched')\n"
                "     return True\n"
            ),
        )

        assert isinstance(result, PendingChange), (
            f"execute() must return PendingChange, got {type(result).__name__}: {result}"
        )


class TestUnifiedDiffToolWorkspaceBoundary:
    """WS-1: UnifiedDiffTool enforces workspace boundary."""

    def test_rejects_absolute_path_outside_workspace(self):
        """Tool should reject absolute paths outside workspace."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path="/tmp/evil_file.txt",
            patch=(
                "--- /tmp/evil_file.txt\n"
                "+++ /tmp/evil_file.txt\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "workspace" in result.error.lower() or "outside" in result.error.lower()

    def test_rejects_parent_traversal(self):
        """Tool should reject paths with '..' that escape workspace."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path=str(TEST_WORKSPACE_ROOT / ".." / "outside.txt"),
            patch=(
                "--- a/outside.txt\n"
                "+++ b/outside.txt\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "workspace" in result.error.lower() or "outside" in result.error.lower()


class TestUnifiedDiffToolPatchValidation:
    """WS-2: Patch format validation."""

    def test_valid_patch_returns_proposed_content(self):
        """A valid patch should return proposed content in PendingChange."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            patch=(
                "--- a/subdir/code.py\n"
                "+++ b/subdir/code.py\n"
                "@@ -1,3 +1,3 @@\n"
                " def hello():\n"
                "-    pass\n"
                "+    print('patched')\n"
                "     return True\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_success(), f"Expected success, got error: {result.error}"
        assert result.operation.value in ("update", "create")
        assert result.proposed_content is not None

    def test_invalid_patch_format_returns_error(self):
        """Invalid patch format should return stable error."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            patch="This is not a valid patch at all",
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert result.error is not None

    def test_context_mismatch_returns_error(self):
        """Patch with wrong context should return error (not silently apply)."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            patch=(
                "--- a/subdir/code.py\n"
                "+++ b/subdir/code.py\n"
                "@@ -999,1 +999,1 @@\n"
                "-    totally_wrong_context\n"
                "+    new_context\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert "context" in result.error.lower() or "mismatch" in result.error.lower()

    def test_nonexistent_file_returns_error(self):
        """Nonexistent file should return error for update operation."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path=str(TEST_WORKSPACE_ROOT / "nonexistent_m6_diff.txt"),
            patch=(
                "--- a/nonexistent_m6_diff.txt\n"
                "+++ b/nonexistent_m6_diff.txt\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()

    def test_empty_patch_returns_error(self):
        """Empty patch should return error."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            patch="",
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()


class TestUnifiedDiffToolPreviewMode:
    """WS-3: Tool should compute preview, not directly write files."""

    def test_original_file_unchanged_after_execute(self):
        """The actual file on disk must not change after execute()."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        target = TEST_WORKSPACE_ROOT / "subdir" / "code.py"
        original_content = target.read_text(encoding="utf-8")

        tool.execute(
            file_path=str(target),
            patch=(
                "--- a/subdir/code.py\n"
                "+++ b/subdir/code.py\n"
                "@@ -1,3 +1,3 @@\n"
                " def hello():\n"
                "-    pass\n"
                "+    print('test')\n"
                "     return True\n"
            ),
        )

        after_content = target.read_text(encoding="utf-8")
        assert after_content == original_content, (
            "File on disk was modified! UnifiedDiffTool should only produce preview."
        )

    def test_result_has_unified_diff(self):
        """Successful result should contain unified diff string."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            patch=(
                "--- a/subdir/code.py\n"
                "+++ b/subdir/code.py\n"
                "@@ -1,3 +1,3 @@\n"
                " def hello():\n"
                "-    pass\n"
                "+    print('diff')\n"
                "     return True\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_success()
        assert result.unified_diff

    def test_result_status_is_preview(self):
        """Result status should always be 'preview' in M6."""
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.pending_change import PendingChange, ChangeStatus

        tool = UnifiedDiffTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            file_path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            patch=(
                "--- a/subdir/code.py\n"
                "+++ b/subdir/code.py\n"
                "@@ -1,3 +1,3 @@\n"
                " def hello():\n"
                "-    pass\n"
                "+    print('preview')\n"
                "     return True\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.status == ChangeStatus.PREVIEW
