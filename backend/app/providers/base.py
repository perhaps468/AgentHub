from abc import ABC, abstractmethod
from dataclasses import dataclass


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


class BaseProvider(ABC):
    @abstractmethod
    async def chat(self, input: ProviderInput) -> ProviderOutput:
        raise NotImplementedError
