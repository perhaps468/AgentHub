# 整体架构设计

## 1.1 迁移范围与目标

### 迁移范围

本次迁移覆盖 quantalogic 的以下模块：

**纳入迁移（P2-P3）**

| quantalogic 模块 | 说明 | 对应 AgentHub 目录 |
|----------------|------|-------------------|
| `agent.py`（React 路线） | ReAct Agent 核心（XML Tool Call） | `agents/runtime/` |
| `generative_model.py` | LLM 补全接口（QwenProvider 适配） | `agents/runtime/providers/` |
| `event_emitter.py` | 事件发射器（业务层事件） | `agents/models/` |
| `memory.py` | 会话记忆（Message / VariableMemory） | `agents/runtime/memory.py` |
| `tool_manager.py` | 工具管理器 | `agents/runtime/tool_manager.py` |
| `tool.py` 基类 | 工具抽象基类 | `agents/tools/` |
| FileTool / ReadFileTool / WriteFileTool | 文件操作工具 | `agents/tools/` |
| UnifiedDiffTool | Diff 工具 | `agents/tools/` |
| `events.py` | 内部业务事件 | `agents/models/events.py` |

**不纳入本次迁移**

| quantalogic 模块 | 原因 |
|-----------------|------|
| `agent.py`（Reasoner 路线） | P3 阶段暂不引入多步 Reasoner，保持 React 简单可靠 |
| `artifact.py` / `workflow_engine.py` | P4 Artifact 体系，本次不迁移 |
| `quantalogic_flow/` | P5-P6 运行时工厂，本次不迁移 |
| `ComposioTool` | P5 扩展集成，本次不引入 |

### 迁移目标

- **Phase 2 目标**：Agent 可运行（ReAct 循环 + 流式输出 + ws.py 协议对接）
- **Phase 3 目标**：Agent 能操作文件（读写、diff、sandbox 隔离）

## 1.2 命名空间规划（agents/ 下各层职责）

```
backend/app/agents/
├── __init__.py
├── registry.py               # Agent 注册表（现有）
├── builtin.py                # 内置 Agent 定义（现有）
│
├── runtime/                  # ★ quantalogic 核心迁移区
│   ├── __init__.py
│   ├── agent.py              # ReAct Agent（复制自 quantalogic agent.py，XML Tool Call）
│   ├── agent_config.py       # AgentConfig 数据类
│   ├── reasoner.py           # Reasoner（Phase3 引入）
│   │
│   ├── providers/            # LLM Provider 适配层
│   │   ├── __init__.py
│   │   └── qwen_adapter.py   # ★ QwenProvider → GenerativeModel 适配
│   │
│   ├── memory.py             # AgentMemory / VariableMemory / Message
│   ├── tool_manager.py       # ToolManager
│   ├── tool_registry.py      # AgentHub 工具注册中心（白名单）
│   │
│   └── templates/            # Prompt Jinja2 模板
│       ├── task_prompt.j2
│       ├── observation_response_format.j2
│       └── ...
│
├── tools/                    # ★ quantalogic 工具实现
│   ├── __init__.py
│   ├── base.py               # Tool 基类（复制自 quantalogic tool.py）
│   ├── file_tool.py          # 文件操作工具（ReadFileTool / WriteFileTool）
│   ├── diff_tool.py          # Diff 工具（UnifiedDiffTool 适配）
│   ├── bash_tool.py          # Bash 执行工具（sandbox）
│   └── registry.py           # 工具白名单注册表
│
├── models/                   # 数据模型
│   ├── __init__.py
│   ├── events.py             # 业务层事件（ThoughtEvent / ToolStartEvent / ToolEndEvent）
│   └── tool_context.py       # ToolContext 数据类
│
└── adapters/                 # 适配层
    ├── __init__.py
    ├── event_adapter.py       # ★ 双层事件适配器（业务层 → 传输层）
    └── stream_adapter.py      # 流式输出适配器
```

## 1.3 迁移前后架构对比

### 迁移前（当前状态）

```
WebSocket 连接
    ↓
ws.py (message_start/delta/end 协议)
    ↓
FixedAgentResponder
    ↓
AgentStreamService
    ↓
QwenProvider (直接 LLM 调用)
    ↓
前端显示（纯文本流）
```

