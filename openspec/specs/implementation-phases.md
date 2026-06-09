# AgentHub 分阶段执行版实现文档

> 文档目标不是提前做好所有底层代码细节，而是以产品视角说明系统为什么这样分期、每一期解决什么问题、采用什么核心接口与实施方案、做到什么程度算完成。

---

## 1. 项目目标与产品定位

AgentHub 的外在形态是一个 IM 风格的 AI 协作产品，但其核心目标不是“把多个模型接进聊天窗口”，而是构建一个以聊天为交互入口、以任务执行为核心能力的 Agent 协作平台。

用户在系统中像使用聊天工具一样创建会话、发送消息、查看回复、切换工作会话；系统在底层逐步提供以下平台能力：

- 以统一消息流承载文本、计划、代码变更、执行结果、预览结果等不同类型信息
- 让单个 Agent 不只是一次性问答，而是能在上下文中持续完成任务
- 让代码类任务能够绑定工作区、生成变更、等待确认并回放执行结果
- 让 Agent 不再与单一模型厂商强绑定，而是支持统一的模型与 API Key 调度
- 让群聊和多 Agent 协作具备明确成员模型、主 Agent 机制与轻量编排能力

本次交付文档采用“从聊天底座到 Runtime，再到代码执行、模型调度、群聊编排”的分期方式组织，确保产品演进路径清晰、边界明确、结构连续。

---

## 2. 设计原则与实现边界

### 2.1 核心设计原则

- 先建立稳定闭环，再扩展智能程度
- 先统一消息流，再引入更复杂的 Agent 行为
- 先把单会话、单任务链路跑通，再扩展到并行会话与群聊协作
- 产品抽象优先，避免把临时实现写死成长期架构
- 文档中的阶段能力应尽量贴近当前项目已实现能力，不夸大未完成部分

### 2.2 全局主线

整个系统的核心主线始终保持为：

```text
用户输入
→ 会话与消息层
→ Agent Runtime
→ Tool / Workspace / Model 调用
→ 结果产出
→ 消息流与前端展示
```

只有这条主线稳定成立，后续的多会话、多 Agent、群聊编排和复杂调度才有意义。

---

## 3. 总体能力演进路线

本次交付采用以下五个主阶段：

### Phase1

IM 聊天底座与实时消息流

### Phase2

单 Agent Runtime 与流式执行

### Phase3

代码工作区、执行环境与产物闭环

### Phase4

Agent 配置体系与统一模型调度

### Phase5

群聊协作与轻量多 Agent 编排

整体演进顺序遵循：

```text
聊天入口
→ 单 Agent 执行
→ 代码任务闭环
→ 多模型统一调度
→ 群聊与轻量编排
```

---

## 4. 全局核心模型与关键对象

从第一阶段开始，全系统围绕以下核心对象展开：

- `Session`
  承载一个完整对话或任务执行上下文，支持单聊与群聊模式。
- `Message`
  承载文本、计划、流式回复、任务结果、代码变更说明等不同消息类型。
- `Agent`
  表示一个可被配置、选择、绑定、调度的智能执行角色。
- `Workspace`
  表示代码类任务绑定的工作区或项目上下文。
- `PendingChange`
  表示待用户确认的结构化代码变更结果。
- `SessionMember`
  表示群聊中的成员关系，包括主 Agent 与普通参与 Agent。
- `OrchestrationRun`
  表示一次群聊编排执行过程的顶层运行记录。
- `OrchestrationTask`
  表示编排运行中的子任务、状态、分配关系与执行结果。

这些对象在不同阶段逐步增强，但不会轻易推翻，以保证产品结构连续。

---

## 5. Phase1：IM 聊天底座与实时消息流

### P1-1 聊天 UI、会话列表与多会话切换

**目标**

建立用户可直接使用的聊天外壳，使系统具备会话列表、消息展示、输入发送和多会话切换能力。

**接口/实施方案**

- 前端构建会话列表区、聊天展示区、输入区与基础头部信息区；会话列表负责展示标题、最近活跃时间、置顶状态和群聊标签，聊天区负责展示当前会话消息流。
- 后端提供 `POST /api/sessions` 创建会话接口，请求体至少包含 `title`、`mode`、`workspace_id`；创建成功后返回完整 `Session` 对象供前端插入列表。
- 后端提供 `GET /api/sessions` 会话列表接口，支持 `include_archived` 等查询参数，默认按当前用户过滤，并按 `is_pinned desc, updated_at desc` 排序。
- 后端提供 `GET /api/sessions/{session_id}` 会话详情接口，返回 `id`、`title`、`mode`、`owner_id`、`workspace_id`、`created_at`、`updated_at` 等字段，供前端进入会话时恢复上下文。
- 前端统一通过 session store 缓存会话列表、当前激活会话和详情数据；刷新页面后先恢复本地状态，再通过接口回源刷新，不依赖一次性 mock 数据。

**测试/完成标准**

- 用户可创建、选择和切换多个会话
- 刷新页面后可恢复最近的会话列表状态
- 会话列表顺序和会话详情展示具有稳定一致性

---

### P1-2 实时消息链路、消息类型与历史恢复

**目标**

