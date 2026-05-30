# 与现有系统对接

> 本文档描述 quantalogic 迁移代码如何与 AgentHub 已有系统（ws.py、agent_stream_service.py、数据库模型）对接。

## 4.1 ws.py 双层事件适配

### 4.1.1 当前 ws.py 协议（不变）

ws.py 已有完整的消息协议：

```python
# ws.py 现有函数
message_start  →  {"type": "message_start", "message": {...}}
message_delta  →  {"type": "message_delta", "delta": "..."}
message_end    →  {"type": "message_end", "status": "..."}
message_error  →  {"type": "message_error", "error_code": "...", "error_message": "..."}
```

### 4.1.2 扩展 ws.py 传输层

**最小改动方案**：在 `message_delta` 中增加可选 `event_type` 字段：

```python
# ws.py 新增/修改函数
async def ws_send_message_delta(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message_id: str,
    delta: str,
    event_type: str | None = None,  # 新增
) -> None:
    payload = {
        "type": "message_delta",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "delta": delta,
    }
    if event_type is not None:
        payload["event_type"] = event_type
    await websocket.send_json(payload)
```

### 4.1.3 EventAdapter 实现

```python
# agents/adapters/event_adapter.py
from fastapi import WebSocket
from typing import AsyncIterator

class EventAdapter:
    """业务层事件 → ws.py 传输层事件"""

    def __init__(
        self,
        websocket: WebSocket,
        agent_role: str,
        stream_id: str,
        message_id: str,
    ):
        self._ws = websocket
        self._agent_role = agent_role
        self._stream_id = stream_id
        self._message_id = message_id

    async def emit_text(self, text: str) -> None:
        """普通文本 delta"""
        await ws_send_message_delta(
            self._ws,
            agent_role=self._agent_role,
            stream_id=self._stream_id,
            message_id=self._message_id,
            delta=text,
            event_type=None,
        )

    async def emit_thinking_start(self) -> None:
        await ws_send_message_delta(
            self._ws,
            agent_role=self._agent_role,
            stream_id=self._stream_id,
            message_id=self._message_id,
            delta="",
            event_type="thinking",
        )

    async def emit_thinking_end(self) -> None:
        await ws_send_message_delta(
            self._ws,
            agent_role=self._agent_role,
            stream_id=self._stream_id,
            message_id=self._message_id,
            delta="",
            event_type="thinking_end",
        )

    async def emit_tool_start(self, tool_name: str, args: dict) -> None:
        import json
        await ws_send_message_delta(
            self._ws,
            agent_role=self._agent_role,
            stream_id=self._stream_id,
            message_id=self._message_id,
            delta=json.dumps({"tool": tool_name, "args": args}),
            event_type="tool_start",
        )

    async def emit_tool_end(
        self, tool_name: str, result: str, success: bool
    ) -> None:
        import json
        await ws_send_message_delta(
            self._ws,
            agent_role=self._agent_role,
            stream_id=self._stream_id,
            message_id=self._message_id,
            delta=json.dumps({
                "tool": tool_name,
                "result": result[:1000],  # 截断长结果
                "success": success,
            }),
            event_type="tool_end",
        )

    async def emit_error(self, error_code: str, error_message: str) -> None:
        await ws_send_message_error(
            self._ws,
            agent_role=self._agent_role,
            stream_id=self._stream_id,
            message_id=self._message_id,
            error_code=error_code,
            error_message=error_message,
        )
```

### 4.1.4 EventEmitter → EventAdapter 桥接

```python
# agents/adapters/event_bridge.py
class EventBridge:
    """将 quantalogic EventEmitter 事件桥接到 EventAdapter"""

    def __init__(self, adapter: EventAdapter):
        self._adapter = adapter
        # 事件映射表
        self._event_map = {
            "task_think_start": adapter.emit_thinking_start,
            "task_think_end": adapter.emit_thinking_end,
            "tool_execution_start": lambda data: adapter.emit_tool_start(
                data.get("tool_name", ""), data.get("arguments", {})
            ),
            "tool_execution_end": lambda data: adapter.emit_tool_end(
                data.get("tool_name", ""),
                str(data.get("response", "")),
                data.get("response", "").__class__.__name__ != "str" or not str(data.get("response", "")).startswith("Error"),
            ),
        }

    def attach_to(self, event_emitter: EventEmitter) -> None:
        """将事件映射注册到 EventEmitter"""
        for event_type, handler in self._event_map.items():
            event_emitter.on(event_type, handler)
```

