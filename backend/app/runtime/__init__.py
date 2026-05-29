"""Runtime package for AgentHub - migrated from quantalogic_react."""

from app.runtime.memory import AgentMemory, Message, VariableMemory
from app.runtime.prompts import system_prompt
from app.runtime.quantlitellm import (
    ContentPolicyViolationError,
    ContextWindowExceededError,
    InvalidRequestError,
    RateLimitError,
    ServiceUnavailableError,
)
from app.runtime.react_agent import Agent
from app.runtime.tool_manager import ToolManager
from app.runtime.version import get_version

try:
    from app.runtime.llm_adapter import LLMAdapter
except ImportError:
    # llm_adapter.py not yet available (M2 not yet executed)
    LLMAdapter = None

__version__ = get_version()

__all__ = [
    "Agent",
    "AgentMemory",
    "LLMAdapter",
    "Message",
    "VariableMemory",
    "ToolManager",
    "system_prompt",
    "get_version",
    "RateLimitError",
    "ContextWindowExceededError",
    "ContentPolicyViolationError",
    "InvalidRequestError",
    "ServiceUnavailableError",
]