建立稳定的消息收发链路，让消息历史、实时推送和消息类型扩展成为后续 Runtime 的统一承载层。

**接口/实施方案**

- 后端提供 `GET /api/sessions/{session_id}/messages` 消息历史接口，支持 `page`、`page_size` 或等价游标参数，用于首次进入会话和刷新后的历史恢复。
- 实时收发采用 `WS /ws/{session_id}` 作为主消息通道，前端在进入会话时建立连接，在切换会话时断开旧连接并连接新会话。
- WebSocket 入站至少支持 `send_message`、`ping`、`pong` 三类动作；`send_message` 请求体至少包含 `session_id`、`content`、`message_type`、`client_message_id`。
- `Message` 统一保留 `id`、`session_id`、`sender_id`、`role`、`type`、`content`、`status`、`metadata`、`payload`、`created_at` 字段，作为后续文本消息、计划消息、任务状态消息和结构化结果消息的统一承载模型。
- `Message.type` 至少预留 `text`、`system`、`plan`、`task_status`、`pending_change`、`preview` 等类型，避免后续新增消息能力时推翻 Phase1 数据模型。
- 前端消息 store 负责把 HTTP 拉取到的历史消息和 WebSocket 推送的实时消息合并到同一消息数组中，避免出现“历史一套、实时一套”的双轨状态。

**测试/完成标准**

- 用户发送消息后，前端能实时看到消息进入会话流
- 刷新页面后，历史消息能够按正确顺序恢复
- 不同类型消息可以使用统一数据结构承载

---

### P1-3 Streaming 流式输出与前端增量渲染

**目标**

将系统回复过程从“一次性返回”升级为“增量流式展示”，为后续 Runtime 与多 Agent 过程输出提供展示基础。

**接口/实施方案**

- 定义最小流式事件协议，WebSocket 事件至少包含 `message_start`、`message_delta`、`message_end`、`message_error` 四类。
- `message_start` 至少携带 `message_id`、`session_id`、`sender_id`、`role`、`type`、`stream_id`；`message_delta` 至少携带 `message_id`、`stream_id`、`delta`；`message_end` 至少携带 `message_id`、`stream_id` 和完成标记或最终内容摘要。
- 前端在收到 `message_start` 时创建流式消息占位气泡，在收到 `message_delta` 时按 `stream_id` 聚合内容，在收到 `message_end` 时将占位气泡切换为完整消息。
- `Message.status` 至少包含 `pending`、`streaming`、`completed`、`failed`，让流式消息和普通消息使用同一状态语义。
- 后端在流式结束后必须将完整内容沉淀到消息存储层，刷新页面后前端通过历史接口拿到的是完整消息，而不是零散的 delta 片段。
- 前端还需要维护连接状态、当前流式消息映射表和输入态，确保连续多条流式回复不会互相串线。

**测试/完成标准**

- 回复内容可以逐段显示，而不是只能最终一次性出现
- 刷新后可看到完整消息，而不是零散的 delta 片段
- 流式链路能被后续 Runtime 直接复用

---

### P1-4 登录态、用户隔离与连接边界

**目标**

为会话、消息和连接链路建立最小用户边界，避免后续 Runtime 与资源对象缺乏 owner 语义。

**接口/实施方案**

- 引入最小登录态，可以是开发态固定用户、mock token 或简单 session 机制，但所有接口都必须能解析出当前用户身份。
- 会话接口 `POST /api/sessions`、`GET /api/sessions`、`GET /api/sessions/{session_id}`、`PATCH /api/sessions/{session_id}` 默认按当前用户过滤和校验，不允许跨用户访问会话。
- 消息历史接口 `GET /api/sessions/{session_id}/messages` 和 `WS /ws/{session_id}` 建连时都必须校验当前用户对该会话是否有访问权限。
- `Session` 至少保存 `owner_id`，`Message` 至少保存 `session_id`、`sender_id`、`owner_id` 或等价所属关系，以确保后续审计、隔离和资源归属清晰。
- 前端请求层统一附带当前用户标识或登录凭证；后端在 `Session`、`Message`、`Workspace`、`Agent`、`SessionMember` 等对象上沿用相同的 owner 语义。
- 这样后续扩展群聊、工作区、Pending Change 等对象时，不需要重新补用户边界。

**测试/完成标准**

- 用户只能访问自己的会话与消息
- 未授权用户不能订阅不属于自己的会话实时通道
- 后续 Runtime 执行可以明确知道请求发起者

---

## 6. Phase2：单 Agent Runtime 与流式执行

### P2-1 Runtime 基础抽象与 Agent 执行入口

**目标**

把系统从“聊天调模型”升级为“由 Agent Runtime 接管执行”的结构。

**接口/实施方案**

- 建立 `Agent`、`ModelAdapter`、`Runtime` 的职责分层：`Agent` 保存角色与配置，`ModelAdapter` 封装具体模型调用，`Runtime` 负责执行流程控制。
- Runtime 提供统一执行入口，如 `Runtime.run(session_id, trigger_message_id)` 或等价方法，由 WebSocket 收到用户消息后触发，而不是直接在 WS 层写模型调用逻辑。
- Runtime 负责读取会话历史、当前 Agent 配置和上下文，再调用对应 `ModelAdapter.generate()` 或 `ModelAdapter.stream_generate()`。
- Runtime 负责把输出结果写回 `Message` 存储层，并通过统一事件桥接层推送到 `WS /ws/{session_id}`。
- WebSocket 层只负责连接管理、消息入站和事件出站，不再直接承担模型调用与业务组装职责。

