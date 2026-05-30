# Phase 2：Runtime 层迁移

> 本文档描述 Phase 2 的具体实施步骤：Agent 运行时核心迁移，让系统具备 ReAct 循环和流式输出能力。

## 2.1 agents/runtime/ 目录结构

创建以下目录和文件：

```
backend/app/agents/runtime/
├── __init__.py
├── agent.py              # ReAct Agent（核心）
├── agent_config.py       # AgentConfig 数据类
├── providers/
│   ├── __init__.py
│   └── qwen_adapter.py   # QwenProvider → GenerativeModel 适配
├── memory.py             # AgentMemory / VariableMemory / Message
├── tool_manager.py       # ToolManager
├── tool_registry.py     # AgentHub 工具注册中心
└── templates/
    ├── task_prompt.j2
    ├── observation_response_format.j2
    ├── variables_prompt.j2
    ├── tools_prompt.j2
    ├── repeated_tool_call_error.j2
    ├── task_summary_prompt.j2
    ├── memory_compaction_prompt.j2
    └── chat_system_prompt.j2
```

## 2.2 QwenProvider 适配层设计

### 2.2.1 问题分析

quantalogic 的 `GenerativeModel` 是 Agent 与 LLM 之间的核心接口：

```python
class GenerativeModel:
    """Expected by quantalogic Agent"""
    def __init__(self, model: str, event_emitter: EventEmitter): ...
    async def async_generate(self, prompt: str) -> ResponseStats: ...
    async def async_generate_with_history(
        self,
        messages_history: list[Message],
        prompt: str,
        streaming: bool,
    ) -> AsyncIterator[str]: ...
    def get_model_max_input_tokens(self) -> int | None: ...
    def get_model_max_output_tokens(self) -> int | None: ...
    def token_counter_with_history(self, messages: list[Message], prompt: str) -> int: ...
```

AgentHub 的 `QwenProvider` 已实现：

```python
class QwenProvider:
    """Already in AgentHub"""
    def __init__(self, settings): ...
    async def chat(self, input: ProviderInput) -> ProviderOutput: ...
    async def stream_chat(self, input: ProviderInput) -> AsyncIterator[ProviderStreamEvent]: ...
```

### 2.2.2 适配层实现

新建 `agents/runtime/providers/qwen_adapter.py`：

```python
from app.providers.base import BaseProvider, ProviderInput, ProviderStreamEvent
from app.providers.openai_compatible import QwenProvider as OriginalQwenProvider

class QwenAdapter(GenerativeModel):
    """将 QwenProvider 适配为 quantalogic GenerativeModel 接口"""

    def __init__(
        self,
        provider: BaseProvider,
        model_name: str,
        event_emitter: EventEmitter,
        max_output_tokens: int = 4096,
        max_input_tokens: int = 128 * 1024,
    ):
        self._provider = provider
        self._model_name = model_name
        self._event_emitter = event_emitter
        self._max_output_tokens = max_output_tokens
        self._max_input_tokens = max_input_tokens

    async def async_generate(self, prompt: str) -> ResponseStats:
        messages = [{"role": "user", "content": prompt}]
        result = await self._provider.chat(ProviderInput(
            system_prompt="",
            user_message=prompt,
            model=self._model_name,
        ))
        return ResponseStats(
            response=result.text,
            usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            model=self._model_name,
            finish_reason="stop",
        )

    async def async_generate_with_history(
        self,
        messages_history: list[Message],
        prompt: str,
        streaming: bool,
    ) -> AsyncIterator[str]:
        # 将 Message 列表转换为 messages 格式
        messages = []
        for msg in messages_history:
            if msg.role == "system":
                messages.append({"role": "system", "content": msg.content})
            elif msg.role == "user":
                messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                messages.append({"role": "assistant", "content": msg.content})

        # 追加当前 prompt
        messages.append({"role": "user", "content": prompt})

        # 调用 provider
        async for event in self._provider.stream_chat(ProviderInput(
            system_prompt="",
            user_message=prompt,  # QwenProvider 暂不支持历史消息，此处需扩展
            model=self._model_name,
        )):
            yield event.text_delta

    def get_model_max_input_tokens(self) -> int | None:
        return self._max_input_tokens

    def get_model_max_output_tokens(self) -> int | None:
        return self._max_output_tokens

    def token_counter_with_history(self, messages: list[Message], prompt: str) -> int:
        # 简单估算：中文约 1 token ~ 1.5 字符，英文约 1 token ~ 4 字符
        total_chars = sum(len(m.content) for m in messages) + len(prompt)
        return int(total_chars / 2)  # 保守估算
```

