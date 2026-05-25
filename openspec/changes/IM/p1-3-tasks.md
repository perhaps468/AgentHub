# Task: P1-3 当前错误链路改造、统一 Message 收敛与前后端协议切换

## 0. 文档定位

- 本文档基于 [openspec/specs/implementation-phases.md](/D:/code/ZiJieAI/AgentHub/openspec/specs/implementation-phases.md) 中的 `Phase1-3 当前错误链路改造`。
- 本文档同时复用 [openspec/specs/roadmap.md](/D:/code/ZiJieAI/AgentHub/openspec/specs/roadmap.md) 中关于 `Phase1` 的阶段边界，尤其是：
  - `Message` 必须先统一封装
  - 当前 LLM 不应继续直接回复 UI
  - `WS` 需先验证统一消息流，而不是固化真实 Runtime
- 本文档按 `task-planning-from-spec` 的结构产出，但按本轮明确要求，特殊地将前端任务并入同一份 task 文档，不再拆成单独 frontend task。
- 本文档吸收本轮已确认实现决策：
  - 直接切换 `WS` 协议到 `message_start` / `message_delta` / `message_end` / `message_error`
  - 主链路不再保留真实 Provider / LLM 回复，改用 `FixedAgentResponder`
  - `Message` 一次升级到最小通用模型：`type` / `content` / `payload` / `metadata` / `status`
  - `typing` 并入 `message_start`
  - 历史消息 REST 与 WS 统一到同一消息形状
  - 当前阶段不做 `session -> conversation` 重命名
  - `shared/schemas/ws_messages.json` 继续作为协议真相源

## 1. 任务目标

- 将当前“`WS -> AgentStreamService -> 真实 provider.stream_chat -> chat_stream/agent_typing -> 前端特判`”链路收敛为统一消息流。
- 让 `Message` 成为后续 `Phase2 Agent Runtime` 可直接复用的最小通用承载模型，而不是当前文本专用模型。
- 将当前前端对 `chat_stream` / `agent_typing` 的临时消费逻辑改造成基于统一事件的流式聚合逻辑。
- 保证本阶段完成后，`Phase2` 只需要替换执行器，不需要重构：
  - `Message`
  - 历史消息接口
  - Streaming 协议
  - WebSocket
  - 前端消息流消费方式

## 2. 当前范围

- 后端 `Message` 数据模型、schema、REST 返回体升级
- `shared` WebSocket Schema / TypeScript 类型升级
- `WS /ws/{session_id}` 出站协议切换
- 当前默认回复链路从真实 provider 切到固定流式回复器
- 前端流式状态管理、消息归并逻辑、页面接线升级
- 自动化测试、联调约束与验收标准

## 3. 不做什么

- 不做 `AgentRuntime`
- 不做 `PromptBuilder`
- 不做 `RuntimeContext`
- 不做 Tool Calling
- 不做 ReAct Loop
- 不接入多 Agent
- 不做 `session -> conversation` 命名迁移
- 不保留真实 LLM 作为默认主链路 fallback
- 不为 `code` / `diff` / `artifact` / `deploy` 做完整业务渲染，只保留消息模型占位
- 不做复杂断线续传、消息回放恢复未完成流

## 4. 依赖与前置条件

