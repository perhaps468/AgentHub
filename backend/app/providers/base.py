from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


class ProviderError(Exception):
    """Base exception for provider errors."""

    pass


class ProviderNotConfiguredError(ProviderError):
    """Raised when provider configuration is incomplete."""

    pass


class ProviderRequestError(ProviderError):
    """Raised when upstream call fails, times out, or returns 5xx."""

    pass


class ProviderResponseInvalidError(ProviderError):
    """Raised when upstream response lacks usable text content."""

    pass


@dataclass(frozen=True)
class ProviderInput:
    system_prompt: str
    user_message: str
    model: str


@dataclass(frozen=True)
class ProviderOutput:
    text: str


@dataclass(frozen=True)
class ProviderStreamEvent:
    """Represents a single raw text delta from the upstream stream."""

    text_delta: str


@dataclass(frozen=True)
class ProviderMessage:
    """A single message in a conversation history.

    Used by the messages-aware Provider interface (chat_with_messages / stream_chat_with_messages).
    """

    role: str
    content: str


@dataclass(frozen=True)
class LLMUsage:
    """Token usage statistics returned by the upstream LLM."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ProviderMessagesInput:
    """Input for the messages-aware Provider interface.

    Carries the full conversation history to the Provider so the upstream
    LLM receives multi-turn context natively rather than degrading to
    a single system_prompt + user_message pair.
    """

    messages: list[ProviderMessage]
    model: str


@dataclass(frozen=True)
class ProviderMessagesOutput:
    """Output from the messages-aware Provider interface."""

    text: str
    usage: LLMUsage | None = None


class BaseProvider(ABC):
    @abstractmethod
    async def chat(self, input: ProviderInput) -> ProviderOutput:
        raise NotImplementedError

    @abstractmethod
    async def stream_chat(self, input: ProviderInput) -> AsyncIterator[ProviderStreamEvent]:
        """Stream raw text deltas from the upstream provider.

        Only yields raw text deltas. Sentence chunking, typing, message_id,
        and stream_id are the responsibility of the caller.
        """
        raise NotImplementedError

    @abstractmethod
    async def chat_with_messages(
        self, input: ProviderMessagesInput
    ) -> ProviderMessagesOutput:
        """Non-streaming completion using the full message history.

        The Provider forwards the complete messages list to the upstream API
        so the LLM sees multi-turn context natively.
        """
        raise NotImplementedError

    @abstractmethod
    async def stream_chat_with_messages(
        self, input: ProviderMessagesInput
    ) -> AsyncIterator[ProviderStreamEvent]:
        """Streaming completion using the full message history.

        The Provider forwards the complete messages list to the upstream API
        and yields raw text deltas to the caller.
        """
        raise NotImplementedError