### 2.2.3 注意事项

当前 `QwenProvider` 的 `stream_chat` 只接收 `(system_prompt, user_message)` 两个字段，不支持多轮历史消息。在适配层需要：

1. **短期方案**：每次调用把完整历史拼成一个大 `user_message`，通过 system_prompt 注入历史上下文（简单但有长度限制）
2. **长期方案**：扩展 `QwenProvider` 支持 `messages: list[dict]` 参数（与 OpenAI Chat Completions API 一致）

## 2.3 ToolRegistry 与事件系统集成

### 2.3.1 工具注册中心

新建 `agents/runtime/tool_registry.py`：

```python
class ToolRegistry:
    """AgentHub 工具注册中心（白名单）"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具到白名单"""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' already registered")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_all(self) -> list[str]:
        return list(self._tools.keys())

    def create_manager(self) -> ToolManager:
        return ToolManager(tools={name: tool for name, tool in self._tools.items()})
```

Phase2 阶段注册的工具（有限白名单）：

| 工具名 | 说明 | 用途 |
|--------|------|------|
| `task_complete` | 任务完成标记 | 来自 quantalogic，必选 |
| `read_file` | 读取文件内容 | Phase3 |
| `write_file` | 写入文件内容 | Phase3 |
| `list_directory` | 列出目录内容 | Phase3 |
| `unified_diff` | 计算文件差异 | Phase3 |

### 2.3.2 事件系统集成

quantalogic Agent 在 ReAct 循环中通过 `EventEmitter` 发射事件：

```python
# Agent 内部发射的事件
"session_start"               # 会话开始
"task_think_start"            # 开始思考
"task_think_end"              # 思考结束
"tool_execution_start"        # 工具执行开始
"tool_execution_end"          # 工具执行结束
"tool_execute_validation_start"  # 工具验证开始
"tool_execute_validation_end"    # 工具验证结束
"task_complete"               # 任务完成
"task_solve_end"              # 解决结束
"error_max_iterations_reached"   # 达到最大迭代
"memory_full"                 # 记忆满
"memory_compacted"            # 记忆压缩完成
"stream_chunk"                # 流式块（流式模式）
"chat_start"                  # 聊天开始
"chat_response"               # 聊天响应
"session_add_message"         # 添加消息到记忆
```

这些事件需要通过 **EventAdapter** 转换为 ws.py 传输层事件。

## 2.4 ToolContext 设计

### 2.4.1 数据类定义

```python
# agents/models/tool_context.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

@dataclass(frozen=True)
class ToolContext:
    """贯穿整个 ReAct 循环的上下文对象"""

    workspace_id: str
    project_id: str
    session_id: str
    user_id: str
    base_path: Path                    # 沙盒根路径
    allowed_patterns: Sequence[str] = field(default_factory=lambda: ["*"])
    denied_patterns: Sequence[str] = field(default_factory=lambda: [])

    def is_path_allowed(self, path: Path) -> bool:
        """检查路径是否在沙盒范围内"""
        try:
            resolved = path.resolve()
            base = self.base_path.resolve()
            resolved.relative_to(base)
            # TODO: 检查 denied_patterns
            return True
        except ValueError:
            return False
```

### 2.4.2 ToolContext 创建时机

在 `AgentStreamService.stream_events()` 开始时创建，传递给 Agent：

```python
class AgentStreamService:
    def __init__(self, ...):
        self.tool_context = ToolContext(
            workspace_id=workspace_id,
            project_id=project_id,
            session_id=session_id,
            user_id=user_id,
            base_path=Path(base_path),
        )

    async def stream_events(self):
        agent = Agent(
            model=QwenAdapter(provider=self.provider, ...),
            tools=self.tool_registry.create_manager(),
            tool_context=self.tool_context,  # 传递给 Agent
            ...
        )
        async for event in agent.async_solve_task_streaming(task):
            yield event
```

## 2.5 双层事件架构详解

### 2.5.1 架构图

