"""Minimal LiteLLM adapter stub for AgentHub runtime.

C 类文件，不复制 quantalogic 原版 quantlitellm（LiteLLM 直连模型层）。
后续改造阶段由 02-implementation-guide.md 决定：
- 应使用 AgentHub Provider/LLMAdapter 替换
- 不应继续作为 Runtime 直连入口
此处 stub 仅保证 generative_model.py import 不断裂，不提供实际 LLM 调用。
"""

from typing import Any, AsyncGenerator, Dict, List

# Minimal exception types that generative_model.py references
class RateLimitError(Exception): pass
class APIConnectionError(Exception): pass
class ServiceUnavailableError(Exception): pass
class Timeout(Exception): pass
class APIError(Exception): pass
class ContextWindowExceededError(Exception): pass
class InvalidRequestError(Exception): pass
class ContentPolicyViolationError(Exception): pass
class AuthenticationError(Exception): pass
class PermissionDeniedError(Exception): pass


async def acompletion(model: str, messages: List[Dict], **kwargs) -> Any:
    """Stub: raises NotImplementedError. Replaced by AgentHub Provider layer in改造阶段."""
    raise NotImplementedError(
        "acompletion is a stub. Replace with AgentHub Provider/LLMAdapter in 改造阶段."
    )


async def aimage_generation(model: str, **kwargs) -> Any:
    """Stub: raises NotImplementedError. Replaced by AgentHub Provider layer in改造阶段."""
    raise NotImplementedError(
        "aimage_generation is a stub. Replace with AgentHub Provider/LLMAdapter in 改造阶段."
    )


def token_counter(model: str, messages: List[Dict], **kwargs) -> int:
    """Stub: returns 0 token count. Real counting via AgentHub Provider in 改造阶段."""
    total_chars = sum(len(m.get("content", "")) for m in messages)
    return total_chars // 4  # rough approximation