**测试/完成标准**

- 单 Agent 回复不再由临时链路直接驱动 UI
- Runtime 成为真实执行入口

**本阶段不做什么**

- 不引入多 Agent 协作

---

### P2-2 Prompt 组装、系统指令与角色配置

**目标**

建立可配置的 Prompt 组织方式，使 Agent 行为不依赖硬编码的单一 system prompt。

**接口/实施方案**

- 建立 `PromptBuilder.build(...)` 或等价方法，按 `system`、`role`、`task`、`history`、`tool_instructions`、`memory_stub` 等模块拼接最终输入。
- `Agent` 配置中至少保留 `name`、`role`、`system_prompt`、`description`、`capability_tags` 等字段，用于参与 prompt 组装。
- 单聊 Agent 与群聊主 Agent 允许使用不同的系统指令模板，避免后续在业务代码中到处分支拼接字符串。
- Prompt 组装层应支持注入当前会话标题、用户输入、运行阶段和必要元数据，为后续任务拆解、代码任务和群聊主持能力提供统一入口。
- 前端不直接参与 prompt 细节，只通过 Agent 配置接口维护角色资料，由后端统一生成最终模型输入。

**测试/完成标准**

- 不同 Agent 可以使用不同角色配置运行
- Prompt 组织逻辑集中管理，不散落在各个调用点

**本阶段不做什么**

- 不做 Prompt Marketplace

---

### P2-3 上下文管理、消息注入与历史裁剪

**目标**

让单 Agent 在多轮对话中拥有稳定可控的上下文能力。

**接口/实施方案**

- 建立 `ContextBuilder.build(session_id, trigger_message_id, agent_id)` 或等价流程，统一收集系统指令、最近消息、必要元数据和工具结果。
- 上下文至少区分 `system_context`、`recent_messages`、`tool_results`、`session_metadata` 四个部分，避免后续所有数据都混在单一数组里。
- 消息历史默认使用最近窗口策略，例如最近 N 条消息或最近若干轮人机对话，超出部分通过摘要或裁剪规则处理。
- 代码任务场景下，上下文还需要注入 `workspace_id`、当前绑定 Agent、最近变更记录等会话元数据。
- 上下文构建完成后统一传递给 PromptBuilder 和 Runtime，不允许在不同 Provider 适配器中再各自拼一套历史。

**测试/完成标准**

- Agent 可稳定承接最近多轮对话上下文
- 上下文构建逻辑可复用且边界清晰

**本阶段不做什么**

- 不实现完整长期记忆

---

### P2-4 Tool Calling、工具注册与调用回注

**目标**

建立 Agent 的最小执行能力，使其可以从纯对话进一步过渡到可调用工具的任务执行体。

**接口/实施方案**

- 定义 `ToolRegistry.register()`、`ToolRegistry.get()`、`ToolRegistry.execute()` 等基础接口，所有工具统一在注册表中管理。
- 单个 `Tool` 至少包含 `name`、`description`、`parameters_schema`、`execute(args)` 四部分，便于模型理解和 Runtime 执行。
- 模型输出若包含工具调用意图，Runtime 负责解析成结构化 `tool_call`，再交给 `ToolRegistry.execute()` 执行。
- 工具执行结果统一封装为 `tool_result`，写入当前运行上下文，必要时也可写成系统消息或运行事件返回前端。
- 第一批工具以基础读写、检索、环境查询为主，为 Phase3 的工作区、文件和执行环境做前置铺垫。
- Runtime 需要限制单轮工具调用次数和失败重试次数，避免错误循环。

**测试/完成标准**

- Agent 能完成最小工具调用闭环
- 工具输出能回流到统一上下文与消息流

**本阶段不做什么**

- 不接入复杂外部平台级工具

---

### P2-5 ReAct Loop、状态机与运行时事件流

**目标**

将 Agent 执行过程从单步生成升级为带状态机的过程化执行循环。

**接口/实施方案**

- Runtime 内部采用 `Think -> Act -> Observe -> Reply` 的循环结构，每一轮都要记录当前状态，而不是单纯写成一个长函数。
- 定义运行时状态，如 `IDLE`、`THINKING`、`CALLING_TOOL`、`OBSERVING`、`RESPONDING`、`FINISHED`、`ERROR`，供日志、审计和前端展示复用。
- 事件桥接层至少支持 `thinking`、`tool_start`、`tool_finish`、`delta`、`done`、`runtime_error` 等事件，并统一映射回 WebSocket。
- 内部状态用于 Runtime 控制，外部事件用于消息流展示和前端过程可视化，二者职责分离。
- 后续群聊编排继续复用这套事件协议，避免单聊和群聊形成两套运行时语义。

**测试/完成标准**

- 前端可以看到过程性输出而非只有最终答案
- Runtime 状态转换可被追踪和记录

**本阶段不做什么**

- 不做复杂跨任务恢复

---

### P2-6 Streaming Runtime、错误恢复与降级策略

