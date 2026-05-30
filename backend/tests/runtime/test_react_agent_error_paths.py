"""M3 - ReactAgent error path tests.

Tests verify:
- Tool-not-found: controllable error, no crash
- XML parse failure: controllable error, no crash
- LLMAdapter raises: error is caught and returned as answer string
- All error paths return a string (not an exception that kills the loop)
"""

import asyncio
from typing import AsyncIterator

import pytest

from app.runtime.generative_model import ResponseStats, TokenUsage


# ─── Fakes ────────────────────────────────────────────────────────────────────

class FakeLLMAdapterOK:
    """Fake that returns a normal response including <action> XML."""

    def __init__(self, text: str = "<action><task_complete><answer>done</answer></task_complete></action>"):
        self._text = text

    async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
        return ResponseStats(
            response=self._text,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=model,
            finish_reason="stop",
        )

    async def async_stream_generate_with_history(
        self, messages_history: list, model: str, **kwargs
    ) -> AsyncIterator[str]:
        for char in self._text:
            yield char


class FakeLLMAdapterError:
    """Fake that raises an exception on generation."""

    def __init__(self, exc: Exception):
        self._exc = exc

    async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
        raise self._exc


class TestToolNotFoundErrorHandling:
    """R3-3: Tool-not-found should be handled gracefully."""

    def test_nonexistent_tool_returns_error_result(self):
        """When LLM calls a tool not in tool list, Agent should return error string, not crash."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        # Response includes <action> tags so tool lookup is attempted
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=FakeLLMAdapterOK(
                text='<action><nonexistent_tool><arg1>value1</arg1></nonexistent_tool></action>'
            ),
            memory=AgentMemory(),
            tools=[],  # no tools registered
            max_iterations=3,
        )

        # Should not raise — error should be caught and returned as string
        result = agent.solve_task("call nonexistent tool", max_iterations=2, clear_memory=True)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_tool_name_in_response_does_not_crash(self):
        """Unknown tool in XML response should not crash the agent."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=FakeLLMAdapterOK(
                text='<action><foobar><x>1</x></foobar></action>'
            ),
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        # Must not raise
        result = agent.solve_task("use foobar", max_iterations=2, clear_memory=True)
        assert isinstance(result, str)


class TestXMLParseErrorHandling:
    """R3-3: Malformed XML in model response should be handled gracefully."""

    def test_malformed_xml_does_not_crash_agent(self):
        """Malformed XML should be handled without raising uncaught exceptions."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        # Response with malformed XML (unclosed tags) but wrapped in <action>
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=FakeLLMAdapterOK(
                text="Here is my answer. <action><tool>value</action>"
            ),
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        # Should not raise
        result = agent.solve_task("give malformed xml", max_iterations=2, clear_memory=True)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_response_handled(self):
        """Empty response from LLM should not crash the agent."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=FakeLLMAdapterOK(text=""),
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        result = agent.solve_task("say nothing", max_iterations=2, clear_memory=True)
        assert isinstance(result, str)

    def test_response_without_action_tag_handled(self):
        """Plain text response (no XML action tag) should be treated as final answer."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        # Plain text without action tags = final answer (terminates in 1 iteration)
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=FakeLLMAdapterOK(
                text="The weather is sunny today. This is my final answer."
            ),
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        result = agent.solve_task("what is the weather", max_iterations=2, clear_memory=True)
        assert isinstance(result, str)
        assert len(result) > 0


class TestLLMAdapterErrorHandling:
    """R3-3: LLMAdapter errors should be caught and returned as answer strings."""

    def test_llm_adapter_raises_returns_error_string(self):
        """When LLMAdapter raises, the agent should return error string, not propagate exception."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=FakeLLMAdapterError(
                RuntimeError("Upstream model unavailable")
            ),
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        # Should NOT raise — error must be caught inside solve_task
        result = agent.solve_task("test upstream failure", max_iterations=2, clear_memory=True)

        assert isinstance(result, str)
        assert "Error" in result or "error" in result.lower(), (
            f"Expected error string, got: {result}"
        )

    def test_llm_adapter_raises_async_returns_error(self):
        """Async LLM error should be caught in async_solve_task."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=FakeLLMAdapterError(
                ConnectionError("Network unreachable")
            ),
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        async def run():
            return await agent.async_solve_task(
                "test async error", max_iterations=2, clear_memory=True
            )

        result = asyncio.run(run())
        assert isinstance(result, str)
        assert "Error" in result or "error" in result.lower()


class TestErrorPathControllability:
    """R3-3: All error paths must be controllable and not kill the loop."""

    def test_error_in_observe_does_not_crash_loop(self):
        """Error in _async_observe_response should be caught, not propagate."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        # Invalid XML that could cause parse errors, wrapped in <action>
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=FakeLLMAdapterOK(
                text='<action><tool><nested><deep>value</deep></nested></tool></action>'
            ),
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        result = agent.solve_task("deeply nested xml", max_iterations=2, clear_memory=True)
        assert isinstance(result, str)

    def test_multiple_iterations_all_error_paths_contained(self):
        """Multiple iterations with potential errors should all be contained."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=FakeLLMAdapterOK(
                text="<action><task_complete><answer>final answer</answer></task_complete></action>"
            ),
            memory=AgentMemory(),
            tools=[],
            max_iterations=5,
        )

        result = agent.solve_task("simple task", max_iterations=5, clear_memory=True)
        assert isinstance(result, str)
        assert len(result) > 0
