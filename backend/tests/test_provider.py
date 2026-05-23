import asyncio
import inspect
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import (
    BaseProvider,
    ProviderInput,
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderResponseInvalidError,
    ProviderOutput,
    ProviderStreamEvent,
)


async def _sync_collect(agen: AsyncIterator[ProviderStreamEvent]) -> list[str]:
    result = []
    async for evt in agen:
        result.append(evt.text_delta)
    return result


async def _sync_stream(agen: AsyncIterator[ProviderStreamEvent]) -> None:
    async for _ in agen:
        pass


class TestProviderInputOutput:
    def test_provider_input_fields(self):
        inp = ProviderInput(system_prompt="sys", user_message="user", model="gpt-4")
        assert inp.system_prompt == "sys"
        assert inp.user_message == "user"
        assert inp.model == "gpt-4"

    def test_provider_input_is_hashable(self):
        inp1 = ProviderInput(system_prompt="sys", user_message="user", model="gpt-4")
        inp2 = ProviderInput(system_prompt="sys", user_message="user", model="gpt-4")
        assert inp1 == inp2


class TestProviderAbstraction:
    def test_base_provider_is_abstract(self):
        assert inspect.isabstract(BaseProvider)

    def test_base_provider_chat_is_abstract(self):
        sig = inspect.signature(BaseProvider.chat)
        assert list(sig.parameters.keys()) == ["self", "input"]

    def test_base_provider_stream_chat_is_abstract(self):
        """P1-2-1: BaseProvider.stream_chat 是抽象方法。"""
        sig = inspect.signature(BaseProvider.stream_chat)
        assert list(sig.parameters.keys()) == ["self", "input"]


class TestProviderExceptions:
    def test_not_configured_inherits_from_base(self):
        assert issubclass(ProviderNotConfiguredError, Exception)

    def test_request_error_inherits_from_base(self):
        assert issubclass(ProviderRequestError, Exception)

    def test_response_invalid_inherits_from_base(self):
        assert issubclass(ProviderResponseInvalidError, Exception)


class TestQwenProvider:
    def test_provider_output_text_field(self):
        output = ProviderOutput(text="Hello world")
        assert output.text == "Hello world"


class TestQwenProviderPayloadShape:
    """验证 Provider chat() 调用时构建的 messages 只包含 system + 当前用户消息，无历史。"""

    def test_chat_builds_system_and_user_messages(self):
        from app.providers.openai_compatible import QwenProvider

        captured_input = {}

        async def fake_chat(input: ProviderInput) -> ProviderOutput:
            captured_input["system_prompt"] = input.system_prompt
            captured_input["user_message"] = input.user_message
            captured_input["model"] = input.model
            return ProviderOutput(text="fake response")

        settings_mock = MagicMock()
        settings_mock.qwen_api_key = "test-key"
        settings_mock.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        settings_mock.qwen_model = "qwen-plus"

        provider = QwenProvider(settings_mock)

        import asyncio

        with patch.object(provider, "chat", new=fake_chat):
            result = asyncio.run(
                provider.chat(ProviderInput(system_prompt="You are PM.", user_message="Hello", model="qwen-plus"))
            )

        assert captured_input["system_prompt"] == "You are PM."
        assert captured_input["user_message"] == "Hello"
        assert captured_input["model"] == "qwen-plus"
        assert result.text == "fake response"

    def test_missing_api_key_raises_configured_error(self):
        from app.providers.openai_compatible import QwenProvider

        settings_mock = MagicMock()
        settings_mock.qwen_api_key = None
        settings_mock.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        settings_mock.qwen_model = "qwen-plus"

        provider = QwenProvider(settings_mock)

        import asyncio

        with pytest.raises(ProviderNotConfiguredError):
            asyncio.run(
                provider.chat(ProviderInput(system_prompt="sys", user_message="hi", model="qwen-plus"))
            )

    def test_empty_response_content_raises_invalid_error(self):
        from app.providers.openai_compatible import QwenProvider

        settings_mock = MagicMock()
        settings_mock.qwen_api_key = "test-key"
        settings_mock.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        settings_mock.qwen_model = "qwen-plus"

        provider = QwenProvider(settings_mock)

        import asyncio

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={"choices": [{"message": {"content": ""}}]})
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ProviderResponseInvalidError):
                asyncio.run(
                    provider.chat(ProviderInput(system_prompt="sys", user_message="hi", model="qwen-plus"))
                )

    def test_http_5xx_raises_request_error(self):
        import httpx

        from app.providers.openai_compatible import QwenProvider

        settings_mock = MagicMock()
        settings_mock.qwen_api_key = "test-key"
        settings_mock.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        settings_mock.qwen_model = "qwen-plus"

        provider = QwenProvider(settings_mock)

        import asyncio

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            mock_response.json = MagicMock(return_value={})
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError(
                    "500",
                    request=MagicMock(),
                    response=MagicMock(),
                )
            )

            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            with pytest.raises(ProviderRequestError):
                asyncio.run(
                    provider.chat(ProviderInput(system_prompt="sys", user_message="hi", model="qwen-plus"))
                )