**目标**

让单 Agent Runtime 不只“能跑”，还具备流式稳定性、失败补偿和兼容性。

**接口/实施方案**

- 统一 `stream_generate()` 与最终消息持久化逻辑，确保流式展示和消息落库由同一 Runtime 链路驱动。
- 对超时、空响应、JSON 解析失败、流式中断、工具执行失败等场景定义明确处理分支，至少返回错误事件或兼容回复。
- 当流式输出失败时，允许 fallback 到非流式生成结果；当模型结果仍不可用时，允许返回默认说明消息，避免前端无反馈。
- 记录最小运行信息，如 `session_id`、`agent_id`、`trigger_message_id`、`error_type`、`fallback_reason`、`token_usage` 或等价字段，为 Phase4 调度审计层做准备。
- 失败后的消息状态要与 `Message.status` 保持一致，不能只在日志中失败、前端却仍显示成功。

**测试/完成标准**

- 常见错误不会直接破坏会话主链路
- 失败情况下仍能向前端输出可理解结果或状态

**本阶段不做什么**

- 不做完整自治恢复系统

---

### P2-7 Phase2 验收与统一消息流接管

**目标**

确认单 Agent Runtime 已经成为系统真实执行中枢。

**接口/实施方案**

- 以“用户消息进入 WS -> Runtime.run() -> ModelAdapter -> 流式事件 -> Message 落库 -> 历史恢复”为核心链路进行验收。
- 验证 PromptBuilder、ContextBuilder、ToolRegistry、Runtime 状态机和事件桥接层是否已经形成统一执行结构，而不是散落在多个调用点。
- 检查旧的直连模型调用逻辑是否已经退出主链路，前端是否完全依赖统一消息流和 WS 事件。
- 为下一阶段记录关键前提：工具调用、工作区绑定、变更输出都必须继续复用这套 Runtime 入口。

**测试/完成标准**

- 单 Agent 可基于上下文与工具完成基础任务
- Runtime 输出稳定进入 Phase1 的消息/流式/WS 链路
- 旧的“直接调模型直接推 UI”链路不再成为主路径

**本阶段不做什么**

- 不在此阶段实现群聊编排

---

## 7. Phase3：代码工作区、执行环境与产物闭环

### P3-1 Workspace 绑定、会话工作区映射与项目边界

**目标**

建立代码类任务的项目边界，让会话与工作区形成稳定映射关系。

**接口/实施方案**

- 提供 `GET /api/workspaces`、`POST /api/workspaces`、`GET /api/workspaces/{workspace_id}` 等工作区接口，支持查询、创建和查看详情。
- `Workspace` 至少保存 `id`、`name`、`root_path`、`owner_id`、`created_at` 等字段，代码类任务通过 `workspace_id` 与会话建立绑定。
- 会话创建或更新时可传入 `workspace_id`，后端在 `Session` 对象上保存该绑定关系，后续 Runtime 读取会话即可定位工作区。
- 运行时解析工作区优先走正式绑定，必要时才使用环境变量或兼容 fallback 路径，避免执行目标不清晰。
- 前端在会话详情或头部区域展示当前工作区信息，用户能明确知道当前代码任务面向哪个项目。

**测试/完成标准**

- 开发型会话能够定位到明确工作区
- 后续读写文件、运行命令和生成变更都依赖统一项目边界

**本阶段不做什么**

- 不做完整云端隔离环境

---

### P3-2 文件读写、补丁修改与代码检索

**目标**

让 Runtime 获得稳定的代码操作能力，而不依赖粗暴整文件覆盖。

**接口/实施方案**

- 在 Runtime 工具层提供 `read_file`、`write_file`、`list_dir`、`search_code` 等文件操作能力，统一走 ToolRegistry 调用。
- 定义结构化修改协议，如 `FilePatch { path, startLine, endLine, newContent }`，优先以补丁或范围修改方式描述变更。
- 代码检索工具支持按关键词、路径或文件模式搜索，供 Agent 在生成变更前定位上下文。
- 文件修改结果先进入中间变更层，而不是直接覆盖正式文件，为后续 Pending Change 和人工确认保留空间。
- 前端无需直接读写文件，但要能根据变更结果展示文件路径、修改摘要和受影响范围。

**测试/完成标准**

- Agent 可以安全读取和修改工作区内容
- 文件操作具备可追踪边界，而不是黑盒写盘

**本阶段不做什么**

- 不把 shell 命令当作主要文件修改方式

---

### P3-3 Diff 生成、Pending Change 与结构化变更展示

**目标**

把代码修改结果从“最终文本”升级为“待确认变更对象”，形成用户可控的产物层。

**接口/实施方案**

- 后端生成结构化 Diff 或统一变更描述，并将结果落为 `PendingChange` 对象，而不是直接把代码内容塞进普通文本消息。
- 提供 `GET /api/pending-changes?session_id=...` 查询接口，返回当前会话待确认变更列表。
- `PendingChange` 至少包含 `id`、`session_id`、`agent_id`、`task_id`、`stream_id`、`file_path`、`unified_diff`、`summary`、`status`、`created_at` 字段。
- WebSocket 或消息流中的变更消息应关联 `pending_change_id`，便于前端点击消息后读取完整 Diff 内容。
- 前端展示层支持显示文件路径、Diff 摘要、执行 Agent、所属任务和当前状态，保证单 Agent 与群聊编排产物复用同一展示模式。

