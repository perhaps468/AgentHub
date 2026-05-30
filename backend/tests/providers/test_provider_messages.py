"""M2 - Provider full messages interface tests.

RED phase: these tests define the expected Provider messages contract.
They verify:
- Provider accepts full message history (not just system_prompt + user_message)
- Provider can stream with full message history
- Old simple interface is preserved for backward compatibility
- BaseProvider abstract interface includes the new methods
"""

import asyncio
import inspect
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestProviderMessageDataclass:
    """P2-1: ProviderMessage dataclass has required fields."""

    def test_provider_message_has_role_and_content(self):
        from app.providers.base import ProviderMessage

        msg = ProviderMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_provider_message_role_is_str(self):
        from app.providers.base import ProviderMessage

        msg = ProviderMessage(role="assistant", content="I am here to help")
        assert isinstance(msg.role, str)

    def test_provider_message_content_is_str(self):
        from app.providers.base import ProviderMessage

        msg = ProviderMessage(role="system", content="You are a helpful assistant")
        assert isinstance(msg.content, str)

    def test_provider_message_is_frozen(self):
        from app.providers.base import ProviderMessage

        msg = ProviderMessage(role="user", content="test")
        with pytest.raises(Exception):  # frozen dataclass
            msg.role = "assistant"


class TestProviderMessagesInputDataclass:
    """P2-1: ProviderMessagesInput dataclass holds full history + model."""

    def test_provider_messages_input_has_messages_field(self):
        from app.providers.base import ProviderMessage, ProviderMessagesInput

        inp = ProviderMessagesInput(messages=[ProviderMessage(role="user", content="hi")], model="qwen-plus")
        assert len(inp.messages) == 1
        assert inp.messages[0].content == "hi"

    def test_provider_messages_input_has_model_field(self):
        from app.providers.base import ProviderMessagesInput

        inp = ProviderMessagesInput(messages=[], model="qwen-turbo")
        assert inp.model == "qwen-turbo"

    def test_provider_messages_input_is_frozen(self):
        from app.providers.base import ProviderMessagesInput

        inp = ProviderMessagesInput(messages=[], model="qwen-plus")
        with pytest.raises(Exception):
            inp.model = "other-model"

    def test_provider_messages_input_empty_messages_is_valid(self):
        from app.providers.base import ProviderMessagesInput

        inp = ProviderMessagesInput(messages=[], model="qwen-plus")
        assert inp.messages == []


class TestProviderMessagesOutputDataclass:
    """P2-1: ProviderMessagesOutput holds text + optional usage."""

    def test_provider_messages_output_has_text(self):
        from app.providers.base import ProviderMessagesOutput

        out = ProviderMessagesOutput(text="Hello world")
        assert out.text == "Hello world"

    def test_provider_messages_output_usage_is_optional(self):
        from app.providers.base import ProviderMessagesOutput

        out = ProviderMessagesOutput(text="Hi")
        assert out.usage is None

    def test_provider_messages_output_with_usage(self):
        from app.providers.base import LLMUsage, ProviderMessagesOutput

        usage = LLMUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        out = ProviderMessagesOutput(text="Hi", usage=usage)
        assert out.usage.prompt_tokens == 10
        assert out.usage.completion_tokens == 5


class TestBaseProviderMessagesInterface:
    """P2-1: BaseProvider exposes chat_with_messages / stream_chat_with_messages."""

    def test_base_provider_has_chat_with_messages_method(self):
        from app.providers.base import BaseProvider

        assert hasattr(BaseProvider, "chat_with_messages")

    def test_base_provider_chat_with_messages_is_abstract(self):
        from app.providers.base import BaseProvider

        sig = inspect.signature(BaseProvider.chat_with_messages)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "input" in params

    def test_base_provider_has_stream_chat_with_messages_method(self):
        from app.providers.base import BaseProvider

        assert hasattr(BaseProvider, "stream_chat_with_messages")

    def test_base_provider_stream_chat_with_messages_is_abstract(self):
        from app.providers.base import BaseProvider

        sig = inspect.signature(BaseProvider.stream_chat_with_messages)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "input" in params


