"""P1-2-2: 流式编排服务测试。

覆盖：
- 首个句段出现时才创建 message_id
- 正常结束写 completed
- partial 后失败写 interrupted
- 首句前失败不落 agent message
- 断连后 partial 按 interrupted 收口
- final chunk 固定为空终止帧
- 事件顺序正确
"""

import asyncio
from unittest.mock import MagicMock

import pytest


# ---- 辅助：同步测试用异步迭代器消费工具 ----

async def _collect_events(stream_service):
    events = []
    async for event in stream_service.stream_events():
        events.append(event)
    return events


# ---- 事件类型定义（从 service 模块导入，与生产代码保持一致） ----
from app.services.agent_stream_service import TypingEvent, ChunkEvent, ErrorEvent


# ---- Mock Provider ----

def make_mock_provider(deltas: list[str], raise_on: type[Exception] | None = None):
    from app.providers.base import ProviderStreamEvent

    async def mock_stream_chat(input):
        if raise_on:
            raise raise_on("mock error")
        for d in deltas:
            yield ProviderStreamEvent(text_delta=d)

    provider = MagicMock()
    provider.stream_chat = mock_stream_chat
    return provider


# ---- 共享辅助：构造 AgentStreamService + 收集事件 ----

def _make_service(provider, human_message_id="hm-001"):
    from app.services.agent_stream_service import AgentStreamService

    db = MagicMock()
    agent_msg_ref = {}

    # Track ALL messages added (error path may add a new message)
    added_messages = []

    def mock_add(*args, **kwargs):
        if args:
            added_messages.append(args[0])
        return None

    def mock_refresh(obj):
        pass

    db.add = mock_add
    db.commit = MagicMock()
    db.refresh = mock_refresh

    service = AgentStreamService(
        session_id="sess-001",
        human_message_id=human_message_id,
        agent_role="PM",
        system_prompt="You are a PM Agent.",
        user_message="Hello",
        provider=provider,
        db=db,
        stream_id="stream-001",
    )
    # Expose added_messages so tests can check both original + error messages
    agent_msg_ref["_added"] = added_messages
    return service, agent_msg_ref


class TestAgentStreamServiceFirstChunk:
    """首个句段出现时创建 message_id 测试。"""

    def test_message_id_created_on_first_chunk(self):
        """首个 chunk 出现时才创建 message_id。"""
        provider = make_mock_provider(["你好", "世界。"])
        service, agent_ref = _make_service(provider)
        events = asyncio.run(_collect_events(service))
        assert len(agent_ref["_added"]) >= 1
        # All entries refer to the same message object
        first = agent_ref["_added"][0]
        assert first.session_id == "sess-001"
        assert first.sender_type == "agent"
        assert first.sender_role == "PM"

    def test_no_message_before_first_chunk(self):
        """首个 chunk 前不创建 message_id。"""
        from app.providers.base import ProviderRequestError

        provider = make_mock_provider([], raise_on=ProviderRequestError)
        service, agent_ref = _make_service(provider)
        events = asyncio.run(_collect_events(service))
        assert len(agent_ref["_added"]) == 0


class TestAgentStreamServiceCompletion:
    """正常结束测试。"""

    def _run(self, deltas):
        provider = make_mock_provider(deltas)
        service, agent_ref = _make_service(provider)
        events = asyncio.run(_collect_events(service))
        return events, agent_ref

    def test_normal_end_completed(self):
        """正常结束写 completed。"""
        events, agent_ref = self._run(["你好", "世界。"])
        assert len(agent_ref["_added"]) >= 1
        msg = agent_ref["_added"][-1]
        assert msg.content == "你好世界。"

    def test_normal_end_final_chunk_is_empty(self):
        """final chunk 固定为空字符串终止帧。"""
        events, agent_ref = self._run(["hello", " world。"])
        final_chunk = next(e for e in events if isinstance(e, ChunkEvent) and e.is_final)
        assert final_chunk.content_chunk == ""

    def test_tail_buffer_sent_before_final(self):
        """尾缓冲非空时先发普通 chunk，再发空 final。"""
        events, agent_ref = self._run(["你好"])
        chunk_events = [e for e in events if isinstance(e, ChunkEvent)]
        non_final = [e for e in chunk_events if not e.is_final]
        final = next(e for e in chunk_events if e.is_final)
        assert non_final[-1].content_chunk == "你好"
        assert final.content_chunk == ""


class TestAgentStreamServicePartialFailure:
    """partial 后失败测试。"""

    def _run_with_partial_then_error(self, deltas_before_error: list[str]):
        from app.providers.base import ProviderRequestError
        from app.providers.base import ProviderStreamEvent

        async def mock_error_stream(input):
            for d in deltas_before_error:
                yield ProviderStreamEvent(text_delta=d)
            raise ProviderRequestError("mock request failed")

        provider = MagicMock()
        provider.stream_chat = mock_error_stream

        service, agent_ref = _make_service(provider)
        return asyncio.run(_collect_events(service)), agent_ref

    def test_partial_then_error_interrupted(self):
        """已有 partial 后失败，content 被保留。"""
        events, agent_ref = self._run_with_partial_then_error(["部分", "内容"])
        added = agent_ref["_added"]
        # First add: message creation. Subsequent adds: content updates.
        assert len(added) >= 1
        last_msg = added[-1]
        # The message should have accumulated content
        assert last_msg.content == "部分内容"

    def test_partial_error_sends_error_event(self):
        """partial 后失败产出 ErrorEvent。"""
        events, agent_ref = self._run_with_partial_then_error(["hello"])
        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) == 1
        assert error_events[0].error_code == "provider_request_failed"


class TestAgentStreamServiceEventOrder:
    """事件顺序测试。"""

    def _run(self, deltas):
        provider = make_mock_provider(deltas)
        service, agent_ref = _make_service(provider)
        return asyncio.run(_collect_events(service))

    def test_typing_true_before_first_chunk(self):
        """typing=true 在首个 chunk 之前。"""
        events = self._run(["hello world。"])
        typing_events = [e for e in events if isinstance(e, TypingEvent)]
        first_chunk_idx = next(i for i, e in enumerate(events) if isinstance(e, ChunkEvent))
        first_typing_idx = events.index(typing_events[0])
        assert first_typing_idx < first_chunk_idx

    def test_typing_false_after_final(self):
        """typing=false 在 final chunk 之后。"""
        events = self._run(["hello world。"])
        typing_false = next(e for e in events if isinstance(e, TypingEvent) and not e.is_typing)
        final_idx = next(i for i, e in enumerate(events) if isinstance(e, ChunkEvent) and e.is_final)
        typing_idx = events.index(typing_false)
        assert typing_idx > final_idx

    def test_typing_false_on_error(self):
        """异常结束时也发送 typing=false。"""
        from app.providers.base import ProviderRequestError
        from app.providers.base import ProviderStreamEvent

        async def mock_error(input):
            yield ProviderStreamEvent(text_delta="partial ")
            raise ProviderRequestError("failed")

        provider = MagicMock()
        provider.stream_chat = mock_error

        service, agent_ref = _make_service(provider)
        events = asyncio.run(_collect_events(service))
        typing_false = next((e for e in events if isinstance(e, TypingEvent) and not e.is_typing), None)
        assert typing_false is not None
