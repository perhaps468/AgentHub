"""Tool for getting the current environment."""

import os
import platform
import socket
import sys
from pathlib import Path


def get_environment(workspace_root: str = "") -> str:
    """Get the current environment information.

    Args:
        workspace_root: The workspace root path for the agent's sandbox boundary.

    Returns:
        A string describing the current environment.
    """
    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown"

    try:
        username = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    except Exception:
        username = "unknown"

    python_version = sys.version.split()[0]
    os_info = f"{platform.system()} {platform.release()}"

    home = Path.home()
    try:
        home = home.resolve()
    except Exception:
        pass

    # T7: Replace CWD with Workspace Root - CWD is process-level, not meaningful for agent
    workspace_line = f"Workspace Root: {workspace_root}" if workspace_root else "Workspace Root: (not configured)"

    return (
        f"Operating System: {os_info}\n"
        f"Hostname: {hostname}\n"
        f"{workspace_line}\n"
        f"User: {username}\n"
        f"Python Version: {python_version}\n"
        f"Home Directory: {home}"
    )
