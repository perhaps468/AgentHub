# -*- coding: utf-8 -*-
"""ApplyChangeTool: formally applies a PendingChange by its change_id.

T3: This tool provides the controlled apply path for the M6 preview->apply chain.
- The agent calls write_file / replace_in_file which returns PendingChange (PREVIEW)
- The agent can then call apply_change with the change_id to commit
- ApplyChangeTool looks up the PendingChange in its registry and calls apply()
- The change transitions from PREVIEW -> APPLIED (or REJECTED on failure)

This decouples apply from the write tools, ensuring:
- Write tools only preview (never directly write)
- Apply is an explicit, separate agent action
- External file modification is detected and rejected
"""

from pathlib import Path
from typing import Optional

from app.runtime.pending_change import ChangeStatus, PendingChange
from app.runtime.tools.tool import Tool, ToolArgument

# Module-level registry shared by all ApplyChangeTool instances
# C-2: Use module-level dict instead of class attribute to avoid Pydantic v2 issues
_PENDING_CHANGE_REGISTRY: dict[str, PendingChange] = {}


class ApplyChangeTool(Tool):
    """Tool to formally apply a previously previewed PendingChange.

    T3: This is the controlled apply entry point. The agent receives
    a PendingChange (with unified_diff for display) from write_file or
    replace_in_file. To commit the change, the agent calls this tool
    with the same change_id.

    The tool:
    1. Looks up the PendingChange by change_id in the registry
    2. Calls PendingChange.apply() (which checks for external modification)
    3. Returns a structured result
    4. Removes the change from the registry after apply
    """

    name: str = "apply_change"
    description: str = (
        "Formally applies a PendingChange that was previously returned by "
        "write_file or replace_in_file. The agent must call this tool with "
        "the same change_id to commit the change. "
        "If the file was modified externally since preview, the apply is rejected."
    )
    need_validation: bool = False

    _workspace_root: Optional["Path"] = None

    arguments: list[ToolArgument] = [
        ToolArgument(
            name="change_id",
            arg_type="string",
            description="The change_id from the PendingChange returned by write_file or replace_in_file.",
            required=True,
            example="abc12345",
        ),
    ]

    def __init__(self, workspace_root: Optional[Path] = None):
        super().__init__()
        self._workspace_root = workspace_root

    @classmethod
    def register_change(cls, pending_change: PendingChange) -> str:
        """Register a PendingChange so it can be applied later by change_id.

        This is called by RuntimeAgentService when a write tool returns a
        PendingChange, to make it available for apply.

        Returns:
            The change_id of the registered change.
        """
        _PENDING_CHANGE_REGISTRY[pending_change.change_id] = pending_change
        return pending_change.change_id

    @classmethod
    def get_change(cls, change_id: str) -> Optional[PendingChange]:
        """Retrieve a registered PendingChange by its change_id."""
        return _PENDING_CHANGE_REGISTRY.get(change_id)

    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered pending changes. Used for testing."""
        _PENDING_CHANGE_REGISTRY.clear()

    @classmethod
    def clear_change(cls, change_id: str) -> bool:
        """Remove a specific pending change from the registry.

        Called after successful apply to clean up the registry.

        Args:
            change_id: The change_id to remove.

        Returns:
            True if the change was removed, False if not found.
        """
        if change_id in _PENDING_CHANGE_REGISTRY:
            del _PENDING_CHANGE_REGISTRY[change_id]
            return True
        return False

    def execute(self, change_id: str) -> str:
        """Apply a pending change by its change_id.

        T3: This is the formal apply entry point. It:
        - Looks up the PendingChange in the registry
        - Calls apply() which verifies the file hasn't changed
        - Transitions the status from PREVIEW to APPLIED or REJECTED
        - Returns a human-readable result string

        Returns:
            A result string describing what happened.
        """
        if not change_id or not change_id.strip():
            return "[Error] change_id cannot be empty."

        pending = _PENDING_CHANGE_REGISTRY.get(change_id)
        if pending is None:
            return f"[Error] No pending change found with change_id='{change_id}'. The change may have already been applied or the ID is invalid."

        if pending.status == ChangeStatus.APPLIED:
            return f"[Error] Change '{change_id}' has already been applied."

        if pending.status == ChangeStatus.REJECTED:
            return f"[Error] Change '{change_id}' was previously rejected."

        # Attempt to apply the change
        success = pending.apply()

        if success:
            # Remove from registry after successful apply
            del _PENDING_CHANGE_REGISTRY[change_id]
            return (
                f"[Applied] {pending.operation.value.upper()} {pending.path} "
                f"(change_id={change_id}).\n"
                f"Change successfully written to disk.\n"
                f"NEXT: If the task is complete, call task_complete with your final answer."
            )
        else:
            # Transition to REJECTED status
            pending.status = ChangeStatus.REJECTED
            return (
                f"[Rejected] Apply failed for change_id='{change_id}'. "
                f"Reason: {pending.error}. "
                f"The file may have been modified after preview."
            )
