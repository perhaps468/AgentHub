"""P1-3-2 FixedAgentResponder.

固定流式回复器，替代真实 LLM Provider：

设计契约（P1-3 task spec Section 6.4）:
- 输入: session_id, user_message, agent_role, db, stream_id
- 输出: 异步生成 message_start -> message_delta* -> message_end
- 行为:
  1. 根据固定模板生成 deterministic 文本
  2. 文本切分为若干固定片段，按顺序输出
  3. 默认输出来源写入 metadata.source = "fixed_responder"
  4. 不调用真实 provider，不读取真实模型配置，不消费历史上下文
"""

import asyncio
import uuid

from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.session import utcnow


_FIXED_TEMPLATE = (
    "你好！我已经收到你的消息「{user_message}」。"
    "作为你的 {agent_role}，我会认真思考并给出回应。"
    "当前系统处于开发阶段，使用固定回复模式。"
    "稍后我们将接入真实的 LLM 模型，提供更智能的服务。"
    "感谢你的耐心等待！"
)

_CHUNK_DELIMITERS = ["。", "！", "？", "\n"]


def _build_full_text(user_message: str, agent_role: str) -> str:
    return _FIXED_TEMPLATE.format(user_message=user_message, agent_role=agent_role)


def _chunk_text(text: str) -> list[str]:
    if not text:
        return []
    chunks = []
    current = ""
    for char in text:
        current += char
        if char in _CHUNK_DELIMITERS:
            chunks.append(current)
            current = ""
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


# --------------------------------------------------------------------------


class MessageStartEvent:
    def __init__(
        self,
        agent_role: str,
        timestamp: str,
        stream_id: str,
        message: Message,
    ) -> None:
        self.type = "message_start"
        self.agent_role = agent_role
        self.timestamp = timestamp
        self.stream_id = stream_id
        self.message = message


class MessageDeltaEvent:
    def __init__(
        self,
        agent_role: str,
        timestamp: str,
        stream_id: str,
        message_id: str,
        delta: str,
    ) -> None:
        self.type = "message_delta"
        self.agent_role = agent_role
        self.timestamp = timestamp
        self.stream_id = stream_id
        self.message_id = message_id
        self.delta = delta


class MessageEndEvent:
    def __init__(
        self,
        agent_role: str,
        timestamp: str,
        stream_id: str,
        message_id: str,
        status: str,
        final_content: str | None = None,
    ) -> None:
        self.type = "message_end"
        self.agent_role = agent_role
        self.timestamp = timestamp
        self.stream_id = stream_id
        self.message_id = message_id
        self.status = status
        self.final_content = final_content


class MessageErrorEvent:
    def __init__(
        self,
        agent_role: str,
        timestamp: str,
        stream_id: str,
        message_id: str,
        error_code: str,
        error_message: str,
    ) -> None:
        self.type = "message_error"
        self.agent_role = agent_role
        self.timestamp = timestamp
        self.stream_id = stream_id
        self.message_id = message_id
        self.error_code = error_code
        self.error_message = error_message


def _iso_now() -> str:
    return utcnow().isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------


class FixedAgentResponder:
    def __init__(
        self,
        session_id: str,
        user_message: str,
        agent_role: str,
        db: Session,
        stream_id: str,
    ) -> None:
        self.session_id = session_id
        self.user_message = user_message
        self.agent_role = agent_role
        self.db = db
        self.stream_id = stream_id

        self._full_text = _build_full_text(user_message, agent_role)
        self._chunks = _chunk_text(self._full_text)
        self._message_id: str | None = None
        self._agent_message: Message | None = None

    async def stream_events(self):
        try:
            agent_msg = Message(
                session_id=self.session_id,
                sender_type="agent",
                sender_role=self.agent_role,
                content="",
                type="text",
                status="streaming",
                payload={"text": ""},
                msg_metadata={
                    "source": "fixed_responder",
                    "render_hint": "markdown",
                    "stream_id": self.stream_id,
                },
            )
            self.db.add(agent_msg)
            self.db.commit()
            self.db.refresh(agent_msg)
            self._message_id = agent_msg.id
            self._agent_message = agent_msg

            yield MessageStartEvent(
                agent_role=self.agent_role,
                timestamp=_iso_now(),
                stream_id=self.stream_id,
                message=agent_msg,
            )

            accumulated = ""
            for chunk_text in self._chunks:
                accumulated += chunk_text
                agent_msg.content = accumulated
                agent_msg.payload = {"text": accumulated}
                self.db.add(agent_msg)
                self.db.commit()

                yield MessageDeltaEvent(
                    agent_role=self.agent_role,
                    timestamp=_iso_now(),
                    stream_id=self.stream_id,
                    message_id=self._message_id,
                    delta=chunk_text,
                )
                await asyncio.sleep(0.05)

            agent_msg.status = "completed"
            agent_msg.created_at = utcnow()
            self.db.add(agent_msg)
            self.db.commit()

            yield MessageEndEvent(
                agent_role=self.agent_role,
                timestamp=_iso_now(),
                stream_id=self.stream_id,
                message_id=self._message_id,
                status="completed",
                final_content=accumulated,
            )

        except Exception as e:
            if self._message_id and self._agent_message:
                self._agent_message.status = "failed"
                self.db.add(self._agent_message)
                self.db.commit()

            yield MessageErrorEvent(
                agent_role=self.agent_role,
                timestamp=_iso_now(),
                stream_id=self.stream_id,
                message_id=self._message_id or "",
                error_code="fixed_responder_failed",
                error_message=str(e),
            )