- `Phase1-1` 已建立 Session / Message / WebSocket 基础主链路。
- `Phase1-2` 已建立流式输出基础能力，但仍使用旧协议与真实 provider 链路。
- 当前仓库中已有可复用模块：
  - [backend/app/models/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/message.py)
  - [backend/app/api/sessions.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/sessions.py)
  - [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
  - [shared/schemas/ws_messages.json](/D:/code/ZiJieAI/AgentHub/shared/schemas/ws_messages.json)
  - [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)
  - [frontend/src/utils/useChatStreamState.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/utils/useChatStreamState.ts)
  - [frontend/src/components/zhu.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu.vue)
- 当前项目运行态仍以 `Base.metadata.create_all()` 为主；若 Alembic 未稳定接管，本阶段 schema 更新需按当前实际方式落地。

## 5. 需要改动的模块、数据模型、接口或配置

### 后端

- 数据模型 / schema
  - [backend/app/models/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/message.py)
  - [backend/app/schemas/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/schemas/message.py)
  - [backend/app/models/__init__.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/__init__.py) 如需同步导出
- WebSocket / 回复器
  - [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
  - 新增 `backend/app/services/fixed_agent_responder.py`
- REST 历史接口
  - [backend/app/api/sessions.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/sessions.py)

### Shared

- [shared/schemas/ws_messages.json](/D:/code/ZiJieAI/AgentHub/shared/schemas/ws_messages.json)
- [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)

### 前端

- [frontend/src/utils/useChatStreamState.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/utils/useChatStreamState.ts)
- [frontend/src/components/zhu.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu.vue)
- [frontend/src/veiws/Chat-show-area.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/veiws/Chat-show-area.vue)
- [frontend/src/types/agenthub.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/types/agenthub.ts)
- [frontend/src/store/module/useSessionStore.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/store/module/useSessionStore.ts) 如消息归并逻辑需同步调整

### 测试

- [backend/tests/test_ws.py](/D:/code/ZiJieAI/AgentHub/backend/tests/test_ws.py) 或当前 WS 测试文件
- [backend/tests/test_ws_provider.py](/D:/code/ZiJieAI/AgentHub/backend/tests/test_ws_provider.py)
- 可新增 `backend/tests/test_fixed_agent_responder.py`
- 可新增 `frontend/src/utils/useChatStreamState.spec.ts`
- 可改造现有前端组件测试

## 6. 统一契约

### 6.1 Message 持久化契约

`Message` 升级为最小通用消息模型。

必备字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 消息 ID |
| `session_id` | string | 是 | 所属会话 |
| `sender_type` | string | 是 | `human` / `agent` / `system` |
| `sender_role` | string \| null | 是 | 当前阶段 Agent 角色 |
| `type` | string | 是 | `text` / `code` / `diff` / `artifact` / `deploy` |
| `content` | string | 是 | 文本类主内容 |
| `payload` | object | 是 | 结构化消息主体 |
| `metadata` | object | 是 | 渲染、来源、stream、artifact 关联等扩展信息 |
| `status` | string | 是 | `pending` / `streaming` / `completed` / `failed` |
| `created_at` | string | 是 | 创建时间 |

本阶段约束：

- `type` 真实落通只做 `text`
- 其他 `type` 只保留枚举占位，不做业务渲染闭环
- `payload` / `metadata` 至少要对 `text` 类型定义最小结构

`text` 消息建议结构：

```json
{
  "type": "text",
  "content": "完整文本内容",
  "payload": {
    "text": "完整文本内容"
  },
  "metadata": {
    "stream_id": "stream-uuid",
    "source": "fixed_responder",
    "render_hint": "markdown"
  },
  "status": "completed"
}
```

持久化规则：

1. human message 先落库，状态默认 `completed`
2. agent message 占位创建时落库，状态为 `streaming`
3. `message_end` 后将完整内容写回，状态置为 `completed`
4. 发生异常时：
   - 若 agent message 已创建，则状态置为 `failed`
   - 若尚未创建，则不落 agent message

状态使用约束：

- `pending` 在 `Phase1-3` 只作为预留枚举，不要求进入主链路
- `streaming` 只允许出现在当前会话的进行中 agent 消息上
- `completed` 与 `failed` 都视为已 finalized 的历史消息状态

### 6.1.1 当前阶段 schema 迁移决策

本阶段不依赖完整 Alembic 流程，直接采用“测试环境自动重建 + 本地开发库一次性迁移脚本”方案。

明确决策如下：

1. 测试环境
   - 继续沿用当前 `sqlite :memory:` + `drop_all/create_all`
   - 只需更新 ORM 模型定义，测试建库自动使用新结构
2. 本地开发数据库
   - 新增一次性迁移脚本，例如 `backend/sql/p1_3_messages_migration.sql`
   - 不保留长期双列兼容，不在代码层同时维护 `content_type/type` 或 `delivery_status/status`
3. 迁移脚本职责
   - 从当前运行时 `messages` 表结构迁移：
     - `content_type -> type`
     - `delivery_status -> status`
   - 为所有旧 `text` 消息回填：
     - `payload = {"text": content}`
     - `metadata = {"source": "legacy_history"}`
   - 状态映射规则：
     - `completed -> completed`
     - `interrupted -> failed`
     - 缺失旧状态时默认 `completed`
4. 迁移完成后
   - 代码只读写新字段
   - 旧列不再作为运行时兼容输入

### 6.2 REST 历史消息契约

`GET /api/sessions/{session_id}/messages` 保持路径不变，但返回统一消息模型，不再沿用旧字段名。

成功响应 `items[*]` 最小字段：

```json
{
  "id": "message-uuid",
  "session_id": "session-uuid",
  "sender_type": "agent",
  "sender_role": "PM",
  "type": "text",
  "content": "完整文本内容",
  "payload": {
    "text": "完整文本内容"
  },
  "metadata": {
    "stream_id": "stream-uuid",
    "source": "fixed_responder",
    "render_hint": "markdown"
  },
  "status": "completed",
  "created_at": "2026-05-24T10:00:00Z"
}
```

约束：

- 历史接口返回结构必须与前端流式完成后的正式消息结构同构
- 刷新页面后，前端应只依赖历史接口恢复完整消息，不依赖旧的增量缓存映射
- 历史接口只返回已 finalized 消息：
  - 返回 `status in ("completed", "failed")`
  - 不返回 `status in ("pending", "streaming")` 的进行中占位消息
- 这意味着页面刷新期间若某条 agent 回复尚未结束，该占位消息不会由历史接口回放；页面只恢复已经完成或失败收口的消息

### 6.3 WebSocket 出站协议

`Phase1-3` 起，服务端出站消息从旧协议切到统一事件协议。

#### `message_start`

```json
{
  "type": "message_start",
  "agent_role": "PM",
  "timestamp": "2026-05-24T10:00:00Z",
  "stream_id": "stream-uuid",
  "message": {
    "id": "message-uuid",
    "session_id": "session-uuid",
    "sender_type": "agent",
    "sender_role": "PM",
    "type": "text",
    "content": "",
    "payload": {
      "text": ""
    },
    "metadata": {
      "stream_id": "stream-uuid",
      "source": "fixed_responder",
      "render_hint": "markdown"
    },
    "status": "streaming",
    "created_at": "2026-05-24T10:00:00Z"
  }
}
```

语义：

- `message_start` 同时承担原来 `typing=true` 的职责
- 前端收到后立即创建 in-flight 消息占位
- `message` 字段必须是完整消息壳，而不是最小标识字段

#### `message_delta`

```json
{
  "type": "message_delta",
  "agent_role": "PM",
  "timestamp": "2026-05-24T10:00:01Z",
  "stream_id": "stream-uuid",
  "message_id": "message-uuid",
  "delta": "这是一段增量文本"
}
```

语义：

- 仅表示正文增量
- 前端只向当前 in-flight 消息追加 `delta`
- 不得把每个 `delta` 当作独立消息插入列表

#### `message_end`

```json
{
  "type": "message_end",
  "agent_role": "PM",
  "timestamp": "2026-05-24T10:00:02Z",
  "stream_id": "stream-uuid",
  "message_id": "message-uuid",
  "status": "completed"
}
```

语义：

- 表示本次流式消息结束
- 前端完成本地收口并释放 in-flight 状态
- 最终正式消息内容以后端历史真相和本次已聚合内容一致为准

#### `message_error`

```json
{
  "type": "message_error",
  "agent_role": "PM",
  "timestamp": "2026-05-24T10:00:02Z",
  "stream_id": "stream-uuid",
  "message_id": "message-uuid",
  "error_code": "fixed_responder_failed",
  "error_message": "Failed to stream fixed response"
}
```

本阶段错误码至少包括：

| `error_code` | 触发条件 |
|------|------|
| `session_not_found` | 会话不存在 |
| `invalid_request` | 请求体非法 |
| `agent_busy` | 同一会话已有在途回复 |
| `fixed_responder_failed` | 固定回复器执行失败 |
| `unknown` | 未分类异常 |

约束：

- `message_error` 替代旧 `error` 作为消息流错误事件
- pre-start 错误也必须带 `stream_id`
- 若已有已创建的 agent message，则应带 `message_id`

### 6.4 FixedAgentResponder 契约

新增临时回复器 `FixedAgentResponder`，不得命名为正式 Runtime。

输入：

- `session_id`
- `user_message`
- `agent_role`
- `db`
- `stream_id`

输出：

- `message_start`
- 多个 `message_delta`
- `message_end`
- 或 `message_error`

运行规则：

1. 根据固定模板生成 deterministic 文本
2. 文本切分为若干固定片段，按顺序输出
3. 默认输出来源写入 `metadata.source = "fixed_responder"`
4. 不调用真实 provider，不读取真实模型配置，不消费历史上下文

建议固定回复模板：

- 保留稳定的结构化文本风格，便于测试
- 可基于用户输入拼入当前消息内容，但不得引入真实 LLM 调用

### 6.5 前端本地消息与 reconciliation 规则

前端本地 optimistic human message 也必须升级到统一消息形状。

发送用户消息时，本地临时消息最小结构：

```json
{
  "id": "temp_human_xxx",
  "session_id": "session-uuid",
  "sender_type": "human",
  "sender_role": null,
  "type": "text",
  "content": "用户输入",
  "payload": {
    "text": "用户输入"
  },
  "metadata": {
    "source": "optimistic_human"
  },
  "status": "completed",
  "created_at": "2026-05-24T10:00:00Z"
}
```

前端收口规则明确如下：

1. `message_start`
   - 使用后端返回的真实 `message.id` 创建 agent in-flight 消息
2. `message_end`
   - 前端完成当前 agent in-flight 消息的本地收口
   - 随后立即对当前会话触发一次后台 `fetchMessages(sessionId)`，用于把 optimistic human message 与 agent 正式历史消息对齐到后端真相
3. `message_error`
   - 若该次请求已产生本地 agent in-flight 消息，也必须触发一次后台 `fetchMessages(sessionId)` 完成失败收口
4. `fetchMessages` merge 规则
   - 历史消息以 `message.id` 为主键 upsert
   - 若历史列表中存在与本地 agent 消息同 `message.id` 的记录，用历史消息覆盖本地消息，不再追加第二条
   - 后台重拉成功后，删除当前会话中 `metadata.source = "optimistic_human"` 的临时 human 消息，由后端已落库的真实 human message 接管
5. 单会话当前阶段只有一条在途 agent 回复，因此一次 `message_end` / `message_error` 对应一次后台重拉即可完成正常与异常两条路径的 reconciliation

## 7. Task 拆分

### P1-3-1 升级 Message 数据模型与历史接口

**任务目标**

将 `Message` 从文本专用模型升级为最小通用消息模型，并让历史接口直接返回统一消息形状。

**当前范围**

- 数据模型字段升级
- Schema / Response Model 升级
- Message 历史 REST 对齐

**不做什么**

- 不做 `session -> conversation` 重命名
- 不展开 `code` / `diff` / `artifact` / `deploy` 的具体业务结构
- 不做 Runtime 抽象

**需要改动的模块**

- [backend/app/models/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/message.py)
- [backend/app/schemas/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/schemas/message.py)
- [backend/app/api/sessions.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/sessions.py)
- [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)
- [frontend/src/types/agenthub.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/types/agenthub.ts)

**详细实现步骤**

1. 将 `content_type` 重构为 `type`
2. 将 `delivery_status` 重构为 `status`
3. 增加 `payload` 与 `metadata`
4. 为 `payload` / `metadata` 提供 JSON 持久化能力
5. 将 Message REST response model 切到统一字段集合
6. 更新 shared / frontend 消息类型，使历史消息与流式完成消息同构
7. 增补一次性迁移脚本方案：
   - 测试环境依赖 ORM 自动重建
   - 本地开发数据库执行 `messages` 表迁移脚本
   - 旧数据按 `content_type/delivery_status -> type/status` 映射并回填 `payload/metadata`

**测试方案**

- 模型测试：
  - `type/status/payload/metadata` 字段存在
  - `status` 默认值符合预期
- 历史接口测试：
  - 返回统一字段
  - 不再返回旧 `content_type/delivery_status`
  - `text` 类型历史消息的 `payload/metadata` 结构符合约定
  - 不返回 `status=streaming` 的进行中占位消息
- 迁移测试：
  - 旧 `completed/interrupted` 数据可映射为新 `completed/failed`
  - 旧文本消息可回填 `payload.text`

**验收标准**

- Message 历史接口与后续流式结束后的正式消息结构一致
- Phase2 不需要再推翻当前 Message 数据模型
- schema 迁移路径已被写成明确决策，不再是开放阻塞项

### P1-3-2 用 FixedAgentResponder 替换真实 provider 主链路

**任务目标**

将当前 WS 主链路从真实 provider 流切换为固定回复器，只验证消息承载、状态切换、落库和推送。

**当前范围**

- 新增 `FixedAgentResponder`
- `ws.py` 改为调用固定回复器
- 移除默认主链路对真实 provider 的依赖

**不做什么**

- 不删除 provider 相关代码
- 不将 `FixedAgentResponder` 上升为 Runtime 抽象
- 不做真实 Prompt / Context / Tool / 历史注入

**需要改动的模块**

- 新增 `backend/app/services/fixed_agent_responder.py`
- [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)

**详细实现步骤**

1. 在 `ws.py` 保留：
   - `ping/pong`
   - `invalid_request`
   - `session_not_found`
   - 会话级 in-flight guard
2. 合法 `send_message` 时先落 human message
3. 创建 agent message 占位并持久化，状态为 `streaming`
4. 调用 `FixedAgentResponder` 输出统一事件流
5. 正常结束时：
   - 回写完整 `content`
   - 同步 `payload.text`
   - `status=completed`
6. 异常时：
   - 若 agent message 已创建，则 `status=failed`
   - 返回 `message_error`

**测试方案**

- WebSocket 时序测试：
  - `message_start -> message_delta* -> message_end`
- 落库测试：
  - human message 先落库
  - agent message 占位后落库
  - 流结束后 `status=completed`
- 错误测试：
  - 固定回复器失败时返回 `message_error`
  - DB 中 agent message 状态为 `failed`
- 旁路测试：
  - 默认主链路不再触发真实 provider 调用

**验收标准**

- 当前默认回复链路已不再依赖真实 provider
- WS 推送、数据库状态与历史接口三者一致

### P1-3-3 切换 shared WebSocket 协议到统一事件模型

**任务目标**

将跨端真相源从旧的 `chat_stream/agent_typing/error` 切到统一的 `message_*` 事件协议。

**当前范围**

- `shared/schemas/ws_messages.json`
- `shared/index.ts`
- 后端出站消息结构
- 前端入站消息类型

**不做什么**

- 不长期保留新旧双协议并存
- 不为兼容旧前端添加长期双发逻辑

**需要改动的模块**

- [shared/schemas/ws_messages.json](/D:/code/ZiJieAI/AgentHub/shared/schemas/ws_messages.json)
- [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)
- [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
- [frontend/src/utils/ws-client.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/utils/ws-client.ts) 如有显式解析

**详细实现步骤**

1. 从 schema 中移除旧主协议角色：
   - `chat_stream`
   - `agent_typing`
   - 旧 `error`
2. 新增：
   - `message_start`
   - `message_delta`
   - `message_end`
   - `message_error`
3. 保持 client->server `send_message` 契约不变
4. 确保 `shared/index.ts` 与 JSON Schema 一致
5. 后端实际返回字段必须和 shared 完全一致

**测试方案**

- shared 类型检查：
  - 新事件类型存在
  - 旧成功事件不再作为主链路联合类型
- 后端契约测试：
  - 返回字段与 schema 对齐
  - 不再发送 `agent_typing/chat_stream`

**验收标准**

- shared 成为统一消息流协议的唯一真相源
- 前后端不再对同一事件使用两套命名和字段语义

### P1-3-4 改造前端 stream 状态机与页面接线

**任务目标**

让前端从旧的 `chat_stream/agent_typing` 特判式归并，切到基于 `message_start/delta/end/error` 的统一流状态管理。

**当前范围**

- `useChatStreamState` 状态机
- 页面接线
- 消息列表流式占位与结束收口

**不做什么**

- 不做复杂视觉重设计
- 不做未完成流跨刷新恢复
- 不增加额外的消息操作体系

**需要改动的模块**

- [frontend/src/utils/useChatStreamState.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/utils/useChatStreamState.ts)
- [frontend/src/components/zhu.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu.vue)
- [frontend/src/veiws/Chat-show-area.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/veiws/Chat-show-area.vue)
- [frontend/src/store/module/useSessionStore.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/store/module/useSessionStore.ts) 如需

**详细实现步骤**

1. 收到 `message_start` 时：
   - 创建当前会话 in-flight 消息占位
   - 占位即使用后端返回的完整消息壳
   - UI 状态标记为 `streaming`
2. 收到 `message_delta` 时：
   - 按 `stream_id + message_id` 归并到同一条消息
   - 追加 `delta`
   - 同步更新临时 `content/payload.text`
3. 收到 `message_end` 时：
   - 当前 in-flight 消息收口
   - 以本地累计内容和后端 message_id 进入正式消息列表
   - 释放 in-flight 状态
   - 立即触发一次后台 `fetchMessages(sessionId)`，完成 optimistic human + agent 正常路径对账
4. 收到 `message_error` 时：
   - 若本地存在同 `stream_id` 消息，标记失败并触发一次历史重拉
   - 重拉后以后端历史真相覆盖本地失败态
   - 若本地无对应消息，仅提示错误，不插入伪消息
5. 发送 human message 时：
   - 本地 optimistic 消息也使用统一消息形状
   - `metadata.source = "optimistic_human"`
6. `fetchMessages` 合并时：
   - 按 `message.id` upsert 正式历史消息
   - 删除当前会话中 `metadata.source = "optimistic_human"` 的临时 human 消息
   - 若正式历史消息与本地 agent 流式消息 `message.id` 相同，则覆盖本地消息，不新增重复项
7. 页面层移除旧的：
   - `agent_typing` 分支
   - `chat_stream` 分支
   - 旧的模拟 chunk 逻辑

**测试方案**

- 状态机测试：
  - `message_start` 创建占位
  - 多个 `message_delta` 正确归并
  - `message_end` 后占位转正式消息
  - `message_end` 后触发一次后台历史重拉
  - `message_error` 时释放悬挂状态并触发历史重拉
  - optimistic human message 使用统一 shape
  - 历史重拉后 optimistic human message 被真实 human message 接管
  - 历史重拉后同 `message.id` 的 agent 消息不会重复插入
- 页面 / 组件测试：
  - 消息只增长一条，不会按增量拆成多条
  - 刷新后只靠历史接口恢复完整消息

**验收标准**

- 前端只感知统一消息流，不感知底层执行器是固定回复器还是未来 Runtime
- 旧 `chat_stream/agent_typing` 前端分支完全退出主链路

### P1-3-5 完成前后端统一验证与阶段验收准备

**任务目标**

补齐本阶段需要的自动化验证和联调验收约束，确保 `Phase1-3` 结束后不存在“真实 LLM 直接回复 UI”的旁路残留。

**当前范围**

- 后端契约测试
- 前端状态机 / 组件测试
- 联调验收清单

**不做什么**

- 不进入 `Phase1-4`
- 不提前做 `Phase2 Runtime` 接管

**需要改动的模块**

- 后端测试文件
- 前端测试文件
- 可在相关 task 文档或 README 中补联调说明

**联调要求**

1. 新建会话并发送消息
2. 后端先落 human message
3. 前端收到 `message_start` 后立即出现 agent 占位
4. 前端逐步收到 `message_delta` 并增长同一条消息
5. 收到 `message_end` 后消息收口
6. 刷新页面后，历史接口返回统一消息模型，页面恢复完整消息
7. 默认主链路不得触发真实 provider

**测试方案**

- 后端：
  - `message_start -> delta* -> end`
  - 错误链路 `message_error`
  - 历史接口统一字段
  - 不再发送旧事件
- 前端：
  - `start` 创建占位
  - `delta` 归并
  - `end` 收口
  - `end` 后触发一次后台历史重拉并完成 optimistic / persisted 对账
  - `error` 不残留悬挂消息
  - 刷新恢复只依赖历史接口

**验收标准**

- 本阶段主链路已满足 `implementation-phases.md` 中 `Phase1-3` 完成标准
- `Phase2` 只需替换执行器，不需重构 IM、Message、Streaming、WebSocket 和前端消息消费方式

## 8. 统一测试方案

建议至少覆盖以下层次：

- 模型 / Schema 测试
  - Message 统一字段存在
- 后端业务测试
  - 固定回复器时序
  - WS 协议映射
  - 历史接口统一字段
- Shared 契约检查
  - schema / TypeScript 类型一致
- 前端状态机测试
  - start / delta / end / error
- 前端组件测试
  - 单条流式消息增长
  - 失败收口

建议验证命令：

- `python -m pytest backend/tests/test_ws.py`
- `python -m pytest backend/tests/test_ws_provider.py`
- 如新增：
  - `python -m pytest backend/tests/test_fixed_agent_responder.py`
- 前端：
  - 项目现有测试命令下运行与 stream state / chat 页面相关测试

## 9. 统一验收标准

- 当前回复链路不再绕过 `Message` 存储、状态与 WS 推送
- `Message` 已具备 `type/content/payload/metadata/status` 最小通用封装
- WebSocket 协议已统一到 `message_start/message_delta/message_end/message_error`
- 固定回复器替代真实 provider 成为默认主链路
- 前端只消费统一事件流，不再依赖 `chat_stream/agent_typing` 特判
- 历史接口与流式完成消息结构一致
- 刷新后消息恢复不依赖增量片段缓存
- 当前仓库中不存在“真实 LLM 直接回复 UI”的默认旁路

## 10. 依赖或阻塞

- 若当前数据库环境已落地旧 `messages` 表结构，需要先明确 `type/status/payload/metadata` 的实际迁移方式。
- 若前端仍有未纳入当前扫描范围的旧 `chat_stream` 依赖，联调前需统一清理，否则会出现隐性双协议消费。
- 若 shared schema 仍被其他旧页面或脚本依赖，需以本 task 为准统一切换，不要在实现时静默保留长期兼容层。

## 11. 下一步

- 本 task 文档完成后，下一步进入 `task-review-from-spec`。