**测试/完成标准**

- 用户看到的是待确认的变更，而不是被直接覆盖的正式代码
- 变更对象能与会话、Agent、任务、流式输出关联

**本阶段不做什么**

- 不做复杂冲突合并系统

---

### P3-4 命令执行、测试运行、日志回传与可观察性

**目标**

让代码任务具备基本执行环境，使 Agent 能运行测试、脚本或检查命令并把结果反馈给用户。

**接口/实施方案**

- Runtime 工具层提供受控命令执行能力，统一在 workspace 根目录下运行，避免脱离项目上下文执行。
- 命令执行结果至少包含 `stdout`、`stderr`、`exit_code`、`started_at`、`finished_at` 等字段，可作为运行日志与错误分析输入。
- 运行过程通过事件流返回前端，至少包括 `terminal_start`、`terminal_stdout`、`terminal_stderr`、`terminal_exit` 四类事件。
- 测试运行、构建检查、脚本执行都沿用同一命令执行抽象，避免为不同命令类型重复造轮子。
- 必要时将关键运行结果写成系统消息或任务状态消息，便于刷新页面后仍能回看重要输出结论。

**测试/完成标准**

- Agent 可以执行基础测试或命令
- 用户能看到关键运行日志与结果状态

**本阶段不做什么**

- 不扩展为完整云沙箱平台

---

### P3-5 预览能力、结果展示与前端联动闭环

**目标**

让网页类或可视化产物不仅能生成，还能被预览和回看。

**接口/实施方案**

- 为可预览产物提供统一预览对象，如 `PreviewArtifact`，至少包含 `workspace_id`、`preview_url`、`status`、`created_at`。
- 预览结果可以通过消息流直接返回，也可以通过会话详情或变更详情中的附加字段返回，前端展示为“查看预览”入口。
- 对网页类任务，预览能力与工作区绑定，确保用户点击预览时看到的是当前项目对应结果，而不是脱离会话的临时内容。
- 若某个 Pending Change 或任务执行结果具备预览价值，消息结构中应允许携带 `preview_url` 或 `preview_artifact_id`。
- 前端在聊天区、右侧面板或变更卡片中展示预览状态，与代码变更和执行日志形成联动闭环。

**测试/完成标准**

- 用户可以看到可预览结果的入口或状态
- 预览能力能融入会话流程，而不是孤立存在

**本阶段不做什么**

- 不做复杂多环境部署平台

---

### P3-6 用户确认、应用变更、拒绝变更与结果回放

**目标**

让代码结果从“AI 产出”变成“用户可控的操作对象”，形成明确的人在回路。

**接口/实施方案**

- 提供 `POST /api/pending-changes/apply` 和 `POST /api/pending-changes/reject` 两个核心接口，分别用于应用或拒绝待确认变更。
- 应用接口请求体至少包含 `pending_change_id`，必要时可附带 `session_id`、`workspace_id`；应用成功后更新工作区内容、变更状态和相关消息展示。
- 拒绝接口请求体至少包含 `pending_change_id` 和可选 `reason`，用于保留用户决策和后续重试依据。
- `PendingChange.status` 至少支持 `pending`、`applied`、`rejected` 三种状态，并在消息流和查询接口中保持一致。
- 对群聊编排产物继续保留 `task_id`、`agent_id`、`stream_id` 等关联字段，保证应用或拒绝后仍能回溯到原始执行来源。

**测试/完成标准**

- 用户可以明确接受或拒绝变更
- 应用结果、拒绝结果和相关消息能够回放与追踪

**本阶段不做什么**

- 不做复杂版本控制工作流编排

---

### P3-7 Phase3 验收与代码任务闭环

**目标**

确认系统已经具备从代码任务输入到变更确认的最小闭环。

**接口/实施方案**

- 以“创建或绑定 workspace -> 读取文件上下文 -> 生成 Pending Change -> `GET /api/pending-changes` 查询 -> apply/reject -> 消息与状态回写”为主链路验收。
- 同时验证命令执行事件、测试日志、预览结果和代码变更是否都能回到同一会话展示层。
- 检查代码类任务在刷新页面后能否恢复工作区、待确认变更和关键执行结果，而不是只在单次运行中可见。
- 明确 Phase3 的产物边界：当前以 Pending Change、Diff、预览和运行日志为主，不扩展为大而全的独立 Artifact 平台。

**测试/完成标准**

- 代码类任务具备完整闭环
- Workspace、Pending Change、执行日志和预览能力可以在同一会话中协同工作

**本阶段不做什么**

- 不把 Phase3 描述为完整 CI/CD 平台

---

## 8. Phase4：Agent 配置体系与统一模型调度

### P4-1 Agent 模板、角色资料、能力标签与配置管理

**目标**

让 Agent 不只是内置角色，而是可被用户查看、创建、编辑和管理的配置对象。

**接口/实施方案**

