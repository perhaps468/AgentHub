"""Tool for getting the current environment."""

import os
import platform
import socket
import sys
from pathlib import Path


def get_environment() -> str:
    """Get the current environment information.

    Returns:
        A string describing the current environment.
    """
    try:
        cwd = os.getcwd()
    except Exception:
        cwd = "unknown"

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

    return (
        f"Operating System: {os_info}\n"
        f"Hostname: {hostname}\n"
        f"Current Working Directory: {cwd}\n"
        f"User: {username}\n"
        f"Python Version: {python_version}\n"
        f"Home Directory: {home}"
    )
