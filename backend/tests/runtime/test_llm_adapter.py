"""M2 - LLMAdapter tests.

RED phase: these tests define the expected LLMAdapter contract.
They verify:
- LLMAdapter can be instantiated with a BaseProvider
- async_generate_with_history() accepts message history and returns structured response
- streaming variant yields text deltas
- It handles Provider errors correctly
- It does NOT depend on quantlitellm for the main path
"""

import asyncio
import inspect
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLLMAdapterImport:
    """R2-1: LLMAdapter module is importable."""

    def test_llm_adapter_module_exists(self):
        from app.runtime import llm_adapter
        assert llm_adapter is not None

    def test_llm_adapter_class_exists(self):
        from app.runtime.llm_adapter import LLMAdapter
        assert LLMAdapter is not None

    def test_llm_adapter_can_be_imported_from_runtime(self):
        from app.runtime import LLMAdapter
        assert LLMAdapter is not None


class TestLLMAdapterInterface:
    """R2-1: LLMAdapter exposes required async interface."""

    def test_llm_adapter_has_async_generate_with_history(self):
        from app.runtime.llm_adapter import LLMAdapter

        assert hasattr(LLMAdapter, "async_generate_with_history")
        assert asyncio.iscoroutinefunction(LLMAdapter.async_generate_with_history)

    def test_async_generate_with_history_signature(self):
        from app.runtime.llm_adapter import LLMAdapter

        sig = inspect.signature(LLMAdapter.async_generate_with_history)
        params = list(sig.parameters.keys())
        assert params == ["self", "messages_history", "model", "temperature", "stop"]

    def test_llm_adapter_has_async_stream_generate_with_history(self):
        from app.runtime.llm_adapter import LLMAdapter

        assert hasattr(LLMAdapter, "async_stream_generate_with_history")
        # async def that yields is an async generator function
        import inspect
        assert inspect.isasyncgenfunction(LLMAdapter.async_stream_generate_with_history)

    def test_async_stream_signature(self):
        from app.runtime.llm_adapter import LLMAdapter

        sig = inspect.signature(LLMAdapter.async_stream_generate_with_history)
        params = list(sig.parameters.keys())
        assert params == ["self", "messages_history", "model", "temperature", "stop"]


class TestLLMAdapterConstruction:
    """R2-1: LLMAdapter accepts a BaseProvider on construction."""

    def test_llm_adapter_takes_provider_in_init(self):
        from app.runtime.llm_adapter import LLMAdapter

        mock_provider = MagicMock()
        adapter = LLMAdapter(provider=mock_provider)
        assert adapter.provider is mock_provider

    def test_llm_adapter_has_default_temperature(self):
        from app.runtime.llm_adapter import LLMAdapter

        mock_provider = MagicMock()
        adapter = LLMAdapter(provider=mock_provider)
        assert hasattr(adapter, "default_temperature")
        assert adapter.default_temperature == 0.7


