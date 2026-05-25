# Task: P1-2 前端句段级流式消费、消息归并与 thinking/typing 展示

## 0. 文档定位

- 本文档是 [openspec/specs/implementation-phases.md](/D:/code/ZiJieAI/AgentHub/openspec/specs/implementation-phases.md) 中 `P1-2 句段级流式输出与 typing` 的前端配套 task 文档。
- 本文档复用已确认的总实现方案，不重新讨论后端边界，也不扩展到 `P1-3` 或 `P2`。
- 本文档以现有后端 task 文档 [openspec/changes/IM/p1-2-tasks.md](/D:/code/ZiJieAI/AgentHub/openspec/changes/IM/p1-2-tasks.md) 为唯一后端契约来源。
- 本文档只拆前端实现任务、前后端联调要求、前端测试方案与前端验收标准。

已确认并直接复用的关键决策：

- 上游是真实流式，服务端做句段聚合，前端按 `stream_id + message_id` 归并。
- Provider 新增 `stream_chat()`，句段聚合放在应用层，不放在 Provider 层。
- `WS /ws/{session_id}` 对齐 `shared` 协议，不保留旧成功消息风格作为长期主链路。
- `chat_stream` 的 final chunk 语义固定为：
  - `is_final=true`
  - `content_chunk=""`
- 前端不自行推断持久化状态，后端通过消息字段暴露 `delivery_status`，前端按字段渲染。
- `delivery_status=interrupted` 的消息需要在前端显示轻量“已中断”标记。
- `typing` 的本期展示范围不再是输入区全局提示，而是消息流尾部的同域占位消息。
- 用户发送后，Agent 应立即出现一条“正在思考...”占位；首个 `chat_stream` chunk 到来后，由同一条消息接管并开始流式增长。

## 1. 任务目标

- 让前端从 `P1-1` 的“每次收到一条完整 `chat_stream` 就 append 一条消息”升级为 `P1-2` 的“流式归并 + final 收口 + typing/thinking 占位”。
- 将 WebSocket 原始协议消费逻辑从页面组件中抽离，形成可复用、可测试的前端 stream 归并状态机 / composable。
- 让消息列表对后端 `P1-2` 契约具备稳定消费能力：
  - `chat_stream`
  - `agent_typing`
  - `error`
  - `delivery_status`
- 保持消息 UI 的最小自然体验：
  - 用户发送后立即看到 Agent 思考中
  - 收到首个 chunk 后，思考占位被真实消息接管
  - `interrupted` 历史消息可识别，但不引入复杂恢复交互

## 2. 当前范围

- 前端 WebSocket 入站消息类型对齐 `shared`。
- 流式归并状态机 / composable。
- Session / Message store 的接线调整。
- 消息流中的 thinking/typing 占位行为。
- 历史消息 `delivery_status` 字段渲染。
- 前端单测 / 组件测试 / 联调验收要求。

## 3. 不做什么

- 不做 token 级动画效果。
- 不做刷新后恢复未完成 in-flight stream。
- 不做多条并行 Agent 回复。
- 不做“暂停 / 恢复 / 继续生成 / 取消生成”。
- 不做复杂错误恢复策略，仅做最小可理解错误收口。
- 不做 `P1-3` 的上下文承接、历史注入或回复链展示。
- 不做 `P2` 的多 Agent、多 Provider、群聊、多参与者流式归并。

## 4. 依赖与前置条件

- 后端 `P1-2` task 已明确以下契约：
  - `chat_stream` 使用 `stream_id`、`message_id`、`content_chunk`、`is_final`
  - `agent_typing` 使用 `stream_id`、`is_typing`
  - `error` 在所有场景下都带 `stream_id`
  - `error_code` 需要覆盖并对齐 `P1-2` 已确认错误码，包括：
    - `agent_busy`
    - `provider_not_configured`
    - `provider_request_failed`
    - `provider_response_invalid`
    - `invalid_request`
    - `session_not_found`
    - `unknown`
  - final chunk 固定为空终止帧
  - `delivery_status` 由后端持久化并暴露给前端