- 提供 `GET /api/agents` Agent 列表接口，返回当前用户可见的系统内置 Agent 与用户自建 Agent。
- 提供 `POST /api/agents` 创建接口、`PATCH /api/agents/{agent_id}` 更新接口、`DELETE /api/agents/{agent_id}` 删除接口，支持完整配置管理。
- Agent 字段至少包含 `id`、`name`、`role`、`description`、`provider`、`model`、`system_prompt`、`capability_tags`、`is_active`、`owner_id`。
- 提供 `GET /api/agents/default` 或等价接口，供前端获取默认 Agent 配置和单聊默认执行者。
- 前端提供 Agent 列表页、创建编辑表单和会话内选择入口，统一使用后端返回配置，不在前端硬编码角色能力。

**测试/完成标准**

- 用户可查看、创建、编辑自己的 Agent 配置
- 系统内置 Agent 与用户 Agent 可以统一管理

**本阶段不做什么**

- 不做完整公开商店化运营

---

### P4-2 Provider / Model / API Key 统一路由与调度

**目标**

建立统一的模型接入层，使不同 Provider、不同模型、不同 API Key 能在一套执行框架中被调度。

**接口/实施方案**

- 通过 `ModelAdapter` 或等价 Provider 抽象层解耦具体厂商，实现 `generate()`、`stream_generate()` 等统一接口。
- Agent 配置中明确保存 `provider`、`model`、`api_key_slot` 或等价路由字段，运行时由调度层解析出最终调用凭证。
- 调度层支持按 Agent、会话或任务选择 Provider、Model、API Key，避免前端直接传入真实密钥。
- 对同一 Provider 的多个 API Key 支持统一路由和降级策略，在某个 key 不可用时可切换到兼容 key 或 fallback 路径。
- 相关调用结果、错误原因和 fallback 决策记录到统一调度日志中，为后续并行会话和群聊编排提供基础。

**测试/完成标准**

- 不同 Agent 可以绑定不同模型或不同 Provider
- 模型切换不破坏上层会话与 Runtime 结构

**本阶段不做什么**

- 不宣称具备企业级超大规模配额调度系统

---

### P4-3 会话级 Agent 绑定、默认 Agent 与切换机制

**目标**

让会话在运行时能够明确知道由哪个 Agent 负责处理，并支持合理切换。

**接口/实施方案**

- 单聊场景下支持默认 Agent 选择逻辑，优先通过 `GET /api/agents/default` 或用户配置获取默认执行者。
- 会话对象中保存 `selected_agent_id`、`default_agent_id` 或等价字段，使每个会话在运行时能解析当前负责执行的 Agent。
- `GET /api/sessions/{session_id}` 返回会话详情时，同时返回当前绑定 Agent 或主处理 Agent 的基础信息。
- 前端切换 Agent 时，通过会话更新接口或专门的绑定接口提交变更，由后端落库后再返回最新绑定结果。
- 群聊场景下主处理 Agent 由成员关系和主 Agent 规则共同决定，不接受前端本地决定。

**测试/完成标准**

- 会话可以稳定解析当前负责执行的 Agent
- 切换或选择 Agent 后，后续消息由正确执行体接管

**本阶段不做什么**

- 不做复杂多人协商式 Agent 选择

---

### P4-4 多会话并行、请求隔离与运行资源分配

**目标**

使系统支持多个会话并行运行，避免把单会话执行逻辑写死成全局串行模式。

**接口/实施方案**

- 每个会话拥有独立的 `session_id`、上下文缓存、Agent 绑定、workspace 绑定和运行状态，所有 Runtime 调用都以会话为主键组织。
- 不同会话可同时通过各自的 `WS /ws/{session_id}` 发起任务，后端按会话隔离 Runtime 实例或运行上下文。
- 流式输出、消息落库、Pending Change、命令执行日志和预览结果都按 `session_id` 归属，防止并行会话之间状态串线。
- 对会话级活跃运行保留查询或恢复接口，为前端刷新页面后恢复对应执行状态做准备。
- 多会话并行是产品行为层面的并发，不要求文档写成底层线程模型，但要明确隔离边界和资源归属。

**测试/完成标准**

- 多个会话可以同时发起任务而不互相覆盖上下文
- 并行会话的执行结果、消息流与变更对象能正确归属

**本阶段不做什么**

- 不做复杂集群级资源调度

---

### P4-5 调用审计、Fallback、超时处理与兼容策略

**目标**

提升调度层稳定性，使模型调用过程可追踪、可解释、可回退。

**接口/实施方案**

- 调度层记录关键调用信息，包括 `session_id`、`agent_id`、`provider`、`model`、`planning_source`、`error_type`、`fallback_reason` 等字段。
- 对超时、空响应、解析失败、流式失败、Provider 不可用等情况定义明确兼容处理路径，必要时切换到 fallback 方案。
- 群聊主 Agent 的计划拆解调用、单 Agent 普通调用和代码任务调用都尽量走同一审计框架，便于横向追踪。
- 关键运行决策既记录到日志，也可在需要时通过系统消息或任务状态反馈给前端，提升可解释性。
- 调用审计在本阶段不是附属功能，而是统一模型调度稳定性的组成部分。

**测试/完成标准**

- 常见失败场景有明确兼容处理
- 调用链路具备基础审计与问题定位能力

**本阶段不做什么**

- 不扩展为独立 APM 产品

