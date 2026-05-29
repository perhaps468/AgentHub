"""Generative model module for AI-powered text generation.

M2 note: the LLM route via `quantlitellm` is deprecated.
The canonical path for runtime LLM calls is through LLMAdapter (app.runtime.llm_adapter),
which wraps the AgentHub Provider layer.  GenerativeModel retains its types
(Message, TokenUsage, ResponseStats) for compatibility with copied react_agent.py,
but actual model calls should migrate to LLMAdapter in M3.
"""

import asyncio
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List

import openai
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from app.runtime.get_model_info import get_max_input_tokens, get_max_output_tokens, get_max_tokens
from app.runtime import quantlitellm as exceptions

MIN_RETRIES = 1


class _NoopEventEmitter:
    """Minimal local placeholder until Runtime event streaming is rebuilt in AgentHub."""

    def emit(self, event: str, *args, **kwargs) -> None:
        logger.debug(f"[runtime noop event] {event}")


class Message(BaseModel):
    """Represents a message in a conversation with a specific role and content."""

    role: str = Field(..., min_length=1)
    content: str | dict = Field(..., min_length=1)
    image_url: str | None = Field(default=None, pattern=r"^https?://")

    @field_validator("role")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace-only")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str | dict) -> str | dict:
        if isinstance(v, str):
            if not v or not v.strip():
                raise ValueError("Text content cannot be empty or whitespace-only")
        elif isinstance(v, dict):
            if not v.get("text") or not v.get("image_url"):
                raise ValueError("Multimodal content must have both text and image_url")
        return v

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, v: str | None) -> str | None:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("Image URL must start with http:// or https://")
        return v


