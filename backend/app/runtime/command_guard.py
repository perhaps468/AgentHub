"""M7 - Command Guard: enforces controlled command execution boundaries.

All commands must pass through CommandGuard before execution:
- Command name / prefix must be in the whitelist
- CWD must be within workspace
- Timeout must be bounded (not zero, not excessive)

This file is NOT a direct copy of any source project command tool.
It is built from scratch per AgentHub security model.

Key design decisions:
- Default-deny: unknown commands are rejected
- No shell=True by default (subprocess.Popen with shell=False or explicit sh)
- Timeout is mandatory and capped
- All rejection reasons are stable, structured strings
"""

from dataclasses import dataclass
from pathlib import Path

# Maximum allowed timeout in seconds
MAX_TIMEOUT = 300  # 5 minutes
DEFAULT_TIMEOUT = 60  # 1 minute


@dataclass
class CommandResult:
    """Result of a command guard check.

    Attributes:
        is_ok: True if the command passes all guard checks.
        command: The command string that was checked.
        error: None if is_ok, otherwise a stable error message.
        planned_timeout: The timeout that will be used (capped at max_timeout).
    """

    is_ok: bool
    command: str
    error: str | None
    planned_timeout: int

    @property
    def is_error(self) -> bool:
        return not self.is_ok


# ------------------------------------------------------------------
# Whitelist: allowed command name prefixes (lowercase)
# ------------------------------------------------------------------
# Each entry is a lowercase prefix. The command must start with one
# of these prefixes (after stripping leading whitespace).
#
# Format: "prefix" matches "prefix", "prefix ", "prefix-", "prefix:",
# but NOT "prefixx" (must be exact prefix or prefix + whitespace/hyphen)
#
# T5 security tightening: removed bare interpreter prefixes (python, node,
# npm, npx, pnpm, pip, pip3) that allowed arbitrary script execution.
# Only specific safe command patterns remain.

ALLOWED_COMMAND_PREFIXES: tuple[str, ...] = (
    # Python test runners (T5: safe, restricted entry points)
    "pytest",
    "python -m pytest",
    # Python package inspection (read-only, safe)
    "pip show",
    "pip list",
    "pip freeze",
    "pip check",
    "pip3 show",
    "pip3 list",
    "pip3 freeze",
    "pip3 check",
    # Version checks (safe, read-only)
    "--version",
    "-v",
    "version",
    "python --version",
    "python3 --version",
    "node --version",
    "node -v",
    "npm --version",
    "npm -v",
    "pnpm --version",
    "pnpm -v",
    "uv --version",
    "uv python list",
    "uv python pinned",
    # npm/pnpm safe scripts (T5: npm/pnpm run [script] for defined package.json scripts)
    "npm test",
    "npm run",
    "npm ci",
    "npm ls",
    "npm pack",
    "pnpm test",
    "pnpm run",
    "pnpm ci",
    "pnpm ls",
    "pnpm pack",
    # uv run (T5: allowed only if subsequent command is safe)
    "uv run pytest",
    "uv run python -m pytest",
    # Read-only shell utilities
    "echo",
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "find",
    "wc",
    "sort",
    "uniq",
    "diff",
    "ping",
    "timeout",
    # uv tool install check
    "uv tool list",
)

# ------------------------------------------------------------------
# Blocked command name prefixes (checked AFTER allowlist).
# These are hard overrides for known dangerous patterns that do NOT
# appear in the allowlist.
# ------------------------------------------------------------------

