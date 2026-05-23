# Task: P1-2 句段级流式输出与 `typing`

## 0. 文档定位

- 本文档基于 [openspec/specs/implementation-phases.md](/D:/code/ZiJieAI/AgentHub/openspec/specs/implementation-phases.md) 中的 `P1-2 句段级流式输出与 typing`。
- 本文档按 `task-planning-from-spec` 拆分 backend/API scoped task，不重新澄清需求，不进入编码，也不拆前端实现任务。
- 本文档复用已确认的阶段边界：
  - `P1-2` 只做句段级 chunk，不做逐 token streaming。
  - `P1-2` 不做复杂中断、续传、消息合并策略。
  - `P1-2` 不做多 Agent、多 Provider、上下文承接，这些分别留在 `P1-3` 和 `P2`。
- 本文档同时吸收本轮已确认实现决策：
  - 上游采用真实流式，`Provider` 新增 `stream_chat()`，返回原始文本 delta 的异步迭代器。
  - 句段聚合放在应用服务层，不放在 Provider 层。
  - `ws.py` 变薄，只保留 WebSocket 入口、协议映射和异常收口。
  - 服务端按“标点优先，阈值兜底”做句段 flush。
  - `typing` 生命周期为：开始前 `typing=true`，结束或失败后 `typing=false`。
  - 首个完整句段出现时创建 agent message，获取稳定 `message_id`；流结束时一次性 finalize 完整内容。
  - 单会话只允许一条在途回复；流式期间拒绝新的 `send_message`。
  - 已开始输出后若失败，保留 partial content，落库为 `interrupted`，同时返回错误事件。
  - WebSocket 出站消息在 `P1-2` 直接对齐 `shared` 中的流式字段，不再沿用当前完整消息风格。
  - `Message` 增加最小持久化状态位：`completed | interrupted`。

## 1. 任务目标

- 将当前 `P1-1` 的“非流式完整回复”升级为“真实上游流式 + 服务端句段聚合 + 前端按 chunk 归并”的最小闭环。
- 在不引入逐 token 复杂度的前提下，让真实 Agent 回复具备清晰的实时感和稳定的 `typing` 状态。
- 将当前实际 WebSocket 返回体收敛到 [shared/schemas/ws_messages.json](/D:/code/ZiJieAI/AgentHub/shared/schemas/ws_messages.json) 与 [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts) 预留的流式契约。
- 为 `P1-3` 的最小上下文承接预留干净的后端边界：Provider 只吐原始 delta，业务层负责句段聚合与消息收口。

## 2. 当前范围

- Provider 抽象从“单次完整文本回复”扩展为“完整回复 + 原始流式 delta 回复”。
- 句段聚合器与流式编排服务。
- `WS /ws/{session_id}` 的流式消息发送链路、`typing` 事件、错误事件和在途并发保护。
- `Message` 持久化状态位与 agent message finalize 语义。
- `shared` WebSocket 协议对齐与后端联调要求。
- 自动化测试、契约测试和验收要求。

## 3. 不做什么

- 不做逐 token 流式渲染。
- 不做流式回复的暂停、恢复、续传或取消。
- 不做多条待发送消息排队。
- 不做同一会话内多条并行 Agent 回复。
- 不做历史消息上下文注入，这些留给 `P1-3`。
- 不做第二个 Provider 接入，这些留给 `P2-3`。
- 不做前端详细实现任务；如涉及前后端协作，只定义 shared / API / WebSocket 契约和联调要求。
- 不做 Auth、JWT 和 `current_user` 收口，这些留给 `P2-1`。

## 4. 依赖与前置条件