## 4.2 agent_stream_service.py 重构

### 4.2.1 当前职责

当前 `agent_stream_service.py` 的职责：

```
Provider.stream_chat()
    → ProviderStreamEvent (原始 delta)
    → AgentStreamService
        → SentenceChunker (句段分词)
        → TypingEvent / ChunkEvent (业务事件)
        → Message 持久化
```

### 4.2.2 重构后职责

重构后的 `AgentStreamService`：

```
Runtime Agent (ReAct 循环)
    → EventBridge (业务事件 → ws.py)
    → AgentStreamService
        → SentenceChunker (句段分词)
        → ChunkEvent (业务事件)
        → Message 持久化
        → DiffTracker (变更追踪)
```

### 4.2.3 重构实现

```python
# agents/adapters/runtime_stream_service.py
from typing import AsyncIterator
from sqlalchemy.orm import Session

from app.models.message import Message
from app.providers.base import BaseProvider
from agents.models.tool_context import ToolContext
from agents.models.workspace import Workspace
from agents.adapters.event_adapter import EventAdapter
from agents.adapters.event_bridge import EventBridge
from agents.runtime.agent import Agent
from agents.runtime.providers.qwen_adapter import QwenAdapter
from agents.runtime.tool_registry import ToolRegistry

@dataclass
class ChunkEvent:
    content_chunk: str
    is_final: bool
    event_type: str | None = None  # 业务事件类型

class RuntimeStreamService:
    """将 Runtime Agent 的输出转换为 ws.py 业务事件流"""

    def __init__(
        self,
        session_id: str,
        human_message_id: str,
        agent_role: str,
        system_prompt: str,
        user_message: str,
        provider: BaseProvider,
        db: Session,
        workspace: Workspace,
        user_id: str,
        stream_id: str | None = None,
    ):
        self.session_id = session_id
        self.human_message_id = human_message_id
        self.agent_role = agent_role
        self.provider = provider
        self.db = db
        self.stream_id = stream_id or str(uuid.uuid4())
        self._system_prompt = system_prompt
        self._user_message = user_message
        self._workspace = workspace
        self._user_id = user_id

        self._agent_message: Message | None = None
        self._accumulated_content: str = ""
        self._chunker = SentenceChunker()
        self._ended = False

    async def stream_events(
        self, websocket: WebSocket
    ) -> AsyncIterator[ChunkEvent | ErrorEvent]:
        """生成业务事件序列，同时通过 websocket 发送传输层事件"""
        # 1. 创建 ToolContext
        tool_context = ToolContext(
            workspace_id=self._workspace.id,
            project_id=self._workspace.project_id,
            session_id=self._session_id,
            user_id=self._user_id,
            base_path=self._workspace.base_path,
        )

        # 2. 创建 EventAdapter（业务 → 传输层）
        event_adapter = EventAdapter(
            websocket=websocket,
            agent_role=self.agent_role,
            stream_id=self.stream_id,
            message_id="",  # 后续填充
        )

        # 3. 创建 Agent
        model_adapter = QwenAdapter(
            provider=self.provider,
            model_name=self.provider._model,
            event_emitter=EventEmitter(),
        )

        tool_registry = ToolRegistry()
        # 注册 Phase3 工具...

        agent = Agent(
            model=model_adapter,
            tools=tool_registry.create_manager(),
            tool_context=tool_context,
            ...
        )

        # 4. 桥接事件
        bridge = EventBridge(event_adapter)
        bridge.attach_to(agent.event_emitter)

        # 5. 发送 message_start
        self._agent_message = Message(...)
        self.db.add(self._agent_message)
        self.db.commit()
        await ws_send_message_start(websocket, self.agent_role, self.stream_id, self._agent_message)

        # 6. ReAct 循环 → 事件流
        async for chunk in agent.async_solve_task_streaming(self._user_message):
            # 句段分词
            for seg in self._chunker.feed(chunk):
                self._accumulated_content += seg
                self._update_message()
                await event_adapter.emit_text(seg)
                yield ChunkEvent(content_chunk=seg, is_final=False)

        # 7. Final
        yield ChunkEvent(content_chunk="", is_final=True)
        self._agent_message.delivery_status = "completed"
        self._update_message()
```