```
┌─────────────────────────────────────────────────────────┐
│                     quantalogic Agent                     │
│  EventEmitter.emit("tool_execution_start", {...})       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              agents/adapters/event_adapter.py             │
│  - 接收业务层事件                                        │
│  - 转换为 ws.py 传输层格式                               │
│  - 控制过滤/节流/聚合                                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              agent_stream_service.py                     │
│  - 聚合事件流                                            │
│  - 句段分词                                              │
│  - 消息创建与持久化                                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                     ws.py                               │
│  - message_start / message_delta / message_end           │
│  - 传输层协议不变                                         │
│  - delta 携带 event_type 区分业务事件                      │
└─────────────────────────────────────────────────────────┘
```

### 2.5.2 事件转换示例

**业务层事件**（quantalogic Agent 发射）：

```python
# Agent 内部
self._emit_event("tool_execution_start", {
    "tool_name": "read_file",
    "arguments": {"file_path": "/workspace/main.py"}
})
```

**EventAdapter 转换**：

```python
# event_adapter.py
class EventAdapter:
    def __init__(self, websocket: WebSocket, agent_role: str):
        self._ws = websocket
        self._agent_role = agent_role

    async def emit(self, event_type: str, data: dict):
        # 业务层事件 → ws.py delta
        if event_type == "tool_execution_start":
            await self._ws.send_json({
                "type": "message_delta",
                "agent_role": self._agent_role,
                "event_type": "tool_start",     # 业务事件标识
                "delta": json.dumps({
                    "tool": data["tool_name"],
                    "args": data["arguments"],
                }),
            })
        elif event_type == "tool_execution_end":
            await self._ws.send_json({
                "type": "message_delta",
                "agent_role": self._agent_role,
                "event_type": "tool_end",
                "delta": json.dumps({
                    "tool": data["tool_name"],
                    "result": data.get("response", "")[:500],  # 截断长结果
                }),
            })
        elif event_type == "task_think_start":
            await self._ws.send_json({
                "type": "message_delta",
                "agent_role": self._agent_role,
                "event_type": "thinking",
                "delta": "",  # thinking 状态无文本
            })
```

### 2.5.3 ws.py payload 扩展

ws.py 的 `message_delta` 帧新增可选字段：

```python
# ws.py 扩展后
async def ws_send_message_delta(
    websocket: WebSocket,
    agent_role: str,
    stream_id: str,
    message_id: str,
    delta: str,
    event_type: str | None = None,  # ← 新增：业务事件类型
):
    payload = {
        "type": "message_delta",
        "agent_role": agent_role,
        "timestamp": _utcnow_iso(),
        "stream_id": stream_id,
        "message_id": message_id,
        "delta": delta,
    }
    if event_type:
        payload["event_type"] = event_type  # ← 可选扩展
    await websocket.send_json(payload)
```

**event_type 取值**：

| event_type | 说明 | 前端渲染 |
|------------|------|----------|
| `null` / 不传 | 普通文本 delta | 追加到消息内容 |
| `thinking` | Agent 思考中 | 显示 thinking 动画 |
| `tool_start` | 工具执行开始 | 显示工具调用卡片 |
| `tool_end` | 工具执行结束 | 更新工具调用卡片状态 |
| `error` | 错误 | 显示错误提示 |

## 2.6 实施步骤

### Step 1：创建目录结构

```bash
mkdir -p backend/app/agents/runtime/providers
mkdir -p backend/app/agents/runtime/templates
mkdir -p backend/app/agents/models
mkdir -p backend/app/agents/tools
mkdir -p backend/app/agents/adapters
```

### Step 2：复制 quantalogic 核心文件

复制优先级（按依赖关系排序）：

1. `agents/models/tool_context.py` — ToolContext 数据类
2. `agents/models/events.py` — 业务层事件类
3. `agents/runtime/memory.py` — Memory / Message / VariableMemory
4. `agents/runtime/providers/qwen_adapter.py` — **新增**：QwenProvider 适配
5. `agents/tools/base.py` — Tool 基类
6. `agents/runtime/tool_manager.py` — ToolManager
7. `agents/runtime/agent.py` — **修改**：Agent（移除 litellm 依赖，注入 QwenAdapter）
8. 复制 `agents/runtime/templates/*.j2` — Jinja2 模板

### Step 3：实现 EventAdapter

实现 `agents/adapters/event_adapter.py`，对接 EventEmitter 和 ws.py。

### Step 4：重构 agent_stream_service.py

将 `AgentStreamService` 从直接调用 Provider 改为调用 `Runtime Agent`。