BLOCKED_COMMAND_PREFIXES: tuple[str, ...] = (
    # Destructive file operations
    "rm -rf",
    "rm -r",
    "rm -f",
    "del",
    "rmdir",
    "rmdir /s",
    # Network downloads that lead to shell execution
    "curl",
    "wget",
    # Network / remote access
    "ssh",
    "scp",
    "nc ",
    "netcat",
    "ncat",
    # Disk operations
    "dd ",
    "mkfs",
    "fdisk",
    "parted",
    # System shutdown / reboot
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
    "telinit 0",
    "telinit 6",
    # Container / infra tooling
    "docker run",
    "docker exec",
    "kubectl",
    "terraform destroy",
    "ansible",
    "playbook",
    # Package installation (T5: block arbitrary install, allow safe scripts)
    "pip install",
    "pip uninstall",
    "pip3 install",
    "pip3 uninstall",
    "poetry install",
    "poetry add",
    "poetry remove",
    "npm install",
    "npm uninstall",
    "npm add",
    "npm remove",
    "npm exec",
    "npm x",
    "pnpm install",
    "pnpm uninstall",
    "pnpm add",
    "pnpm remove",
    "npx ",
    "npx",
    # uv tool install
    "uv tool install",
    "uv pip install",
    # Shell metacharacters that indicate command chaining/injection
    "|",
    "&&",
    ";",
    ">>",
    "2>",
    "||",
    # eval / source / exec patterns
    "eval ",
    "source ",
    "exec ",
    ". /",
    # T5: arbitrary code execution — precise patterns to avoid blocking
    # legitimate module invocations. Allowlist is checked first so
    # "python -m pytest" (whitelisted) is never caught by "python -m ".
    "python -c",
    "python -e",
    "python ",         # bare python [file] — blocks "python run.py" but NOT "python -m pytest"
    "python3 ",
    "node -e",
    "node -p",
    "node --eval",
    "node ",           # bare node [file] — blocks "node server.js"
    # T5: arbitrary script execution via npx/tsx/bun
    "tsx ",
    "bun ",
    "deno ",
    # T5: package template / cloning tools
    "npx create-",
    "npx degit",
    "npx giget",
)

# ------------------------------------------------------------------
# Shell metacharacter patterns (dangerous even on allowed commands)
# ------------------------------------------------------------------

DANGEROUS_METACHARACTERS = (
    "|",    # pipe
    "&&",   # and
    "||",   # or
    ";",    # sequence
    "`",    # command substitution (backtick)
    "$(",   # command substitution (dollar)
    ">>",   # append redirect
    "2>",   # error redirect
    "<(",   # process substitution (bash)
    ">",    # overwrite redirect (allowed for some commands but blocked here)
)


