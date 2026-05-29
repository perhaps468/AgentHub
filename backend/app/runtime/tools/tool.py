"""Minimal Tool abstract for AgentHub runtime.

C 类文件，不复制 quantalogic 原版 tool.py（它只是 quantalogic_toolbox.tool 的 re-export），
在 AgentHub 内建立独立 Tool/ToolArgument 抽象。
此处 stub 保证 A/B 类文件 import 不断裂，后续改造阶段由 02-implementation-guide.md 决定实际抽象。
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolArgument(BaseModel):
    """Represents a tool argument definition."""

    name: str
    arg_type: str = "string"
    description: str = ""
    required: bool = False
    default: Optional[str] = None
    example: Optional[str] = None


class Tool(BaseModel):
    """Minimal Tool abstract stub."""

    name: str = "unnamed_tool"
    description: str = ""
    arguments: list = Field(default_factory=list)
    need_validation: bool = False
    need_variables: bool = False
    need_caller_context_memory: bool = False
    need_post_process: bool = False

    model_config = {"extra": "allow"}

    def model_post_init(self, __context) -> None:
        """Pydantic v2 lifecycle hook — subclasses can override to set dynamic runtime fields.

        Use object.__setattr__(self, name, value) to set fields that are not part
        of the Pydantic model schema. This avoids 'extra field not allowed' errors.
        """
        pass

    def to_markdown(self) -> str:
        """Convert tool to markdown description."""
        lines = [self.description, "\n**Parameters:**"]
        for arg in self.arguments:
            # T6: exclude internal injectable parameters from model-visible schema
            if self._is_internal_injectable(arg):
                continue
            req = "(required)" if arg.required else "(optional)"
            default = f" default: `{arg.default}`" if arg.default else ""
            lines.append(f"- `{arg.name}` ({arg.arg_type}) {req}{default}: {arg.description}")
        return "\n".join(lines)

    def get_non_injectable_arguments(self) -> list:
        """Get arguments that are not injected at runtime."""
        return [arg for arg in self.arguments if not self._is_injectable(arg) and not self._is_internal_injectable(arg)]

    def _is_injectable(self, arg: ToolArgument) -> bool:
        return arg.name in ("variables", "caller_context_memory")

    def _is_internal_injectable(self, arg: ToolArgument) -> bool:
        """T6: workspace_root is injected internally by the runtime, not by the model."""
        return arg.name == "workspace_root"

    def get_injectable_properties_in_execution(self) -> dict:
        """Override in subclasses to provide internal injectable values (e.g. workspace_root)."""
        return {}

    def execute(self, **kwargs) -> str:
        raise NotImplementedError(f"Tool {self.name} does not implement execute()")

    def async_execute(self, **kwargs) -> str:
        return self.execute(**kwargs)
