# Task: P1-1 单 Provider 适配与首个真实 PM Agent 接入

## 0. 文档定位

- 本文档基于 [openspec/specs/implementation-phases.md](/D:/code/ZiJieAI/AgentHub/openspec/specs/implementation-phases.md) 中的 `P1-1 单 Provider 适配与首个真实 Agent 接入`。
- 本文档按 `task-planning-from-spec` 拆分后端/API scoped task，不重做需求澄清，不进入编码，也不拆前端实现任务。
- 本文档同时吸收本轮已确认实现决策：
  - 首个真实 Provider 使用千问 OpenAI 兼容接口。
  - 默认模型为 `qwen-plus`。
  - 默认唯一 Agent 为内置 `PM Agent`，`id=pm_agent`，`sender_role=PM`。
  - 根目录使用本地 `.env`，仓库提交 `.env.example`。
  - 未配置 `QWEN_API_KEY` 时允许后端启动，但在用户发消息时返回配置错误。
  - `P1-1` 仅做非流式完整回复。
  - `P1-1` 仅发送“当前用户消息 + 固定 system prompt”，不提前注入历史消息。
  - 用户消息先落库，再调用上游；上游失败走错误事件，不落库成正式 Agent 消息。

## 1. 任务目标

- 将当前 `Echo` 路径升级为“单真实 Provider + 单真实内置 Agent”的后端闭环。
- 在业务层之外建立最小 Provider 抽象，避免把千问调用细节硬编码进 WebSocket 消息流程。
- 建立代码内置 Agent 注册表，并注册唯一默认 Agent `PM Agent`。
- 为前端展示当前唯一 Agent 身份提供稳定契约，但不开放模型/Agent 切换。
- 保持 P1-1 边界清晰，不提前实现流式、多 Provider、多 Agent、自建 Agent 或会话历史承接。

## 2. 当前范围

- 根目录环境变量读取与 `.env.example` 占位。
- 单 Provider 抽象与千问 OpenAI 兼容实现。
- 内置 Agent 注册表与默认 `PM Agent` 定义。
- `WS /ws/{session_id}` 的真实 Agent 消息发送链路。
- 默认 Agent 身份读取接口，供前端启动后展示 `PM Agent`。
- 自动化测试、错误契约与联调验收要求。

## 3. 不做什么

- 不接入第二个 Provider。
- 不开放用户切换模型或切换 Agent。
- 不做用户自建 Agent。
- 不做句段流式、`typing`、token streaming，这些留给 `P1-2`。
- 不做最近历史消息承接，这些留给 `P1-3`。
- 不做 Auth、JWT、`current_user` 收口，这些留给 `P2-1`。
- 不新增数据库表或新增 Agent 持久化模型；`PM Agent` 先作为代码内置定义存在。
- 不把上游错误写成正式 Agent 消息。
- 不把模型名暴露为前端必须展示的信息。

## 4. 依赖与前置条件

