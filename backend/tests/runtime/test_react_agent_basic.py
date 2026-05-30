"""M3 - ReactAgent basic loop tests.

RED phase: define the expected ReactAgent + LLMAdapter integration contract.
Tests verify:
- ReactAgent can be instantiated with LLMAdapter (no longer requires GenerativeModel)
- solve_task() in no-tool mode returns a final answer
- async_solve_task() produces correct answer via LLMAdapter path
- memory/history is accumulated correctly across iterations
- ResponseStats-style result is produced
"""

import asyncio
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest


# ─── Fake Tool for validation denial tests ───────────────────────────────────────

from app.runtime.tools.tool import Tool, ToolArgument


class FakeValidationTool(Tool):
    """Tool that requires validation. Used for testing validation denial paths."""

    name: str = "fake_validation_tool"
    need_validation: bool = True
    arguments: list = [ToolArgument(name="path", arg_type="string", required=True)]

    def execute(self, path: str) -> str:
        return f"would write to {path}"


class FakeLLMAdapter:
    """Fake LLMAdapter that returns canned responses for testing.

    Does NOT touch network or real providers.
    """

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or [
            "I am thinking step by step.",
        ]
        self.call_count = 0
        self.calls: list[dict] = []

    async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
        from app.runtime.generative_model import ResponseStats, TokenUsage

        idx = min(self.call_count, len(self.responses) - 1)
        text = self.responses[idx]
        self.call_count += 1

        self.calls.append({
            "model": model,
            "num_messages": len(messages_history),
        })

        return ResponseStats(
            response=text,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=model,
            finish_reason="stop",
        )

    async def async_stream_generate_with_history(
        self, messages_history: list, model: str, **kwargs
    ) -> AsyncIterator[str]:
        idx = min(self.call_count, len(self.responses) - 1)
        text = self.responses[idx]
        self.call_count += 1
        for char in text:
            yield char