**当前缺陷**：

- Agent 仅做 LLM 补全，没有 ReAct 循环
- 没有工具调用能力（不能读文件、不能执行命令）
- 没有业务层事件（thinking、tool_start 等对前端不可见）

### 迁移后（Phase2 完成后）

```
WebSocket 连接
    ↓
ws.py (message_start/delta/end 协议) ← 协议不变
    ↓
EventAdapter（业务层 → 传输层）← 新增
    ↓
agent_stream_service.py（重构）
    ↓
Runtime Agent ← 新增
    ├── Agent（ReAct 循环）
    │   ├── ToolManager（工具调度）
    │   ├── Memory（会话记忆）
    │   └── EventEmitter（事件发射）
    │
    ├── QwenAdapter ← 新增（QwenProvider → GenerativeModel）
    │   ↓
    └── QwenProvider（已有，保留）
    ↓
前端显示（文本流 + 业务事件）
```

**改进点**：

- Agent 有了 ReAct 循环（Think → Action → Observe）
- 工具白名单机制（安全）
- 业务层事件丰富（thinking、tool_start、tool_end）
- 双层事件架构（协议稳定 + 内部灵活）

### Phase3 完成后

在 Phase2 基础上增加：

```
Agent
    ├── ToolManager
    │   ├── FileTool（读/写/列表文件）
    │   ├── DiffTool（统一 diff）
    │   └── BashTool（sandboxed 执行）
    │
    └── ToolContext（workspace / project / session / user）
            ↓
    Workspace 隔离（base_path 限制）
```

## 1.4 关键设计决策详解

### 决策 3：QwenProvider 适配层

**目的**：让 quantalogic 的 `GenerativeModel` 接口能与 AgentHub 已有的 `QwenProvider` 对接。

quantalogic 的 `GenerativeModel` 期望：

```python
# quantalogic/generative_model.py 接口
class GenerativeModel:
    async def async_generate(self, prompt: str) -> ResponseStats
    async def async_generate_with_history(self, messages_history: list, prompt: str, streaming: bool) -> AsyncIterator[str]
```

AgentHub 的 `QwenProvider` 已实现：

```python
# openai_compatible.py 接口
class QwenProvider:
    async def chat(self, input: ProviderInput) -> ProviderOutput
    async def stream_chat(self, input: ProviderInput) -> AsyncIterator[ProviderStreamEvent]
```

**适配层职责**：

- 将 `ProviderInput` → 转换为 quantalogic 的消息格式
- 将 `ProviderStreamEvent` → 适配为 quantalogic 的流式响应
- 处理 token 计数、max_tokens 等量化参数

### 决策 4：双层事件架构

**传输层**（ws.py 协议，不变）：

```python
# ws.py 已有
message_start  →  {"type": "message_start", "message": {...}}
message_delta  →  {"type": "message_delta", "delta": "..."}
message_end    →  {"type": "message_end", "status": "..."}
```

**业务层**（AgentHub 新增）：

```python
# agents/models/events.py
class ThoughtEvent:       # Agent 思考开始
class ToolStartEvent:     # 工具执行开始
class ToolEndEvent:       # 工具执行结束
class ErrorEvent:         # 错误事件
```

**EventAdapter 转换逻辑**：

```
Agent._emit_event("task_think_start") → EventAdapter → ws.send_json({...}) 携带 event_type
Agent._emit_event("tool_execution_start") → EventAdapter → ws.send_json({...}) 携带 event_type
Agent._emit_event("tool_execution_end") → EventAdapter → ws.send_json({...}) 携带 event_type
```

前端通过 `delta` 字段中的 `event_type` 区分业务事件类型，无需改变 ws.py 的协议帧类型。

### 决策 6：ToolContext

```python
@dataclass
class ToolContext:
    workspace_id: str          # Workspace 标识
    project_id: str            # 项目标识
    session_id: str            # 会话标识
    user_id: str              # 用户标识
    base_path: Path            # 工作目录（沙盒根路径）
    allowed_patterns: list[str]  # 允许的文件模式（glob）
    denied_patterns: list[str]   # 禁止的文件模式（glob）
```

ToolContext 在 ReAct 循环开始时创建，贯穿整个工具调用链传递给每个 Tool 实例。
