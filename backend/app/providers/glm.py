import json
from typing import Any, AsyncIterator

import httpx

from app.observability.audit_models import AuditContext
from app.observability.audit_recorder import get_audit_recorder
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


class GlmProvider(BaseProvider):
    """智谱 GLM Provider — 兼容 OpenAI Chat Completions 协议。"""

    def __init__(self, settings: Any) -> None:
        self._api_key = settings.glm_api_key
        self._base_url = settings.glm_base_url
        self._model = settings.glm_model

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
                "GLM_API_KEY is not configured. Please set it in .env"
            )

        messages = [
            {"role": "system", "content": input.system_prompt},
            {"role": "user", "content": input.user_message},
        ]

        recorder = get_audit_recorder()
        recorder.record_llm_request(
            provider="glm",
            model=self._model,
            request_kind="chat",
            messages=messages,
            base_url=self._base_url,
            stream=False,
        )

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
                recorder.record_llm_error(
                    error_type="ProviderRequestError",
                    error_message=f"Upstream returned {e.response.status_code}: {e.response.text}",
                    status_code=e.response.status_code,
                )
                raise ProviderRequestError(f"Upstream returned {e.response.status_code}: {e.response.text}")
            except (httpx.RequestError, TimeoutError) as e:
                recorder.record_llm_error(
                    error_type="ProviderRequestError",
                    error_message=f"Upstream request failed: {e}",
                )
                raise ProviderRequestError(f"Upstream request failed: {e}")

        data = response.json()
        choices = data.get("choices")
        if not choices:
            recorder.record_llm_error(
                error_type="ProviderResponseInvalidError",
                error_message="Upstream response has no choices",
            )
            raise ProviderResponseInvalidError("Upstream response has no choices")

        message = choices[0].get("message")
        if not message:
            recorder.record_llm_error(
                error_type="ProviderResponseInvalidError",
                error_message="Upstream response message is missing",
            )
            raise ProviderResponseInvalidError("Upstream response message is missing")

        content = self._extract_text(message.get("content"))
        if not content or not content.strip():
            recorder.record_llm_error(
                error_type="ProviderResponseInvalidError",
                error_message="Upstream response content is empty",
            )
            raise ProviderResponseInvalidError("Upstream response content is empty")

        usage_data = data.get("usage")
        usage = None
        if usage_data:
            usage = {
                "prompt_tokens": usage_data.get("prompt_tokens", 0),
                "completion_tokens": usage_data.get("completion_tokens", 0),
                "total_tokens": usage_data.get("total_tokens", 0),
            }
        finish_reason = choices[0].get("finish_reason")
        recorder.record_llm_response(
            full_text=content.strip(),
            usage=usage,
            finish_reason=finish_reason,
        )

        return ProviderOutput(text=content.strip())

    async def stream_chat(self, input: ProviderInput) -> AsyncIterator[ProviderStreamEvent]:
        if not self._api_key:
            raise ProviderNotConfiguredError(
                "GLM_API_KEY is not configured. Please set it in .env"
            )

        messages = [
            {"role": "system", "content": input.system_prompt},
            {"role": "user", "content": input.user_message},
        ]

        recorder = get_audit_recorder()
        recorder.record_llm_request(
            provider="glm",
            model=self._model,
            request_kind="stream_chat",
            messages=messages,
            base_url=self._base_url,
            stream=True,
        )

        sequence_index = 0
        final_text_parts: list[str] = []

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
                        recorder.record_llm_error(
                            error_type="ProviderRequestError",
                            error_message=f"Upstream returned {e.response.status_code}: {err_body}",
                            status_code=e.response.status_code,
                        )
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
                            final_text_parts.append(content)
                            recorder.record_llm_stream_delta(
                                delta_text=content,
                                sequence_index=sequence_index,
                            )
                            sequence_index += 1
                            yield ProviderStreamEvent(text_delta=content)

                    if not has_yielded:
                        recorder.record_llm_error(
                            error_type="ProviderResponseInvalidError",
                            error_message="Upstream streaming response contains no usable text content",
                        )
                        raise ProviderResponseInvalidError(
                            "Upstream streaming response contains no usable text content"
                        )

                    final_text = "".join(final_text_parts)
                    recorder.record_llm_stream_complete(
                        final_text=final_text,
                    )

        except httpx.RequestError as e:
            recorder.record_llm_error(
                error_type="ProviderRequestError",
                error_message=f"Upstream request failed: {e}",
            )
            raise ProviderRequestError(f"Upstream request failed: {e}")

    async def chat_with_messages(self, input: ProviderMessagesInput) -> ProviderMessagesOutput:
        if not self._api_key:
            raise ProviderNotConfiguredError(
                "GLM_API_KEY is not configured. Please set it in .env"
            )

        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in input.messages
        ]

        recorder = get_audit_recorder()
        recorder.record_llm_request(
            provider="glm",
            model=input.model or self._model,
            request_kind="chat_with_messages",
            messages=messages,
            base_url=self._base_url,
            stream=False,
        )

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
                recorder.record_llm_error(
                    error_type="ProviderRequestError",
                    error_message=f"Upstream returned {e.response.status_code}: {e.response.text}",
                    status_code=e.response.status_code,
                )
                raise ProviderRequestError(
                    f"Upstream returned {e.response.status_code}: {e.response.text}"
                )
            except (httpx.RequestError, TimeoutError) as e:
                recorder.record_llm_error(
                    error_type="ProviderRequestError",
                    error_message=f"Upstream request failed: {e}",
                )
                raise ProviderRequestError(f"Upstream request failed: {e}")

        data = response.json()
        choices = data.get("choices")
        if not choices:
            recorder.record_llm_error(
                error_type="ProviderResponseInvalidError",
                error_message="Upstream response has no choices",
            )
            raise ProviderResponseInvalidError("Upstream response has no choices")

        message = choices[0].get("message")
        if not message:
            recorder.record_llm_error(
                error_type="ProviderResponseInvalidError",
                error_message="Upstream response message is missing",
            )
            raise ProviderResponseInvalidError("Upstream response message is missing")

        content = self._extract_text(message.get("content"))
        if not content or not content.strip():
            recorder.record_llm_error(
                error_type="ProviderResponseInvalidError",
                error_message="Upstream response content is empty",
            )
            raise ProviderResponseInvalidError("Upstream response content is empty")

        usage_data = data.get("usage")
        usage = None
        usage_dict = None
        if usage_data:
            usage_dict = {
                "prompt_tokens": usage_data.get("prompt_tokens", 0),
                "completion_tokens": usage_data.get("completion_tokens", 0),
                "total_tokens": usage_data.get("total_tokens", 0),
            }
            usage = LLMUsage(
                prompt_tokens=usage_dict["prompt_tokens"],
                completion_tokens=usage_dict["completion_tokens"],
                total_tokens=usage_dict["total_tokens"],
            )
        finish_reason = choices[0].get("finish_reason")
        recorder.record_llm_response(
            full_text=content.strip(),
            usage=usage_dict,
            finish_reason=finish_reason,
        )

        return ProviderMessagesOutput(text=content.strip(), usage=usage)

    async def stream_chat_with_messages(
        self, input: ProviderMessagesInput
    ) -> AsyncIterator[ProviderStreamEvent]:
        if not self._api_key:
            raise ProviderNotConfiguredError(
                "GLM_API_KEY is not configured. Please set it in .env"
            )

        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in input.messages
        ]

        recorder = get_audit_recorder()
        recorder.record_llm_request(
            provider="glm",
            model=input.model or self._model,
            request_kind="stream_chat_with_messages",
            messages=messages,
            base_url=self._base_url,
            stream=True,
        )

        sequence_index = 0
        final_text_parts: list[str] = []

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
                        recorder.record_llm_error(
                            error_type="ProviderRequestError",
                            error_message=f"Upstream returned {e.response.status_code}: {err_body}",
                            status_code=e.response.status_code,
                        )
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
                            final_text_parts.append(content)
                            recorder.record_llm_stream_delta(
                                delta_text=content,
                                sequence_index=sequence_index,
                            )
                            sequence_index += 1
                            yield ProviderStreamEvent(text_delta=content)

                    if not has_yielded:
                        recorder.record_llm_error(
                            error_type="ProviderResponseInvalidError",
                            error_message="Upstream streaming response contains no usable text content",
                        )
                        raise ProviderResponseInvalidError(
                            "Upstream streaming response contains no usable text content"
                        )

                    final_text = "".join(final_text_parts)
                    recorder.record_llm_stream_complete(
                        final_text=final_text,
                    )

        except httpx.RequestError as e:
            recorder.record_llm_error(
                error_type="ProviderRequestError",
                error_message=f"Upstream request failed: {e}",
            )
            raise ProviderRequestError(f"Upstream request failed: {e}")
