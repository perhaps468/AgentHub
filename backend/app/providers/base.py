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