---

### P4-6 Phase4 验收与调度层稳定性

**目标**

确认系统已具备统一模型调度与 Agent 配置管理能力。

**接口/实施方案**

- 以“`GET /api/agents` 查看配置 -> `POST/PATCH /api/agents` 维护 Agent -> 会话绑定 Agent -> 运行时解析 Provider/Model/API Key -> 记录 fallback 与审计”为主链路进行验收。
- 检查默认 Agent、自建 Agent、Provider 路由、多会话并行和调用审计是否能在一套结构内协同工作。
- 确保模型层切换不会破坏上层消息流、Runtime、工作区和群聊规则。

**测试/完成标准**

- Agent 配置、模型路由、多会话隔离与审计机制协同成立
- 上层聊天、Runtime、代码工作区不因模型切换而失稳

**本阶段不做什么**

- 不将 Phase4 描述为完整平台治理系统

---

## 9. Phase5：群聊协作与轻量多 Agent 编排

### P5-1 群聊会话模型、成员关系与主 Agent 机制

**目标**

让群聊从 UI 概念升级为真正可运行的会话模型，并明确主 Agent 规则。

**接口/实施方案**

- 引入 `SessionMember` 作为群聊成员关系模型，至少包含 `id`、`session_id`、`member_type`、`member_id`、`is_primary`、`health_status`、`created_at` 字段。
- 群聊会话的 `Session.mode` 使用 `group` 标记，后端通过成员表而不是前端临时数据判断群聊结构。
- 主 Agent 规则在后端固定：每个群聊必须存在且只存在一个 `is_primary=true` 的主 Agent。
- 普通参与 Agent 与主 Agent 使用同一成员模型，但在角色语义、调度优先级和前端展示上进行区分。
- 群聊会话详情接口返回成员列表，前端不再自己拼接“谁在群里、谁是主 Agent”。

**测试/完成标准**

- 群聊会话具备真实成员模型
- 主 Agent 可被后端稳定解析

**本阶段不做什么**

- 不实现多真人同时加入同一会话的完整协作系统

---

### P5-2 群聊创建规则、成员展示与前端群聊入口

**目标**

让用户可以创建具备主 Agent 和参与 Agent 的群聊，并在前端清晰看到成员结构。

**接口/实施方案**

- `POST /api/sessions` 在 `mode=group` 时支持 `participant_agent_ids` 字段，用于提交用户额外勾选的参与 Agent。
- 后端创建群聊时自动加入固定主 Agent，并对 `participant_agent_ids` 去重校验，避免主 Agent 重复落库。
- `GET /api/sessions/{session_id}` 在群聊场景下返回 `members` 数组，每项至少包含 `member_type`、`member_id`、`display_name`、`is_primary`、`health_status`。
- 前端在会话列表中为群聊增加小标签，在会话头部展示主 Agent、参与 Agent 和基础健康状态，但不单独拆出新的列表分区体系。
- 即使用户未选择其他参与 Agent，也允许成功创建“仅主 Agent”的最小群聊。

**测试/完成标准**

- 用户可以完成群聊创建
- 刷新页面后群成员信息可恢复展示
- 前端显示依赖后端真实返回，而不是前端硬编码

**本阶段不做什么**

- 不做动态成员增删与主 Agent 切换

---

### P5-3 主 Agent 驱动的任务拆解、Planner 与分发

**目标**

让群聊不只是多人展示，而是由主 Agent 主持、拆解任务并选择合适执行者。

**接口/实施方案**

- 群聊消息进入 `WS /ws/{session_id}` 后，后端优先解析该会话的主 Agent，由主 Agent 负责主持拆解。
- 主 Agent 通过 Planner 能力生成计划摘要和子任务列表，必要时调用专门的 planner prompt 与解析逻辑。
- 引入 `OrchestrationRun` 作为一次群聊编排执行的顶层记录，保存 `planner_agent_id`、`status`、`summary`、`planning_source` 等字段。
- 引入 `OrchestrationTask` 作为子任务记录，至少包含 `id`、`run_id`、`assigned_agent_id`、`title`、`goal`、`status`、`depends_on`。
- 当 planner 结果不可用时，允许回退到规则拆分或 fallback splitter，保证复杂请求仍能拆出最小可执行任务集。

**测试/完成标准**

- 复杂请求可被拆成结构化任务
- 拆解结果可与参与 Agent 列表形成分发关系

**本阶段不做什么**

- 不承诺完整 DAG 引擎或强一致调度器

---

### P5-4 编排运行状态、任务进度流与运行恢复

**目标**

让群聊编排可观测、可恢复，而不是一次性黑盒执行。

**接口/实施方案**

- 提供 `GET /api/sessions/{session_id}/active-run` 接口，返回当前活动的 `run` 和 `tasks`，供前端刷新恢复。
- 提供 `GET /api/orchestration/sessions/{session_id}/runs/latest` 获取最近一次编排运行，以及 `GET /api/orchestration/runs/{run_id}` 查询指定运行详情。
- `OrchestrationRun.status` 至少支持 `planned`、`running`、`finished`、`failed` 等状态，`OrchestrationTask.status` 至少支持 `pending`、`running`、`done`、`failed`。
- WebSocket 事件至少包含 `orchestration_run_started`、`orchestration_run_updated`、`orchestration_run_finished`，必要时包含 task 级别更新。
- 前端在进入群聊会话时，除建立 WebSocket 外，还主动查询 active run，用于恢复任务面板、计划摘要和执行进度。