- 现有前端主要相关模块：
  - [frontend/src/components/zhu.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu.vue)
  - [frontend/src/veiws/Chat-show-area.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/veiws/Chat-show-area.vue)
  - [frontend/src/store/module/useSessionStore.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/store/module/useSessionStore.ts)
  - [frontend/src/utils/ws-client.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/utils/ws-client.ts)
  - [frontend/src/utils/agenthub-ws.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/utils/agenthub-ws.ts)
  - [frontend/src/types/agenthub.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/types/agenthub.ts)
  - [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)

## 5. 现状与问题

- 当前页面层仍直接消费 WebSocket 消息，并在收到 `chat_stream` 时直接 `appendMessage`。
- 当前前端入站消息模型仍偏 `P1-1` 风格，依赖旧字段：
  - `content`
  - `sender_role`
  - `created_at`
- 当前消息列表缺少“in-flight reply”概念，没有按 `stream_id + message_id` 做归并。
- 当前前端没有 thinking 占位消息，也没有 `delivery_status=interrupted` 的 UI 表达。

这意味着如果直接接入后端 `P1-2`：

- chunk 会被误当作多条独立消息插入。
- `typing` / `thinking` 生命周期无法稳定表达。
- final chunk 与 pre-stream error 无法被正确收口。

## 6. 前端契约与运行规则

### 6.1 前端数据模型约束

历史消息模型至少需要支持：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 历史消息唯一 ID |
| `session_id` | string | 是 | 所属会话 |
| `sender_type` | string | 是 | `human` / `agent` / `system` |
| `sender_role` | string \| null | 是 | 当前阶段 Agent 角色可为 `PM` |
| `content` | string | 是 | 消息完整正文 |
| `content_type` | string | 是 | 当前阶段固定 `text` |
| `created_at` | string | 是 | 创建时间 |
| `delivery_status` | string | 否 | `completed` / `interrupted` |

前端视图层允许额外维护仅存在于 UI 的临时字段，例如：

| 字段 | 类型 | 说明 |
|------|------|------|
| `ui_status` | string | `thinking` / `streaming` / `done` |
| `stream_id` | string | 当前 in-flight stream 的追踪键 |
| `message_id` | string | 首个 chunk 到来后绑定的真实消息 ID |
| `is_ephemeral` | boolean | 是否为未持久化的临时视图消息 |

约束：

- `delivery_status` 是后端真相源，前端不得自行长期推断。
- `ui_status` 仅用于视图层或 composable 内部，不写回后端消息模型。
- thinking 占位仅存在于前端视图层，不写入历史消息 store，也不参与历史消息持久化去重。

### 6.2 WebSocket 消费规则

#### `agent_typing`

前端收到：

```json
{
  "type": "agent_typing",
  "agent_role": "PM",
  "timestamp": "2026-05-23T10:29:58Z",
  "stream_id": "stream-uuid",
  "is_typing": true
}
```

运行规则：

- 收到 `is_typing=true` 时：
  - 若该 `stream_id` 尚无 in-flight 视图消息，则在消息流尾部立即插入一条临时 Agent 占位消息
  - 占位文案使用统一文案，例如：`PM 正在思考...`
  - 占位消息状态记为 `ui_status=thinking`
  - 此时占位没有真实 `message_id`，只能以 `stream_id` 作为临时身份
- 收到 `is_typing=false` 时：
  - 若该 `stream_id` 已有真实消息接管，则关闭其 typing 状态
  - 若该 `stream_id` 仅存在 thinking 占位且从未收到任何 chunk，则需结合本次流是否以 `error` 收口决定移除占位

#### `chat_stream`

前端收到：

```json
{
  "type": "chat_stream",
  "agent_role": "PM",
  "timestamp": "2026-05-23T10:30:00Z",
  "stream_id": "stream-uuid",
  "message_id": "message-uuid",
  "content_chunk": "这是本次 flush 出来的一段文本。",
  "is_final": false
}
```

运行规则：

- 归并键固定为 `stream_id + message_id`。
- 首个普通 chunk 到来时：
  - 若此前已有同 `stream_id` 的 thinking 占位，则由该条占位消息被接管
  - 接管的唯一语义固定为：
    - 占位保留原有视觉位置
    - 占位立即绑定真实 `message_id`
    - 占位从“仅按 `stream_id` 临时标识”切换为“按 `stream_id + message_id` 稳定标识”
    - 该切换是“替换原占位身份”，不是新增第二条消息
  - 占位切换为真实流式消息
  - 真实消息内容初始化为首个 `content_chunk`
  - 真实消息状态记为 `ui_status=streaming`
