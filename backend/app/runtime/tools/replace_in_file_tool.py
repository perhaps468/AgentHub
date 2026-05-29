"""Tool for replacing sections in an existing file based on SEARCH/REPLACE blocks.

M6: Returns PendingChange instead of direct file write.
Uses WorkspaceGuard for path boundary validation.
"""

import difflib
import os
from pathlib import Path
from typing import List, Optional, Tuple

from app.runtime.pending_change import ChangeOperation, ChangeStatus, PendingChange
from app.runtime.tools.tool import Tool, ToolArgument
from app.runtime.workspace import WorkspaceGuard, WorkspaceAccessError


class SearchReplaceBlock:
    """Represents a single SEARCH/REPLACE block."""

    def __init__(self, search: str, replace: str):
        self.search = search
        self.replace = replace
        self.similarity: Optional[float] = None


class ReplaceInFileTool(Tool):
    """Tool for replacing sections in an existing file based on SEARCH/REPLACE blocks.

    M6 behaviour:
    - Validates workspace boundary before any file access
    - Returns PendingChange (preview) instead of writing directly
    - Computes unified_diff for display
    """

    name: str = "replace_in_file_tool"
    description: str = (
        "Updates sections of content in an existing file using SEARCH/REPLACE blocks. "
        "If exact matches are not found, the tool attempts to find similar sections based on similarity. "
        "⚠️ THIS TOOL MUST BE USED IN PRIORITY TO UPDATE AN EXISTING FILE. "
        "Returns a preview of the change; the change is not applied until explicitly confirmed."
    )
    need_validation: bool = True
    SIMILARITY_THRESHOLD: float = 0.85

    # Workspace root injected at construction time; defaults to process cwd
    _workspace_root: Optional[Path] = None

    arguments: list[ToolArgument] = [
        ToolArgument(
            name="path",
            arg_type="string",
            description="The path of the file to modify.",
            required=True,
            example="./src/main.py",
        ),
        ToolArgument(
            name="diff",
            arg_type="string",
            description=(
                "Define one or more SEARCH/REPLACE blocks:\n"
                "<<<<<<< SEARCH\n"
                "[exact content to find]\n"
                "=======\n"
                "[new content to replace with]\n"
                ">>>>>>> REPLACE\n"
            ),
            required=True,
            example=(
                "<<<<<<< SEARCH\n"
                "def old_function():\n"
                "    pass\n"
                "=======\n"
                "def new_function():\n"
                "    print('Hello, World!')\n"
                ">>>>>>> REPLACE\n"
            ),
        ),
    ]

    def __init__(self, workspace_root: Optional[Path] = None):
        super().__init__()
        self._workspace_root = workspace_root

    @property
    def _guard(self) -> WorkspaceGuard:
        """Lazy workspace guard initialized from environment or default."""
        if self._workspace_root:
            # Ensure workspace root is absolute for reliable path joining
            root = self._workspace_root.expanduser()
            if not root.is_absolute():
                root = root.resolve()
            return WorkspaceGuard(root)
        ws_root = os.environ.get("WORKSPACE_ROOT", os.getcwd())
        return WorkspaceGuard(ws_root)

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize leading whitespace by converting tabs to spaces."""
        return "\n".join([self._normalize_line(line) for line in text.split("\n")])

    def _normalize_line(self, line: str) -> str:
        """Normalize leading whitespace in a single line."""
        leading_ws = len(line) - len(line.lstrip())
        return line.replace("\t", "    ", leading_ws)

    def parse_diff(self, diff: str) -> List[SearchReplaceBlock]:
        """Parse the diff string into a list of SearchReplaceBlock instances."""
        if not diff or not diff.strip():
            raise ValueError("Empty or invalid diff string provided")

        blocks: List[SearchReplaceBlock] = []
        lines = diff.splitlines()
        idx = 0

        while idx < len(lines):
            line = lines[idx].strip()
            if line == "<<<<<<< SEARCH":
                search_lines = []
                idx += 1

                while idx < len(lines) and lines[idx].strip() != "=======":
                    search_lines.append(lines[idx])
                    idx += 1

                if idx >= len(lines):
                    raise ValueError("Invalid diff format: Missing '=======' marker")

                replace_lines = []
                idx += 1

                while idx < len(lines) and lines[idx].strip() != ">>>>>>> REPLACE":
                    replace_lines.append(lines[idx])
                    idx += 1

                if idx >= len(lines):
                    raise ValueError("Invalid diff format: Missing '>>>>>>> REPLACE' marker")

                search_content = "\n".join(search_lines).rstrip()
                replace_content = "\n".join(replace_lines).rstrip()

                blocks.append(SearchReplaceBlock(search=search_content, replace=replace_content))

            idx += 1

        if not blocks:
            raise ValueError("No valid SEARCH/REPLACE blocks found in the diff")

        return blocks

    def _find_similar_match(self, search: str, content: str) -> Tuple[float, str]:
        """Finds the most similar substring in content compared to search with whitespace normalization."""
        norm_search = self._normalize_whitespace(search)
        norm_content = self._normalize_whitespace(content)
        content_lines = content.split("\n")
        norm_content_lines = norm_content.split("\n")

        if len(norm_content_lines) < len(norm_search.split("\n")):
            return 0.0, ""

        max_similarity = 0.0
        best_match = ""
        search_line_count = len(norm_search.split("\n"))

        for i in range(len(norm_content_lines) - search_line_count + 1):
            candidate_norm = "\n".join(norm_content_lines[i: i + search_line_count])
            similarity = difflib.SequenceMatcher(None, norm_search, candidate_norm).ratio()

            if similarity > max_similarity:
                max_similarity = similarity
                best_match = "\n".join(content_lines[i: i + search_line_count])

        return max_similarity, best_match

    def _is_overlapping(self, changes: List[Tuple[int, int]], start: int, end: int) -> bool:
        """Checks if the given range overlaps with any existing changes."""
        return any(not (end <= change_start or start >= change_end) for change_start, change_end in changes)

    def execute(self, path: str, diff: str) -> PendingChange:
        """Compute a SEARCH/REPLACE preview, returning PendingChange instead of writing.

        M6: This method never writes to disk. It returns a PendingChange with
        unified_diff computed for display.
        """
        # Validate path presence
        if not path or not path.strip():
            return PendingChange.make_error("", "File path cannot be empty")

        # Validate diff presence
        if not diff or not diff.strip():
            return PendingChange.make_error(path, "Diff content cannot be empty")

        # Validate workspace boundary
        try:
            resolved_path = self._guard.resolve_write_path(path)
        except Exception as e:
            return PendingChange.make_error(path, f"Workspace access denied: {e}")

        resolved_str = str(resolved_path)

        # Parse diff blocks
        try:
            blocks = self.parse_diff(diff)
        except ValueError as e:
            return PendingChange.make_error(resolved_str, str(e))

        # Read original file
        if not resolved_path.exists():
            return PendingChange.make_error(
                resolved_str,
                f"File not found: '{resolved_str}'",
            )

        try:
            original_content = resolved_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return PendingChange.make_error(resolved_str, f"File must be UTF-8 encoded: '{resolved_str}'")
        except Exception as e:
            return PendingChange.make_error(resolved_str, f"Failed to read file '{resolved_str}': {e}")

        # Apply blocks to content (preview only, no file write)
        content = original_content
        changes: List[Tuple[int, int]] = []
        last_similarity = 0.0

        for idx, block in enumerate(blocks, 1):
            if not block.search:
                if block.replace:
                    content += f"\n{block.replace}"
                continue

            match_found = False

            # Exact match
            if block.search in content:
                start = content.find(block.search)
                end = start + len(block.search)
                if not self._is_overlapping(changes, start, end):
                    if block.replace:
                        content = f"{content[:start]}{block.replace}{content[end:]}"
                    else:
                        content = f"{content[:start]}{content[end:]}"
                    changes.append((start, start + len(block.replace) if block.replace else start))
                    match_found = True

            # Similar match fallback
            if not match_found:
                similarity, matched_str = self._find_similar_match(block.search, content)
                last_similarity = similarity
                if similarity >= self.SIMILARITY_THRESHOLD and matched_str:
                    start = content.find(matched_str)
                    end = start + len(matched_str)
                    if not self._is_overlapping(changes, start, end):
                        block.similarity = similarity
                        if block.replace:
                            content = f"{content[:start]}{block.replace}{content[end:]}"
                        else:
                            content = f"{content[:start]}{content[end:]}"
                        changes.append((start, start + len(block.replace) if block.replace else start))
                        match_found = True

            if not match_found:
                sim_msg = f" Best similarity: {last_similarity:.1%}" if last_similarity > 0 else ""
                return PendingChange.make_error(
                    resolved_str,
                    f"No matching content found for block {idx}.{sim_msg}",
                )

        if content == original_content:
            return PendingChange.make_error(resolved_str, "No changes needed (content already matches)")

        # Return PendingChange with preview
        return PendingChange.make_update(
            path=resolved_str,
            original_content=original_content,
            proposed_content=content,
        )