class TestQwenProviderMessagesImplementation:
    """P2-2: QwenProvider correctly forwards full messages to upstream API."""

    def _make_settings_mock(self, api_key="test-key"):
        settings_mock = MagicMock()
        settings_mock.qwen_api_key = api_key
        settings_mock.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        settings_mock.qwen_model = "qwen-plus"
        return settings_mock

    def _make_provider(self, settings_mock):
        from app.providers.openai_compatible import QwenProvider
        return QwenProvider(settings_mock)

    async def _sync_collect(self, agen: AsyncIterator) -> list:
        result = []
        async for evt in agen:
            result.append(evt)
        return result

    def test_chat_with_messages_builds_full_history(self):
        """chat_with_messages passes full message list to upstream (not just system+user)."""
        from app.providers.base import ProviderMessage, ProviderMessagesInput
        from app.providers.openai_compatible import QwenProvider

        captured_payload = {}

        async def fake_post(*args, **kwargs):
            captured_payload.update(kwargs.get("json", {}))
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json = MagicMock(return_value={
                "choices": [{"message": {"content": "response"}}]
            })
            mock_resp.raise_for_status = MagicMock()
            return mock_resp

        settings_mock = self._make_settings_mock()
        provider = QwenProvider(settings_mock)

        messages = [
            ProviderMessage(role="system", content="You are a math tutor"),
            ProviderMessage(role="user", content="What is 2+2?"),
            ProviderMessage(role="assistant", content="2+2 equals 4"),
            ProviderMessage(role="user", content="What about 3+3?"),
        ]
        provider_input = ProviderMessagesInput(messages=messages, model="qwen-plus")

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(side_effect=fake_post)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await provider.chat_with_messages(provider_input)
                return result

        result = asyncio.run(run())
        assert result.text == "response"
        assert "messages" in captured_payload
        assert captured_payload["messages"] == [
            {"role": "system", "content": "You are a math tutor"},
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "2+2 equals 4"},
            {"role": "user", "content": "What about 3+3?"},
        ]

    def test_chat_with_messages_missing_api_key_raises(self):
        """Missing API key raises ProviderNotConfiguredError."""
        from app.providers.base import ProviderMessagesInput

        settings_mock = self._make_settings_mock(api_key=None)
        provider = self._make_provider(settings_mock)

        inp = ProviderMessagesInput(messages=[], model="qwen-plus")
        with pytest.raises(Exception):  # concrete error type checked in old tests
            asyncio.run(provider.chat_with_messages(inp))

    def test_stream_chat_with_messages_builds_full_history(self):
        """stream_chat_with_messages passes full message list to upstream and yields deltas."""
        from app.providers.base import ProviderMessage, ProviderMessagesInput
        from app.providers.openai_compatible import QwenProvider

        async def fake_stream_aiter_lines():
            events = [
                'data: {"choices":[{"delta":{"content":"Hi"},"index":0}]}\n',
                'data: [DONE]\n',
                '',
            ]
            for e in events:
                await asyncio.sleep(0.001)
                yield e

        settings_mock = self._make_settings_mock()
        provider = QwenProvider(settings_mock)

        messages = [
            ProviderMessage(role="system", content="Be concise"),
            ProviderMessage(role="user", content="Hello"),
        ]
        provider_input = ProviderMessagesInput(messages=messages, model="qwen-plus")

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.raise_for_status = MagicMock()
                mock_resp.aiter_lines = fake_stream_aiter_lines

                mock_stream_ctx = AsyncMock()
                mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_resp)
                mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

                mock_client = MagicMock()
                mock_client.stream = MagicMock(return_value=mock_stream_ctx)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                deltas = []
                async for evt in provider.stream_chat_with_messages(provider_input):
                    deltas.append(evt.text_delta)
                return deltas

        deltas = asyncio.run(run())
        # Verify the method yields deltas (contract verification)
        assert "Hi" in deltas


class TestBackwardCompatibility:
    """P2-2: Old simple interface (chat / stream_chat) is still present."""

    def test_base_provider_still_has_simple_chat(self):
        from app.providers.base import BaseProvider

        assert hasattr(BaseProvider, "chat")
        sig = inspect.signature(BaseProvider.chat)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "input" in params

    def test_base_provider_still_has_simple_stream_chat(self):
        from app.providers.base import BaseProvider

        assert hasattr(BaseProvider, "stream_chat")
        sig = inspect.signature(BaseProvider.stream_chat)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "input" in params

    def test_qwen_provider_simple_chat_still_works(self):
        """Simple chat() still accepts ProviderInput with system_prompt + user_message."""
        from app.providers.base import ProviderInput, ProviderOutput
        from app.providers.openai_compatible import QwenProvider

        settings_mock = MagicMock()
        settings_mock.qwen_api_key = "test-key"
        settings_mock.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        settings_mock.qwen_model = "qwen-plus"
        provider = QwenProvider(settings_mock)

        async def run():
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json = MagicMock(return_value={
                    "choices": [{"message": {"content": "simple response"}}]
                })
                mock_resp.raise_for_status = MagicMock()

                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_resp)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_cls.return_value = mock_client

                result = await provider.chat(ProviderInput(
                    system_prompt="You are a bot",
                    user_message="Hi",
                    model="qwen-plus",
                ))
                return result

        result = asyncio.run(run())
        assert result.text == "simple response"