class TestReactAgentWithLLMAdapter:
    """R3-1: ReactAgent accepts LLMAdapter and runs without GenerativeModel."""

    def test_agent_can_be_instantiated_with_llm_adapter(self):
        """Agent should accept llm_adapter in __init__ and not require GenerativeModel."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(responses=["answer"])
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
        )
        assert agent is not None

    def test_agent_solve_task_returns_final_answer_no_tools(self):
        """solve_task() in no-tool mode should return a final answer string."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(responses=["The answer is 42."])
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=3,
        )

        result = agent.solve_task("What is 6 * 7?", max_iterations=2, clear_memory=True)
        assert isinstance(result, str)
        assert result == "The answer is 42."

    def test_async_solve_task_produces_string_result(self):
        """async_solve_task() should return a non-empty string result."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(responses=["Python is a programming language."])
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=3,
        )

        async def run():
            return await agent.async_solve_task(
                "Tell me about Python.", max_iterations=2, clear_memory=True
            )

        result = asyncio.run(run())
        assert isinstance(result, str)
        assert len(result) > 0

    def test_agent_uses_llm_adapter_for_generation(self):
        """Agent should call LLMAdapter, not the copied GenerativeModel."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(responses=["response text"])
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        agent.solve_task("test prompt", max_iterations=2, clear_memory=True)
        assert fake.call_count >= 1, "LLMAdapter should have been called at least once"

    def test_agent_strips_protocol_tags_when_no_action_is_returned(self):
        """When the model returns only protocol XML, the final answer should stay user-visible."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(
            responses=[
                "<thinking><execution_analysis>你好，我可以帮你处理这个问题。</execution_analysis></thinking>",
            ]
        )
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=3,
        )

        result = agent.solve_task("你好", max_iterations=2, clear_memory=True)
        assert result == "你好，我可以帮你处理这个问题。"


class TestReactAgentMemoryHistory:
    """R3-1: Memory/history flows through to LLMAdapter correctly."""

    def test_memory_accumulates_across_iterations(self):
        """Each LLM call should receive accumulated memory messages."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(responses=[
            "<action><task_complete><answer>final answer</answer></task_complete></action>",
        ])
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=5,
        )

        agent.solve_task("test memory", max_iterations=5, clear_memory=True)

        assert fake.call_count >= 1, f"Expected at least 1 LLM call, got {fake.call_count}"
        # Verify memory was passed to the LLM call
        assert len(fake.calls) >= 1
        assert fake.calls[0]["num_messages"] >= 2, (
            f"Expected at least 2 messages (system + user) in first call, got {fake.calls[0]['num_messages']}"
        )

    def test_system_message_is_in_history(self):
        """System prompt should appear as first message in history."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(responses=["response"])
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        agent.solve_task("test", max_iterations=2, clear_memory=True)

        assert fake.call_count >= 1
        # System message + user message = at least 2
        assert fake.calls[0]["num_messages"] >= 2, "History should contain system + user messages"


class TestReactAgentStreaming:
    """R3-1: Streaming path also goes through LLMAdapter."""

    def test_streaming_mode_parameter_accepted_without_crash(self):
        """streaming=True is accepted and does not crash the agent.

        M3 scope: streaming is intentionally out of scope.
        The agent accepts streaming=True, but both branches call the same
        non-streaming LLM path. Streaming delta output is M4/M5 territory.
        This test only verifies the parameter doesn't break the loop.
        """
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(responses=["streamed response"])
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        async def run():
            return await agent.async_solve_task(
                "test", max_iterations=2, streaming=True, clear_memory=True
            )

        result = asyncio.run(run())
        assert isinstance(result, str)
        assert fake.call_count >= 1, "LLMAdapter should be called"

    def test_streaming_low_signal_response_falls_back_to_non_streaming_answer(self):
        """If streaming only yields markdown shell, the final answer should come from fallback generation."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        class LowSignalStreamingAdapter(FakeLLMAdapter):
            async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
                from app.runtime.generative_model import ResponseStats, TokenUsage

                self.call_count += 1
                return ResponseStats(
                    response="你好，我是正常回复。",
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history: list, model: str, **kwargs
            ) -> AsyncIterator[str]:
                self.call_count += 1
                for char in "####":
                    yield char

        fake = LowSignalStreamingAdapter()
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        async def run():
            return await agent.async_solve_task(
                "test",
                max_iterations=2,
                streaming=True,
                clear_memory=True,
            )

        result = asyncio.run(run())
        assert result == "你好，我是正常回复。"


    def test_streaming_incomplete_identity_reply_falls_back_to_full_answer(self):
        """Streaming '我是' should be retried instead of becoming the final answer."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        class IncompleteIdentityStreamingAdapter(FakeLLMAdapter):
            async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
                from app.runtime.generative_model import ResponseStats, TokenUsage

                self.call_count += 1
                return ResponseStats(
                    response="我是 AgentHub 的运行时助手。",
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history: list, model: str, **kwargs
            ) -> AsyncIterator[str]:
                self.call_count += 1
                for char in "我是":
                    yield char

        fake = IncompleteIdentityStreamingAdapter()
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        async def run():
            return await agent.async_solve_task(
                "你是谁",
                max_iterations=2,
                streaming=True,
                clear_memory=True,
            )

        result = asyncio.run(run())
        assert result == "我是 AgentHub 的运行时助手。"

    def test_streaming_incomplete_xml_prefix_falls_back_to_full_answer(self):
        """A lone '<' should be treated as an incomplete protocol prefix, not a final reply."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        class IncompleteXmlPrefixStreamingAdapter(FakeLLMAdapter):
            async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
                from app.runtime.generative_model import ResponseStats, TokenUsage

                self.call_count += 1
                return ResponseStats(
                    response="当然可以，下面是一个 Java 版的 HelloWorld。",
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history: list, model: str, **kwargs
            ) -> AsyncIterator[str]:
                self.call_count += 1
                yield "<"

        fake = IncompleteXmlPrefixStreamingAdapter()
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=2,
        )

        async def run():
            return await agent.async_solve_task(
                "帮我写一个java版的helloworld吗",
                max_iterations=2,
                streaming=True,
                clear_memory=True,
            )

        result = asyncio.run(run())
        assert result == "当然可以，下面是一个 Java 版的 HelloWorld。"


class TestValidationDenial:
    """Verify tool validation denial does not crash with 'await bool'."""

    def test_validation_denied_does_not_crash_with_await_bool(self):
        """When a tool with need_validation=True is denied, no 'await bool' error occurs."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(
            responses=["<action><fake_validation_tool><path>/tmp/test.txt</path></fake_validation_tool></action>"]
        )
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[FakeValidationTool()],
            max_iterations=3,
        )

        # Should not raise "object bool can't be used in 'await' expression"
        result = agent.solve_task("write something", max_iterations=3, clear_memory=True)

        # Denial returns an error message, not a crash
        assert isinstance(result, str)
        assert "denied" in result or "Error" in result

    def test_validation_denied_async_path(self):
        """Async solve_task also handles validation denial without crash."""
        import asyncio as _asyncio
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = FakeLLMAdapter(
            responses=["<action><fake_validation_tool><path>/tmp/test.txt</path></fake_validation_tool></action>"]
        )
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[FakeValidationTool()],
            max_iterations=3,
        )

        async def run():
            return await agent.async_solve_task(
                "write something",
                max_iterations=3,
                clear_memory=True,
            )

        result = _asyncio.run(run())
        assert isinstance(result, str)
        assert "denied" in result or "Error" in result
