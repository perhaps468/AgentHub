# -*- coding: utf-8 -*-
"""T5: CommandGuard whitelist security tightening tests.

Tests that interpreter-level arbitrary script execution is blocked:
- python -c / -e / -m arbitrary → restricted
- node -e / node -p / npx arbitrary → blocked
- npm install / npm exec → blocked
- poetry run / uv run → restricted to safe commands
- Bare interpreter prefixes removed from whitelist
"""

import pytest


class TestInterpreterPrefixBlocked:
    """T5: Bare interpreter prefixes are NOT in the whitelist."""

    def test_bare_python_rejected(self):
        """Bare 'python' command is NOT whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("python")
        assert not result.is_ok
        assert "not in whitelist" in result.error or "not an allowed command" in result.error

    def test_python_minus_c_rejected(self):
        """'python -c' (arbitrary code) is NOT whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("python -c 'print(1)'")
        assert not result.is_ok

    def test_python_minus_e_rejected(self):
        """'python -e' (arbitrary code) is NOT whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("python -e print('hello')")
        assert not result.is_ok

    def test_bare_node_rejected(self):
        """Bare 'node' command is NOT whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("node")
        assert not result.is_ok

    def test_node_minus_e_rejected(self):
        """'node -e' (arbitrary code) is NOT whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("node -e 'console.log(1)'")
        assert not result.is_ok

    def test_bare_npm_rejected(self):
        """Bare 'npm' (without specific safe subcommand) is NOT whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npm")
        assert not result.is_ok

    def test_bare_npx_rejected(self):
        """Bare 'npx' (without specific safe subcommand) is NOT whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npx")
        assert not result.is_ok

    def test_npx_tsx_script_rejected(self):
        """'npx tsx script.ts' (arbitrary script execution) is NOT whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npx tsx script.ts")
        assert not result.is_ok


class TestSafeCommandPatternsAllowed:
    """T5: Specific safe command patterns ARE still whitelisted."""

    def test_pytest_allowed(self):
        """pytest is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("pytest")
        assert result.is_ok

    def test_pytest_with_args_allowed(self):
        """pytest with arguments is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("pytest tests/ --tb=short -q")
        assert result.is_ok

    def test_python_m_pytest_allowed(self):
        """'python -m pytest' is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("python -m pytest")
        assert result.is_ok

    def test_python_m_pytest_args_allowed(self):
        """'python -m pytest [args]' is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("python -m pytest tests/ -v")
        assert result.is_ok

    def test_node_minus_version_allowed(self):
        """'node --version' is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("node --version")
        assert result.is_ok

    def test_npm_test_allowed(self):
        """'npm test' (running package.json test script) is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npm test")
        assert result.is_ok

    def test_npm_run_build_allowed(self):
        """'npm run build' (running build script) is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npm run build")
        assert result.is_ok

    def test_npm_run_allowed(self):
        """'npm run [script]' (running defined scripts) is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npm run lint")
        assert result.is_ok

    def test_npm_ci_allowed(self):
        """'npm ci' (clean install from lockfile) is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npm ci")
        assert result.is_ok

    def test_pnpm_test_allowed(self):
        """'pnpm test' is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("pnpm test")
        assert result.is_ok

    def test_pnpm_run_allowed(self):
        """'pnpm run [script]' is whitelisted."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("pnpm run test")
        assert result.is_ok


class TestDangerousPatternsBlocked:
    """T5: Dangerous patterns are blocked even if partial prefix matches."""

    def test_npm_install_blocked(self):
        """'npm install' (arbitrary package install) is blocked."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npm install lodash")
        assert not result.is_ok

    def test_npm_exec_blocked(self):
        """'npm exec' (arbitrary package execution) is blocked."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npm exec -- some-package")
        assert not result.is_ok

    def test_npx_create_app_blocked(self):
        """'npx create-*' (template instantiation) is blocked."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npx create-react-app my-app")
        assert not result.is_ok

    def test_npx_degit_blocked(self):
        """'npx degit' (direct repo cloning) is blocked."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("npx degit user/repo dest")
        assert not result.is_ok

    def test_pnpm_add_blocked(self):
        """'pnpm add' (add package) is blocked."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("pnpm add lodash")
        assert not result.is_ok

    def test_pnpm_install_blocked(self):
        """'pnpm install' (install all packages) is blocked."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("pnpm install")
        assert not result.is_ok

    def test_python_arbitrary_script_blocked(self):
        """'python <arbitrary_file>' is blocked (not module-based)."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("python run.py")
        assert not result.is_ok

    def test_node_arbitrary_script_blocked(self):
        """'node <arbitrary_file>' is blocked."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("node script.js")
        assert not result.is_ok


class TestShellMetacharactersBlocked:
    """T5: Shell metacharacters are blocked regardless of prefix."""

    def test_python_with_semicolon_blocked(self):
        """'python; echo pwned' is blocked by metachar check."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("python; echo pwned")
        assert not result.is_ok

    def test_pytest_with_pipe_blocked(self):
        """'pytest | cat' is blocked by metachar check."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("pytest | cat")
        assert not result.is_ok

    def test_node_with_backtick_blocked(self):
        """'node `cat /etc/passwd`' is blocked."""
        from app.runtime.command_guard import CommandGuard

        guard = CommandGuard(workspace_root=".")
        result = guard.validate_command("node `whoami`")
        assert not result.is_ok
