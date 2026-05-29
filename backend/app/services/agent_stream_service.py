"""流式编排服务 (Agent Stream Service)。

---

## ⚠️ 废弃声明（M0 现状收口）

本文 件 **`agent_stream_service.py`** 是旧试验性链路，**不是当前主链路**。

- **当前主链路**：`backend/app/api/ws.py` + `FixedAgentResponder`
- **本文 件**：`agent_stream_service.py` — 既往试验性流式链路尝试
- **消息字段不兼容**：本文 件使用 `content_type`、`delivery_status`，与现有 `Message` 模型不一致
- **后续里程碑不得以此文件作为新 Runtime 的实施基座**
- **最终替代者**：M5 新增 `runtime_agent_service.py`（接入 `react_agent.py` 后）

可参考本文 件的"句子聚合 / typing 生命周期"思路，但不得继续扩展。

---

将 Provider 的原始 delta 升级为句段级业务事件流：
- typing 生命周期管理
- 句段聚合（委托给 SentenceChunker）
- 首个句段时创建 agent message
- 正常/异常结束时 finalize 消息
- 产出稳定的业务事件序列
"""

import uuid
from dataclasses import dataclass
from typing import AsyncIterator

from sqlalchemy.orm import Session

from app.models.message import Message
from app.providers.base import (
    BaseProvider,
    ProviderInput,
    ProviderNotConfiguredError,
    ProviderRequestError,
    ProviderResponseInvalidError,
)
from app.services.sentence_chunker import SentenceChunker


# ---- 错误码映射 ----

_ERROR_CODE_MAP = {
    ProviderNotConfiguredError: "provider_not_configured",
    ProviderRequestError: "provider_request_failed",
    ProviderResponseInvalidError: "provider_response_invalid",
}


def _map_error(exc: Exception) -> tuple[str, str]:
    for exc_type, code in _ERROR_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return code, str(exc)
    return "unknown", str(exc) or "Unknown error"


# ---- 业务事件类型 ----

@dataclass
class TypingEvent:
    is_typing: bool


@dataclass
class ChunkEvent:
    content_chunk: str
    is_final: bool


@dataclass
class ErrorEvent:
    error_code: str
    error_message: str


class AgentStreamService:
    """流式编排服务。

    不持有 WebSocket 对象，不处理多会话并发调度。
    负责：
    - typing 生命周期
    - 句段聚合
    - 消息创建与 finalize
    - 产出面向 ws.py 的业务事件序列
    """

    def __init__(
        self,
        session_id: str,
        human_message_id: str,
        agent_role: str,
        system_prompt: str,
        user_message: str,
        provider: BaseProvider,
        db: Session,
        stream_id: str | None = None,
    ) -> None:
        self.session_id = session_id
        self.human_message_id = human_message_id
        self.agent_role = agent_role
        self.provider = provider
        self.db = db
        self.stream_id = stream_id or str(uuid.uuid4())
        self._system_prompt = system_prompt
        self._user_message = user_message

        self._agent_message: Message | None = None
        self._accumulated_content: str = ""
        self._chunker = SentenceChunker()
        self._ended = False

    async def stream_events(self) -> AsyncIterator[TypingEvent | ChunkEvent | ErrorEvent]:
        """生成业务事件序列。"""
        yield TypingEvent(is_typing=True)

        try:
            agent_message_created = False

            async for delta in self.provider.stream_chat(
                ProviderInput(
                    system_prompt=self._system_prompt,
                    user_message=self._user_message,
                    model="",
                )
            ):
                if not agent_message_created:
                    self._agent_message = Message(
                        session_id=self.session_id,
                        sender_type="agent",
                        sender_role=self.agent_role,
                        content="",
                        content_type="text",
                    )
                    self.db.add(self._agent_message)
                    self.db.commit()
                    self.db.refresh(self._agent_message)
                    agent_message_created = True

                for chunk in self._chunker.feed(delta.text_delta):
                    self._accumulated_content += chunk
                    self._update_message()
                    yield ChunkEvent(content_chunk=chunk, is_final=False)

            # Normal end
            tail_chunks = self._chunker.flush(force=True)
            for chunk in tail_chunks:
                self._accumulated_content += chunk
                self._update_message()
                yield ChunkEvent(content_chunk=chunk, is_final=False)

            # Final empty frame
            yield ChunkEvent(content_chunk="", is_final=True)

            self._agent_message.delivery_status = "completed"
            self._update_message()

        except Exception as exc:  # noqa: BLE001
            code, msg = _map_error(exc)
            # Flush remaining buffer BEFORE error handling
            tail_chunks = self._chunker.flush(force=True)
            for chunk in tail_chunks:
                self._accumulated_content += chunk
                self._update_message()
                yield ChunkEvent(content_chunk=chunk, is_final=False)
            self._do_error_end(code, msg, agent_message_created)
            yield ErrorEvent(error_code=code, error_message=msg)

        finally:
            if not self._ended:
                self._ended = True
                yield TypingEvent(is_typing=False)

    def _update_message(self) -> None:
        if self._agent_message is None:
            return
        self._agent_message.content = self._accumulated_content
        self.db.add(self._agent_message)
        self.db.commit()

    def _do_error_end(
        self,
        code: str,
        message: str,
        agent_created: bool,
    ) -> None:
        # Only update if we already had a message with accumulated content
        if agent_created and self._agent_message is not None and self._accumulated_content:
            self._agent_message.delivery_status = "interrupted"
            self._update_message()

    def interrupt(self) -> None:
        """WebSocket 断开时调用，执行中断收口。"""
        if self._ended:
            return
        self._ended = True
        if self._agent_message is not None and self._accumulated_content:
            self._agent_message.delivery_status = "interrupted"
            self._agent_message.content = self._accumulated_content
            self.db.add(self._agent_message)
            self.db.commit()
