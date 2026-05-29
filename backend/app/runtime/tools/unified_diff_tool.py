"""Tool for applying unified diff patches.

M6: Returns PendingChange instead of direct file write.
Uses WorkspaceGuard for path boundary validation.
"""

import difflib
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.runtime.pending_change import ChangeOperation, ChangeStatus, PendingChange
from app.runtime.tools.tool import Tool, ToolArgument
from app.runtime.workspace import WorkspaceGuard, WorkspaceAccessError


class LineType:
    CONTEXT = " "
    ADDITION = "+"
    DELETION = "-"


class PatchError(Exception):
    def __init__(self, message: str, context: Optional[Dict] = None):
        self.context = context or {}
        super().__init__(message)


class Patch:
    """Minimal unified diff patch parser and applier (read-only in M6)."""

    def __init__(self, content: str):
        self.content = content
        self.original_filename: Optional[str] = None
        self.new_filename: Optional[str] = None
        self.hunks: List["Hunk"] = []
        self._parse()

    def _parse(self) -> None:
        if not self.content or not self.content.strip():
            raise PatchError("Empty patch content")

        if self.content.startswith("<![CDATA[") and self.content.endswith("]]>"):
            self.content = self.content[9:-3]

        lines = self.content.splitlines()
        if not lines:
            raise PatchError("No lines in patch")

        # Parse headers
        for line in lines:
            if line.startswith("--- "):
                self.original_filename = line[4:].split("\t")[0].strip()
            elif line.startswith("+++ "):
                self.new_filename = line[4:].split("\t")[0].strip()

        # Parse hunks
        current_hunk_lines: List[str] = []
        in_hunk = False

        for line in lines:
            if line.startswith("@@ "):
                if current_hunk_lines:
                    self.hunks.append(Hunk(current_hunk_lines))
                    current_hunk_lines = []
                in_hunk = True

            if in_hunk:
                current_hunk_lines.append(line)
            elif not (line.startswith("--- ") or line.startswith("+++ ") or line.strip() == ""):
                pass

        if current_hunk_lines:
            self.hunks.append(Hunk(current_hunk_lines))

        if not self.hunks:
            raise PatchError("No valid hunks found in patch")

    def apply_preview(self, original_content: str) -> str:
        """Apply the patch to text content and return new text (preview only)."""
        if not original_content:
            original_lines: List[str] = []
        else:
            original_lines = original_content.splitlines(keepends=True)
            # Ensure last line ends with newline
            if original_lines and not original_lines[-1].endswith("\n"):
                original_lines[-1] += "\n"

        for hunk in self.hunks:
            offset = hunk.validate(original_lines)
            original_lines = hunk.apply(original_lines, offset)

        return "".join(original_lines) if original_lines else ""


class Hunk:
    """Represents a hunk in a unified diff patch."""

    def __init__(self, lines: List[str]):
        self.lines = lines
        self.header: Optional[str] = lines[0] if lines else ""
        self._parse_header()

    def _parse_header(self) -> None:
        if not self.header or not self.header.startswith("@@ "):
            raise PatchError("Invalid hunk header", {"header": self.header})
        parts = self.header.split("@@")
        if len(parts) < 2:
            raise PatchError("Malformed hunk header", {"header": self.header})
        ranges = parts[1].strip().split(" ")
        if len(ranges) < 2:
            raise PatchError("Invalid hunk ranges", {"header": self.header})
        try:
            self.orig_start, self.orig_count = self._parse_range(ranges[0][1:])
            self.new_start, self.new_count = self._parse_range(ranges[1][1:])
        except ValueError as e:
            raise PatchError(f"Invalid range format: {e}", {"header": self.header})

    def _parse_range(self, r: str) -> Tuple[int, int]:
        if "," in r:
            s, c = r.split(",")
            return int(s), int(c)
        return int(r), 1

    def validate(self, file_lines: List[str]) -> int:
        """Validate context and return offset adjustment."""
        if not file_lines:
            return 0

        start = max(0, self.orig_start - 1)
        offset = 0

        for i, line in enumerate(self.lines[1:]):
            if not line or line[0] not in (" ", "-", "+"):
                continue
            if line[0] in (" ", "-"):  # context or deletion
                expected_pos = start + i + offset
                if expected_pos >= len(file_lines):
                    raise PatchError(
                        "Context mismatch: end of file",
                        {"expected_line": expected_pos + 1, "file_lines": len(file_lines)},
                    )
                expected = file_lines[expected_pos].rstrip()
                actual = line[1:].rstrip()
                if expected != actual:
                    # Try to find within tolerance
                    found = False
                    for delta in range(-5, 6):
                        pos = expected_pos + delta
                        if 0 <= pos < len(file_lines) and file_lines[pos].rstrip() == actual:
                            offset += delta
                            found = True
                            break
                    if not found:
                        raise PatchError(
                            "Context mismatch",
                            {
                                "expected": expected,
                                "actual": actual,
                                "at_line": expected_pos + 1,
                            },
                        )
            if line[0] in (" ", "+"):
                offset += 1

        return offset

    def apply(self, lines: List[str], offset: int) -> List[str]:
        """Apply this hunk to lines with given offset."""
        start = max(0, self.orig_start - 1) + offset
        result = lines[:start]
        file_pos = start

        for line in self.lines[1:]:
            if not line:
                continue
            prefix = line[0]
            content = line[1:] if len(line) > 1 else ""

            if prefix == " ":
                if file_pos < len(lines):
                    result.append(lines[file_pos])
                    file_pos += 1
            elif prefix == "-":
                file_pos += 1
            elif prefix == "+":
                result.append(content.rstrip() + "\n")

        result.extend(lines[file_pos:])
        return result


