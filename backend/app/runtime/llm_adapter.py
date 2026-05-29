"""LLMAdapter — AgentHub runtime's LLM abstraction over the Provider layer.

M2 milestone: replaces the copied LLM stub path with a real implementation
that calls the AgentHub Provider layer (BaseProvider).

This is the only place in the runtime that should call Provider methods.
All other runtime code should go through LLMAdapter.

Not yet connected to ReactAgent (that's M3).
"""

from typing import AsyncIterator

from loguru import logger


class LLMAdapter:
    """Unified LLM interface for the AgentHub runtime.

    Wraps a BaseProvider and exposes a quantalogic-style async_generate_with_history()
    that matches the signature ReactAgent already calls.

    Usage::

        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.openai_compatible import QwenProvider

        provider = QwenProvider(settings)
        adapter = LLMAdapter(provider=provider)

        result = await adapter.async_generate_with_history(
            messages_history=[Message(role="user", content="hi")],
            model="qwen-plus",
        )
    """

    def __init__(
        self,
        provider,  # BaseProvider — type deferred to avoid circular dep
        default_temperature: float = 0.7,
    ) -> None:
        self.provider = provider
        self.default_temperature = default_temperature

    async def async_generate_with_history(
        self,
        messages_history: list,
        model: str,
        temperature: float | None = None,
        stop: list[str] | None = None,
    ):
        """Non-streaming completion with full conversation history.

        Args:
            messages_history: List of runtime Message objects (role + content).
            model: Model identifier passed to the Provider.
            temperature: Sampling temperature (defaults to self.default_temperature).
            stop: Stop words (passed through to Provider if supported).

        Returns:
            ResponseStats with text, model, usage, and finish_reason fields.
        """
        temp = temperature if temperature is not None else self.default_temperature
        logger.debug(
            f"LLMAdapter generating with {len(messages_history)} history messages, model={model}"
        )

        from app.providers.base import ProviderMessage, ProviderMessagesInput

        def _to_provider_message(msg) -> ProviderMessage:
            # Accept both Message objects and plain dicts.
            # LLMWrapper copies the list before appending, but Agent.memory.memory
            # can still contain legacy dict entries from other code paths.
            if isinstance(msg, dict):
                return ProviderMessage(role=msg["role"], content=str(msg.get("content", "")))
            return ProviderMessage(role=msg.role, content=str(msg.content))

        provider_messages = [_to_provider_message(msg) for msg in messages_history]

        provider_input = ProviderMessagesInput(
            messages=provider_messages,
            model=model,
        )

        provider_output = await self.provider.chat_with_messages(provider_input)

        from app.runtime.generative_model import ResponseStats, TokenUsage

        usage = None
        if provider_output.usage:
            usage = TokenUsage(
                prompt_tokens=provider_output.usage.prompt_tokens,
                completion_tokens=provider_output.usage.completion_tokens,
                total_tokens=provider_output.usage.total_tokens,
            )
        else:
            usage = TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)

        return ResponseStats(
            response=provider_output.text,
            usage=usage,
            model=model,
            finish_reason="stop",
        )

    async def async_stream_generate_with_history(
        self,
        messages_history: list,
        model: str,
        temperature: float | None = None,
        stop: list[str] | None = None,
    ) -> AsyncIterator[str]:
        """Streaming completion with full conversation history.

        Yields raw text deltas from the upstream provider.

        Args:
            messages_history: List of runtime Message objects (role + content).
            model: Model identifier passed to the Provider.
            temperature: Sampling temperature (defaults to self.default_temperature).
            stop: Stop words (passed through to Provider if supported).

        Yields:
            Raw text delta strings.
        """
        logger.debug(
            f"LLMAdapter streaming with {len(messages_history)} history messages, model={model}"
        )

        from app.providers.base import ProviderMessage, ProviderMessagesInput

        def _to_provider_message(msg) -> ProviderMessage:
            # Accept both Message objects and plain dicts.
            # LLMWrapper copies the list before appending, but Agent.memory.memory
            # can still contain legacy dict entries from other code paths.
            if isinstance(msg, dict):
                return ProviderMessage(role=msg["role"], content=str(msg.get("content", "")))
            return ProviderMessage(role=msg.role, content=str(msg.content))

        provider_messages = [_to_provider_message(msg) for msg in messages_history]

        provider_input = ProviderMessagesInput(
            messages=provider_messages,
            model=model,
        )

        async for event in self.provider.stream_chat_with_messages(provider_input):
            yield event.text_delta
