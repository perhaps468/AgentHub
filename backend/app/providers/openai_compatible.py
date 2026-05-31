import json
from typing import Any, AsyncIterator

import httpx

from app.providers.base import (
    AsyncIterator,
    BaseProvider,
    LLMUsage,
    ProviderInput,
    ProviderMessage,
    ProviderMessagesInput,
    ProviderMessagesOutput,
    ProviderNotConfiguredError,
    ProviderOutput,
    ProviderRequestError,
    ProviderResponseInvalidError,
    ProviderStreamEvent,
    ProviderOutput as Output,
)


class QwenProvider(BaseProvider):
    def __init__(self, settings: Any) -> None:
        self._api_key = settings.qwen_api_key
        self._base_url = settings.qwen_base_url
        self._model = settings.qwen_model

    def _extract_text(self, value: Any) -> str:
        if isinstance(value, str):
            return value

        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                    continue
                nested_text = item.get("content")
                if isinstance(nested_text, str):
                    parts.append(nested_text)
            return "".join(parts)

        if isinstance(value, dict):
            for key in ("text", "content"):
                nested = value.get(key)
                if isinstance(nested, str):
                    return nested

        return ""

    async def chat(self, input: ProviderInput) -> Output:
        if not self._api_key:
            raise ProviderNotConfiguredError(
                "QWEN_API_KEY is not configured. Please set it in .env"
            )

        messages = [
            {"role": "system", "content": input.system_prompt},
            {"role": "user", "content": input.user_message},
        ]

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self._base_url.rstrip('/')}/chat/completions",
                    json={
                        "model": self._model,
                        "messages": messages,
                    },
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise ProviderRequestError(f"Upstream returned {e.response.status_code}: {e.response.text}")
            except (httpx.RequestError, TimeoutError) as e:
                raise ProviderRequestError(f"Upstream request failed: {e}")

        data = response.json()
        choices = data.get("choices")
        if not choices:
            raise ProviderResponseInvalidError("Upstream response has no choices")

        message = choices[0].get("message")
        if not message:
            raise ProviderResponseInvalidError("Upstream response message is missing")

        content = self._extract_text(message.get("content"))
        if not content or not content.strip():
            raise ProviderResponseInvalidError("Upstream response content is empty")

        return ProviderOutput(text=content.strip())

    async def stream_chat(self, input: ProviderInput) -> AsyncIterator[ProviderStreamEvent]:
        if not self._api_key:
            raise ProviderNotConfiguredError(
                "QWEN_API_KEY is not configured. Please set it in .env"
            )

        messages = [
            {"role": "system", "content": input.system_prompt},
            {"role": "user", "content": input.user_message},
        ]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url.rstrip('/')}/chat/completions",
                    json={
                        "model": self._model,
                        "messages": messages,
                        "stream": True,
                    },
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as e:
                        try:
                            err_body = e.response.text
                        except httpx.ResponseNotRead:
                            err_body = "(streaming body not available)"
                        raise ProviderRequestError(
                            f"Upstream returned {e.response.status_code}: {err_body}"
                        )

                    has_yielded = False
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or line == "data: [DONE]":
                            if has_yielded:
                                break
                            else:
                                continue

                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choices = data.get("choices")
                        if not choices:
                            continue

                        delta = choices[0].get("delta", {})
                        content = self._extract_text(delta.get("content"))
                        if content:
                            has_yielded = True
                            yield ProviderStreamEvent(text_delta=content)

                    if not has_yielded:
                        raise ProviderResponseInvalidError(
                            "Upstream streaming response contains no usable text content"
                        )
        except httpx.RequestError as e:
            raise ProviderRequestError(f"Upstream request failed: {e}")

    async def chat_with_messages(self, input: ProviderMessagesInput) -> ProviderMessagesOutput:
        """Non-streaming completion using the full message history.

        Forwards the complete messages list to the upstream API so the LLM
        receives multi-turn context natively.
        """
        if not self._api_key:
            raise ProviderNotConfiguredError(
                "QWEN_API_KEY is not configured. Please set it in .env"
            )

        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in input.messages
        ]

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self._base_url.rstrip('/')}/chat/completions",
                    json={
                        "model": input.model or self._model,
                        "messages": messages,
                    },
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise ProviderRequestError(
                    f"Upstream returned {e.response.status_code}: {e.response.text}"
                )
            except (httpx.RequestError, TimeoutError) as e:
                raise ProviderRequestError(f"Upstream request failed: {e}")

        data = response.json()
        choices = data.get("choices")
        if not choices:
            raise ProviderResponseInvalidError("Upstream response has no choices")

        message = choices[0].get("message")
        if not message:
            raise ProviderResponseInvalidError("Upstream response message is missing")

        content = self._extract_text(message.get("content"))
        if not content or not content.strip():
            raise ProviderResponseInvalidError("Upstream response content is empty")

        usage_data = data.get("usage")
        usage = None
        if usage_data:
            usage = LLMUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

        return ProviderMessagesOutput(text=content.strip(), usage=usage)

    async def stream_chat_with_messages(
        self, input: ProviderMessagesInput
    ) -> AsyncIterator[ProviderStreamEvent]:
        """Streaming completion using the full message history.

        Forwards the complete messages list to the upstream API and yields
        raw text deltas to the caller.
        """
        if not self._api_key:
            raise ProviderNotConfiguredError(
                "QWEN_API_KEY is not configured. Please set it in .env"
            )

        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in input.messages
        ]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url.rstrip('/')}/chat/completions",
                    json={
                        "model": input.model or self._model,
                        "messages": messages,
                        "stream": True,
                    },
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as e:
                        try:
                            err_body = e.response.text
                        except httpx.ResponseNotRead:
                            err_body = "(streaming body not available)"
                        raise ProviderRequestError(
                            f"Upstream returned {e.response.status_code}: {err_body}"
                        )

                    has_yielded = False
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or line == "data: [DONE]":
                            if has_yielded:
                                break
                            else:
                                continue

                        if not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue

                        choices = data.get("choices")
                        if not choices:
                            continue

                        delta = choices[0].get("delta", {})
                        content = self._extract_text(delta.get("content"))
                        if content:
                            has_yielded = True
                            yield ProviderStreamEvent(text_delta=content)

                    if not has_yielded:
                        raise ProviderResponseInvalidError(
                            "Upstream streaming response contains no usable text content"
                        )
        except httpx.RequestError as e:
            raise ProviderRequestError(f"Upstream request failed: {e}")