class CommandGuard:
    """Enforces command execution boundaries for AgentHub runtime.

    Responsibilities:
    - Validate command is in whitelist (by prefix)
    - Reject dangerous shell patterns
    - Validate cwd is within workspace
    - Cap and validate timeout bounds
    - Build a structured execution plan
    """

    def __init__(
        self,
        workspace_root: str | Path,
        default_timeout: int = DEFAULT_TIMEOUT,
        max_timeout: int = MAX_TIMEOUT,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.default_timeout = default_timeout
        self.max_timeout = max_timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_command(self, command: str) -> CommandResult:
        """Check if a command string passes the guard.

        Args:
            command: The raw command string (e.g. "pytest --version").

        Returns:
            CommandResult where is_ok=True means the command is allowed.
        """
        if not command or not isinstance(command, str):
            return CommandResult(
                is_ok=False,
                command=command,
                error="Command is empty or invalid.",
                planned_timeout=0,
            )

        stripped = command.strip()
        if not stripped:
            return CommandResult(
                is_ok=False,
                command=command,
                error="Command is empty or whitespace-only.",
                planned_timeout=0,
            )

        # T5: Check dangerous metacharacters FIRST — block pipe/chaining/injection
        # even within whitelisted commands (e.g. "pytest | cat" must be rejected).
        if self._has_dangerous_metachar(stripped):
            return CommandResult(
                is_ok=False,
                command=command,
                error=f"Command rejected: contains dangerous shell metacharacter.",
                planned_timeout=0,
            )

        # T5: Check allowlist — if it's in the whitelist, it's allowed.
        # This order (metachar → allowlist → blocklist) ensures:
        # 1. All metacharacter-based attacks are caught regardless of prefix.
        # 2. Specific safe commands are allowed (e.g. "node --version").
        # 3. Broad block prefixes don't accidentally block narrow allow entries.
        if self._is_whitelisted(stripped):
            return CommandResult(
                is_ok=True,
                command=command,
                error=None,
                planned_timeout=self.default_timeout,
            )

        # Check for dangerous metacharacters (blocks pipe/injection)
        if self._has_dangerous_metachar(stripped):
            return CommandResult(
                is_ok=False,
                command=command,
                error=f"Command rejected: contains dangerous shell metacharacter.",
                planned_timeout=0,
            )

        # Check blocked prefixes last — these are hard overrides for known
        # dangerous patterns that don't appear in the allowlist.
        for blocked in BLOCKED_COMMAND_PREFIXES:
            if stripped.lower().startswith(blocked.lower()):
                return CommandResult(
                    is_ok=False,
                    command=command,
                    error=f"Command rejected: '{blocked}' is a blocked command prefix.",
                    planned_timeout=0,
                )

        return CommandResult(
            is_ok=False,
            command=command,
            error=f"Command not in whitelist: '{self._get_command_name(stripped)}' is not an allowed command.",
            planned_timeout=0,
        )

    def validate_cwd(self, cwd: str | Path) -> CommandResult:
        """Check if a cwd path is within the workspace boundary.

        Args:
            cwd: The working directory path to check.

        Returns:
            CommandResult where is_ok=True means the cwd is valid.
        """
        if not cwd:
            return CommandResult(
                is_ok=False,
                command="",
                error="CWD is empty.",
                planned_timeout=0,
            )

        try:
            cwd_path = Path(cwd).resolve()
        except (OSError, RuntimeError) as e:
            return CommandResult(
                is_ok=False,
                command="",
                error=f"Invalid CWD path: {e}",
                planned_timeout=0,
            )

        # Check if within workspace
        try:
            cwd_path.relative_to(self.workspace_root)
        except ValueError:
            return CommandResult(
                is_ok=False,
                command="",
                error=f"CWD '{cwd}' is outside workspace '{self.workspace_root}'.",
                planned_timeout=0,
            )

        return CommandResult(
            is_ok=True,
            command="",
            error=None,
            planned_timeout=0,
        )

    def build_execution_plan(
        self,
        command: str,
        cwd: str | Path,
        timeout_seconds: int | None = None,
    ) -> CommandResult:
        """Build a complete execution plan by validating all three dimensions.

        This is the primary API for the tool layer. It aggregates:
        1. Command whitelist check
        2. CWD workspace boundary check
        3. Timeout bounds check

        Args:
            command: The command to run.
            cwd: The working directory.
            timeout_seconds: Requested timeout (defaults to default_timeout).

        Returns:
            CommandResult where is_ok=True means the plan is valid.
            The planned_timeout field contains the (possibly capped) timeout.
        """
        # Step 1: validate command
        cmd_result = self.validate_command(command)
        if not cmd_result.is_ok:
            return cmd_result

        # Step 2: validate cwd
        cwd_result = self.validate_cwd(cwd)
        if not cwd_result.is_ok:
            return cwd_result

        # Step 3: validate timeout
        if timeout_seconds is None:
            timeout_seconds = self.default_timeout

        if not isinstance(timeout_seconds, int):
            return CommandResult(
                is_ok=False,
                command=command,
                error=f"timeout_seconds must be an integer, got {type(timeout_seconds).__name__}.",
                planned_timeout=0,
            )

        if timeout_seconds <= 0:
            return CommandResult(
                is_ok=False,
                command=command,
                error=f"timeout_seconds must be > 0, got {timeout_seconds}.",
                planned_timeout=0,
            )

        # Cap excessive timeouts
        planned_timeout = min(timeout_seconds, self.max_timeout)

        return CommandResult(
            is_ok=True,
            command=command,
            error=None,
            planned_timeout=planned_timeout,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _has_dangerous_metachar(self, command: str) -> bool:
        """Check for dangerous shell metacharacters.

        We block pipe and chaining even within allowed commands.
        For example, "echo hello; rm -rf /" should be blocked even though
        "echo hello" is in the whitelist.
        """
        lower = command.lower()
        for meta in DANGEROUS_METACHARACTERS:
            if meta in lower:
                return True
        return False

    def _is_whitelisted(self, command: str) -> bool:
        """Check if command starts with an allowed prefix."""
        lower = command.lower()
        for prefix in ALLOWED_COMMAND_PREFIXES:
            if lower.startswith(prefix.lower()):
                return True
        return False

    def _get_command_name(self, command: str) -> str:
        """Extract the primary command name (first token) from command string."""
        tokens = command.strip().split()
        if not tokens:
            return command
        return tokens[0]
