# -*- coding: utf-8 -*-
"""Direct-reply protocol tests.

Covers the "direct reply first, action only when needed" runtime protocol:
- Direct plain-text answer without <action> is a first-class success path.
- No-action protocol XML (thinking-only) is normalized to visible text.
- Action call path (task_complete, tools) is not affected.
- Low-signal streaming (e.g. "####") triggers non-streaming fallback.
- Normal streaming text does NOT trigger fallback.
- Direct reply is propagated as message_end.final_content.
"""

import asyncio
from typing import AsyncIterator

import pytest

from app.runtime.generative_model import ResponseStats, TokenUsage


# ─── Fake LLMAdapters ────────────────────────────────────────────────────────

class StreamingFakeAdapter:
    """Fake adapter that yields text character-by-character for streaming tests."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or ["response"]
        self.call_count = 0

    async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
        idx = min(self.call_count, len(self.responses) - 1)
        text = self.responses[idx]
        self.call_count += 1
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


class LowSignalStreamingAdapter:
    """Fake adapter: streaming yields low-signal shell, non-streaming returns real answer."""

    def __init__(self, fallback_text: str):
        self.fallback_text = fallback_text
        self.stream_called = False
        self.non_stream_called = False

    async def async_generate_with_history(self, messages_history: list, model: str, **kwargs):
        self.non_stream_called = True
        return ResponseStats(
            response=self.fallback_text,
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=model,
            finish_reason="stop",
        )

    async def async_stream_generate_with_history(
        self, messages_history: list, model: str, **kwargs
    ) -> AsyncIterator[str]:
        self.stream_called = True
        for char in "####":
            yield char


# ─── Test: Direct reply (no <action>) ────────────────────────────────────────


class TestDirectReplyNoAction:
    """Verify plain-text response without <action> is a successful final answer."""

    def test_direct_reply_returns_plain_text_as_answer(self):
        """Model returns '你好！' without <action> → answer is '你好！', no tool parsing."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = StreamingFakeAdapter(responses=["你好！"])
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=3,
        )

        result = agent.solve_task("你好", max_iterations=3, clear_memory=True)

        assert result == "你好！"
        assert fake.call_count == 1  # only one LLM call, no retry

    def test_direct_reply_no_tool_call(self):
        """No-action response must NOT trigger tool call detection."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        collected: list[tuple[str, dict]] = []

        class CollectingEmitter:
            def emit(self, event: str, data: dict | None = None) -> None:
                collected.append((event, data or {}))

        fake = StreamingFakeAdapter(responses=["hello world"])
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            event_emitter=CollectingEmitter(),
            max_iterations=3,
        )

        result = agent.solve_task("greet me", max_iterations=3, clear_memory=True)

        assert result == "hello world"
        event_names = [name for name, _ in collected]
        assert "tool_execution_start" not in event_names
        assert "tool_execution_end" not in event_names

    def test_direct_reply_does_not_trigger_retry(self):
        """Direct reply with visible content must NOT trigger non-streaming fallback."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        class CountingAdapter(StreamingFakeAdapter):
            pass

        fake = CountingAdapter(responses=["正常回复内容。"])
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

        assert result == "正常回复内容。"
        assert fake.call_count == 1  # no fallback retry

    def test_direct_reply_async_streaming(self):
        """async_solve_task with streaming=True on direct reply works."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = StreamingFakeAdapter(responses=["异步流式直接回复。"])
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
        assert result == "异步流式直接回复。"


# ─── Test: No-action protocol XML normalization ───────────────────────────────


class TestNoActionProtocolNormalization:
    """Verify thinking/XML-only responses are normalized to visible text."""

    def test_thinking_only_xml_normalized_to_visible_text(self):
        """<thinking><execution_analysis>你好</execution_analysis></thinking> → '你好'."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = StreamingFakeAdapter(
            responses=[
                "<thinking><execution_analysis>你好，我可以帮你处理这个问题。</execution_analysis></thinking>"
            ]
        )
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=3,
        )

        result = agent.solve_task("你好", max_iterations=3, clear_memory=True)
        assert result == "你好，我可以帮你处理这个问题。"
        assert "<thinking>" not in result

    def test_nested_xml_with_plain_text_extracted(self):
        """Nested XML with inner text is extracted correctly."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = StreamingFakeAdapter(
            responses=[
                "<thinking>\n<execution_analysis>你好</execution_analysis>\n<decision_matrix>done</decision_matrix>\n</thinking>"
            ]
        )
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=3,
        )

        result = agent.solve_task("test", max_iterations=3, clear_memory=True)
        assert result in ("你好", "你好 done", "done")
        assert "<execution_analysis>" not in result

    def test_pure_markdown_header_only_low_signal(self):
        """Pure markdown header with no visible text is detected as low-signal."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        low_signal = LowSignalStreamingAdapter(fallback_text="这是fallback回复。")
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=low_signal,
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
        assert result == "这是fallback回复。"
        assert low_signal.stream_called
        assert low_signal.non_stream_called