class UnifiedDiffTool(Tool):
    """Tool for applying unified diff patches.

    M6 behaviour:
    - Validates workspace boundary before any file access
    - Returns PendingChange (preview) instead of writing directly
    - Computes unified_diff for display
    """

    name: str = "unified_diff"
    description: str = (
        "Applies a unified diff patch to update a file. "
        "Returns a preview of the change; the change is not applied until explicitly confirmed."
    )
    need_validation: bool = False
    lenient: bool = True
    tolerance: int = 5

    _workspace_root: Optional[Path] = None

    arguments: list[ToolArgument] = [
        ToolArgument(
            name="file_path",
            arg_type="string",
            description="The path to the file to patch. Using an absolute path is recommended.",
            required=True,
            example="/path/to/file.txt",
        ),
        ToolArgument(
            name="patch",
            arg_type="string",
            description=(
                "The unified diff patch content.\n"
                "Must contain --- / +++ headers and @@ hunk markers.\n"
                "Example:\n"
                "--- a/file.txt\n"
                "+++ b/file.txt\n"
                "@@ -1,3 +1,4 @@\n"
                " Hello!\n"
                "+New line!"
            ),
            required=True,
            example="--- a/file.txt\n+++ b/file.txt\n@@ -1,3 +1,4 @@\n Hello!\n+New line!",
        ),
    ]

    def __init__(self, workspace_root: Optional[Path] = None):
        super().__init__()
        self._workspace_root = workspace_root

    @property
    def _guard(self) -> WorkspaceGuard:
        if self._workspace_root:
            resolved_root = self._workspace_root.expanduser().resolve()
            return WorkspaceGuard(resolved_root)
        ws_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
        return WorkspaceGuard(ws_root)

    def execute(self, file_path: str, patch: str) -> PendingChange:
        """Compute a unified diff patch preview, returning PendingChange instead of writing.

        M6: This method never writes to disk. It returns a PendingChange with
        unified_diff computed for display.
        """
        # Validate presence
        if not file_path or not file_path.strip():
            return PendingChange.make_error("", "File path cannot be empty")

        if not patch or not patch.strip():
            return PendingChange.make_error(file_path, "Patch content cannot be empty")

        # Validate workspace boundary
        try:
            resolved_path = self._guard.resolve_write_path(file_path)
        except Exception as e:
            return PendingChange.make_error(file_path, f"Workspace access denied: {e}")

        resolved_str = str(resolved_path)

        # Parse patch
        try:
            patch_obj = Patch(patch)
        except PatchError as e:
            return PendingChange.make_error(resolved_str, f"Invalid patch format: {e}")
        except Exception as e:
            return PendingChange.make_error(resolved_str, f"Failed to parse patch: {e}")

        # Read original content
        file_exists = resolved_path.exists()
        if file_exists:
            try:
                original_content = resolved_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return PendingChange.make_error(resolved_str, f"File must be UTF-8 encoded: '{resolved_str}'")
            except Exception as e:
                return PendingChange.make_error(resolved_str, f"Failed to read file: {e}")
        else:
            # For update operation, existing file is required
            return PendingChange.make_error(
                resolved_str,
                f"File not found (use write_file tool to create new files): '{resolved_str}'",
            )

        # Apply patch (preview only)
        try:
            proposed_content = patch_obj.apply_preview(original_content)
        except PatchError as e:
            return PendingChange.make_error(resolved_str, f"Patch context mismatch: {e}")
        except Exception as e:
            return PendingChange.make_error(resolved_str, f"Failed to apply patch: {e}")

        # No change?
        if proposed_content == original_content:
            return PendingChange.make_error(resolved_str, "No changes needed (patch produces identical content)")

        return PendingChange.make_update(
            path=resolved_str,
            original_content=original_content,
            proposed_content=proposed_content,
        )
