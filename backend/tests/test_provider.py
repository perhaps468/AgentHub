from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import (
    BaseProvider,
    ProviderInput,
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderResponseInvalidError,
    ProviderOutput,
)


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
        import inspect

        assert inspect.isabstract(BaseProvider)

    def test_base_provider_chat_is_abstract(self):
        import inspect

        sig = inspect.signature(BaseProvider.chat)
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