- 后续普通 chunk 到来时：
  - 只向同一条消息追加 `content_chunk`
  - 不新增第二条 Agent 消息
- 当收到 `is_final=true && content_chunk=""` 时：
  - 仅作为终止帧使用
  - 不向正文追加内容
  - 当前消息状态切换为 `ui_status=done`
  - 本地 in-flight 映射释放

与历史消息去重规则：

- thinking 占位在首个 chunk 到来前不得写入历史消息 store。
- 首个 chunk 到来后，当前流式消息可进入前端消息视图主链路，但必须绑定真实 `message_id`。
- 若同一 `message_id` 的历史消息、终态同步结果或重拉结果进入列表：
  - 必须与当前已接管的流式消息合并
  - 不得新增第二条相同 `message_id` 的消息
- 前端消息列表的最终去重主键以 `message_id` 为准；`stream_id` 仅用于 in-flight 请求态追踪。

#### `error`

前端收到：

```json
{
  "type": "error",
  "agent_role": "PM",
  "timestamp": "2026-05-23T10:30:02Z",
  "stream_id": "stream-uuid",
  "error_code": "provider_request_failed",
  "error_message": "Provider request failed"
}
```

运行规则：

- 所有 `error` 都必须按 `stream_id` 归属到某次请求。
- 若该 `stream_id` 仅存在 thinking 占位且从未收到 chunk：
  - 移除 thinking 占位
  - 不留下空 Agent 消息
- 若该 `stream_id` 已经进入真实流式消息阶段：
  - 前端不再继续增长该消息
  - 当前页面必须立即触发一次当前会话消息重拉，以拿到后端 finalized 后的 `delivery_status`
  - 在重拉结果返回前，该消息可进入本地过渡态，例如 `ui_status=syncing_interrupted`
  - 重拉结果返回后，必须以后端历史消息为准完成收口：
    - 若返回同 `message_id` 且 `delivery_status=interrupted`，则用该历史消息替换本地 in-flight 视图消息
    - 若返回同 `message_id` 且 `delivery_status=completed`，则按 completed 收口
- 前端可保留最小错误反馈，但不得因为错误事件再插入一条伪 Agent 文本消息污染历史流。

### 6.3 历史消息渲染规则

- `GET /api/sessions/{session_id}/messages` 返回的历史消息是唯一历史真相源。
- 若历史消息 `delivery_status=completed`：
  - 按普通消息展示
- 若历史消息 `delivery_status=interrupted`：
  - 在气泡或消息尾部显示轻量“已中断”标记
  - 不要求本期提供恢复按钮或特殊交互

### 6.4 会话切换与边界规则

- in-flight stream 状态必须按 `session_id` 隔离。
- 切换会话时：
  - 不得把前一会话的临时 thinking / streaming 视图污染到当前会话
  - 当前会话消息列表应由“该会话历史消息 + 该会话 in-flight 视图”组成
- 刷新页面后：
  - 不要求恢复旧的未完成流式态
  - 只依赖历史接口恢复 finalized 消息

## 7. Task 拆分

### FE-P1-2-1 对齐前端 WS 类型与消息模型

**任务目标**

将前端类型系统从 `P1-1` 的完整消息回推模型切换到 `P1-2` 的流式协议模型，为后续归并状态机提供稳定输入。

**当前范围**

- WebSocket 入站消息类型对齐 `shared`
- 历史消息模型补齐 `delivery_status`
- 清理旧的成功消息字段依赖

**不做什么**

- 不在这一 task 内实现完整 UI 逻辑
- 不在这一 task 内实现 thinking 占位或消息归并

**需要改动的模块**

- [frontend/src/types/agenthub.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/types/agenthub.ts)
- [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)
- [shared/schemas/ws_messages.json](/D:/code/ZiJieAI/AgentHub/shared/schemas/ws_messages.json)
- [frontend/src/utils/ws-client.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/utils/ws-client.ts)

**详细实现步骤**

1. 对齐或复用 `shared` 中的 WebSocket 消息类型定义。
2. 为前端历史消息模型增加 `delivery_status` 字段。
3. 对齐 `shared` 中 `P1-2` 需要的 `error_code` 枚举，至少包括：
   - `agent_busy`
   - `provider_not_configured`
   - `provider_request_failed`
   - `provider_response_invalid`
   - `invalid_request`
   - `session_not_found`
   - `unknown`
