from typing import Any

import httpx

from app.providers.base import (
    BaseProvider,
    ProviderInput,
    ProviderNotConfiguredError,
    ProviderOutput,
    ProviderRequestError,
    ProviderResponseInvalidError,
    ProviderOutput as Output,
)


class QwenProvider(BaseProvider):
    def __init__(self, settings: Any) -> None:
        self._api_key = settings.qwen_api_key
        self._base_url = settings.qwen_base_url
        self._model = settings.qwen_model

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

        content = message.get("content")
        if not content or not content.strip():
            raise ProviderResponseInvalidError("Upstream response content is empty")

        return ProviderOutput(text=content.strip())
