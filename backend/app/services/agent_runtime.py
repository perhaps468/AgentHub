"""Agent runtime - 业务编排层，桥接 Provider 和 Agent 注册表。

提供 get_provider() 工厂函数，按 provider 标识返回对应 Provider 实例。
"""

from app.core.config import get_settings
from app.providers.base import BaseProvider


_PROVIDER_REGISTRY = {
    "openai": "openai_compatible.OpenAIProvider",
    "qwen_openai_compatible": "openai_compatible.QwenProvider",
    "doubao": "doubao.DoubaoProvider",
    "glm": "glm.GlmProvider",
}


def _import_provider_class(provider_id: str) -> type[BaseProvider]:
    """Import and return the provider class for the given identifier."""
    if provider_id not in _PROVIDER_REGISTRY:
        known = ", ".join(sorted(_PROVIDER_REGISTRY.keys()))
        raise ValueError(f"Unknown provider: {provider_id!r}. Known providers: {known}")

    module_name, class_name = _PROVIDER_REGISTRY[provider_id].rsplit(".", 1)
    module_path = f"app.providers.{module_name}"
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_provider(provider_id: str, model: str | None = None) -> BaseProvider:
    """Get a Provider instance for the given provider identifier.

    Args:
        provider_id: Provider identifier (e.g. "qwen_openai_compatible", "doubao").
        model: Optional model override. If None, uses the default from settings.

    Returns:
        A BaseProvider instance configured for the given provider.

    Raises:
        ValueError: If the provider identifier is unknown.
    """
    settings = get_settings()
    provider_cls = _import_provider_class(provider_id)
    provider = provider_cls(settings)
    if model is not None:
        provider._model = model
    return provider


def resolve_agent_config(agent) -> tuple[str, str]:
    """Resolve provider_id and model from an Agent record.

    Args:
        agent: Agent ORM object with provider and model attributes.

    Returns:
        Tuple of (provider_id, model).
    """
    provider_id = getattr(agent, "provider", None) or "qwen_openai_compatible"
    model = getattr(agent, "model", None) or "qwen-plus"
    return provider_id, model


def get_provider_for_agent(agent) -> BaseProvider:
    """Create a Provider instance from an Agent's configuration.

    This is the primary entry point for runtime to obtain the correct
    provider for a given Agent.

    Args:
        agent: Agent ORM object with provider and model attributes.

    Returns:
        A BaseProvider instance configured per the agent.
    """
    provider_id, model = resolve_agent_config(agent)
    return get_provider(provider_id, model=model)