4. 移除前端主链路对以下旧字段的依赖：
   - `chat_stream.content`
   - `chat_stream.sender_role`
   - `chat_stream.created_at`
5. 让 `ws-client` 能正确透传：
   - `chat_stream`
   - `agent_typing`
   - `error`

**测试方案**

- 类型断言测试或编译期检查：
  - `chat_stream` 必须具备 `stream_id`、`message_id`、`content_chunk`、`is_final`
  - `agent_typing` 必须具备 `stream_id`、`is_typing`
  - `error` 必须支持 `P1-2` 约定的错误码枚举
  - 历史消息支持 `delivery_status`

**验收标准**

- 前端主链路不再依赖旧的完整消息风格字段。
- `P1-2` 协议字段可被完整表达。

### FE-P1-2-2 新增 stream 归并状态机 / composable

**任务目标**

将 WebSocket 原始协议消费逻辑从页面组件抽离，建立可独立测试的前端流式归并状态机。

**当前范围**

- thinking 占位创建与收口
- `chat_stream` 归并
- final frame 终止逻辑
- pre-stream error 收口

**不做什么**

- 不直接读写具体页面 DOM
- 不在此层承担历史接口拉取
- 不把临时 UI 状态写入后端消息模型

**需要改动的模块**

- 新增 `frontend/src/composables/useChatStreamState.ts` 或等价模块
- 可配合更新 [frontend/src/store/module/useSessionStore.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/store/module/useSessionStore.ts)

**详细实现步骤**

1. 设计按 `session_id` 隔离的 in-flight 状态容器。
2. 设计按 `stream_id` 索引的请求态：
   - 是否已出现 thinking 占位
   - 是否已收到首个 chunk
   - 当前 message_id
   - 当前聚合正文
   - 当前是否处于 `syncing_interrupted` 过渡态
3. 收到 `agent_typing=true` 时创建消息流尾部临时占位。
4. 收到首个 `chat_stream` 普通 chunk 时，用真实消息接管占位，并完成从临时 `stream_id` 身份到稳定 `message_id` 身份的切换。
5. 收到后续 chunk 时持续归并正文。
6. 收到 final 空终止帧时完成本次流式消息收口并释放 in-flight。
7. 收到 pre-stream error 时移除 thinking 占位。
8. 收到 partial 后 error 时停止继续增长，并立即触发当前会话消息重拉，等后端 `delivery_status` 真相源完成同屏收口。

**测试方案**

- 状态机单测：
  - `agent_typing=true` 创建占位
  - 首个 chunk 接管占位
  - 接管后绑定 `message_id` 且不产生双消息
  - 多 chunk 正确归并
  - final 空终止帧不追加正文
  - pre-stream error 移除占位
  - partial 后 error 会触发一次消息重拉并以同 `message_id` 历史消息收口
  - 会话隔离成立

**验收标准**

- 状态机可以在不挂载页面组件的情况下独立测试。
- 一次流式回复在前端只表现为一条 in-flight Agent 消息。

### FE-P1-2-3 改造页面接线与消息列表渲染

**任务目标**

让页面组件只消费统一的消息视图，而不是直接理解 WebSocket 协议细节。

**当前范围**

- 页面与 `ws-client` 的接线改造
- 消息列表合成视图
- thinking 占位与 streaming 消息渲染
- `interrupted` 轻量标记

**不做什么**

- 不做复杂视觉重设计
- 不在消息列表中新增第二套临时消息体系

**需要改动的模块**

- [frontend/src/components/zhu.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu.vue)
- [frontend/src/veiws/Chat-show-area.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/veiws/Chat-show-area.vue)
- [frontend/src/store/module/useSessionStore.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/store/module/useSessionStore.ts)
- 相关消息气泡组件

**详细实现步骤**

1. 页面层不再在收到 `chat_stream` 时直接 `appendMessage`。
2. 页面层将 WS 入站事件交给 stream 状态机处理。
3. 消息列表视图改为组合：
   - 历史 finalized 消息
   - 当前会话 in-flight 视图消息
4. thinking 占位使用消息流内的 Agent 临时消息样式。
5. 历史消息若 `delivery_status=interrupted`，显示轻量“已中断”标记。
6. 保证“thinking 占位 -> streaming 正文 -> finalized 消息”是同一条视觉消息链，而不是两条。
7. 若当前页发生 partial 后 error，页面需在重拉完成后将同一 `message_id` 的历史消息无缝接管当前流式消息位置。