class TokenUsage(BaseModel):
    """Represents token usage statistics for a language model."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ResponseStats(BaseModel):
    """Represents detailed statistics for a model response."""

    response: str
    usage: TokenUsage
    model: str
    finish_reason: str | None = None
    data: List[Dict[str, Any]] | None = None
    created: str | None = None


class GenerativeModel:
    """Generative model for AI-powered text and image generation with async support."""

    def __init__(
        self,
        model: str = "ollama/qwen2.5-coder:14b",
        temperature: float = 0.7,
        event_emitter: _NoopEventEmitter | None = None,
    ) -> None:
        """Initialize a generative model with configurable parameters."""
        logger.debug(f"Initializing GenerativeModel with model={model}, temperature={temperature}")
        self.model = model
        self.temperature = temperature
        self.event_emitter = event_emitter or _NoopEventEmitter()

    RETRIABLE_EXCEPTIONS = (
        exceptions.RateLimitError,
        exceptions.APIConnectionError,
        exceptions.ServiceUnavailableError,
        exceptions.Timeout,
        exceptions.APIError,
    )

    CONTEXT_EXCEPTIONS = (
        exceptions.ContextWindowExceededError,
        exceptions.InvalidRequestError,
    )

    POLICY_EXCEPTIONS = (exceptions.ContentPolicyViolationError,)

    AUTH_EXCEPTIONS = (
        exceptions.AuthenticationError,
        exceptions.PermissionDeniedError,
    )

    async def async_generate_with_history(
        self,
        messages_history: list[Message],
        prompt: str,
        image_url: str | None = None,
        streaming: bool = False,
        stop_words: list[str] | None = None,
    ) -> ResponseStats | AsyncGenerator[str, None]:
        """Asynchronously generate a response with conversation history and optional image.

        M2 note: this method currently calls the quantlitellm stub.
        The canonical runtime LLM path is through LLMAdapter (M3 onward).
        This method is retained for backward compatibility with react_agent.py.
        """
        messages = [{"role": msg.role, "content": str(msg.content)} for msg in messages_history]

        if image_url:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": str(prompt)},
                        {"type": "image_url", "image_url": {"url": image_url}},
                    ],
                }
            )
        else:
            messages.append({"role": "user", "content": str(prompt)})

        if streaming:
            self.event_emitter.emit("stream_start")
            return self._async_stream_response(messages, stop_words)

        try:
            from app.runtime import quantlitellm
            logger.debug(f"Async generating response for prompt: {prompt}")
            response = await quantlitellm.acompletion(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                num_retries=MIN_RETRIES,
                stop=stop_words,
                extra_headers={"X-Title": "agenthub"},
            )
            logger.debug(f"Raw response from {self.model}: {response}")

            if hasattr(response, "error") and response.error:
                error_msg = response.error.get("message", "Unknown error")
                logger.warning(f"API returned error: {error_msg}")
                raise openai.APIError(
                    message=f"API error: {error_msg}",
                    request={"model": self.model, "messages": messages},
                    body={"error": response.error},
                )

            token_usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            )
            content = response.choices[0].message.content
            if content is None:
                logger.warning(f"Received None content from {self.model}. Raw response: {response}")
                raise ValueError(f"Model {self.model} returned no content for the given input.")

            return ResponseStats(
                response=content,
                usage=token_usage,
                model=self.model,
                finish_reason=response.choices[0].finish_reason,
            )
        except Exception as e:
            self._handle_generation_exception(e)

    async def _async_stream_response(self, messages, stop_words: list[str] | None = None):
        """Private method to handle asynchronous streaming responses."""
        try:
            from app.runtime import quantlitellm
            response = await quantlitellm.acompletion(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                stream=True,
                stop=stop_words,
                num_retries=MIN_RETRIES,
            )
            async for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    self.event_emitter.emit("stream_chunk", chunk.choices[0].delta.content)
                    yield chunk.choices[0].delta.content
            self.event_emitter.emit("stream_end")
        except Exception as e:
            logger.error(f"Async streaming error: {str(e)}")
            raise

    async def async_generate(
        self,
        prompt: str,
        image_url: str | None = None,
        streaming: bool = False,
    ) -> ResponseStats | AsyncGenerator[str, None]:
        """Asynchronously generate a response without conversation history."""
        return await self.async_generate_with_history([], prompt, image_url, streaming)

    def _handle_generation_exception(self, e):
        """Handle exceptions during generation."""
        error_details = {
            "error_type": type(e).__name__,
            "message": str(e),
            "model": self.model,
            "provider": getattr(e, "llm_provider", "unknown"),
            "status_code": getattr(e, "status_code", None),
        }

        logger.error("LLM Generation Error: {}", error_details)

        if isinstance(e, self.AUTH_EXCEPTIONS):
            raise openai.AuthenticationError(
                message=f"Authentication failed with provider {error_details['provider']}",
                request={"model": self.model, "temperature": self.temperature},
                body={"error": {"message": str(e), "type": "authentication_error"}},
            ) from e

        if isinstance(e, self.CONTEXT_EXCEPTIONS):
            raise openai.InvalidRequestError(
                message=f"Context window exceeded or invalid request: {str(e)}",
                request={"model": self.model, "temperature": self.temperature},
                body={"error": {"message": str(e), "type": "invalid_request_error"}},
            ) from e

        if isinstance(e, self.POLICY_EXCEPTIONS):
            raise openai.APIError(
                message=f"Content policy violation: {str(e)}",
                request={"model": self.model, "temperature": self.temperature},
                body={"error": {"message": str(e), "type": "policy_violation"}},
            ) from e

        if isinstance(e, openai.OpenAIError):
            raise

        raise openai.APIError(
            message=f"Unexpected error during generation: {str(e)}",
            request={"model": self.model, "temperature": self.temperature},
            body={"error": {"message": str(e), "type": "unexpected_error"}},
        ) from e

    def get_max_tokens(self) -> int:
        """Get the maximum number of tokens that can be generated by the model."""
        return get_max_tokens(self.model)

    def get_model_max_input_tokens(self) -> int | None:
        """Get the maximum number of input tokens for the model."""
        return get_max_input_tokens(self.model)

    def get_model_max_output_tokens(self) -> int | None:
        """Get the maximum number of output tokens for the model."""
        return get_max_output_tokens(self.model)

    async def async_generate_image(self, prompt: str, params: Dict[str, Any]) -> ResponseStats:
        """Asynchronously generate an image using the specified model and parameters."""
        try:
            from app.runtime import quantlitellm
            logger.debug(f"Async generating image with params: {params}")
            generation_params = {**params, "prompt": prompt}
            model = generation_params.pop("model")
            response = await quantlitellm.aimage_generation(model=model, **generation_params)

            if hasattr(response, "data"):
                data = []
                for img in response.data:
                    img_data = {}
                    if hasattr(img, "url"):
                        img_data["url"] = str(img.url)
                    if hasattr(img, "b64_json"):
                        img_data["b64_json"] = str(img.b64_json)
                    if hasattr(img, "revised_prompt"):
                        img_data["revised_prompt"] = str(img.revised_prompt)
                    data.append(img_data)
            else:
                data = [{"url": str(response.url)}]

            if hasattr(response, "created"):
                try:
                    created = datetime.fromtimestamp(response.created).isoformat()
                except (TypeError, ValueError):
                    created = str(response.created)
            else:
                created = None

            return ResponseStats(
                response="",
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                model=str(params["model"]),
                data=data,
                created=created,
            )
        except Exception as e:
            logger.error(f"Error in async image generation: {str(e)}")
            raise

    def token_counter(self, messages: list[Message]) -> int:
        """Count the number of tokens in a list of messages."""
        from app.runtime import quantlitellm
        logger.debug(f"Counting tokens for {len(messages)} messages using model {self.model}")
        litellm_messages = [{"role": msg.role, "content": str(msg.content)} for msg in messages]
        return quantlitellm.token_counter(model=self.model, messages=litellm_messages)

    def token_counter_with_history(self, messages_history: list[Message], prompt: str) -> int:
        """Count the number of tokens in a list of messages and a prompt."""
        from app.runtime import quantlitellm
        litellm_messages = [{"role": msg.role, "content": str(msg.content)} for msg in messages_history]
        litellm_messages.append({"role": "user", "content": str(prompt)})
        return quantlitellm.token_counter(model=self.model, messages=litellm_messages)

    async def async_token_counter(self, messages: list[Message]) -> int:
        """Asynchronously count the number of tokens in a list of messages."""
        from app.runtime import quantlitellm
        logger.debug(f"Async counting tokens for {len(messages)} messages using model {self.model}")
        litellm_messages = [{"role": msg.role, "content": str(msg.content)} for msg in messages]
        return await asyncio.to_thread(quantlitellm.token_counter, model=self.model, messages=litellm_messages)

    async def async_token_counter_with_history(self, messages_history: list[Message], prompt: str) -> int:
        """Asynchronously count the number of tokens in a list of messages and a prompt."""
        from app.runtime import quantlitellm
        litellm_messages = [{"role": msg.role, "content": str(msg.content)} for msg in messages_history]
        litellm_messages.append({"role": "user", "content": str(prompt)})
        return await asyncio.to_thread(quantlitellm.token_counter, model=self.model, messages=litellm_messages)