- `MVP-3` 已提供最小 Session / Message / WebSocket 接口。
- `MVP-4` 已具备“用户消息落库 + Agent 消息落库 + WebSocket 返回”的最小闭环。
- `MVP-5` 已提供 `ping/pong` 与基础重连契约。
- 当前后端已有可复用模块：
  - [backend/app/core/config.py](/D:/code/ZiJieAI/AgentHub/backend/app/core/config.py)
  - [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
  - [backend/app/api/sessions.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/sessions.py)
  - [backend/tests/test_ws.py](/D:/code/ZiJieAI/AgentHub/backend/tests/test_ws.py)
- 当前 `Message` 模型字段已足够承载 P1-1：
  - `sender_type`
  - `sender_role`
  - `content`
  - `content_type`

## 5. 需要改动的后端模块、接口或配置

- 配置与样例文件
  - [backend/app/core/config.py](/D:/code/ZiJieAI/AgentHub/backend/app/core/config.py)
  - [README.md](/D:/code/ZiJieAI/AgentHub/README.md)
  - 新增根目录 `.env.example`
- Provider 抽象与实现
  - 新增 `backend/app/providers/base.py`
  - 新增 `backend/app/providers/openai_compatible.py`
- 内置 Agent 定义与注册表
  - 新增 `backend/app/agents/builtin.py`
  - 新增 `backend/app/agents/registry.py`
- Agent Runtime / 业务编排
  - 可新增 `backend/app/services/agent_runtime.py`
  - 改造 [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
- Agent 身份读取接口
  - 新增 `backend/app/api/agents.py`
  - 改造 [backend/app/main.py](/D:/code/ZiJieAI/AgentHub/backend/app/main.py)
- 测试
  - 改造 [backend/tests/test_ws.py](/D:/code/ZiJieAI/AgentHub/backend/tests/test_ws.py)
  - 新增 `backend/tests/test_agents_api.py`
  - 可新增 `backend/tests/test_provider_runtime.py`

不需要改动：

- 数据库 schema
- Session REST 契约
- Message 历史 REST 契约

## 6. 契约与配置约束

### 6.1 环境变量契约

根目录 `.env.example` 至少提供以下占位字段：

```env
QWEN_API_KEY=your_qwen_api_key_here
QWEN_BASE_URL=<qwen-openai-compatible-base-url>
QWEN_MODEL=qwen-plus
```

字段约束：

| 字段 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `QWEN_API_KEY` | string | 否 | 无 | 缺失时允许启动，但真实发消息时报配置错误 |
| `QWEN_BASE_URL` | string | 是 | 无 | 千问 OpenAI 兼容接口基础地址 |
| `QWEN_MODEL` | string | 否 | `qwen-plus` | P1-1 默认模型 |

运行时规则：

- 后端启动时不因 `QWEN_API_KEY` 缺失而失败。
- 当用户发消息且 Provider 配置不完整时，返回 WebSocket 错误事件。
- 真实密钥只放本地 `.env`，不得提交到 GitHub。

### 6.2 默认 Agent 定义契约

默认唯一 Agent 为代码内置定义，不落库，不从环境变量读取 prompt。

最小字段：

| 字段 | 值 |
|------|------|
| `id` | `pm_agent` |
| `name` | `PM Agent` |
| `role` | `PM` |
| `avatar_url` | 占位值，可为空 |
| `provider` | `qwen_openai_compatible` |
| `model` | `qwen-plus` |

`sender_role` 存储规则：

- Agent 成功回复时，消息 `sender_role` 固定写入 `PM`。
- 前端显示名使用 `PM Agent`，不展示模型名。

### 6.3 PM Agent Prompt 契约

`PM Agent` 的 system prompt 必须以内置常量方式保存在后端代码中，并满足以下精确职责：

```text
你是 AgentHub 的 PM Agent（Product Manager Agent）。

你的职责是：
- 理解用户真实需求
- 拆解功能与阶段目标
- 控制 MVP 范围
- 输出结构化任务
- 为 Architect / Coder / Reviewer Agent 提供清晰上下文

你始终需要从：
- 产品目标
- 用户体验
- 系统演进
- 可实现性
几个角度思考问题。

【行为规则】

1. 不直接写代码
除非用户明确要求，否则不要输出实现代码。

2. 优先做需求收敛
先明确：
- 用户真正要解决什么问题
- 哪些是核心功能
- 哪些属于后续增强

3. 严格控制 MVP
避免：
- 过度设计
- 提前复杂化
- 把 P2/P3 能力塞进 MVP

4. 强调闭环
优先保证：
- 可运行
- 可演示
- 可验证

5. 输出结构化结果
默认按以下格式输出：

# 需求理解
# 功能拆解
# 推荐实现顺序
# Agent 分工
# 风险与注意事项

【AgentHub 特殊要求】

AgentHub 的核心是：
- IM 聊天
- Agent Runtime
- 多 Agent 协作
- 上下文连续
- 产物与 Diff 状态

重点关注：
- Session / Message 抽象
- Streaming
- Orchestrator 边界
- Workspace / VFS
- 多 Agent 流程

警惕：
- 只有 UI 没有 Runtime
- 临时方案导致后期重构
- 阶段边界混乱

你的目标不是“回答问题”，而是：
帮助系统形成清晰、可持续演进的产品结构。
```

### 6.4 默认 Agent 信息读取接口

新增只读接口：

```text
GET /api/agents/default
```

认证方式：

- `P1` 阶段无 Auth。

成功响应：

```json
{
  "id": "pm_agent",
  "name": "PM Agent",
  "role": "PM",
  "avatar_url": null
}
```

字段定义：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 内置 Agent 稳定 ID |
| `name` | string | 是 | 前端展示名 |
| `role` | string | 是 | 展示用角色缩写 |
| `avatar_url` | string \| null | 是 | 头像占位，可为空 |

约束：

- 不返回模型名。
- 不返回 prompt。
- 不返回可切换 Agent 列表。

### 6.5 WebSocket 发消息契约

沿用当前入口：

```text
WS /ws/{session_id}
```

客户端请求体保持不变：

```json
{
  "action": "send_message",
  "session_id": "session-uuid",
  "content": "用户输入"
}
```

P1-1 运行规则：

1. 校验请求合法性。
2. 先落库 human message。
3. 读取默认内置 Agent `pm_agent`。
4. 组织上游请求：
   - 固定 system prompt：`PM Agent` prompt
   - 固定 user 输入：当前这一次用户消息
   - 不注入历史消息
5. 调用千问 OpenAI 兼容接口，使用非流式完整回复。
6. 成功时落库 agent message。
7. 通过当前 `chat_stream` 契约返回完整 Agent 消息。

成功响应结构沿用当前 `chat_stream`：

```json
{
  "type": "chat_stream",
  "message_id": "message-uuid",
  "session_id": "session-uuid",
  "sender_type": "agent",
  "sender_role": "PM",
  "content": "PM Agent 的完整回复",
  "content_type": "text",
  "created_at": "2026-05-23T10:30:00Z"
}
```

### 6.6 WebSocket 错误事件契约

错误继续复用现有 `error` 事件格式：

```json
{
  "type": "error",
  "error_code": "provider_not_configured",
  "error_message": "Provider is not configured"
}
```

本阶段新增或明确的错误码：

| `error_code` | 触发条件 | 是否落库 Agent 消息 |
|------|------|------|
| `provider_not_configured` | `QWEN_API_KEY` 或必要 Provider 配置缺失 | 否 |
| `provider_request_failed` | 上游调用失败、超时、5xx、网络错误 | 否 |
| `provider_response_invalid` | 上游响应缺少可用文本内容 | 否 |
| `invalid_request` | WebSocket 请求体非法 | 否 |
| `session_not_found` | 目标会话不存在 | 否 |

持久化规则：

- human message 在上游调用前已落库，因此错误场景下应保留用户消息。
- 上游失败时不得新增 agent message 持久化记录。

## 7. Task 拆分

### P1-1-1 扩展运行时配置并建立单 Provider 抽象

**任务目标**

为真实 Agent 调用建立最小可扩展的 Provider 边界，并完成千问 OpenAI 兼容配置接入。

**当前范围**

- 扩展 `Settings` 支持 `QWEN_API_KEY`、`QWEN_BASE_URL`、`QWEN_MODEL`。
- 新建统一 Provider 接口。
- 提供千问 OpenAI 兼容实现。

**不做什么**

- 不接入第二个 Provider。
- 不引入供应商 SDK 直连业务层。
- 不实现流式接口。

**依赖与前置条件**

- 根目录 `.env` 已被现有配置逻辑加载。
- 当前后端 `requirements.txt` 尚未绑定 OpenAI SDK；如需新增依赖，应只为 OpenAI 兼容调用服务。

**需要改动的模块**

- [backend/app/core/config.py](/D:/code/ZiJieAI/AgentHub/backend/app/core/config.py)
- `backend/app/providers/base.py`
- `backend/app/providers/openai_compatible.py`
- 根目录 `.env.example`
- 视实现需要更新 [backend/requirements.txt](/D:/code/ZiJieAI/AgentHub/backend/requirements.txt)

**详细实现步骤**

1. 在 `Settings` 中加入千问相关配置字段。
2. 定义 Provider 抽象接口，最小能力只包含“异步获取一次非流式完整文本回复”。
3. 定义统一输入结构，至少包括：
   - `system_prompt`
   - `user_message`
   - `model`
4. 定义统一输出结构，至少包括：
   - `text`
   - 原始响应元信息占位
5. 实现千问 OpenAI 兼容 Provider。
6. 对配置缺失和响应不可用场景抛出稳定业务异常，供 WebSocket 层映射为错误事件。

**测试方案**

- 配置解析测试：
  - 未设置 `QWEN_MODEL` 时默认使用 `qwen-plus`
  - 未设置 `QWEN_API_KEY` 时应用仍可启动
- Provider 单元测试：
  - 使用 stub/mock 验证请求 payload 只包含固定 system prompt 与当前用户消息
  - 预先构造同一 session 的历史消息，断言这些历史消息不会进入 Provider payload
  - 使用 stub/mock 验证缺失配置时抛出 `provider_not_configured` 对应异常

**验收标准**

- 业务层不直接拼接 OpenAI 兼容请求细节。
- Provider 可被替换而不改 WebSocket 路由主流程。
- 配置缺失不会阻止应用启动。

### P1-1-2 建立内置 Agent 注册表并注册默认 PM Agent

**任务目标**

用代码内置定义承载当前唯一默认 Agent，同时为后续多内置角色扩展保留稳定结构。

**当前范围**

- 建立轻量注册表。
- 注册唯一默认 Agent `pm_agent`。
- 固化 `PM Agent` prompt 与展示元信息。

**不做什么**

- 不落库 Agent。
- 不做用户自建 Agent。
- 不返回 Agent 列表。

**依赖与前置条件**

- P1-1-1 已提供 Provider 标识与模型配置读取能力。

**需要改动的模块**

- `backend/app/agents/builtin.py`
- `backend/app/agents/registry.py`
- 可新增 `backend/app/schemas/agent.py`

**接口契约**

- 注册表对业务层至少提供：
  - `get_default_agent()`
  - `get_agent(agent_id)`

**详细实现步骤**

1. 定义内置 Agent 数据结构：
   - `id`
   - `name`
   - `role`
   - `avatar_url`
   - `provider`
   - `model`
   - `system_prompt`
2. 录入唯一默认 Agent `pm_agent`。
3. 将 `PM Agent` 的完整 prompt 固化在代码常量中。
4. 约束后续业务层只通过注册表获取默认 Agent，而不直接写死 prompt 和模型。

**测试方案**

- 断言默认 Agent 为 `pm_agent`
- 断言其 `name` 为 `PM Agent`
- 断言其 `role` 为 `PM`
- 断言其 `model` 为 `qwen-plus` 或环境变量覆盖值

**验收标准**

- 业务层不再直接写死 Agent 文本常量。
- 后续扩展多个内置 Agent 时无需推翻接口形状。

### P1-1-3 用真实 PM Agent 替换 Echo 消息链路

**任务目标**

将当前 WebSocket 中的 Echo 逻辑替换为“human message 落库 -> 默认 PM Agent 调用真实 Provider -> agent message 落库 -> 完整回复推送”的真实链路。

**当前范围**

- 保持 `WS /ws/{session_id}` 请求入口不变。
- 保持 `chat_stream` 成功事件结构不变。
- 新增真实 Provider 调用与错误事件映射。

**不做什么**

- 不做流式推送。
- 不做 `typing`。
- 不做历史消息注入。
- 不做模型切换。

**依赖与前置条件**

- P1-1-1 Provider 可用。
- P1-1-2 默认 Agent 注册表可用。
- 现有 Session / Message 持久化可用。

**需要改动的模块**

- [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
- 可新增 `backend/app/services/agent_runtime.py`
- [backend/app/models/message.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/message.py) 一般无需改 schema

**详细实现步骤**

1. 保留 `ping/pong` 与 `invalid_request` 处理逻辑。
2. 在合法 `send_message` 时先写入 human message，并更新 `session.updated_at`。
3. 通过注册表读取默认 Agent `pm_agent`。
4. 构建 Provider 输入，只包含：
   - `PM Agent` system prompt
   - 当前这一次用户消息
5. 调用千问 OpenAI 兼容 Provider，使用非流式完整回复。
6. 成功时写入 agent message：
   - `sender_type=agent`
   - `sender_role=PM`
   - `content_type=text`
7. 继续通过现有 `chat_stream` 结构推送完整 Agent 回复。
8. 配置缺失、网络失败、响应无有效文本时：
   - 不落库 agent message
   - 返回稳定 `error` 事件

**测试方案**

- 使用 mock Provider 验证发送一条消息时：
  - 先持久化 human message
  - 再持久化 agent message
  - agent message `sender_role=PM`
  - 预先在同一 session 写入历史消息，断言本次 Provider 调用仍只收到当前用户消息，不包含任何历史消息
- 缺失 `QWEN_API_KEY` 时：
  - WebSocket 仍可建立
  - `send_message` 返回 `provider_not_configured`
  - Message 历史只新增 human message
- 上游失败时：
  - 返回 `provider_request_failed`
  - 不新增 agent message
- 上游返回空文本时：
  - 返回 `provider_response_invalid`
  - 不新增 agent message

**验收标准**

- Echo 文本不再出现在正常成功链路中。
- 成功消息来自真实 Provider 返回。
- 失败场景不会污染会话历史中的 Agent 消息。

### P1-1-4 提供默认 Agent 只读身份接口并完成联调测试

**任务目标**

给前端提供当前唯一默认 Agent 的显示信息契约，并补齐围绕 P1-1 的后端/API 验收测试。

**当前范围**

- 新增 `GET /api/agents/default`
- 接入主应用路由
- 补齐后端自动化测试与联调说明

**不做什么**

- 不做 Agent 列表接口。
- 不做 Agent 切换接口。
- 不返回模型名给前端展示。

**依赖与前置条件**

- P1-1-2 默认 Agent 注册表可用。
- [backend/app/main.py](/D:/code/ZiJieAI/AgentHub/backend/app/main.py) 可注册新路由。

**需要改动的模块**

- `backend/app/api/agents.py`
- [backend/app/main.py](/D:/code/ZiJieAI/AgentHub/backend/app/main.py)
- `backend/tests/test_agents_api.py`
- [README.md](/D:/code/ZiJieAI/AgentHub/README.md)

**接口契约**

- 使用 `6.4 默认 Agent 信息读取接口`

**详细实现步骤**

1. 新增只读路由 `GET /api/agents/default`。
2. 路由从注册表读取默认 Agent 并只返回展示字段。
3. 不返回模型、prompt、provider 凭据。
4. 在 README 中说明：
   - 本地 `.env` 配置方式
   - `.env.example` 作用
   - 默认 Agent 为 `PM Agent`
   - 模型不在前端展示

**测试方案**

- API 测试：
  - `GET /api/agents/default` 返回 `pm_agent / PM Agent / PM`
- WebSocket 集成测试：
  - 成功场景返回 `sender_role=PM`
  - 非法请求仍返回 `invalid_request`
  - `ping/pong` 行为不受影响

**验收标准**

- 前端可通过单一只读接口获取默认 Agent 显示信息。
- `P1-1` 新增能力不破坏现有 Session / Message / ping-pong 测试。

## 8. 统一测试方案

建议至少覆盖：

- `python -m pytest backend/tests/test_ws.py`
- `python -m pytest backend/tests/test_agents_api.py`
- 如新增 Provider runtime 单测：
  - `python -m pytest backend/tests/test_provider_runtime.py`

推荐测试层次：

- 配置测试：验证启动时允许缺失密钥。
- Provider 单测：全部走 mock，不依赖真实外网。
- API 测试：验证默认 Agent 读取接口。
- WebSocket 集成测试：验证真实 Agent 成功与失败链路。

## 9. 统一验收标准

- 用户进入系统后，可稳定与默认唯一真实 Agent `PM Agent` 对话。
- Provider 接入不硬编码在 WebSocket 路由业务细节中，存在明确抽象边界。
- 前端有稳定方式获取默认 Agent 身份，且不展示底层模型名。
- 未配置 `QWEN_API_KEY` 时后端仍可启动，但发消息会返回明确错误事件。
- 发送消息成功时：
  - human message 已落库
  - agent message 已落库
  - `sender_role=PM`
  - 返回完整非流式文本
- 发送消息失败时：
  - human message 保留
  - agent message 不落库
  - WebSocket 返回稳定错误码
- 本阶段没有提前引入：
  - 流式输出
  - `typing`
  - 历史消息承接
  - 多 Provider
  - 多 Agent
  - 自建 Agent

## 10. 依赖或阻塞

- 若项目决定引入新的 OpenAI SDK 或 HTTP 客户端依赖，需要先确认与现有 `requirements.txt` 的兼容性。
- 若前端后续希望完全不新增 Agent 读取接口，也可退回为前端内置显示常量，但那会削弱后端作为唯一真实来源的作用；如要改，应单独 review，不要在实现时静默改 scope。
- 若未来 `P2` 需要持久化 Agent 元数据，应新增独立 spec/task，不要反向改造本阶段的内置注册表闭环。

## 11. 下一步

- 本 task 文档完成后，下一步进入 `task-review-from-spec`。
