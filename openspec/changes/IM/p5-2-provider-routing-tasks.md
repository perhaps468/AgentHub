# Task: P5-2 第二个 Provider 接入、Provider Factory 落地与会话按 Agent 路由到对应第三方 API

## 1. 背景与前提

- 当前 runtime 主链路已经是 `Provider -> LLMAdapter -> RuntimeAgentService`，核心抽象已存在：
  - [backend/app/providers/base.py](/D:/code/ZiJieAI/AgentHub/backend/app/providers/base.py)
  - [backend/app/runtime/llm_adapter.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/llm_adapter.py)
  - [backend/app/runtime/runtime_agent_service.py](/D:/code/ZiJieAI/AgentHub/backend/app/runtime/runtime_agent_service.py)
- 但当前实际使用链路仍然在 [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py) 中硬编码实例化 `QwenProvider`，还没有统一的 provider factory。
- 当前系统发送消息时，并不会根据“当前会话选中的 Agent”动态选择 provider。
- `Agent` 将作为第三方 API 配置载体，至少需要承载：
  - `provider`
  - `model`
  - `system_prompt`
  - `role`
- 本 task 的目标不是多 Agent 并行编排，也不是 Orchestrator。
- 本 task 的目标是打通这条链路：
  - 用户进入某个会话
  - 会话绑定某个 Agent
  - Agent 绑定某个 provider
  - 本次消息发送时，后端自动选择该 Agent 对应的第三方 API

## 2. 实现方案

### 2.1 接入第二个 Provider

- 参考现有 [backend/app/providers/openai_compatible.py](/D:/code/ZiJieAI/AgentHub/backend/app/providers/openai_compatible.py) 的实现方式，新增第二个 provider 文件。
- 第二个 provider 必须完整实现 `BaseProvider` 的四个接口：
  - `chat`
  - `stream_chat`
  - `chat_with_messages`
  - `stream_chat_with_messages`
- 第二个 provider 必须复用现有错误语义：
  - `ProviderNotConfiguredError`
  - `ProviderRequestError`
  - `ProviderResponseInvalidError`
- 第二个 provider 必须支持当前 runtime 所依赖的 messages-aware 调用路径，不能只实现旧的单轮 `system_prompt + user_message` 接口。
- 第二个 provider 的实现要求与现有 provider 对齐，至少包括：
  - 请求头、鉴权、超时、stream 开关的统一封装
  - 上游响应正文到 `ProviderOutput` / `ProviderStreamEvent` 的稳定映射
  - 流式返回中对空 chunk、终止帧、异常帧的处理
  - 审计日志接入，保持与现有 provider 相同的 request / response / stream delta / error 记录能力
- 第二个 provider 不需要在本 task 中抽象“厂商通用基类”，但命名、输入输出和错误处理风格必须与现有 provider 保持一致，避免后续 factory 接入时出现特例分支。

### 2.2 落地 Provider Factory

- 将当前 [backend/app/services/agent_runtime.py](/D:/code/ZiJieAI/AgentHub/backend/app/services/agent_runtime.py) 从“固定返回 `QwenProvider`”升级为真正的 provider factory。
- provider factory 至少支持：
  - 按 `provider` 标识返回对应 provider 实例
  - 支持传入或覆盖 `model`
  - 对未知 provider 给出明确异常，而不是静默 fallback
- provider factory 输出统一为 `BaseProvider`，上游 runtime 不感知具体厂商类型。
- `ws.py` 不再直接 import 并实例化 `QwenProvider`。
- provider factory 建议承担的职责边界如下：
  - 从 `settings` 读取该 provider 所需配置
  - 根据 `provider` 标识实例化具体 provider
  - 在必要时把 Agent 绑定的 `model` 注入 provider 实例
  - 对配置缺失、provider 不存在、model 不合法等情况给出结构化错误
- provider factory 不应承担的职责：
  - 不负责会话查询
  - 不负责 Agent 查询
  - 不负责 runtime 执行
  - 不负责多 provider fallback
- provider factory 应成为后续所有 provider 接入的唯一扩展点，新 provider 落地时只允许：
  - 新增 provider 实现
  - 在 factory 中注册映射
  不允许继续修改 `ws.py` 主链路来接第三方 API。

### 2.3 建立 Agent -> Provider 绑定

- 在 Agent 配置模型中明确加入 `provider` 字段。
- `provider` 字段值建议使用稳定枚举，例如：
  - `qwen_openai_compatible`
  - `xxx_vendor`
- Agent 的 `model` 字段表示该 provider 下实际调用的模型。
- 默认内置 Agent 也必须显式声明 `provider`，不能再依赖运行时硬编码推断。
- 如果当前会话尚未正式持久化 Agent 绑定关系，则本 task 至少要求把“会话如何解析出当前 Agent”这条链路明确收口到一个位置，避免后续继续散落在前端 title、默认值或临时字段里。
- 若现阶段会话模型只能支持单 Agent，则本 task 只围绕“单会话绑定单 Agent”展开，不提前扩展多 Agent 会话结构。
- 本 task 不要求你一次性完成完整 Agent 管理产品化，但要求 Agent 数据层和运行时链路对 `provider/model` 已经是第一等字段。

### 2.4 打通会话按 Agent 路由 Provider 的执行链路

- 发送消息时，后端不再以“全局默认 provider”为准，而是以“当前会话对应的 Agent 配置”为准。
- 主链路应调整为：
  1. 根据 `session_id` 找到当前会话
  2. 根据会话找到其绑定的 Agent
  3. 从 Agent 读取 `provider` 和 `model`
  4. 通过 provider factory 实例化对应 provider
  5. 创建 `LLMAdapter`
  6. 创建 `RuntimeAgentService`
  7. 执行并返回流式结果