# ─── Test: Action call path regression ───────────────────────────────────────


class TestActionCallPathRegression:
    """Verify action call path is not affected by direct-reply changes."""

    def test_task_complete_still_works(self):
        """<action><task_complete><answer>ok</answer></task_complete></action> → 'ok'."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = StreamingFakeAdapter(
            responses=["<action><task_complete><answer>ok</answer></task_complete></action>"]
        )
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=3,
        )

        result = agent.solve_task("say ok", max_iterations=3, clear_memory=True)
        assert result == "ok"

    def test_action_call_emits_tool_events(self):
        """Action call should emit tool_execution_start/end events."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        collected: list[tuple[str, dict]] = []

        class CollectingEmitter:
            def emit(self, event: str, data: dict | None = None) -> None:
                collected.append((event, data or {}))

        fake = StreamingFakeAdapter(
            responses=["<action><task_complete><answer>final</answer></task_complete></action>"]
        )
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            event_emitter=CollectingEmitter(),
            max_iterations=3,
        )

        result = agent.solve_task("test", max_iterations=3, clear_memory=True)
        assert result == "final"
        event_names = [name for name, _ in collected]
        assert "tool_execution_start" in event_names
        assert "tool_execution_end" in event_names

    def test_action_xml_with_visible_text_normalized(self):
        """Action XML with plain text inside is normalized correctly."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        fake = StreamingFakeAdapter(
            responses=["<action><task_complete><answer>答案是42。</answer></task_complete></action>"]
        )
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=fake,
            memory=AgentMemory(),
            tools=[],
            max_iterations=3,
        )

        result = agent.solve_task("test", max_iterations=3, clear_memory=True)
        assert result == "答案是42。"


# ─── Test: Low-signal detection ───────────────────────────────────────────────


class TestLowSignalDetection:
    """Verify low-signal streaming content triggers fallback correctly."""

    def test_hash_only_is_low_signal(self):
        """'####' contains no visible text and should be detected as low-signal."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        assert agent._is_low_signal_response("####") is True

    def test_markdown_header_only_is_low_signal(self):
        """Pure markdown headers without content are low-signal."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        # "## " is only whitespace after #, no visible content -> low-signal
        assert agent._is_low_signal_response("## ") is True
        assert agent._is_low_signal_response("###") is True
        # "# 标题" has visible Chinese characters after #, NOT low-signal
        assert agent._is_low_signal_response("# 标题") is False

    def test_normal_text_is_not_low_signal(self):
        """Normal Chinese or English text is NOT low-signal."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        assert agent._is_low_signal_response("你好") is False
        assert agent._is_low_signal_response("hello world") is False
        assert agent._is_low_signal_response("### 标题\n实际内容") is False

    def test_low_signal_streaming_triggers_fallback(self):
        """Streaming '####' should trigger non-streaming fallback."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        low_signal = LowSignalStreamingAdapter(fallback_text="你好，我是正常回复。")
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=low_signal,
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
        assert low_signal.stream_called
        assert low_signal.non_stream_called

    def test_normal_streaming_does_not_fallback(self):
        """Streaming normal text should NOT trigger non-streaming fallback."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        class NormalTextAdapter:
            """Adapter that streams normal text via async_generate_with_history(streaming=True)."""
            def __init__(self):
                self.stream_called = False
                self.non_stream_called = False

            async def async_generate_with_history(self, messages_history, model, **kwargs):
                import asyncio
                full = ""
                async for delta in self.async_stream_generate_with_history(messages_history, model, **kwargs):
                    full += delta
                self.non_stream_called = True
                from app.runtime.generative_model import ResponseStats, TokenUsage
                return ResponseStats(
                    response=full,
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ) -> AsyncIterator[str]:
                self.stream_called = True
                for char in "正常回复内容。":
                    yield char

        normal = NormalTextAdapter()
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=normal,
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
        assert result == "正常回复内容。"
        assert normal.stream_called
        assert not normal.non_stream_called  # fallback NOT triggered


# ─── Test: Final answer normalization ─────────────────────────────────────────


