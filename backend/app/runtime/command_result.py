# -*- coding: utf-8 -*-
"""Task C-5: Command Result Payload module.

Provides structured payload for command execution results used by
RunCommandTool, runtime events, and WS protocol.
"""

from dataclasses import dataclass


@dataclass
class CommandResultPayload:
    """Structured payload for command execution results.

    Attributes:
        type: Always "command_result".
        command: The executed command string.
        cwd: Working directory where command was executed.
        stdout: Standard output from the command.
        stderr: Standard error from the command.
        exit_code: Process exit code.
        success: Whether the command succeeded (exit_code == 0).
        timed_out: Whether the command timed out.
    """

    type: str = "command_result"
    command: str = ""
    cwd: str = ""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    success: bool = True
    timed_out: bool = False

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "type": self.type,
            "command": self.command,
            "cwd": self.cwd,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "success": self.success,
            "timed_out": self.timed_out,
        }