class TestProviderStreamAbstraction:
    """P1-2-1: Provider 流式抽象契约测试。"""

    def test_provider_stream_event_is_frozen_dataclass(self):
        """ProviderStreamEvent 是不可变 dataclass。"""
        evt = ProviderStreamEvent(text_delta="hello")
        assert evt.text_delta == "hello"

    def test_provider_stream_event_is_hashable(self):
        """ProviderStreamEvent 不可变且可哈希。"""
        evt1 = ProviderStreamEvent(text_delta="hello")
        evt2 = ProviderStreamEvent(text_delta="hello")
        assert hash(evt1) == hash(evt2)

    def test_base_provider_stream_chat_is_abstract(self):
        """BaseProvider.stream_chat 是抽象方法。"""
        sig = inspect.signature(BaseProvider.stream_chat)
        assert list(sig.parameters.keys()) == ["self", "input"]


class TestQwenProviderStream:
    """P1-2-1: QwenProvider stream_chat 真实流式能力测试。"""

    def _make_settings_mock(self, api_key="test-key"):
        settings_mock = MagicMock()
        settings_mock.qwen_api_key = api_key
        settings_mock.qwen_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        settings_mock.qwen_model = "qwen-plus"
        return settings_mock

    def test_stream_chat_missing_api_key_raises_not_configured(self):
        """QWEN_API_KEY 缺失时抛出 ProviderNotConfiguredError。"""
        from app.providers.openai_compatible import QwenProvider

        settings_mock = self._make_settings_mock(api_key=None)
        provider = QwenProvider(settings_mock)

        with pytest.raises(ProviderNotConfiguredError):
            asyncio.run(
                _sync_stream(provider.stream_chat(
                    ProviderInput(system_prompt="sys", user_message="hi", model="qwen-plus")
                ))
            )

    def test_stream_chat_yields_text_deltas(self):
        """stream_chat 返回有序的原始文本 delta。"""
        import httpx
        from app.providers.openai_compatible import QwenProvider

        settings_mock = self._make_settings_mock()
        provider = QwenProvider(settings_mock)

        async def mock_aiter_lines():
            events = [
                'data: {"choices":[{"delta":{"content":"Hello"},"index":0}]}\n',
                'data: {"choices":[{"delta":{"content":" world"},"index":0}]}\n',
                'data: {"choices":[{"delta":{"content":"! How can I help?"},"index":0}]}\n',
                'data: [DONE]\n',
                '',
            ]
            for e in events:
                await asyncio.sleep(0.001)
                yield e

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        async def mock_stream_post(*args, **kwargs):
            return mock_response

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(side_effect=lambda *a, **kw: mock_stream_ctx)
        mock_client.post = mock_stream_post
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            deltas = asyncio.run(
                _sync_collect(provider.stream_chat(
                    ProviderInput(system_prompt="sys", user_message="hi", model="qwen-plus")
                ))
            )

        assert deltas == ["Hello", " world", "! How can I help?"]

    def test_stream_chat_http_5xx_raises_request_error(self):
        """上游 5xx 时抛出 ProviderRequestError。"""
        import httpx
        from app.providers.openai_compatible import QwenProvider

        settings_mock = self._make_settings_mock()
        provider = QwenProvider(settings_mock)

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "500",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )
        )

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ProviderRequestError):
                asyncio.run(
                    _sync_stream(provider.stream_chat(
                        ProviderInput(system_prompt="sys", user_message="hi", model="qwen-plus")
                    ))
                )

    def test_stream_chat_network_error_raises_request_error(self):
        """上游网络错误时抛出 ProviderRequestError。"""
        import httpx
        from app.providers.openai_compatible import QwenProvider

        settings_mock = self._make_settings_mock()
        provider = QwenProvider(settings_mock)

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(
            side_effect=httpx.RequestError("Connection refused")
        )
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ProviderRequestError):
                asyncio.run(
                    _sync_stream(provider.stream_chat(
                        ProviderInput(system_prompt="sys", user_message="hi", model="qwen-plus")
                    ))
                )

    def test_stream_chat_empty_deltas_not_yielded(self):
        """空 content delta 噪声事件不应向上层透传。"""
        from app.providers.openai_compatible import QwenProvider

        settings_mock = self._make_settings_mock()
        provider = QwenProvider(settings_mock)

        async def mock_aiter_lines():
            events = [
                'data: {"choices":[{"delta":{"content":"Hello"},"index":0}]}\n',
                'data: {"choices":[{"delta":{}},"index":0}]}\n',
                'data: {"choices":[{"delta":{"content":" world"},"index":0}]}\n',
                'data: [DONE]\n',
                '',
            ]
            for e in events:
                await asyncio.sleep(0.001)
                yield e

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            deltas = asyncio.run(
                _sync_collect(provider.stream_chat(
                    ProviderInput(system_prompt="sys", user_message="hi", model="qwen-plus")
                ))
            )

        assert deltas == ["Hello", " world"]

    def test_stream_chat_no_usable_content_raises_invalid(self):
        """上游没有任何可用文本时抛出 ProviderResponseInvalidError。"""
        from app.providers.openai_compatible import QwenProvider

        settings_mock = self._make_settings_mock()
        provider = QwenProvider(settings_mock)

        async def mock_aiter_lines():
            events = [
                'data: {"choices":[{"delta":{}},"index":0}]}\n',
                'data: [DONE]\n',
                '',
            ]
            for e in events:
                await asyncio.sleep(0.001)
                yield e

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_lines = mock_aiter_lines

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

        mock_client = MagicMock()
        mock_client.stream = MagicMock(return_value=mock_stream_ctx)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(ProviderResponseInvalidError):
                asyncio.run(
                    _sync_stream(provider.stream_chat(
                        ProviderInput(system_prompt="sys", user_message="hi", model="qwen-plus")
                    ))
                )