class TestFinalAnswerNormalization:
    """Verify _normalize_final_answer strips protocol markup from direct replies."""

    def test_plain_text_unchanged(self):
        """Plain text is returned as-is."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        assert agent._normalize_final_answer("你好世界") == "你好世界"

    def test_thinking_tag_stripped(self):
        """<thinking> tags are stripped."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        result = agent._normalize_final_answer(
            "<thinking>Some thinking content</thinking>"
        )
        assert "<thinking>" not in result
        assert "Some thinking content" in result

    def test_answer_tag_extracted(self):
        """<answer> tag content is extracted."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        result = agent._normalize_final_answer(
            "<thinking><answer>Final answer text</answer></thinking>"
        )
        assert result == "Final answer text"

    def test_empty_string_unchanged(self):
        """Empty string returns empty string."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        assert agent._normalize_final_answer("") == ""

    def test_protocol_tag_names_detection(self):
        """_looks_like_protocol_markup correctly identifies protocol XML."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        assert agent._looks_like_protocol_markup("<thinking>test</thinking>") is True
        assert agent._looks_like_protocol_markup("<action><tool></action>") is True
        assert agent._looks_like_protocol_markup("hello world") is False
        assert agent._looks_like_protocol_markup("<div>hello</div>") is False


# ─── Test: Incomplete direct reply detection ──────────────────────────────────


class TestIncompleteDirectReplyDetection:
    """Verify _is_incomplete_direct_reply correctly identifies truncated streaming phrases."""

    def test_short_truncated_phrases_detected(self):
        """Short Chinese opening phrases like '我能', '可以', '好的' are flagged as incomplete (exact match)."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        for phrase in ("我能", "可以", "当然", "好的", "好的，", "我来", "让我", "请稍等", "首先", "我可以", "我会", "我将", "没问题", "这个问"):
            assert agent._is_incomplete_direct_reply(phrase) is True, f"'{phrase}' should be incomplete"

    def test_short_english_phrases_detected(self):
        """Short English opening phrases like 'Sure', 'Okay', 'I can' are flagged as incomplete."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        for phrase in ("Sure", "Okay", "I can", "Let me", "I'll", "Certainly", "Of course"):
            assert agent._is_incomplete_direct_reply(phrase) is True, f"'{phrase}' should be incomplete"

    def test_longer_phrase_with_punctuation_not_detected(self):
        """Complete sentences that start with short phrases but end with punctuation are NOT incomplete."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        # These start with short phrases but have more content after - NOT incomplete
        assert agent._is_incomplete_direct_reply("我可以帮你。") is False
        assert agent._is_incomplete_direct_reply("好的，我来处理。") is False
        assert agent._is_incomplete_direct_reply("Sure, let me help.") is False
        assert agent._is_incomplete_direct_reply("I can help you.") is False

    def test_normal_complete_text_not_detected(self):
        """Normal complete Chinese and English text is NOT flagged as incomplete."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        assert agent._is_incomplete_direct_reply("你好，世界") is False
        assert agent._is_incomplete_direct_reply("当然，可以。") is False
        assert agent._is_incomplete_direct_reply("当然，可以") is False
        assert agent._is_incomplete_direct_reply("Let me help you.") is False
        assert agent._is_incomplete_direct_reply("Certainly, I'll help.") is False

    def test_empty_and_long_strings_not_detected(self):
        """Empty string and strings over 15 chars are NOT flagged as incomplete."""
        from app.runtime.react_agent import Agent

        agent = Agent.__new__(Agent)
        assert agent._is_incomplete_direct_reply("") is False
        assert agent._is_incomplete_direct_reply("我能能能能能能能能能能能能") is False  # long "我能..."
        assert agent._is_incomplete_direct_reply("好的，非常感谢你的帮助。") is False  # starts with 好的 but too long


class TestIncompleteDirectReplyFallback:
    """Verify incomplete streaming phrases trigger non-streaming fallback."""

    def test_incomplete_truncated_phrase_triggers_fallback(self):
        """Streaming '我能' should trigger non-streaming fallback."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        class IncompleteStreamingAdapter:
            def __init__(self, fallback_text: str):
                self.fallback_text = fallback_text
                self.stream_called = False
                self.fallback_called = False

            async def async_generate_with_history(self, messages_history, model, **kwargs):
                self.fallback_called = True
                from app.runtime.generative_model import ResponseStats, TokenUsage
                return ResponseStats(
                    response=self.fallback_text,
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ) -> AsyncIterator[str]:
                self.stream_called = True
                for char in "我能":
                    yield char

        fallback_text = "我能帮你查看代码并修复问题。"
        adapter = IncompleteStreamingAdapter(fallback_text=fallback_text)
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=adapter,
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
        assert adapter.stream_called
        assert adapter.fallback_called  # fallback WAS triggered
        assert result == fallback_text

    def test_complete_short_sentence_does_not_trigger_fallback(self):
        """Complete short sentence like '可以，我来帮你。' should NOT trigger fallback."""
        from app.runtime.react_agent import Agent
        from app.runtime.memory import AgentMemory

        class CompleteTextAdapter:
            def __init__(self):
                self.stream_called = False
                self.fallback_called = False

            async def async_generate_with_history(self, messages_history, model, **kwargs):
                self.fallback_called = True
                from app.runtime.generative_model import ResponseStats, TokenUsage
                return ResponseStats(
                    response="SHOULD NOT USE THIS",
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                    model=model,
                    finish_reason="stop",
                )

            async def async_stream_generate_with_history(
                self, messages_history, model, **kwargs
            ) -> AsyncIterator[str]:
                self.stream_called = True
                for char in "可以，我来帮你。":
                    yield char

        adapter = CompleteTextAdapter()
        agent = Agent(
            model_name="qwen-plus",
            llm_adapter=adapter,
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
        assert adapter.stream_called
        assert not adapter.fallback_called  # fallback NOT triggered
        assert result == "可以，我来帮你。"