**测试/完成标准**

- 群聊任务运行过程可被持续观察
- 刷新或重进会话后，活动运行状态可以恢复

**本阶段不做什么**

- 不实现完整中断恢复编排平台

---

### P5-5 多 Agent 结果汇总、计划摘要与消息回传

**目标**

让多 Agent 协作结果能回到统一消息流中，形成可读的用户体验，而不是散乱的中间产物堆积。

**接口/实施方案**

- 主 Agent 在任务拆解完成后生成计划摘要消息，并在子任务执行完成后汇总阶段结果与最终答复。
- 计划摘要、任务进度消息、最终回复、Pending Change 和预览结果都通过统一 `Message` 结构写回当前会话。
- 群聊结果消息的 `metadata` 或 `payload` 中可关联 `run_id`、`task_id`、`agent_id`、`pending_change_id`、`preview_url` 等字段。
- 当前阶段共享的是结构化任务结果和产物关联，而不是把所有 Agent 的完整内部上下文全部暴露给前端。
- 前端按统一消息流展示群聊阶段结果，避免额外维护一套独立于聊天区的“编排结果专用数据流”。

**测试/完成标准**

- 用户能看到清晰的任务拆解摘要与阶段结果
- 群聊中的多 Agent 结果不会脱离主会话消息流

**本阶段不做什么**

- 不做复杂最终合并冲突治理

---

### P5-6 Phase5 验收与轻量编排闭环

**目标**

确认群聊已经从展示层能力升级为具备轻量编排能力的协作入口。

**接口/实施方案**

- 以“`POST /api/sessions` 创建群聊 -> `GET /api/sessions/{session_id}` 获取成员 -> `WS /ws/{session_id}` 发送复杂任务 -> planner 拆解 -> run/task 查询与更新 -> 结果汇总消息回写”为主链路验收。
- 同时验证 `SessionMember`、`OrchestrationRun`、`OrchestrationTask`、Pending Change 和消息流之间的关联是否一致。
- 检查前端刷新页面后，群成员、最近计划、活动运行和关键任务状态能否通过接口恢复，而不是依赖内存残留。
- 明确 Phase5 的能力定位是“轻量多 Agent 编排”，而不是无限自治系统。

**测试/完成标准**

- 群聊具备成员模型、主 Agent 机制和轻量任务编排能力
- 多 Agent 执行结果可被会话、任务和消息流统一承载

**本阶段不做什么**

- 不把 Phase5 描述为完整自治型多 Agent 操作系统

---

## 10. 本次交付未纳入的高级能力

以下能力可以作为后续演进方向，但不纳入本次基础交付范围：

- 长生命周期任务持续运行
- 周期唤醒与事件驱动自治
- 长期记忆、跨会话知识积累与自动摘要
- 完整多租户权限系统
- 完整公开 Agent Marketplace
- 高复杂度云端执行与部署平台

这些能力只有在当前聊天、Runtime、工作区、模型调度与轻量编排已经稳定的前提下才有扩展价值。

---

## 11. 分阶段验收方式

每个阶段都遵循相同验收顺序：

1. 明确阶段目标和边界
2. 完成阶段主链路闭环
3. 验证核心模型、消息流与接口是否成立
4. 验证本阶段能力能否作为下一阶段前提
5. 将关键设计决策回写到文档
6. 通过验收后再进入下一阶段

总体验收不以“功能点数量”作为唯一标准，而是看以下能力是否按顺序稳定建立：

- IM 聊天底座是否稳定
- 单 Agent Runtime 是否真正接管执行
- 代码类任务是否具备工作区与变更确认闭环
- Agent 配置与模型调度是否统一
- 群聊协作是否具备真实成员关系与轻量编排能力

---

## 12. 后续任务拆解原则

后续如需继续拆 task，建议直接从本文件分期继续往下拆。

### 12.1 拆解原则

- 一级 task 使用阶段编号，如 `P2-4`、`P3-3`、`P5-4`
- 二级 task 围绕“目标 / 接口或实施方案 / 测试或完成标准”继续展开
- task 必须回到阶段边界，不应跨阶段偷带能力

### 12.2 推荐拆解方式

例如：

- `P2-4-1` 实现 ToolRegistry 与基础工具调用协议
- `P2-5-1` 建立 Runtime 状态机与事件派发
- `P3-3-1` 生成 Pending Change 并关联 session / agent / task
- `P3-6-1` 实现变更应用与拒绝接口
- `P4-2-1` 建立 Provider / Model / API Key 路由层
- `P4-4-1` 处理多会话并发执行隔离
- `P5-3-1` 实现主 Agent 计划拆解与 fallback 分发
- `P5-4-1` 建立 orchestration run/task 的查询与恢复接口

### 12.3 文档维护要求

- 新增实现时优先补充到对应阶段
- 不在阶段外另起一套平行产品叙事
- 文档应持续贴近真实实现，避免“文档设计”和“项目能力”长期分叉
