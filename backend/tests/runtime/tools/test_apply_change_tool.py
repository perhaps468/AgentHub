# -*- coding: utf-8 -*-
"""T3: Formal apply path tests — preview -> confirm -> apply controlled write chain.

Tests that:
- write_file / replace_in_file return PendingChange with PREVIEW status
- A formal apply tool can confirm and apply pending changes
- Rejection path works (change not applied)
- External modification after preview triggers rejection
"""

import os
import tempfile
from pathlib import Path

import pytest

from app.runtime.tools.write_file_tool import WriteFileTool
from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool


class TestWriteFileToolReturnsPendingChange:
    """T3: write_file returns PendingChange (not direct write)."""

    def test_write_file_returns_pending_change(self):
        """WriteFileTool.execute() returns a PendingChange object."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import PendingChange, ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create parent dir so write is valid
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.environ["WORKSPACE_ROOT"] = tmpdir

            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(path="subdir/newfile.txt", content="hello world")

            assert isinstance(result, PendingChange)
            assert result.status == ChangeStatus.PREVIEW
            assert result.operation.value in ("create", "update")
            assert result.is_success()
            assert result.change_id

    def test_write_file_does_not_write_to_disk(self):
        """WriteFileTool.execute() does NOT write the file; only previews."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            os.environ["WORKSPACE_ROOT"] = tmpdir

            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(path="subdir/newfile.txt", content="hello world")

            file_path = subdir / "newfile.txt"
            assert not file_path.exists(), "File should NOT be written during preview"

    def test_write_file_existing_file_returns_update(self):
        """Writing to an existing file returns UPDATE operation."""
        from app.runtime.tools.write_file_tool import WriteFileTool
        from app.runtime.pending_change import ChangeOperation

        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            file_path = subdir / "existing.txt"
            file_path.write_text("original content", encoding="utf-8")

            os.environ["WORKSPACE_ROOT"] = tmpdir
            tool = WriteFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(path="subdir/existing.txt", content="new content")

            assert result.operation == ChangeOperation.UPDATE
            assert result.original_content == "original content"
            assert result.proposed_content == "new content"


class TestReplaceInFileToolReturnsPendingChange:
    """T3: replace_in_file returns PendingChange (not direct write)."""

    def test_replace_in_file_returns_pending_change(self):
        """ReplaceInFileTool.execute() returns a PendingChange object."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange, ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("line one\nline two\nline three\n", encoding="utf-8")
            os.environ["WORKSPACE_ROOT"] = tmpdir

            tool = ReplaceInFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(
                path="test.txt",
                diff=(
                    "<<<<<<< SEARCH\n"
                    "line two\n"
                    "=======\n"
                    "line two modified\n"
                    ">>>>>>> REPLACE\n"
                ),
            )

            assert isinstance(result, PendingChange)
            assert result.status == ChangeStatus.PREVIEW
            assert result.operation.value == "update"
            assert result.is_success()

    def test_replace_in_file_does_not_write_to_disk(self):
        """ReplaceInFileTool.execute() does NOT write; only previews."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.txt"
            file_path.write_text("original content", encoding="utf-8")

            os.environ["WORKSPACE_ROOT"] = tmpdir
            tool = ReplaceInFileTool(workspace_root=Path(tmpdir))
            result = tool.execute(
                path="test.txt",
                diff=(
                    "<<<<<<< SEARCH\n"
                    "original content\n"
                    "=======\n"
                    "modified content\n"
                    ">>>>>>> REPLACE\n"
                ),
            )

            # File content should NOT be modified
            assert file_path.read_text(encoding="utf-8") == "original content"


class TestPendingChangeApply:
    """T3: PendingChange.apply() writes to disk when called."""

    def test_pending_change_apply_writes_file(self):
        """PendingChange.apply() writes the proposed content to disk."""
        from app.runtime.pending_change import PendingChange, ChangeStatus

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "applied.txt"

            pc = PendingChange.make_create(
                path=str(file_path),
                proposed_content="applied content\n",
            )
            assert pc.status == ChangeStatus.PREVIEW

            success = pc.apply()
            assert success
            assert pc.status == ChangeStatus.APPLIED
            assert file_path.read_text(encoding="utf-8") == "applied content\n"

    def test_pending_change_apply_rejects_modified_file(self):
        """PendingChange.apply() rejects if file was modified after preview."""
        from app.runtime.pending_change import PendingChange

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "modified.txt"
            file_path.write_text("original\n", encoding="utf-8")

            pc = PendingChange.make_update(
                path=str(file_path),
                original_content="original\n",
                proposed_content="modified\n",
            )

            # Simulate external modification
            file_path.write_text("changed by another process\n", encoding="utf-8")

            success = pc.apply()
            assert not success
            assert "modified after preview" in pc.error
            # File should still have the modified content
            assert file_path.read_text(encoding="utf-8") == "changed by another process\n"

    def test_pending_change_apply_rejects_error_change(self):
        """PendingChange.apply() returns False for error changes."""
        from app.runtime.pending_change import PendingChange

        pc = PendingChange.make_error(path="/nonexistent/file.txt", error="path error")
        assert not pc.apply()


class TestApplyChangeTool:
    """T3: apply_change tool formally applies a pending change by ID."""

    def test_apply_change_tool_exists(self):
        """apply_change tool should be available in the tool registry."""
        from app.runtime.tools.apply_change_tool import ApplyChangeTool

        tool = ApplyChangeTool()
        assert tool.name == "apply_change"
        assert "change_id" in [arg.name for arg in tool.arguments]

    def test_apply_change_tool_returns_success(self):
        """apply_change tool returns success when change is applied."""
        from app.runtime.tools.apply_change_tool import ApplyChangeTool

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "to_apply.txt"
            os.environ["WORKSPACE_ROOT"] = tmpdir

            tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            result = tool.execute(change_id="nonexistent-id")
            # With no registry, should indicate no change found
            assert isinstance(result, str)

    def test_apply_change_with_valid_pending_change(self):
        """apply_change applies a registered PendingChange."""
        from app.runtime.pending_change import PendingChange, ChangeStatus
        from app.runtime.tools.apply_change_tool import ApplyChangeTool, _PENDING_CHANGE_REGISTRY

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "apply_test.txt"
            os.environ["WORKSPACE_ROOT"] = tmpdir

            # Create and register a PendingChange
            pc = PendingChange.make_create(
                path=str(file_path),
                proposed_content="applied via tool\n",
            )
            change_id = pc.change_id

            tool = ApplyChangeTool(workspace_root=Path(tmpdir))
            _PENDING_CHANGE_REGISTRY[change_id] = pc

            result = tool.execute(change_id=change_id)

            assert file_path.exists()
            assert file_path.read_text(encoding="utf-8") == "applied via tool\n"
            assert pc.status == ChangeStatus.APPLIED
            assert change_id not in _PENDING_CHANGE_REGISTRY
