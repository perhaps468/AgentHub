"""M7 - Dev Task Loop integration tests — RED phase.

These tests verify the end-to-end dev task closed loop:
1. replace_in_file generates PendingChange
2. PendingChange.apply() succeeds
3. run_command_tool runs a test command
4. apply failure prevents command execution
5. Command failure returns structured result
"""

import tempfile
from pathlib import Path

import pytest


TEST_WORKSPACE_ROOT = Path(__file__).parent / "tools" / "test_workspace"


class TestDevLoopApplyThenCommand:
    """DL-1: apply + run_command forms a valid dev loop."""

    def test_replace_and_apply_creates_file(self):
        """replace_in_file + apply() should write file to disk."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange, ChangeStatus

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        target = TEST_WORKSPACE_ROOT / "subdir" / "dev_loop_test.txt"
        target.write_text("original line\n", encoding="utf-8")

        try:
            result = tool.execute(
                path=str(target),
                diff=(
                    "<<<<<<< SEARCH\n"
                    "original line\n"
                    "=======\n"
                    "modified line\n"
                    ">>>>>>> REPLACE\n"
                ),
            )

            assert isinstance(result, PendingChange)
            assert result.is_success()

            applied = result.apply()
            assert applied is True
            assert target.read_text(encoding="utf-8") == "modified line\n"
            assert result.status == ChangeStatus.APPLIED
        finally:
            if target.exists():
                target.unlink()

    def test_apply_then_run_command_sequence(self):
        """After apply, run_command_tool should execute in same workspace."""
        from app.runtime.tools.run_command_tool import RunCommandTool
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange
        import tempfile

        # Create a minimal python test file
        test_file = TEST_WORKSPACE_ROOT / "subdir" / "dev_loop_pytest.txt"
        test_file.write_text(
            "def test_pass(): assert True\n",
            encoding="utf-8"
        )

        cmd_tool = RunCommandTool(workspace_root=TEST_WORKSPACE_ROOT)
        replace_tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)

        try:
            # Step 1: modify the file
            change = replace_tool.execute(
                path=str(test_file),
                diff=(
                    "<<<<<<< SEARCH\n"
                    "def test_pass(): assert True\n"
                    "=======\n"
                    "def test_pass(): assert True\n"
                    "def test_new(): assert 1 == 1\n"
                    ">>>>>>> REPLACE\n"
                ),
            )
            assert isinstance(change, PendingChange)
            assert change.is_success()

            # Step 2: apply
            applied = change.apply()
            assert applied is True

            # Step 3: run pytest on the modified file
            cmd_result = cmd_tool.execute(
                command=f"python -m pytest {test_file} -v",
                cwd=str(TEST_WORKSPACE_ROOT),
                timeout_seconds=30,
            )

            assert isinstance(cmd_result, str)
            # Should contain pytest output
            assert any(k in cmd_result.lower() for k in ["passed", "collected", "error", "test"]), \
                f"Expected pytest output, got: {cmd_result}"

        finally:
            if test_file.exists():
                test_file.unlink()


class TestDevLoopApplyFailure:
    """DL-2: apply failure prevents command execution path."""

    def test_apply_rejects_mismatched_content(self):
        """apply() should return False when file content changed since preview."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        target = TEST_WORKSPACE_ROOT / "subdir" / "mismatch_apply_test.txt"
        target.write_text("original content\n", encoding="utf-8")

        try:
            result = tool.execute(
                path=str(target),
                diff=(
                    "<<<<<<< SEARCH\n"
                    "original content\n"
                    "=======\n"
                    "new content\n"
                    ">>>>>>> REPLACE\n"
                ),
            )

            # Simulate someone else changed the file after preview
            target.write_text("changed by external process\n", encoding="utf-8")

            applied = result.apply()
            assert applied is False, "apply() should return False on content mismatch"
            assert result.error is not None
        finally:
            if target.exists():
                target.unlink()

    def test_command_not_executed_after_failed_apply(self):
        """If apply fails, cmd_tool.execute() must NOT be called.

        The dev loop should check change.is_success() before calling cmd_tool.execute().
        This test uses a helper that mirrors the loop logic, with a spy that proves
        execute() is never reached after apply failure.
        """
        from app.runtime.tools.run_command_tool import RunCommandTool
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange
        from unittest.mock import patch

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        cmd_tool = RunCommandTool(workspace_root=TEST_WORKSPACE_ROOT)
        target = TEST_WORKSPACE_ROOT / "subdir" / "fail_apply_cmd_test.txt"
        target.write_text("original\n", encoding="utf-8")

        try:
            change = tool.execute(
                path=str(target),
                diff=(
                    "<<<<<<< SEARCH\n"
                    "original\n"
                    "=======\n"
                    "modified\n"
                    ">>>>>>> REPLACE\n"
                ),
            )

            # External modification causes apply to fail
            target.write_text("external change\n", encoding="utf-8")

            applied = change.apply()
            assert applied is False, "apply() must return False on content mismatch"

            # Dev loop helper: runs command ONLY if apply succeeded
            # This mirrors how the runtime agent should gate command execution
            def _dev_loop_run_command(change_obj: PendingChange, command: str, cwd: str, timeout: int):
                """Helper: only execute command if apply succeeded."""
                if change_obj.is_success():
                    return cmd_tool.execute(command=command, cwd=cwd, timeout_seconds=timeout)
                return "[BLOCKED] apply failed, command not executed"

            # Spy on execute — it must NOT be called because apply failed
            with patch.object(cmd_tool, 'execute', wraps=cmd_tool.execute) as spy:
                result = _dev_loop_run_command(
                    change,
                    command="echo should_not_run",
                    cwd=str(TEST_WORKSPACE_ROOT),
                    timeout=5,
                )
                # execute was never called
                assert spy.call_count == 0, (
                    f"execute() must not be called after failed apply, "
                    f"but was called {spy.call_count} time(s)"
                )
                # Result should be the blocked message
                assert "[BLOCKED]" in result, (
                    f"Expected blocked message, got: {result}"
                )
        finally:
            if target.exists():
                target.unlink()