## 4.3 数据库模型兼容性

### 4.3.1 现有模型（保持不变）

AgentHub 现有数据库模型：

```
Message
├── id: str (UUID)
├── session_id: str (FK → ChatSession)
├── sender_type: str ("human" | "agent")
├── sender_role: str | None
├── content: str
├── type: str ("text")
├── status: str ("completed" | "failed" | "interrupted")
├── delivery_status: str | None
├── payload: dict | None
├── metadata: dict | None
├── created_at: datetime
└── updated_at: datetime

ChatSession
├── id: str (UUID)
├── project_id: str
├── owner_id: str
├── title: str | None
├── status: str
├── created_at: datetime
└── updated_at: datetime
```

### 4.3.2 兼容性保证

1. **Message 字段不变**：Agent 生成的消息仍然写入 `Message` 表，字段格式不变
2. **Session 关联不变**：`session_id` 仍然指向 `ChatSession`
3. **历史消息加载**：通过 `MemoryPersister.load_history()` 将 Message 表内容加载到 AgentMemory

### 4.3.3 新增字段（可选扩展）

如果未来需要存储更详细的 Agent 运行时信息，可以扩展 `Message.metadata`：

```python
# Agent 运行时元数据存储到 Message.metadata
metadata = {
    "iteration_count": 5,
    "tools_used": ["read_file", "write_file", "unified_diff"],
    "tracked_files": ["/workspace/main.py", "/workspace/utils.py"],
    "event_summary": {
        "tool_starts": 8,
        "tool_ends": 8,
        "thinking_events": 12,
    },
}
```

## 4.4 端到端调用链

完整调用链（Phase2 完成后）：

```
前端 WebSocket 发送消息
    ↓
ws.py session_websocket()
    ↓
FixedAgentResponder → RuntimeStreamService（新增路径）
    ↓
RuntimeStreamService.stream_events(websocket)
    ↓
EventBridge 桥接 EventEmitter → EventAdapter
    ↓
Agent (ReAct 循环)
    ├── ToolManager
    ├── Memory
    ├── EventEmitter
    └── QwenAdapter
            ↓
    QwenProvider.stream_chat()
            ↓
LLM 流式响应
    ↓
Agent 内部解析 XML Tool Call
    ↓
Tool 执行
    ↓
EventEmitter 发射业务事件
    ↓
EventBridge 路由到 EventAdapter
    ↓
EventAdapter → ws_send_message_delta(event_type="tool_start")
    ↓
前端接收并渲染工具调用卡片
    ↓
Message 持久化到数据库
    ↓
前端接收 message_end
```

## 4.5 兼容性矩阵

| 组件 | 迁移前 | 迁移后 | 兼容性 |
|------|--------|--------|--------|
| ws.py 协议 | `message_start/delta/end` | 扩展 `event_type` 可选字段 | ✅ 向后兼容 |
| `QwenProvider` | 直接调用 | 通过 QwenAdapter 封装 | ✅ 不变 |
| `Message` 模型 | 直接写入 | 通过 MemoryPersister 写入 | ✅ 不变 |
| `ChatSession` | 直接关联 | 直接关联 | ✅ 不变 |
| `FixedAgentResponder` | 直接调用 Provider | 保留（简单回复场景）<br>新增 RuntimeStreamService（Agent 场景） | ✅ 分流 |
| 前端 | 消费 `message_delta.delta` | 额外消费 `message_delta.event_type` | ✅ 前端可选处理 |