**测试方案**

- 组件测试：
  - 用户发送后立刻出现“PM 正在思考...”
  - 首个 chunk 到来后占位被正文接管
  - 不出现双消息
  - partial 后 error 时同屏收口为带“已中断”标记的历史消息
  - `interrupted` 消息显示标记

**验收标准**

- 用户可立即看到 Agent 正在思考。
- 首个 chunk 后消息开始自然增长。
- UI 不会把 chunk 拆成多条消息。

### FE-P1-2-4 完成前端联调与自动化验证

**任务目标**

让前端 `P1-2` 的可见行为通过自动化测试和联调清单被定死，避免实现时再次分叉。

**当前范围**

- 前端单测 / 组件测试补齐
- 与后端 `P1-2` 契约的联调清单

**不做什么**

- 不在这一 task 内扩充新的功能范围

**需要改动的模块**

- 相关前端测试文件
- [frontend/src/components/zhu.spec.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu.spec.ts)
- 可新增 stream 状态机测试文件

**联调要求**

- 前端必须按 `stream_id + message_id` 归并，不得按 chunk 逐条插入历史消息。
- 前端必须将 `is_final=true && content_chunk=""` 视为纯终止帧。
- 前端必须正确处理 pre-stream error 的占位移除。
- 前端必须在 partial 后 error 时触发当前会话消息重拉，并以同 `message_id` 的历史消息完成同屏收口。
- 前端必须按历史接口返回的 `delivery_status` 渲染“已中断”。

**测试方案**

- 建议至少覆盖：
  - `typing=true -> thinking 占位出现`
  - `thinking -> 首个 chunk 接管`
  - `thinking -> 首个 chunk 接管后绑定 message_id 且不双发`
  - `多个 chunk -> 单消息增长`
  - `final 空终止帧 -> 收口`
  - `typing 后直接 error -> 占位消失`
  - `partial 后 error -> 触发重拉 -> 同屏显示 interrupted`
  - `interrupted` 历史消息渲染标记
  - 跨会话不串流

**验收标准**

- 前端自动化测试能覆盖主要流式体验风险点。
- 前后端联调时无需再猜测 `P1-2` 协议语义。

## 8. 统一测试方案

建议至少覆盖以下层次：

- 类型层
  - `shared` / 前端消息类型对齐
- 状态机层
  - thinking 占位
  - stream 归并
  - final 收口
  - pre-stream error 收口
- 组件层
  - 消息流内 thinking 展示
  - 占位被首个 chunk 接管
  - interrupted 标记展示
- 联调层
  - 后端 `P1-2` 协议事件顺序可被前端稳定消费

## 9. 前端统一验收标准

- 用户发送消息后，消息流尾部会立即出现一条 Agent thinking 占位。
- 首个 `chat_stream` chunk 到来后，thinking 占位被同一条真实流式消息接管。
- 首个 chunk 接管后，消息会绑定真实 `message_id`，后续历史同步不会再生成第二条相同消息。
- 后续 chunk 只会增长同一条消息，不会拆成多条。
- `is_final=true && content_chunk=""` 只作为终止帧，不追加正文。
- pre-stream error 不会在消息流里留下空 Agent 消息。
- partial 后 error 时，当前页面会自动重拉当前会话消息，并在同屏将该消息收口为后端 finalized 状态。
- 历史消息若 `delivery_status=interrupted`，会显示轻量“已中断”标记。
- 不同会话的 in-flight stream 不会互相污染。
- 刷新页面后不要求恢复未完成流式态，但能通过历史接口恢复 finalized 消息。

## 10. 依赖或阻塞

- 若后端历史消息接口尚未暴露 `delivery_status`，则“已中断”标记无法成立。
- 若前端继续同时保留旧 `chat_stream.content` 风格和新协议长期共存，会增加页面层分叉逻辑，需尽快统一到 `P1-2` 契约。
- 若消息列表当前组件强依赖“消息一定来自持久化历史”，则需要先接受“前端存在临时视图消息”的设计。

## 11. 下一步

- 本文档确认后，进入针对前端 task 文档的 review。
- review 通过后，再进入前端实现与 TDD。
