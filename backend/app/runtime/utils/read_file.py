"""Tool for reading a file content."""

import os


def read_file(file_path: str) -> str:
    """Reads a file and returns its content.

    Args:
        file_path: The path to the file to read.

    Returns:
        The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()