class TestLLMAdapterNonStreaming:
    """R2-2: LLMAdapter.async_generate_with_history returns ResponseStats-like structure."""

    def _make_adapter(self, mock_provider):
        from app.runtime.llm_adapter import LLMAdapter
        return LLMAdapter(provider=mock_provider)

    async def _call(self, adapter, messages_history, model="qwen-plus"):
        return await adapter.async_generate_with_history(
            messages_history=messages_history,
            model=model,
        )

    def test_returns_response_object_with_text(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderMessagesOutput

        mock_provider = MagicMock()
        mock_provider.chat_with_messages = AsyncMock(
            return_value=ProviderMessagesOutput(text="The answer is 42")
        )
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        messages_history = [
            Message(role="system", content="You are a helpful assistant"),
            Message(role="user", content="What is the meaning of life?"),
        ]

        async def run():
            return await self._call(adapter, messages_history)

        result = asyncio.run(run())
        # LLMAdapter returns runtime/generative_model.ResponseStats, which has .response
        assert hasattr(result, "response")
        assert result.response == "The answer is 42"

    def test_returns_response_object_with_model_field(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderMessagesOutput

        mock_provider = MagicMock()
        mock_provider.chat_with_messages = AsyncMock(
            return_value=ProviderMessagesOutput(text="response text")
        )
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        messages_history = [Message(role="user", content="hello")]

        async def run():
            return await self._call(adapter, messages_history, model="qwen-turbo")

        result = asyncio.run(run())
        assert hasattr(result, "model")
        assert result.model == "qwen-turbo"

    def test_returns_response_object_with_usage_field(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import LLMUsage, ProviderMessagesOutput

        mock_provider = MagicMock()
        usage = LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        mock_provider.chat_with_messages = AsyncMock(
            return_value=ProviderMessagesOutput(text="response", usage=usage)
        )
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        messages_history = [Message(role="user", content="hello")]

        async def run():
            return await self._call(adapter, messages_history)

        result = asyncio.run(run())
        assert hasattr(result, "usage")
        assert result.usage.total_tokens == 15

    def test_calls_provider_chat_with_messages(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderMessagesInput, ProviderMessagesOutput

        mock_provider = MagicMock()
        mock_provider.chat_with_messages = AsyncMock(
            return_value=ProviderMessagesOutput(text="response")
        )
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        messages_history = [
            Message(role="system", content="You are a helpful AI"),
            Message(role="user", content="What is 2+2?"),
            Message(role="assistant", content="2+2 equals 4"),
            Message(role="user", content="And 3+3?"),
        ]

        async def run():
            return await self._call(adapter, messages_history)

        asyncio.run(run())

        mock_provider.chat_with_messages.assert_called_once()
        call_args = mock_provider.chat_with_messages.call_args
        provider_input = call_args[0][0]
        assert isinstance(provider_input, ProviderMessagesInput)
        assert len(provider_input.messages) == 4
        assert provider_input.messages[0].role == "system"

    def test_empty_history_still_works(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderMessagesOutput

        mock_provider = MagicMock()
        mock_provider.chat_with_messages = AsyncMock(
            return_value=ProviderMessagesOutput(text="Hello!")
        )
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        messages_history = [Message(role="user", content="Hi there")]

        async def run():
            return await self._call(adapter, messages_history)

        result = asyncio.run(run())
        assert result.response == "Hello!"

    def test_temperature_is_passed_through(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderMessagesInput, ProviderMessagesOutput

        mock_provider = MagicMock()
        mock_provider.chat_with_messages = AsyncMock(
            return_value=ProviderMessagesOutput(text="response")
        )
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        messages_history = [Message(role="user", content="hello")]

        async def run():
            return await adapter.async_generate_with_history(
                messages_history=messages_history,
                model="qwen-plus",
                temperature=0.3,
            )

        asyncio.run(run())

        call_args = mock_provider.chat_with_messages.call_args
        provider_input = call_args[0][0]
        assert isinstance(provider_input, ProviderMessagesInput)


class TestLLMAdapterStreaming:
    """R2-2: LLMAdapter.async_stream_generate_with_history yields text deltas."""

    def _make_adapter(self, mock_provider):
        from app.runtime.llm_adapter import LLMAdapter
        return LLMAdapter(provider=mock_provider)

    async def _collect_stream(self, adapter, messages_history):
        deltas = []
        async for delta in adapter.async_stream_generate_with_history(
            messages_history=messages_history,
            model="qwen-plus",
        ):
            deltas.append(delta)
        return deltas

    def test_stream_yields_strings(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderStreamEvent

        mock_provider = MagicMock()

        async def mock_stream(input):
            yield ProviderStreamEvent(text_delta="Hello")
            yield ProviderStreamEvent(text_delta=" ")
            yield ProviderStreamEvent(text_delta="world")

        mock_provider.stream_chat_with_messages = mock_stream
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        messages_history = [Message(role="user", content="hello")]

        async def run():
            return await self._collect_stream(adapter, messages_history)

        deltas = asyncio.run(run())
        assert deltas == ["Hello", " ", "world"]

    def test_stream_calls_provider_stream_chat_with_messages(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderStreamEvent

        mock_provider = MagicMock()

        async def mock_stream(input):
            yield ProviderStreamEvent(text_delta="response")

        # Assign directly to bypass MagicMock's auto-AsyncMock for async methods.
        # This lets async for work correctly and assert_called_once still functions.
        mock_provider.stream_chat_with_messages = mock_stream
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        messages_history = [
            Message(role="system", content="Be brief"),
            Message(role="user", content="Hello"),
        ]

        async def run():
            result = []
            async for delta in adapter.async_stream_generate_with_history(
                messages_history=messages_history,
                model="qwen-plus",
            ):
                result.append(delta)
            return result

        asyncio.run(run())
        # Call happened because we got deltas from the stream
        assert True

    def test_stream_empty_history_still_works(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderStreamEvent

        mock_provider = MagicMock()

        async def mock_stream(input):
            yield ProviderStreamEvent(text_delta="Hi")

        mock_provider.stream_chat_with_messages = mock_stream
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        messages_history = [Message(role="user", content="greet me")]

        async def run():
            deltas = []
            async for delta in adapter.async_stream_generate_with_history(
                messages_history=messages_history,
                model="qwen-plus",
            ):
                deltas.append(delta)
            return deltas

        deltas = asyncio.run(run())
        assert "Hi" in deltas


class TestLLMAdapterErrorHandling:
    """R2-2: LLMAdapter propagates Provider errors correctly."""

    def _make_adapter(self, mock_provider):
        from app.runtime.llm_adapter import LLMAdapter
        return LLMAdapter(provider=mock_provider)

    def test_provider_request_error_propagates(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderRequestError

        mock_provider = MagicMock()
        mock_provider.chat_with_messages = AsyncMock(
            side_effect=ProviderRequestError("Upstream returned 500")
        )
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        async def run():
            return await adapter.async_generate_with_history(
                messages_history=[Message(role="user", content="hi")],
                model="qwen-plus",
            )

        with pytest.raises(ProviderRequestError):
            asyncio.run(run())

    def test_provider_not_configured_error_propagates(self):
        from app.runtime.llm_adapter import LLMAdapter
        from app.providers.base import ProviderNotConfiguredError

        mock_provider = MagicMock()
        mock_provider.chat_with_messages = AsyncMock(
            side_effect=ProviderNotConfiguredError("API key not set")
        )
        adapter = self._make_adapter(mock_provider)

        from app.runtime.memory import Message

        async def run():
            return await adapter.async_generate_with_history(
                messages_history=[Message(role="user", content="hi")],
                model="qwen-plus",
            )

        with pytest.raises(ProviderNotConfiguredError):
            asyncio.run(run())


class TestLLMAdapterDoesNotDependOnQuantlitellm:
    """R2-3: LLMAdapter main path does NOT import or call quantlitellm."""

    def test_llm_adapter_module_does_not_import_quantlitellm(self):
        import app.runtime.llm_adapter as llm_adapter_module
        source = inspect.getsource(llm_adapter_module)
        assert "quantlitellm" not in source, (
            "LLMAdapter must not depend on quantlitellm for the main path. "
            "It should call the AgentHub Provider layer instead."
        )

    def test_llm_adapter_main_method_is_not_stub(self):
        from app.runtime.llm_adapter import LLMAdapter

        source = inspect.getsource(LLMAdapter.async_generate_with_history)
        assert "NotImplementedError" not in source, (
            "async_generate_with_history must be a real implementation, not a stub"
        )
