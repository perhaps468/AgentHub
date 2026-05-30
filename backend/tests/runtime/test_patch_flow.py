"""Integration tests for M6 patch flow — RED phase.

These tests verify the end-to-end patch flow:
1. Write tools produce PendingChange objects (not direct file writes)
2. RuntimeAgentService applies patches atomically
3. Workspace boundary is enforced throughout
4. Preview -> apply lifecycle works correctly
"""

from pathlib import Path

import pytest

TEST_WORKSPACE_ROOT = Path(__file__).parent / "tools" / "test_workspace"


class TestPatchFlowPendingChange:
    """PF-1: All write tools return PendingChange structures."""

    def test_replace_returns_pending_change(self):
        """replace_in_file_tool returns PendingChange."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "pass\n"
                "=======\n"
                "print('patched')\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange), f"Expected PendingChange, got {type(result)}"

    def test_unified_diff_returns_pending_change(self):
        """unified_diff_tool returns PendingChange."""
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

        assert isinstance(result, PendingChange), f"Expected PendingChange, got {type(result)}"

    def test_write_file_returns_pending_change(self):
        """write_file_tool returns PendingChange."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        tool = WriteFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "new_flow_test.txt"),
            content="def test(): pass\n",
        )

        assert isinstance(result, PendingChange), f"Expected PendingChange, got {type(result)}"


class TestPatchFlowStructure:
    """PF-2: PendingChange has all required fields for apply."""

    def test_pending_change_has_required_fields(self):
        """Successful PendingChange has path, proposed_content, status."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange, ChangeStatus

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "pass\n"
                "=======\n"
                "print('test')\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_success()
        assert result.file_path is not None
        assert result.proposed_content is not None
        assert result.status == ChangeStatus.PREVIEW

    def test_pending_change_has_unified_diff(self):
        """Successful PendingChange contains unified_diff for display."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "pass\n"
                "=======\n"
                "print('diff')\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_success()
        assert result.unified_diff is not None
        assert len(result.unified_diff) > 0

    def test_error_pending_change_has_error_message(self):
        """Error PendingChange has meaningful error message."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "code.py"),
            diff=(
                "<<<<<<< SEARCH\n"
                "THIS_DOES_NOT_EXIST_IN_THE_FILE\n"
                "=======\n"
                "new\n"
                ">>>>>>> REPLACE\n"
            ),
        )

        assert isinstance(result, PendingChange)
        assert result.is_error()
        assert result.error is not None
        assert len(result.error) > 0


class TestPatchFlowApply:
    """PF-3: Apply operation actually writes to disk."""

    def test_pending_change_can_be_applied(self):
        """PendingChange.apply() writes file to disk."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        target = TEST_WORKSPACE_ROOT / "subdir" / "apply_test_file.txt"
        target.write_text("original content\n", encoding="utf-8")

        try:
            result = tool.execute(
                path=str(target),
                diff=(
                    "<<<<<<< SEARCH\n"
                    "original content\n"
                    "=======\n"
                    "applied content\n"
                    ">>>>>>> REPLACE\n"
                ),
            )

            assert isinstance(result, PendingChange)
            assert result.is_success()

            # Apply the change
            applied = result.apply()

            assert applied is True, "apply() should return True on success"
            content = target.read_text(encoding="utf-8")
            assert content == "applied content\n", f"Expected 'applied content\\n', got {content!r}"
        finally:
            if target.exists():
                target.unlink()

    def test_apply_returns_false_on_mismatch(self):
        """apply() returns False if file changed since preview."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        target = TEST_WORKSPACE_ROOT / "subdir" / "mismatch_test.txt"
        target.write_text("original\n", encoding="utf-8")

        try:
            result = tool.execute(
                path=str(target),
                diff=(
                    "<<<<<<< SEARCH\n"
                    "original\n"
                    "=======\n"
                    "modified\n"
                    ">>>>>>> REPLACE\n"
                ),
            )

            # Simulate file changed after preview
            target.write_text("changed by someone else\n", encoding="utf-8")

            applied = result.apply()
            assert applied is False, "apply() should return False on mismatch"
        finally:
            if target.exists():
                target.unlink()


class TestPatchFlowWorkspaceBoundary:
    """PF-4: Workspace boundary enforced throughout patch flow."""

    def test_all_tools_reject_outside_workspace(self):
        """All write tools reject paths outside workspace."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        outside_path = "/tmp/m6_evil.txt"

        for tool_cls, kwargs in [
            (ReplaceInFileTool, {"path": outside_path, "diff": "<<<<<< SEARCH\nx\n=======\ny\n>>>>>>> REPLACE\n"}),
            (UnifiedDiffTool, {"file_path": outside_path, "patch": "--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y\n"}),
            (WriteFileTool, {"path": outside_path, "content": "evil"}),
        ]:
            tool = tool_cls(workspace_root=TEST_WORKSPACE_ROOT)
            result = tool.execute(**kwargs)

            assert isinstance(result, PendingChange), f"{tool_cls.__name__} should return PendingChange"
            assert result.is_error(), f"{tool_cls.__name__} should reject outside workspace"

    def test_parent_traversal_rejected(self):
        """Paths with '..' that escape workspace are rejected."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.tools.unified_diff_tool import UnifiedDiffTool
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange

        escape_path = str(TEST_WORKSPACE_ROOT / ".." / "escape.txt")

        for tool_cls, kwargs in [
            (ReplaceInFileTool, {"path": escape_path, "diff": "<<<<<< SEARCH\nx\n=======\ny\n>>>>>>> REPLACE\n"}),
            (UnifiedDiffTool, {"file_path": escape_path, "patch": "--- a\n+++ b\n@@ -1 +1 @@\n-x\n+y\n"}),
            (WriteFileTool, {"path": escape_path, "content": "escape"}),
        ]:
            tool = tool_cls(workspace_root=TEST_WORKSPACE_ROOT)
            result = tool.execute(**kwargs)

            assert isinstance(result, PendingChange)
            assert result.is_error(), f"{tool_cls.__name__} should reject traversal"
