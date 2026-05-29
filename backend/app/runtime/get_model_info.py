"""Minimal model info stub for AgentHub runtime.

C 类文件，不复制 quantalogic 原版 get_model_info / model_info 相关链路。
这些服务于 LiteLLM / 模型元信息，不应原样迁入。
后续改造阶段由 02-implementation-guide.md 决定从 AgentHub Provider 层获取模型元信息。
"""


def get_max_tokens(model: str) -> int:
    """Stub: returns default max tokens. Real value from AgentHub Provider in 改造阶段."""
    return 4096


def get_max_input_tokens(model: str) -> int | None:
    """Stub: returns default input tokens. Real value from AgentHub Provider in 改造阶段."""
    return 128 * 1024


def get_max_output_tokens(model: str) -> int | None:
    """Stub: returns default output tokens. Real value from AgentHub Provider in 改造阶段."""
    return 4096
