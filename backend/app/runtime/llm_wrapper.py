"""LLMWrapper — bridges the copied GenerativeModel interface to LLMAdapter.

M3: This wrapper satisfies the GenerativeModel-interface dependencies in
copied react_agent.py so the main execution path can switch to LLMAdapter.

The wrapper:
- Wraps an LLMAdapter (AgentHub Provider-backed)
- Exposes the same methods that copied react_agent.py calls on GenerativeModel
- Provides safe stub defaults for token_counter (no quantlitellm dependency)
"""

from typing import AsyncIterator

from app.runtime.context_hygiene import estimate_text_tokens
from app.runtime.generative_model import ResponseStats, TokenUsage


class LLMWrapper:
    """Wraps LLMAdapter with a GenerativeModel-compatible interface.

    react_agent.py calls these methods on self.model:
      - async_generate_with_history(messages_history, prompt, ...)  [main LLM call]
      - async_generate(prompt)                                      [summary / compaction]
      - get_model_max_input_tokens()                                [context limit]
      - get_model_max_output_tokens()                               [output limit]
      - token_counter_with_history(messages, prompt)                 [token estimation]
      - token_counter(messages)                                      [token estimation]
      - get_max_tokens()                                             [output limit]

    All of these are satisfied by this wrapper over LLMAdapter.
    """

    def __init__(
        self,
        llm_adapter,
        model_name: str = "qwen-plus",
        event_emitter=None,
    ):
        self._llm_adapter = llm_adapter
        self.model = model_name
        self.event_emitter = event_emitter

    async def async_stream_generate_with_history(
        self,
        messages_history: list,
        prompt: str,
        image_url=None,
        stop_words: list | None = None,
    ) -> AsyncIterator[str]:
        """T2: Streaming generation path — yields raw token deltas.

        Wraps LLMAdapter.async_stream_generate_with_history().
        The caller (ReactAgent) receives token-level deltas and should emit
        a 'model_delta' event for each token.
        """
        messages = list(messages_history)
        messages.append({"role": "user", "content": prompt})

        async for delta in self._llm_adapter.async_stream_generate_with_history(
            messages_history=messages,
            model=self.model,
            stop=stop_words,
        ):
            yield delta

    async def async_generate_with_history(
        self,
        messages_history: list,
        prompt: str,
        image_url=None,
        streaming: bool = False,
        stop_words: list | None = None,
    ):
        """Main generation path: calls LLMAdapter.async_generate_with_history.

        ReactAgent calls this with (messages_history, prompt) — the extra
        positional prompt becomes the last user message appended to history.
        When streaming=True, delegates to async_stream_generate_with_history()
        and assembles the full response (used in T2 streaming path).
        """
        messages = list(messages_history)
        messages.append({"role": "user", "content": prompt})

        if streaming:
            # T2: assemble full response from streaming deltas
            full = ""
            async for delta in self._llm_adapter.async_stream_generate_with_history(
                messages_history=messages,
                model=self.model,
                stop=stop_words,
            ):
                full += delta
            from app.runtime.generative_model import ResponseStats, TokenUsage
            return ResponseStats(
                response=full,
                usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
                model=self.model,
                finish_reason="stop",
            )

        return await self._llm_adapter.async_generate_with_history(
            messages_history=messages,
            model=self.model,
            stop=stop_words,
        )

    async def async_generate(self, prompt: str, image_url=None, streaming: bool = False):
        """Generate without history — used for summarization/compaction.

        streaming is accepted for signature compatibility but M3 only implements
        non-streaming (compaction/summary is synchronous enough).
        """
        return await self.async_generate_with_history(
            messages_history=[],
            prompt=prompt,
            image_url=image_url,
            streaming=False,
        )

    def get_model_max_input_tokens(self) -> int | None:
        """Return hard-coded input token limit. Real value from Provider in future milestones."""
        return 128 * 1024

    def get_model_max_output_tokens(self) -> int | None:
        """Return hard-coded output token limit. Real value from Provider in future milestones."""
        return 4096

    def get_max_tokens(self) -> int:
        """Alias for output token limit."""
        return self.get_model_max_output_tokens() or 4096

    def token_counter(self, messages: list) -> int:
        """Stub token counter — returns conservative estimate without quantlitellm."""
        total = 0
        for msg in messages:
            content = str(msg.content) if hasattr(msg, "content") else str(msg.get("content", ""))
            total += estimate_text_tokens(content)
        return total

    def token_counter_with_history(self, messages_history: list, prompt: str) -> int:
        """Stub token counter including prompt. Conservative estimate."""
        count = self.token_counter(messages_history)
        count += estimate_text_tokens(prompt)
        return count