- `MVP-3` 已提供最小 Session / Message / WebSocket 入口。
- `MVP-4` 已提供 human message 落库、agent message 落库与 WebSocket 返回的最小闭环。
- `MVP-5` 已提供 `ping/pong`、基础重连和前端连接状态机。
- `P1-1` 已完成真实 Provider 接入、默认 `PM Agent`、`WS /ws/{session_id}` 的真实 Agent 非流式链路。
- 当前已有可复用模块：
  - [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
  - [backend/app/providers/base.py](/D:/code/ZiJieAI/AgentHub/backend/app/providers/base.py)
  - [backend/app/providers/openai_compatible.py](/D:/code/ZiJieAI/AgentHub/backend/app/providers/openai_compatible.py)
  - [backend/app/services/agent_runtime.py](/D:/code/ZiJieAI/AgentHub/backend/app/services/agent_runtime.py)
  - [backend/app/models/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/message.py)
  - [shared/schemas/ws_messages.json](/D:/code/ZiJieAI/AgentHub/shared/schemas/ws_messages.json)
  - [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)

## 5. 需要改动的后端模块、数据模型、接口或配置

- Provider 抽象与实现
  - [backend/app/providers/base.py](/D:/code/ZiJieAI/AgentHub/backend/app/providers/base.py)
  - [backend/app/providers/openai_compatible.py](/D:/code/ZiJieAI/AgentHub/backend/app/providers/openai_compatible.py)
- 流式编排服务
  - 新增 `backend/app/services/agent_stream_service.py`
  - 可拆分 `backend/app/services/sentence_chunker.py`
- WebSocket 入口与消息协议映射
  - [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
- 数据模型
  - [backend/app/models/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/message.py)
  - 如项目使用迁移工具，则新增对应 migration；如当前仍使用 `Base.metadata.create_all`，则同步更新建表结构
- Shared 契约
  - [shared/schemas/ws_messages.json](/D:/code/ZiJieAI/AgentHub/shared/schemas/ws_messages.json)
  - [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)
- 测试
  - [backend/tests/test_provider.py](/D:/code/ZiJieAI/AgentHub/backend/tests/test_provider.py)
  - [backend/tests/test_ws_provider.py](/D:/code/ZiJieAI/AgentHub/backend/tests/test_ws_provider.py)
  - 可新增 `backend/tests/test_sentence_chunker.py`
  - 可新增 `backend/tests/test_agent_stream_service.py`

不需要改动：

- Session REST 路由路径与方法。
- `send_message` 的客户端入参形状。
- `ping/pong` 基础行为。

## 6. 契约与运行规则

### 6.1 Provider 抽象契约

在现有 `chat()` 基础上新增流式能力：

```python
@dataclass(frozen=True)
class ProviderStreamEvent:
    text_delta: str


class BaseProvider(ABC):
    @abstractmethod
    async def chat(self, input: ProviderInput) -> ProviderOutput:
        ...

    @abstractmethod
    async def stream_chat(self, input: ProviderInput) -> AsyncIterator[ProviderStreamEvent]:
        ...
```

约束：

- `stream_chat()` 只负责输出原始文本增量，不负责句段切分、不负责 `typing`、不负责 `message_id` 和 `stream_id`。
- `Provider` 抛出的业务异常继续沿用：
  - `ProviderNotConfiguredError`
  - `ProviderRequestError`
  - `ProviderResponseInvalidError`
- `P1-2` 的千问实现必须走真实上游流式能力，不允许在完整回复返回后本地假切句模拟流式。

### 6.2 `Message` 持久化契约

`messages` 表新增最小状态字段：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `delivery_status` | string | 是 | `completed` | Agent 回复持久化状态，枚举：`completed`、`interrupted` |

持久化规则：

- human message 仍在调用 Provider 前落库。
- agent message 在首个完整句段 flush 时创建，拿到稳定 `message_id`。
- 流正常结束时：
  - 将完整累计文本写回 agent message
  - `delivery_status=completed`
- 流已开始输出后失败时：
  - 将已累计 partial content 写回 agent message
  - `delivery_status=interrupted`
- 若上游在首个句段出现前失败：
  - 不落库 agent message
  - 仅保留 human message

说明：

- `delivery_status` 是后端真相源，用于支撑后续历史恢复和上下文注入判断。
- 本阶段不要求必须通过 Message REST 响应暴露该字段给前端；如不暴露，不得影响 `P1-2` 主链路成立。

### 6.3 句段聚合规则

服务端必须在业务层做句段切分，推荐抽象出独立聚合器。

切分规则：

1. 原始 delta 先进内存 buffer。
2. 命中强边界即 flush：
   - `。！？!?；;`
   - 双换行
3. 若迟迟没有强边界，使用兜底 flush：
   - 累计字符数达到 `50` 个字符
   - 或等待时间达到 `700ms`
4. 流结束时，剩余 buffer 必须全部 flush。

约束：

- flush 粒度是“句段级文本块”，不是 token。
- 聚合器输出必须是稳定、可测试的纯业务逻辑，不依赖具体 WebSocket 对象。

### 6.4 WebSocket 出站协议

`P1-2` 开始，`WS /ws/{session_id}` 的服务端成功事件正式对齐 `shared`。

#### `chat_stream`

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

字段定义：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定值 `chat_stream` |
| `agent_role` | string | 是 | 当前唯一真实 Agent 的角色，`P1-2` 固定为 `PM` |
| `timestamp` | string | 是 | 服务端发送该 chunk 的时间 |
| `stream_id` | string | 是 | 同一条流式回复的唯一 ID |
| `message_id` | string | 是 | 同一条 agent message 的稳定 ID |
| `content_chunk` | string | 是 | 本次追加的句段 chunk |
| `is_final` | boolean | 是 | 是否为该次回复的最后一个 chunk |

运行规则：

- 首个 chunk 出现时 `message_id` 必须已稳定。
- 最后一条 chunk 必须带 `is_final=true`。
- final chunk 固定作为“终止帧”使用，`content_chunk` 必须为空字符串。
- 若流结束时仍有尾缓冲文本，必须先发送一条 `is_final=false` 的普通 chunk 承载尾缓冲，再发送空的 final chunk。

#### `agent_typing`

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

- 开始消费上游流前先发一次 `is_typing=true`。
- 中间不反复发送 typing 心跳。
- 正常结束后，最后一个 `chat_stream(is_final=true)` 发完，再发 `is_typing=false`。
- 异常结束时也必须发 `is_typing=false`。

#### `error`

`error` 事件需向 `BaseMessage` 靠拢，且 `stream_id` 在所有错误场景下都必填。

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

新增或明确的错误码：

| `error_code` | 触发条件 | 是否已有 partial 输出 | 是否落库 agent message |
|------|------|------|------|
| `provider_not_configured` | Provider 配置缺失 | 否 | 否 |
| `provider_request_failed` | 上游调用失败、超时、网络错误、5xx | 可能有 | 有 partial 时是 |
| `provider_response_invalid` | 上游流式响应缺少可用文本内容 | 可能有 | 有 partial 时是 |
| `invalid_request` | WebSocket 请求体非法 | 否 | 否 |
| `session_not_found` | 会话不存在 | 否 | 否 |
| `agent_busy` | 同一会话已有在途回复 | 否 | 否 |
| `unknown` | 未分类异常 | 可能有 | 有 partial 时是 |

`stream_id` 生成规则：

- 对每一次合法的 `send_message` 请求，在进入 in-flight 校验前先生成一个请求级 `stream_id`。
- 该 `stream_id` 贯穿本次请求的全部服务端事件，包括：
  - `agent_typing`
  - `chat_stream`
  - `error`
- 对 `agent_busy`、`provider_not_configured`、首句前失败等 pre-stream 错误，也必须返回该请求级 `stream_id`。
- 对非 `send_message` 类错误事件，如连接建立后的 `session_not_found`、非法请求体导致的 `invalid_request`，服务端也必须生成一次性的错误级 `stream_id`，保证 `BaseMessage` 契约不被破坏。

### 6.5 在途并发保护

`P1-2` 只允许单会话单在途回复。

规则：

- 当某个 `session_id` 已有流式回复尚未收口时，新的 `send_message` 必须被拒绝。
- 服务端返回稳定错误事件 `agent_busy`。
- 当 WebSocket 在流式过程中断开时，服务端必须立刻停止继续消费上游流，并以“本次回复被中断”处理收口。
- 若断开前已经产生过至少一个句段 chunk：
  - 将当前累计 partial content 写回 agent message
  - `delivery_status=interrupted`
  - 释放 in-flight guard
- 若断开发生在首个句段前：
  - 不创建 agent message
  - 仅释放 in-flight guard
- 在途状态的释放条件：
  - 正常结束且已发送 `typing=false`
  - 异常结束且已发送 `typing=false`
  - 连接关闭并完成上述中断收口

不做：

- 不做排队
- 不做抢占
- 不做取消上一个请求

### 6.6 与历史接口的关系

- `GET /api/sessions/{session_id}/messages` 仍只返回已 finalize 的历史消息。
- 未完成的 in-flight 流式状态只存在于当前连接内存态，不要求刷新后恢复。
- 如某条 agent message 已以 `interrupted` finalize，则刷新后可作为普通历史消息返回；本阶段不强制前端做特殊 UI 标识。
- 若流式过程中连接断开并已产生 partial content，刷新后历史接口返回的应是该条 `interrupted` message，而不是丢失或继续增长的消息。

## 7. Task 拆分

### P1-2-1 扩展 Provider 流式接口并输出原始文本 delta

**任务目标**

将当前 Provider 能力从“单次完整回复”扩展为“完整回复 + 原始流式 delta 回复”，为上层句段聚合提供稳定输入边界。

**当前范围**

- 扩展 `BaseProvider` 接口。
- 为千问 OpenAI 兼容 Provider 增加真实上游流式实现。
- 保持 `chat()` 非流式能力不退化。

**不做什么**

- 不在 Provider 层切句。
- 不在 Provider 层发 `typing`。
- 不在 Provider 层生成 WebSocket 协议事件。

**依赖与前置条件**

- `P1-1` 已有 `ProviderInput`、`ProviderOutput` 和千问非流式实现。

**需要改动的模块**

- [backend/app/providers/base.py](/D:/code/ZiJieAI/AgentHub/backend/app/providers/base.py)
- [backend/app/providers/openai_compatible.py](/D:/code/ZiJieAI/AgentHub/backend/app/providers/openai_compatible.py)
- [backend/tests/test_provider.py](/D:/code/ZiJieAI/AgentHub/backend/tests/test_provider.py)

**详细实现步骤**

1. 在 `base.py` 中新增 `ProviderStreamEvent` 与 `stream_chat()` 抽象方法。
2. 保持 `ProviderInput` 结构不扩 scope，仅沿用：
   - `system_prompt`
   - `user_message`
   - `model`
3. 在 `QwenProvider` 中调用真实上游流式接口。
4. 将上游事件归一化为原始文本 delta 迭代输出。
5. 对配置缺失、上游失败、空响应继续抛出稳定业务异常。
6. 保证：
   - 无文本 delta 的噪声事件不会向上层透传为空 chunk
   - 流结束后资源被正确释放
   - 流式异常前是否已分配请求级 `stream_id` 不影响异常映射

**测试方案**

- Provider 抽象测试：
  - `BaseProvider.stream_chat` 为抽象方法
  - `ProviderStreamEvent` 结构稳定
- Qwen Provider 单测：
  - 能将上游流式事件映射为有序的原始文本 delta
  - `QWEN_API_KEY` 缺失时抛出 `ProviderNotConfiguredError`
  - 上游 5xx/网络错误时抛出 `ProviderRequestError`
  - 上游没有任何可用文本时抛出 `ProviderResponseInvalidError`

**验收标准**

- 业务层可以通过统一接口消费原始 delta，而不关心具体 Provider 响应格式。
- `chat()` 原有行为保持可用。
- `stream_chat()` 是真实上游流式，而不是完整文本后本地伪流式。

### P1-2-2 建立句段聚合器与流式编排服务

**任务目标**

把 Provider 输出的原始 delta 升级为“句段级 chunk + 生命周期状态”的业务事件流，形成可复用的流式编排主链路。

**当前范围**

- 句段聚合器。
- 流式编排服务。
- 首句建 `message_id`、结束时 finalize、失败时 partial 保留的业务语义。

**不做什么**

- 不直接持有 WebSocket 对象。
- 不处理多会话并发调度。
- 不注入历史上下文。

**依赖与前置条件**

- `P1-2-1` 已提供 `stream_chat()`。
- 当前默认唯一 Agent 仍为 `PM Agent`。

**需要改动的模块**

- 新增 `backend/app/services/sentence_chunker.py`
- 新增 `backend/app/services/agent_stream_service.py`
- 可复用 [backend/app/services/agent_runtime.py](/D:/code/ZiJieAI/AgentHub/backend/app/services/agent_runtime.py)
- 可更新 [backend/app/models/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/message.py)

**详细实现步骤**

1. 抽象句段聚合器：
   - 输入：原始 delta
   - 输出：若干句段 chunk
   - 内部维护 buffer、固定 `50` 字符阈值与固定 `700ms` 时间阈值
2. 抽象流式编排服务：
   - 输入：`session_id`、当前用户消息、默认 Agent、Provider、请求级 `stream_id`
   - 输出：面向 `ws.py` 的业务事件序列
3. 编排服务在开始前产出：
   - `typing=true`
4. 编排服务消费 Provider 原始 delta，经聚合器 flush 后：
   - 首个句段出现时创建 agent message，占位 `message_id`
   - 同步累计完整文本
   - 逐段产出 `chat_stream`
5. 正常结束时：
   - flush 剩余 buffer
   - 完整内容回写 agent message
   - `delivery_status=completed`
   - 先产出最后一条承载尾缓冲的普通 chunk（若尾缓冲非空）
   - 再产出 `chat_stream(is_final=true, content_chunk="")`
   - 最后产出 `typing=false`
6. 已有 partial 后异常结束时：
   - 将 partial content 回写 agent message
   - `delivery_status=interrupted`
   - 产出 `error` 和 `typing=false`
7. 若在首个句段前即失败：
   - 不创建 agent message
   - 直接产出 `error` 和 `typing=false`
8. 若 WebSocket 在流式过程中断开：
   - 立即停止继续消费上游流
   - 已有 partial 时按 `interrupted` finalize
   - 无 partial 时不落 agent message

**测试方案**

- 句段聚合器单测：
  - 标点 flush
  - 双换行 flush
  - 固定 `50` 字符阈值 flush
  - 固定 `700ms` 时间阈值 flush
  - 流结束尾缓冲 flush
- 编排服务单测：
  - 首个句段出现时才创建 `message_id`
  - 正常结束写 `completed`
  - partial 后失败写 `interrupted`
  - 首句前失败不落 agent message
  - 断连后 partial 按 `interrupted` 收口
  - final chunk 固定为空终止帧
  - 事件顺序正确

**验收标准**

- 句段聚合逻辑不依赖 WebSocket，可独立测试。
- 编排服务可以独立于路由测试“事件顺序 + 落库 + 收口”。
- 正常和失败两条链路都不会造成消息内容与数据库状态不一致。

### P1-2-3 改造 WebSocket 主链路、在途保护与流式协议映射

**任务目标**

将当前 `WS /ws/{session_id}` 从“完整消息一次返回”升级为“typing + chunk 流 + final + 错误收口”的协议入口，并保证同一会话单在途。

**当前范围**

- `ws.py` 只保留请求校验、会话校验、in-flight guard、业务服务调用和协议事件发送。
- WebSocket 出站消息正式切到 `shared` 契约。
- 新增 `agent_busy` 保护。

**不做什么**

- 不在 `ws.py` 内部实现句段切分。
- 不在 `ws.py` 内部堆积 Provider 细节。
- 不实现队列、取消或并行流。

**依赖与前置条件**

- `P1-2-2` 编排服务可输出稳定业务事件。

**需要改动的模块**

- [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
- [backend/app/models/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/message.py)
- [shared/schemas/ws_messages.json](/D:/code/ZiJieAI/AgentHub/shared/schemas/ws_messages.json)
- [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)

**接口契约**

- 客户端请求体保持不变：

```json
{
  "action": "send_message",
  "session_id": "session-uuid",
  "content": "用户输入"
}
```

- 服务端成功事件与错误事件使用 `6.4 WebSocket 出站协议`。

**详细实现步骤**

1. 保留 `ping/pong` 和 `invalid_request` 行为。
2. human message 仍在进入流式编排前落库。
3. 在 `ws.py` 中增加会话级 in-flight guard。
4. 对每次合法 `send_message` 请求先生成请求级 `stream_id`，无论后续是否进入真正流式回复。
5. 当已有在途回复时：
   - 拒绝新的 `send_message`
   - 返回 `agent_busy`
6. 正常请求时调用流式编排服务，逐个发送：
   - `agent_typing`
   - `chat_stream`
   - `error`
7. 服务端发送的 `chat_stream` 不再使用当前的：
   - `content`
   - `sender_role`
   - `created_at`
   作为主协议字段
8. 服务端必须改为发送：
   - `agent_role`
   - `timestamp`
   - `stream_id`
   - `content_chunk`
   - `is_final`
9. 对所有 `error` 事件补齐：
   - `agent_role`
   - `timestamp`
   - `stream_id`
10. 连接关闭时：
   - 调用编排服务的中断收口逻辑
   - 再清理 in-flight guard，避免会话永久锁死。

**测试方案**

- WebSocket 业务测试：
  - `typing=true -> chunk -> final chunk -> typing=false` 顺序成立
  - `message_id` 在首个 chunk 后稳定
  - `is_final=true` 的 final chunk 固定为 `content_chunk=""`
  - `is_final=true` 结束后不再继续发送 chunk
  - 流式期间第二次 `send_message` 返回 `agent_busy`
  - `agent_busy`、`provider_not_configured`、首句前失败都带请求级 `stream_id`
  - partial 后失败时：
    - 错误事件可收到
    - `typing=false` 必定发送
    - agent message 以 `interrupted` 落库
  - 连接中途关闭时：
    - 服务端不继续消费上游流
    - 已有 partial 的消息以 `interrupted` 落库
- 契约测试：
  - 返回字段与 `shared` 一致
  - 旧 `chat_stream.content` 风格不再作为成功链路主格式

**验收标准**

- `ws.py` 变为薄路由，不再同时承担 Provider 细节、切句和完整落库编排。
- 同一会话不能出现两条在途流式回复。
- `shared` 约定与后端实际返回不再分叉。

### P1-2-4 完成 shared 对齐、自动化验证与联调要求

**任务目标**

确保 `P1-2` 的后端链路、shared 契约和联调假设一致，避免实现完成后再回退协议。

**当前范围**

- shared schema / type 对齐。
- 后端自动化测试补齐。
- 前后端联调要求说明。

**不做什么**

- 不编写前端页面或组件任务。
- 不补 `P1-3` 上下文承接逻辑。

**依赖与前置条件**

- `P1-2-1` 到 `P1-2-3` 已完成协议与服务拆分。

**需要改动的模块**

- [shared/schemas/ws_messages.json](/D:/code/ZiJieAI/AgentHub/shared/schemas/ws_messages.json)
- [shared/index.ts](/D:/code/ZiJieAI/AgentHub/shared/index.ts)
- [backend/tests/test_provider.py](/D:/code/ZiJieAI/AgentHub/backend/tests/test_provider.py)
- [backend/tests/test_ws_provider.py](/D:/code/ZiJieAI/AgentHub/backend/tests/test_ws_provider.py)
- 可新增 `backend/tests/test_sentence_chunker.py`
- 可新增 `backend/tests/test_agent_stream_service.py`

**联调要求**

- 前端必须按 `stream_id + message_id` 归并流式 chunk。
- 前端不得把每个 chunk 当作独立历史消息插入。
- 前端在 `is_final=true` 前应将该条回复视为 in-flight。
- 前端应将 `is_final=true && content_chunk=""` 视为纯终止帧，不再向消息正文追加文本。
- 前端收到 `agent_typing=false` 后应关闭 typing 展示。
- 前端无需实现刷新后恢复未完成流；刷新后仅依赖历史接口恢复 finalized 消息。

**测试方案**

- 建议至少执行：
  - `python -m pytest backend/tests/test_provider.py`
  - `python -m pytest backend/tests/test_ws_provider.py`
  - `python -m pytest backend/tests/test_sentence_chunker.py`
  - `python -m pytest backend/tests/test_agent_stream_service.py`
- 若保留旧的 WebSocket 集成测试文件，还需补充：
  - 协议字段断言
  - partial failure 断言
  - `agent_busy` 断言

**验收标准**

- shared schema、共享类型和后端真实返回字段一致。
- 自动化测试覆盖 Provider、聚合器、编排服务和 WebSocket 时序四层风险点。
- 前端联调方不需要再猜测 `chat_stream` 字段语义。

## 8. 统一测试方案

建议至少覆盖以下层次：

- Provider 单测
  - 验证 `stream_chat()` 输出原始 delta
  - 验证异常映射
- 聚合器单测
  - 验证句段 flush 规则
- 编排服务单测
  - 验证首句建消息、normal finalize、partial failure、disconnect finalize
- WebSocket 业务测试
  - 验证事件顺序、协议字段、并发保护、错误收口

建议验证命令：

- `python -m pytest backend/tests/test_provider.py`
- `python -m pytest backend/tests/test_ws_provider.py`
- `python -m pytest backend/tests/test_sentence_chunker.py`
- `python -m pytest backend/tests/test_agent_stream_service.py`

## 9. 统一验收标准

- 用户发送消息后，真实 Agent 回复具备可观察的句段级流式体验。
- 前端在 Agent 输出期间可稳定展示 `typing` 状态。
- 同一会话内新的 `send_message` 不会与当前流式回复并发执行。
- 服务端成功事件与 `shared` 中的 `chat_stream` / `agent_typing` 字段保持一致。
- 服务端所有 `error` 事件都满足 `BaseMessage`，`stream_id` 必填。
- 正常结束时 agent message 持久化为完整文本，`delivery_status=completed`。
- 已开始输出后失败时，partial content 被保留并持久化，`delivery_status=interrupted`。
- 连接中途断开且已产生 partial content 时，也按 `interrupted` 收口并可通过历史接口恢复。
- 首句前失败时不会污染历史，agent message 不落库。
- 本阶段没有提前引入：
  - token streaming
  - 中断恢复
  - 历史上下文承接
  - 多 Provider
  - 多 Agent

## 10. 依赖或阻塞

- 若当前数据库结构已经落地到真实环境，需要明确 `delivery_status` 字段的迁移方式。
- 若千问 OpenAI 兼容接口的流式事件形状与预期差异较大，需要先以真实接口样本确认 Provider 映射逻辑，但不能把这种厂商差异泄漏到业务层。
- 若前端当前已强依赖旧 `chat_stream.content` 风格，联调时需要先切 shared 契约；这属于联调阻塞，不应在后端实现时静默保留双协议长期共存。

## 11. 下一步

- 本 task 文档完成后，下一步进入 `task-review-from-spec`。
