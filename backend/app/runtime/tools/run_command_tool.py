# -*- coding: utf-8 -*-
"""M7 - Run Command Tool.

Executes whitelisted development commands within workspace boundary and timeout constraints.
Not a copy of any source project tool — built per AgentHub security model.

Key design:
- All commands pass through CommandGuard (whitelist + cwd + timeout)
- Returns structured string output: command / cwd / stdout / stderr / exit_code / timed_out / success
- Never raises unhandled exceptions to runtime
- Uses subprocess with shell=False (command parsed via shlex/cross-platform split)
"""

import subprocess
import sys
from pathlib import Path

from app.runtime.command_guard import CommandGuard
from app.runtime.tools.tool import Tool, ToolArgument


class RunCommandTool(Tool):
    """Tool for executing whitelisted development commands.

    Executes commands within a workspace boundary and timeout constraint.
    All commands are validated against CommandGuard before execution.

    Input:
        command: The command string to execute (e.g. "pytest --version").
        cwd: Working directory for the command (must be within workspace).
        timeout_seconds: Maximum time to wait (auto-capped by CommandGuard).

    Output:
        Structured string with command, cwd, stdout, stderr, exit_code, timed_out, success.
    """

    name: str = "run_command_tool"
    description: str = (
        "Executes a whitelisted development command within workspace boundary and timeout. "
        "Use this to run tests, builds, or diagnostics after applying code changes. "
        "Commands must be in the allowed list (pytest, python, npm, node, etc.). "
        "CWD must be within the workspace. Returns structured result with stdout/stderr/exit_code."
    )
    arguments: list = [
        ToolArgument(
            name="command",
            arg_type="string",
            description=(
                "The command to execute. Must be a whitelisted command "
                "(e.g. pytest, python, npm, node, echo, ls). "
                "Shell metacharacters (|; &&) are not allowed."
            ),
            required=True,
            example="pytest --version",
        ),
        ToolArgument(
            name="cwd",
            arg_type="string",
            description=(
                "Working directory for the command. Must be within the workspace. "
                "Use relative paths from workspace root or absolute paths within workspace."
            ),
            required=True,
            example=".",
        ),
        ToolArgument(
            name="timeout_seconds",
            arg_type="int",
            description=(
                "Maximum time in seconds to wait for command completion. "
                "Must be > 0. Auto-capped at 300 seconds. Default: 60."
            ),
            required=False,
            default="60",
            example="30",
        ),
    ]

    def model_post_init(self, __context) -> None:
        import os

        # Priority: 1) injected workspace_root, 2) env var fallback
        if self.workspace_root:
            ws = str(Path(self.workspace_root).resolve())
        else:
            ws = os.environ.get("WORKSPACE_ROOT", "")
        object.__setattr__(self, "_workspace_root", ws)
        object.__setattr__(self, "_guard", CommandGuard(workspace_root=self._workspace_root))

    def _format_result(
        self,
        command: str,
        cwd: str,
        stdout: str,
        stderr: str,
        exit_code: int,
        timed_out: bool,
        success: bool,
    ) -> str:
        """Format execution result as a structured string for agent consumption."""
        timed_str = "true" if timed_out else "false"
        success_str = "true" if success else "false"

        lines = [
            f"[COMMAND] {command}",
            f"[CWD] {cwd}",
            f"[EXIT_CODE] {exit_code}",
            f"[TIMED_OUT] {timed_str}",
            f"[SUCCESS] {success_str}",
            "",
            "--- STDOUT ---",
            stdout if stdout else "(no stdout)",
            "",
            "--- STDERR ---",
            stderr if stderr else "(no stderr)",
        ]
        return "\n".join(lines)

    def execute(
        self,
        command: str,
        cwd: str,
        timeout_seconds: int | str | None = None,
        **kwargs,
    ) -> str:
        """Execute a whitelisted command with workspace and timeout constraints.

        Args:
            command: The command string to execute.
            cwd: Working directory (must be within workspace).
            timeout_seconds: Max wait time in seconds.

        Returns:
            Structured string result with stdout/stderr/exit_code.
            Never raises — all errors are captured in result string.
        """
        # Normalize timeout_seconds
        if timeout_seconds is None:
            timeout_seconds = self._guard.default_timeout

        try:
            timeout_seconds = int(timeout_seconds)
        except (ValueError, TypeError):
            return f"Error: timeout_seconds must be an integer, got {timeout_seconds!r}"

        if timeout_seconds <= 0:
            return (
                f"Error: timeout_seconds must be > 0, got {timeout_seconds}. "
                "Commands without a timeout are not allowed."
            )

        # Step 1: build execution plan via guard
        plan = self._guard.build_execution_plan(
            command=command,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )

        if not plan.is_ok:
            return f"Error: {plan.error}"

        actual_timeout = plan.planned_timeout

        # Step 2: execute
        try:
            result = self._run_subprocess(
                command=command,
                cwd=cwd,
                timeout=actual_timeout,
            )
            return result

        except subprocess.TimeoutExpired:
            stdout = ""
            stderr = f"Command timed out after {actual_timeout} seconds."
            return self._format_result(
                command=command,
                cwd=cwd,
                stdout=stdout,
                stderr=stderr,
                exit_code=-1,
                timed_out=True,
                success=False,
            )

        except OSError as e:
            return self._format_result(
                command=command,
                cwd=cwd,
                stdout="",
                stderr=f"OS error: {e}",
                exit_code=-1,
                timed_out=False,
                success=False,
            )

        except Exception as e:
            # Catch-all: never let exceptions propagate to runtime
            return self._format_result(
                command=command,
                cwd=cwd,
                stdout="",
                stderr=f"Unexpected error: {e}",
                exit_code=-1,
                timed_out=False,
                success=False,
            )

    def _parse_command(self, command: str) -> list[str]:
        """Parse command string into list for subprocess with shell=False.

        Uses shlex.split() for cross-platform safe splitting.
        Since guard has already blocked shell metacharacters (|;&& etc.),
        the command is safe to parse. This is NOT shell execution —
        subprocess runs the program directly with arguments.
        """
        import shlex
        import sys

        if sys.platform == "win32":
            return self._parse_command_windows(command)
        return shlex.split(command)

    def _parse_command_windows(self, command: str) -> list[str]:
        """Parse command on Windows: split on whitespace, preserve quoted args.

        Unlike shlex (which is POSIX-biased), this handles Windows paths
        like 'C:\\Program Files\\test.exe' and 'C:/path/file.txt' correctly.
        """
        tokens = []
        current = ""
        in_quote = False
        quote_char = None
        i = 0
        command = command.strip()

        while i < len(command):
            ch = command[i]

            if ch in ('"', "'") and not in_quote:
                in_quote = True
                quote_char = ch
            elif ch == quote_char and in_quote:
                in_quote = False
                quote_char = None
            elif ch.isspace() and not in_quote:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += ch

            i += 1

        if current:
            tokens.append(current)

        return tokens if tokens else [command]

    def _run_subprocess(
        self,
        command: str,
        cwd: str,
        timeout: int,
    ) -> str:
        """Run command via subprocess with shell=False.

        Guard has already validated the command is whitelisted and free of
        shell metacharacters. We parse the command into a list and invoke
        the program directly — no shell interpretation.
        """
        try:
            cmd_list = self._parse_command(command)

            proc = subprocess.Popen(
                cmd_list,
                shell=False,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()  # drain
                raise

            exit_code = proc.returncode

            # On Windows, some commands produce CRLF; normalize to LF
            if sys.platform == "win32":
                stdout = stdout.replace("\r\n", "\n")
                stderr = stderr.replace("\r\n", "\n")

            return self._format_result(
                command=command,
                cwd=cwd,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                timed_out=False,
                success=(exit_code == 0),
            )

        except OSError as e:
            # Command not found, permission denied, etc.
            return self._format_result(
                command=command,
                cwd=cwd,
                stdout="",
                stderr=f"Command failed to start: {e}",
                exit_code=-1,
                timed_out=False,
                success=False,
            )