- 若当前会话没有绑定 Agent，则按已定义的默认 Agent 逻辑补齐，但默认 Agent 本身也必须走同一套 provider factory。
- runtime / ws 层不得再为每个 provider 单独写分支逻辑；provider 差异只允许收敛在 provider 实现和 factory 中。
- 这条链路在代码中的最小落点应包括：
  - 会话读取位置
  - Agent 解析位置
  - provider factory 调用位置
  - `LLMAdapter` 构造位置
  - `RuntimeAgentService` 构造位置
- 建议把“根据会话解析 Agent 并生成 provider”的逻辑提取成单独函数或服务，避免 `ws.py` 继续膨胀成同时负责鉴权、路由、provider 实例化、runtime 启动的聚合点。
- 执行链路上的错误分类需要明确：
  - 会话不存在
  - 会话无权访问
  - 会话未绑定 Agent
  - Agent 不存在
  - Agent 绑定了未知 provider
  - provider 配置缺失
  - provider 上游调用失败
  这些错误都应在 WS 层转换为现有错误事件语义，而不是直接抛出未分类异常。

### 2.5 配置与边界

- 为第二个 provider 增加独立配置项，例如：
  - `API_KEY`
  - `BASE_URL`
  - `MODEL`
- 所有配置通过 `settings` 读取，不允许在 provider 实现中硬编码密钥、URL 或模型名。
- 若当前项目已有 `.env` 与 `settings` 体系，本 task 必须把第二个 provider 完整纳入该体系，而不是通过临时环境变量读取绕过配置层。
- 本 task 不做：
  - 一个会话同时调用多个 Agent
  - 一个请求并发跑多个 provider
  - provider 级负载均衡
  - provider 自动 fallback
- 本 task 也不要求前端新增复杂配置界面；如果 Agent 的 `provider` 和 `model` 已能在后端配置或通过现有 Agent 管理能力写入，就足以支撑本次链路打通。

## 3. 测试方案

### 3.1 Provider 单元测试

- 第二个 provider 能成功完成：
  - 非流式请求
  - 流式请求
  - 带完整 messages history 的请求
- 当配置缺失时返回 `ProviderNotConfiguredError`
- 当上游请求失败时返回 `ProviderRequestError`
- 当上游响应为空或结构无效时返回 `ProviderResponseInvalidError`
- 流式测试至少覆盖：
  - 正常 delta 连续返回
  - 空行 / 无效行被跳过
  - 正常结束帧终止
  - 未产出可用内容时报错
- 若第二个 provider 的响应结构与 Qwen 不同，需要显式测试文本抽取逻辑，避免 runtime 拿到空字符串但上游实际已返回内容。

### 3.2 Provider Factory 测试

- 传入不同 `provider` 标识时，factory 返回对应 provider 实例
- 传入未知 `provider` 标识时，factory 返回明确错误
- factory 能正确读取对应 provider 的配置
- 如支持 Agent 覆盖模型，需补充：
  - 未显式传入 model 时使用 provider 默认 model
  - 传入 Agent model 时覆盖默认 model
- factory 测试应保证：新增 provider 时，只需要新增映射，不需要修改上游 runtime 调用方式。

### 3.3 会话路由测试

- 会话绑定 Agent A，且 Agent A 绑定 Qwen provider 时，消息命中 Qwen provider
- 会话绑定 Agent B，且 Agent B 绑定第二个 provider 时，消息命中第二个 provider
- 切换不同会话后，请求会按各自 Agent 配置路由，不发生 provider 串用
- 这里建议至少做两类验证：
  - 行为验证：mock 两个 provider，断言实际被调用的是正确的那个
  - 数据验证：断言 runtime 使用的 `model` 与 Agent 绑定配置一致
- 若当前测试基础设施允许，可直接在 WS 测试中构造两个会话分别绑定不同 Agent，验证消息进入各自链路。

### 3.4 Runtime / WS 集成测试

- `ws.py` 主链路不再硬编码 `QwenProvider`
- 对同一套 WS/runtime 逻辑，换不同 Agent 会走不同 provider
- 某个 provider 失败时，WS 能返回正确错误事件，不影响错误语义
- 集成测试至少覆盖：
  - 成功路径：消息发送 -> provider 调用 -> runtime 返回 -> `message_start/delta/end`
  - 配置错误路径：provider 未配置 -> 返回明确错误
  - 路由错误路径：Agent 绑定未知 provider -> 返回明确错误
  - 隔离路径：会话 A 和会话 B 分别命中不同 provider
- 若暂时不方便做真实上游联调，集成测试可先使用 provider stub / mock 完成，但必须能证明调用点已不再固定耦合 Qwen。

## 4. 验收标准

- 系统中不再只有硬编码的 `QwenProvider` 主链路。
- 第二个 provider 已按 `BaseProvider` 规范接入，并能被真实调用。
- provider factory 已成为 provider 实例化的唯一入口。
- Agent 已具备 `provider` 配置字段，并作为第三方 API 绑定载体。
- 发送消息时，后端能够根据“当前会话绑定的 Agent”自动选择对应 provider，而不是使用全局固定 provider。
- 切换到不同 Agent 的会话后，请求会命中各自绑定的第三方 API。
- runtime / ws 层不需要为每个新增 provider 再复制一套执行分支。