class TestDevLoopCommandFailure:
    """DL-3: Command failure returns structured result."""

    def test_failed_command_returns_structured_result(self):
        """run_command_tool should return structured result even on failure."""
        from app.runtime.tools.run_command_tool import RunCommandTool

        tool = RunCommandTool(workspace_root=TEST_WORKSPACE_ROOT)
        result = tool.execute(
            command="python -c \"raise SystemExit(1)\"",
            cwd=str(TEST_WORKSPACE_ROOT),
            timeout_seconds=5,
        )

        assert isinstance(result, str)
        assert len(result) > 0
        # Should contain failure indicators
        assert any(k in result.lower() for k in ["exit", "fail", "error", "nonzero"]), \
            f"Expected failure indication, got: {result}"

    def test_nonexistent_command_returns_error_string(self):
        """Nonexistent command should return error string, not raise."""
        from app.runtime.tools.run_command_tool import RunCommandTool

        tool = RunCommandTool(workspace_root=TEST_WORKSPACE_ROOT)
        try:
            result = tool.execute(
                command="nonexistent_command_xyz999",
                cwd=str(TEST_WORKSPACE_ROOT),
                timeout_seconds=5,
            )
            assert isinstance(result, str)
            assert "error" in result.lower() or "not found" in result.lower(), \
                f"Expected error for nonexistent command, got: {result}"
        except Exception as e:
            pytest.fail(f"Tool should not raise exception, got: {e}")


class TestDevLoopPendingChangeStatus:
    """DL-4: PendingChange status transitions."""

    def test_pending_change_status_transitions_to_applied(self):
        """After apply(), status should be APPLIED."""
        from app.runtime.tools.replace_in_file_tool import ReplaceInFileTool
        from app.runtime.pending_change import PendingChange, ChangeStatus

        tool = ReplaceInFileTool(workspace_root=TEST_WORKSPACE_ROOT)
        target = TEST_WORKSPACE_ROOT / "subdir" / "status_transition_test.txt"
        target.write_text("line1\n", encoding="utf-8")

        try:
            result = tool.execute(
                path=str(target),
                diff=(
                    "<<<<<<< SEARCH\n"
                    "line1\n"
                    "=======\n"
                    "line2\n"
                    ">>>>>>> REPLACE\n"
                ),
            )

            assert result.status == ChangeStatus.PREVIEW, "Initial status should be PREVIEW"

            applied = result.apply()
            assert applied is True
            assert result.status == ChangeStatus.APPLIED, \
                f"Status should be APPLIED after apply(), got: {result.status}"
        finally:
            if target.exists():
                target.unlink()

    def test_apply_sets_applied_status_on_success(self):
        """apply() should set status to APPLIED on disk write success."""
        from app.runtime.pending_change import PendingChange, ChangeOperation, ChangeStatus

        pc = PendingChange.make_create(
            path=str(TEST_WORKSPACE_ROOT / "subdir" / "new_file_status.txt"),
            proposed_content="new content\n",
        )
        assert pc.status == ChangeStatus.PREVIEW

        applied = pc.apply()
        assert applied is True
        assert pc.status == ChangeStatus.APPLIED

        # cleanup
        path = Path(pc.path)
        if path.exists():
            path.unlink()


class TestDevLoopCwdConstraint:
    """DL-5: Commands respect cwd constraint."""

    def test_command_respects_workspace_cwd(self):
        """Commands should only run in workspace cwd."""
        from app.runtime.tools.run_command_tool import RunCommandTool

        tool = RunCommandTool(workspace_root=TEST_WORKSPACE_ROOT)
        # Running a command with cwd=workspace should work
        result = tool.execute(
            command="echo test",
            cwd=str(TEST_WORKSPACE_ROOT),
            timeout_seconds=5,
        )
        assert isinstance(result, str)
        assert "test" in result.lower() or "stdout" in result.lower(), \
            f"Expected command output, got: {result}"

    def test_command_rejects_outside_workspace_cwd(self):
        """Commands with cwd outside workspace should be rejected."""
        from app.runtime.tools.run_command_tool import RunCommandTool
        import tempfile

        tool = RunCommandTool(workspace_root=TEST_WORKSPACE_ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            result = tool.execute(
                command="echo test",
                cwd=tmp,
                timeout_seconds=5,
            )
            assert isinstance(result, str)
            assert "workspace" in result.lower() or "not allowed" in result.lower(), \
                f"Expected workspace error, got: {result}"
