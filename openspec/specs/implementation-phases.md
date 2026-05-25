# AgentHub 分阶段执行版实现文档（Phase1 ~ Phase7）

> 本文档用于把 `proposal.md` 中的产品目标改写成便于后续持续拆 task、做实现、做评审的执行版文档。
>
> 它不追求把所有实现细节一次性写死，而是要求每个阶段都能回答清楚：这一阶段为什么做、要做什么、产出什么、接口和抽象如何定义、做到什么程度算完成。

---

## 1. 总愿景

AgentHub 的表层形态是一个 IM 风格的 AI 协作产品，但它的真实目标不是“把多个大模型接进聊天窗口”，而是构建一个基于聊天交互的 Agent Runtime Platform。

用户像使用飞书、微信或 ChatGPT 一样创建会话、发送消息、查看回复，但系统底层要逐步具备以下平台能力：

- 用统一消息流承载文本、代码、Diff、预览、文档、部署结果等多种产物
- 让单 Agent 能在会话里持续执行任务，而不只是一次性问答
- 让 Code Agent 能安全地操作工作区、文件、命令和预览环境
- 让 Artifact 从聊天内容升级为可管理、可版本化、可操作的平台资产
- 让用户可以创建自己的 Agent，并在统一 runtime 上运行
- 让多个 Agent 在可控调度系统下协作，而不是简单“群聊”

最终目标不是一个“能聊天的 AI 应用”，而是一个从 IM 入口逐步演化出来的 “Agent OS”。

---

## 2. 总实现原则

- 先做工程闭环，再增加智能程度
- 先保证消息流、状态、工具、产物、权限等基础设施稳定，再引入多 Agent、自主规划、长期记忆等高级能力
- 总实现顺序必须遵循从 IM 底座到 Runtime，再到 Code、Artifact、Marketplace、Scheduling 的演进路径
- 同一阶段必须优先做闭环，不优先追求功能面
- 统一复用 `proposal.md` 中定义的产品目标和能力边界，不在实现阶段静默扩 scope

整个项目的核心主线必须始终保持为：

```text
用户输入
→ Agent Runtime
→ Tool 调用
→ 产物生成
→ 消息流展示
```

只有这条链路成立，后续所有能力扩展才有意义。

---

## 3. 分阶段总览

### Phase1

IM 聊天底座

### Phase2

单 Agent Runtime

### Phase3

Code Agent 能力

### Phase4

Artifact 体系

### Phase5

用户自建 Agent

### Phase6

Orchestrator 多 Agent 编排

### Phase7

高级自治与持续运行

---

## 4. 全局约束

- 从 Phase1 开始就统一保留 `Conversation`、`Message`、`Participant`、`Agent`、`Artifact` 等核心抽象
- `Message` 不能被设计成纯文本模型，必须为后续代码、Diff、预览、文件、部署状态等消息类型预留结构
- 当前 LLM 回复链路不得继续直接驱动 UI 和业务状态，必须先收敛到统一消息流，避免干扰 Phase2 的 Agent Runtime 实现
- Runtime、Tool、Workspace、Artifact、Scheduling 这些平台层抽象要逐阶段增强，不允许在某个功能里临时写死
- 每个阶段都要说明“本阶段不做什么”，避免提前引入下一阶段复杂度
- 每个阶段完成前必须先验证闭环，不能只完成局部模块
- 阶段完成后必须说明本阶段已经完成总愿景中的哪些能力，以及哪些能力仍未完成

---

## 5. Phase1：IM 聊天底座

### Phase1-1 聊天 UI 与实时消息流

**目标**

完成用户可直接使用的 IM 交互外壳，让系统具备会话切换、消息展示、发送消息、实时更新的基础体验。

**要做什么**

- 搭建会话列表、消息流、输入框、发送按钮等核心聊天界面
- 支持用户消息和系统/Agent 占位消息的基础展示区分
- 建立最小 `Conversation`、`Message`、`Participant` 数据结构，保证 UI 不依赖临时内存状态
- 支持会话列表查询、消息历史查询、发送消息等基础接口
- 接入 WebSocket 或等价实时通道，建立会话级消息推送能力

**接口/抽象**

- `Conversation`
  至少包含 `id`、`title`、`type`、`owner_id`、`created_at`、`updated_at`
- `Message`
  至少包含 `id`、`conversation_id`、`sender_id`、`role`、`type`、`content`、`status`、`created_at`
- `Participant`
  至少包含 `conversation_id`、`user_id`、`agent_id`
- 会话级实时消息通道，例如 `WS /ws/{conversation_id}`

**完成标准**

- 用户可以创建或选择会话并发送消息
- 页面能实时收到新消息并展示
- 刷新后可以恢复会话列表和消息历史
- UI 层不再依赖一次性 demo 状态

**本阶段不做什么**

- 不追求复杂视觉设计
- 不做多 Agent 协作
- 不做复杂消息动作系统

---

### Phase1-2 Streaming 流式输出

**目标**

把已经实现的流式输出能力正式收敛进 Phase1，形成后续 Runtime 复用的统一流式协议，避免 Phase2 重造。

**要做什么**

- 定义流式消息的最小协议，例如开始、增量、结束、失败
- 前端支持流式消息增量渲染和完成态切换
- 后端通过 WebSocket 或等价通道推送流式事件
- 当前阶段可以使用固定内容或模拟增量流验证链路，不要求真实 Agent 参与

**接口/抽象**

- 流式事件建议包含：
  `message_start`、`message_delta`、`message_end`、`message_error`
- `Message.status`
  至少覆盖 `pending`、`streaming`、`completed`、`failed`
- 前端至少维护会话状态、消息数组状态、连接状态、输入状态和流式消息聚合状态

**完成标准**

- 固定内容或模拟内容可以通过 streaming 协议逐步展示
- 流式消息完成后能落入普通消息历史
- 刷新后看到的是完整消息，而不是丢失的增量片段
- Phase2 可以直接把 Runtime 事件映射到这套流式输出协议

**本阶段不做什么**

- 不实现 Runtime thinking/tool 事件
- 不实现后台任务系统
- 不实现复杂断线续传

---

### Phase1-3 当前错误链路改造

**目标**

修正当前“Message 没有统一封装、LLM 直接回复并驱动 UI”的错误链路，把它改造成 Phase2 Agent Runtime 可以接管的前置状态。

**当前问题**

- `Message` 如果只是文本或临时对象，后续代码、Diff、Artifact、部署状态都无法稳定复用
- 当前 LLM 链路如果是“用户发送消息 -> 直接调用 LLM -> UI 流式展示”，会把 IM 层、模型调用和回复展示耦合在一起
- 真实 LLM 回复如果继续留在 Phase1 主链路，会提前固化 prompt、context、provider、streaming 的实现方式，干扰 Phase2 的 `AgentRuntime`、`PromptBuilder`、`RuntimeContext` 和 ReAct Loop 设计

**要做什么**

- 将 `Message` 封装为统一消息承载结构，至少保留 `type`、`content`、`metadata`、`payload`、`status`
- 当前 LLM 回复链路不再直接产出真实业务回复，而是先改为通过统一消息协议输出
- WS 接口在 Phase1 先回复固定 Agent 消息或固定流式片段，只验证消息封装、状态切换、存储和推送链路
- 把现有流式 token 展示能力迁移到 `message_start`、`message_delta`、`message_end` 协议上
- 明确真实 LLM、Prompt、Context、Tool 调用由 Phase2 的 Runtime 接管

**接口/抽象**

- `Message.type`
  至少覆盖 `text`、`code`、`diff`、`artifact`、`deploy`
- `Message.content`
  用于文本类主内容
- `Message.payload`
  用于结构化消息主体
- `Message.metadata`
  用于渲染、来源、关联 artifact、stream 信息等扩展属性
- 临时回复器可以命名为 `FixedAgentResponder`、`MockLlmResponder` 或等价实现，但不得暴露为正式 Runtime 抽象

**完成标准**

- 当前回复链路不再绕过 `Message` 存储、状态和 WS 推送
- UI 只感知统一消息流，不感知底层是固定回复、临时 LLM 还是未来 AgentRuntime
- Phase2 只需要替换执行器，不需要重构 IM、Message、Streaming、WebSocket
- P1 结束时不会遗留“LLM 直接回复 UI”的旁路线

**本阶段不做什么**

- 不做 `AgentRuntime`
- 不做 `PromptBuilder`
- 不做 `RuntimeContext`
- 不做 Tool Calling
- 不做 ReAct Loop
- 不接入多 Agent

---

### Phase1-4 基础用户登录与用户隔离

**目标**

让 IM 底座从第一阶段开始具备最小用户边界，避免后续会话、Agent、Artifact、Workspace 都要返工补 owner。

**要做什么**

- 实现最小登录态，可以是账号密码、dev login、mock login 或简单 token
- 当前用户信息必须能被前端、HTTP 接口和 WebSocket 链路识别
- `Conversation`、`Message`、`Participant` 至少关联 `user_id` 或 `owner_id`
- 会话列表、消息历史、发送消息、实时通道都按当前用户隔离
- 为后续 `Agent`、`Artifact`、`Workspace` 预留 owner 边界

**接口/抽象**

- `User`
  至少包含 `id`、`name`、`created_at`
- `Session` 或等价登录态
  至少能识别当前请求所属用户
- 会话和消息查询必须默认带用户过滤条件

**完成标准**

- 用户 A 看不到用户 B 的会话和消息
- 创建会话、发送消息、恢复历史都绑定当前用户
- WebSocket 连接不能订阅不属于当前用户的会话
- 进入 Phase2 前，Runtime 执行可以明确知道“是谁发起的、在哪个用户边界内运行”

**本阶段不做什么**

- 不做完整 RBAC
- 不做组织、团队、租户体系
- 不做第三方 OAuth

---

### Phase1-5 Phase1 用户验证与阶段验收

**目标**

确认系统已经是“可持续承载 Agent 能力”的 IM 底座，而不是只能演示一次的聊天页面。

**要做什么**

- 由用户验证创建会话、发送消息、实时接收、历史恢复的主链路
- 验证 fixed/mock Agent 回复能通过统一 Message 和 streaming 协议展示
- 验证不同用户之间的会话和消息隔离
- 记录 Phase1 的关键技术决策，作为 Phase2 Runtime 接管的前置约束

**阶段验收标准**

- IM 主链路闭环成立
- 数据模型不需要在 Phase2 被推翻
- 消息流已经可以作为后续 Runtime 的统一输出层
- 当前错误 LLM 链路已经被收敛，不再直接驱动 UI
- 用户隔离成立，后续 Runtime 有明确 owner 边界

**本阶段已完成的总愿景能力**

- 建立了 IM 风格入口和基础会话体验
- 建立了统一消息流的最小承载方式
- 为未来文本、代码、Diff、预览、部署结果等消息类型预留结构
- 建立了用户边界，避免后续平台资源无 owner

**本阶段仍未完成的总愿景能力**

- 尚未建立单 Agent Runtime
- 尚未建立 Tool 调用
- 尚未建立 Code Agent、Workspace、Artifact、用户自建 Agent 和多 Agent 编排
- 尚未让真实 LLM 作为 AgentRuntime 执行体持续完成任务

**进入下一阶段前置条件**

- 用户确认基础 IM 体验和用户隔离足以承载 Runtime
- Message、Streaming、WS 链路能被 Phase2 复用
- 不存在绕过统一消息流的 LLM 回复旁路

---

## 6. Phase2：单 Agent Runtime

### Phase2-1 Runtime 基础抽象

**目标**

把系统从“聊天调用模型”升级为“任务驱动的 Agent 执行引擎”。

**要做什么**

- 解耦 `Agent`、`Model`、`Tool`、`Runtime`
- 定义 `Agent` 是配置体、`Runtime` 是执行体
- 为 Runtime 建立阶段化接口，而不是单一 `run()`
- 接管 Phase1 的 fixed/mock 回复器，把真实模型调用纳入 Runtime 执行链路

**接口/抽象**

- `Agent`
  至少包含 `id`、`name`、`profile`、`prompt`、`tools`、`runtime`
- `AgentRuntime`
  建议包含 `buildContext()`、`think()`、`act()`、`observe()`、`reply()`

**完成标准**

- 系统不再把 Agent 和某个模型厂商强耦合
- Runtime 可以承载后续工具调用、错误恢复、反思和多 Agent 编排
- 真实 LLM 回复通过 Runtime 输出到 Phase1 统一消息流

**本阶段不做什么**

- 不接入复杂工具
- 不做多 Agent

---

### Phase2-2 Prompt System

**目标**

建立可组合、可扩展的 Prompt 构建层，让 Agent 行为不依赖硬编码 system prompt。

**要做什么**

- 把 Prompt 拆成 system、role、memory、tool、history、task 等模块
- 建立统一 Prompt 组装器
- 让不同 Agent 和不同任务可以复用同一套组装机制

**接口/抽象**

- `PromptBuilder`
  建议包含 `buildSystem()`、`buildHistory()`、`buildMemory()`、`buildToolInstructions()`、`buildCurrentTask()`、`buildFinalPrompt()`

**完成标准**

- Prompt 可以按角色、历史、工具、任务动态拼接
- 新 Agent 不需要复制一份完整 prompt 文本

**本阶段不做什么**

- 不做复杂人格商店
- 不做用户自定义 Prompt Marketplace

---

### Phase2-3 Context Management

**目标**

让 Agent 拥有最小可控的上下文管理能力，避免会话变长后 runtime 直接失控。

**要做什么**

- 建立最近消息窗口
- 区分系统上下文、固定上下文、最近消息、工具结果和记忆占位
- 统一在 `buildContext()` 阶段构建模型输入

**接口/抽象**

- `RuntimeContext`
  建议包含 `system`、`pinned`、`recentMessages`、`toolResults`、`memory`

**完成标准**

- Agent 能承接最近多轮上下文
- 上下文构建逻辑不散落在不同 provider 或 agent 实现里

**本阶段不做什么**

- 不做长期记忆系统
- 不做跨会话知识召回

---

### Phase2-4 Tool Calling

**目标**

建立 Agent 与 ChatBot 的本质分界线，让 Agent 具备最小可执行能力。

**要做什么**

- 定义 Tool 抽象和 Tool 注册机制
- 支持模型输出 tool call，runtime 解析并执行
- 把 tool result 回注入上下文，再继续推理
- 先只做最小工具闭环

**接口/抽象**

- `Tool`
  至少包含 `name`、`description`、`parameters`、`execute(args)`
- `ToolRegistry`
  至少包含 `register()`、`get()`、`execute()`
- 第一批工具建议仅限 `read_file`、`write_file`、`search_web` 这类最小集合

**完成标准**

- Agent 能判断是否调用工具
- 工具调用和结果回注形成闭环
- Runtime 能承载后续 MCP、Function Calling、Sandbox 工具接入

**本阶段不做什么**

- 不接 Browser、Docker、Computer Use 这类复杂工具

---

### Phase2-5 ReAct Loop 与 Streaming Runtime

**目标**

实现真正的 Agent 执行循环和运行时事件流。

**要做什么**

- 按 `Think -> Act -> Observe -> Reply` 组织 runtime loop
- 建立 runtime 状态机，而不是只写一个 `while`
- 将 thinking、tool_start、tool_finish、delta、done 等事件映射到 Phase1 消息流

**接口/抽象**

- `RuntimeState`
  建议包含 `IDLE`、`THINKING`、`CALLING_TOOL`、`OBSERVING`、`RESPONDING`、`FINISHED`、`ERROR`
- 事件流建议包含：
  `thinking`、`tool_start`、`tool_finish`、`token` 或 `delta`、`done`

**完成标准**

- Agent 可以在一个任务内多轮决策和工具执行
- 前端可以看到 runtime 的过程性输出，而不只是最终答案

**本阶段不做什么**

- 不做后台任务系统
- 不做复杂任务恢复

---

### Phase2-6 Runtime State、错误恢复与 Memory 雏形

**目标**

让单 Agent Runtime 从“可跑”变成“可持续运行、可恢复、可扩展”的平台层。

**要做什么**

- 持久化最小执行状态
- 记录当前步骤、工具调用、阶段状态和中间结果
- 支持工具失败、JSON 解析失败、超时等场景下的最小恢复逻辑
- 为 memory 能力预留结构，不在本阶段完全展开

**接口/抽象**

- `RuntimeExecution`
  建议包含 `taskId`、`status`、`currentStep`、`toolCalls`、`intermediateResults`、`createdAt`
- 错误恢复至少要能区分：
  tool error、parse error、timeout、model error

**完成标准**

- 单 Agent Runtime 已经不是简单聊天，而是最小任务执行平台
- Tool、Prompt、Context、Loop、Streaming、State 已形成统一 runtime 架构

**本阶段不做什么**

- 不做多 Agent 编排
- 不做完整记忆系统

---

### Phase2-7 Phase2 阶段验收

**阶段验收标准**

- 单 Agent 可以基于会话历史生成回复
- 真实 LLM 回复已经由 Runtime 接管，而不是 Phase1 临时链路
- Prompt、Context、Tool、Loop、Streaming、State 形成统一架构
- Runtime 输出可以稳定进入 Phase1 的 Message/Streaming/WS 链路

**本阶段已完成的总愿景能力**

- 让单 Agent 能在会话里持续执行任务，而不只是一次性问答
- 建立了 Agent Runtime Platform 的最小执行层
- 为 Code Agent、Artifact 和多 Agent 编排提供统一执行入口

**本阶段仍未完成的总愿景能力**

- Code Agent 尚不能安全操作工作区、文件、命令和预览环境
- Artifact 尚未平台化
- 用户自建 Agent 和多 Agent 编排尚未完成

**进入下一阶段前置条件**

- Runtime 抽象稳定
- 工具调用闭环成立
- Runtime 事件可以被消息流观察和回放

---

## 7. Phase3：Code Agent 能力

### Phase3-1 Workspace Runtime

**目标**

建立 Code Agent 的环境边界，让“会话操作项目”这件事有清晰载体。

**要做什么**

- 抽象 `Workspace`
- 让会话和工作区建立绑定关系
- 为后续文件修改、预览、部署、Artifact、Sandbox 提供统一上下文

**接口/抽象**

- `Workspace`
  至少包含 `id`、`ownerId`、`rootPath`、`runtimeState`

**完成标准**

- 每个开发型会话都能定位到明确工作区
- 后续代码与产物操作不再依赖“当前机器某个默认目录”

**本阶段不做什么**

- 不直接做完整容器隔离

---

### Phase3-2 File Tool System

**目标**

让 Code Agent 获得文件读写与检索能力，并从第一版就建立可扩展的修改协议。

**要做什么**

- 实现 `read_file`、`write_file`、`list_dir`、`search_code`、`create_file`、`delete_file`
- 避免用“整体覆盖文件”作为唯一修改方式
- 定义 patch 或 range edit 协议

**接口/抽象**

- `FilePatch`
  至少包含 `path`、`startLine`、`endLine`、`newContent`

**完成标准**

- Code Agent 可以安全读取、修改和检索工作区内容
- 文件修改协议可支撑后续 Diff、Review、Undo、Version History

**本阶段不做什么**

- 不直接把 terminal 命令执行当成文件操作主路径

---

### Phase3-3 Diff System

**目标**

把代码改动从“结果文本”升级为“系统一级数据结构”。

**要做什么**

- 计算工作区改动并生成 diff artifact
- 在聊天流中展示 diff
- 建立“临时修改区 -> diff 产物 -> 用户确认”的主链路

**接口/抽象**

- `CodeDiffArtifact`
  至少包含 `id`、`filePath`、`patches`、`beforeHash`、`afterHash`

**完成标准**

- Agent 改动可以被结构化展示
- 用户看到的是待确认的变更，而不是被直接覆盖的正式代码

**本阶段不做什么**

- 不直接落盘正式代码
- 不做复杂合并冲突系统

---

### Phase3-4 Sandbox Runtime

**目标**

让 Code Agent 可以执行命令和观察运行结果，但先从最小受控环境起步。

**要做什么**

- 支持受限 subprocess 执行
- 获取 stdout、stderr、exit code
- 为 session 维度保存执行记录

**接口/抽象**

- `SandboxSession`
  至少包含 `id`、`workspaceId`、`processState`、`logs`

**完成标准**

- Agent 能运行测试、构建或本地命令
- 执行结果能反馈给 runtime 和聊天消息流

**本阶段不做什么**

- 不直接上 Kubernetes 或云沙箱

---

### Phase3-5 Terminal Runtime、Preview Runtime、Self-Repair Loop

**目标**

让 Code Agent 具备“可观察、可预览、可有限自修复”的完整环境交互能力。

**要做什么**

- 把 terminal 输出做成事件流
- 建立 preview session 和 iframe / URL 预览能力
- 支持 `run test -> fail -> analyze -> modify -> rerun` 的有限修复循环

**接口/抽象**

- Terminal 事件建议包含：
  `terminal_start`、`terminal_stdout`、`terminal_stderr`、`terminal_exit`
- `PreviewArtifact`
  至少包含 `previewUrl`、`workspaceId`、`status`
- 自修复建议限制 `MAX_RETRY`

**完成标准**

- 用户能在聊天里看到代码执行过程
- 网页或产物能被预览
- Agent 可以在有限次数内完成最小自修复闭环

**本阶段不做什么**

- 不做无限自动修复
- 不做完整长期项目记忆

---

### Phase3-6 Phase3 阶段验收

**阶段验收标准**

- Code Agent 可以在明确 workspace 边界内读取、修改、检索文件
- 文件改动可以生成结构化 diff，并进入消息流展示
- 命令执行和预览结果可以反馈给 Runtime 和用户
- 自修复循环有明确次数限制和可观察过程

**本阶段已完成的总愿景能力**

- 让 Code Agent 能安全地操作工作区、文件、命令和预览环境
- 让代码执行过程和产物预览进入聊天消息流
- 为 Artifact 平台化提供 diff、preview、workspace 等前置能力

**本阶段仍未完成的总愿景能力**

- Artifact 尚未成为独立平台资产
- 用户自建 Agent 尚未完成
- 多 Agent 编排尚未完成
- 长生命周期任务和高级自治尚未完成

**进入下一阶段前置条件**

- Workspace、File Tool、Diff、Sandbox、Preview 主链路成立
- Code Agent 改动不会绕过用户确认和结构化 diff
- 代码执行结果可以被 Runtime 状态和消息流追踪

---

## 8. Phase4：Artifact 体系

### Phase4-1 Artifact Schema

**目标**

把代码、网页、文档、PPT、Diff、部署结果统一收敛为平台级 Artifact。

**要做什么**

- 定义统一 Artifact 主模型
- 让 Artifact 独立于 Message 存在
- 为版本、动作、权限、渲染预留结构

**接口/抽象**

- `Artifact`
  至少包含 `id`、`ownerId`、`conversationId`、`type`、`version`、`metadata`、`contentRef`、`createdAt`

**完成标准**

- 产物不再只是聊天记录的一部分
- 后续渲染、操作、版本化都基于统一 Artifact 模型推进

---

### Phase4-2 Storage、Versioning、Renderer

**目标**

让 Artifact 具备真正的平台属性，而不是临时附件。

**要做什么**

- 区分元数据与内容存储
- 建立 artifact 版本链
- 为不同 artifact 类型建立渲染器

**接口/抽象**

- 存储策略：
  `metadata -> DB`
  `content -> Object Storage`
- 版本链至少要有：
  `parentArtifactId`、`version`、`changeSummary`

**完成标准**

- 大文件产物可以独立存储
- Artifact 可以追踪版本历史
- 系统可以按类型展示代码、网页、文档、PPT 等产物

---

### Phase4-3 Permission、Action、Lifecycle

**目标**

让 Artifact 从“能展示”升级为“能管理、能操作、能流转”。

**要做什么**

- 定义 artifact 权限边界
- 定义 artifact 动作体系，如 preview、apply、download、deploy
- 定义生成、更新、确认、归档、删除等生命周期

**完成标准**

- 产物已经成为系统资产层，而不是消息附件层
- 后续 Agent、用户、编排系统都可以围绕 Artifact 协作

---

### Phase4-4 Phase4 阶段验收

**阶段验收标准**

- Artifact 可以独立于 Message 存储和查询
- Artifact 支持元数据、内容引用、版本链和类型化渲染
- Artifact 操作具备最小权限和生命周期边界

**本阶段已完成的总愿景能力**

- 让 Artifact 从聊天内容升级为可管理、可版本化、可操作的平台资产
- 让代码、网页、文档、PPT、Diff、部署结果具备统一承载模型

**本阶段仍未完成的总愿景能力**

- 用户自建 Agent 尚未完成
- 多 Agent 编排尚未完成
- 高级自治和持续运行尚未完成

**进入下一阶段前置条件**

- Agent 和用户都能围绕 Artifact 做查询、展示和操作
- Artifact 权限和 owner 边界不依赖前端约定
- 产物不再只能依附于消息文本存在

---

## 9. Phase5：用户自建 Agent

### Phase5-1 Agent Template 与 Profile System

**目标**

让平台从“内置 Agent 集合”升级为“用户可配置自己的 Agent 蓝图”。

**要做什么**

- 定义 Agent Template
- 定义 Agent Profile、能力标签、角色说明
- 明确用户创建的是 Blueprint，不是一次性实例

**接口/抽象**

- `AgentTemplate`
- `AgentProfile`
- `CapabilityTag`

**完成标准**

- 用户可以创建带名称、角色、Prompt、模型、能力标签的 Agent
- 自建 Agent 可以在统一 runtime 上执行

---

### Phase5-2 Tool Permission、Runtime Factory、Store/Share

**目标**

让自建 Agent 具备真正的平台可运营性，而不只是一个 prompt 配置页。

**要做什么**

- 为自建 Agent 建立工具权限边界
- 建立 runtime factory，按模板实例化运行时
- 为后续 Agent Store / 分享能力预留结构

**完成标准**

- 自建 Agent 可以安全接入系统工具和 runtime
- 平台已经具备 Agent Marketplace 的基础骨架

---

### Phase5-3 Phase5 阶段验收

**阶段验收标准**

- 用户可以创建、查看、编辑自己的 Agent 蓝图
- 自建 Agent 可以通过统一 Runtime Factory 实例化并执行
- 工具权限边界不会因用户自建 Agent 被绕过

**本阶段已完成的总愿景能力**

- 让用户可以创建自己的 Agent，并在统一 runtime 上运行
- 为 Agent Store、分享、模板化运营打下基础

**本阶段仍未完成的总愿景能力**

- 多 Agent 编排尚未完成
- 高级自治和持续运行尚未完成

**进入下一阶段前置条件**

- Agent Template、Profile、Runtime Factory 边界稳定
- 用户自建 Agent 与系统内置 Agent 都能被统一调度入口识别
- 工具权限能约束不同 Agent 的执行能力

---

## 10. Phase6：Orchestrator 多 Agent 编排

### Phase6-1 Task Graph 与 Planner

**目标**

把多 Agent 协作从“群聊回复”升级为“有任务结构的调度系统”。

**要做什么**

- 定义任务节点与依赖关系
- 建立 planner，将用户需求拆成子任务图
- 明确哪些任务可串行、哪些任务可并行

**接口/抽象**

- `TaskGraph` / `TaskDAG`
- `PlannerOutput`
  至少包含任务节点、依赖边和目标 artifact

**完成标准**

- 多 Agent 协作有明确任务结构
- 失败恢复、暂停、重试、状态展示都有统一挂载点

---

### Phase6-2 Agent Selector、Parallel Runtime、Shared Context Bus

**目标**

让多个 Agent 在隔离上下文下协作，并通过产物共享而不是聊天污染完成配合。

**要做什么**

- 选择适合某个子任务的 Agent
- 支持并行 runtime 执行
- 建立共享总线，让 Agent 共享 artifact 和必要状态

**接口/抽象**

- `AgentSelector`
- `ParallelRuntime`
- `SharedContextBus`

**完成标准**

- 多个 Agent 可以并行工作
- 每个 Agent 有独立上下文
- 共享的是 Artifact 和结构化结果，而不是完整聊天历史

---

### Phase6-3 Artifact Merge、Failure Recovery、Human Interrupt

**目标**

让多 Agent 编排可收束、可中断、可恢复，而不是只会“越来越乱”。

**要做什么**

- 合并多个 Agent 产出
- 处理执行失败和降级
- 支持人工打断、人工确认和人工继续

**完成标准**

- Orchestrator 可以稳定协调多个 Agent 的阶段性产出
- 用户对复杂任务有介入和控制能力

---

### Phase6-4 Phase6 阶段验收

**阶段验收标准**

- Orchestrator 可以把复杂任务拆成结构化任务图
- 多个 Agent 可以在隔离上下文中串行或并行执行
- 多 Agent 输出可以通过 Artifact 和结构化结果合并
- 用户可以中断、确认、继续或降级复杂任务

**本阶段已完成的总愿景能力**

- 让多个 Agent 在可控调度系统下协作，而不是简单“群聊”
- 建立 TaskGraph、AgentSelector、ParallelRuntime、SharedContextBus 等编排基础

**本阶段仍未完成的总愿景能力**

- 高级自治、长生命周期任务、周期唤醒和长期记忆尚未完成

**进入下一阶段前置条件**

- 多 Agent 编排可观测、可中断、可恢复
- 多 Agent 共享边界基于 Artifact 和结构化状态，而不是复制完整聊天历史
- 编排失败不会破坏已有单 Agent、Workspace、Artifact 链路

---

## 11. Phase7：高级自治与持续运行

### Phase7-1 长生命周期 Runtime

**目标**

让 Agent 从一次性任务执行，升级为可持续运行、可周期唤醒、可长期跟踪目标的系统能力。

**要做什么**

- 支持长任务状态保存
- 支持周期性唤醒或事件触发
- 支持任务跨会话或跨时间片继续执行

**接口/抽象**

- 长生命周期任务记录
- 唤醒条件
- 持续运行状态机

**完成标准**

- Agent 不再局限于一次对话内完成任务
- 系统具备持续运行型 agent 的最小基础

---

### Phase7-2 高级记忆、反思与自治能力

**目标**

让系统在已有工程闭环基础上，逐步增加更高级的智能能力。

**要做什么**

- 建立长期记忆与摘要压缩
- 加入反思、复盘和自我修正策略
- 在明确安全边界内支持更高自治程度

**完成标准**

- 记忆、反思、自治都建立在稳定 runtime、workspace、artifact、scheduling 基础之上
- 系统能力增强不需要推翻前面阶段的工程结构

**本阶段不做什么**

- 不为了“更智能”破坏既有权限、安全与可观测边界

---

### Phase7-3 Phase7 阶段验收

**阶段验收标准**

- 长生命周期任务可以保存、恢复、继续执行
- 周期唤醒或事件触发不会绕过权限和可观测边界
- 记忆、反思、自治能力建立在已有 Runtime、Workspace、Artifact、Scheduling 基础之上

**本阶段已完成的总愿景能力**

- 建立高级自治与持续运行的最小平台能力
- 让 Agent 具备跨时间片、跨任务阶段继续工作的基础

**本阶段仍未完成的总愿景能力**

- 后续增强不再属于基础阶段路线，应按新的 spec 继续扩展

**进入下一阶段前置条件**

- 若继续扩展，必须创建新的 spec 或变更方案
- 不允许在没有安全、权限、可观测边界的情况下增加自治能力

---

## 12. 验收方式

每个阶段都必须按以下顺序完成：

1. 明确本阶段目标和边界
2. 完成本阶段闭环实现
3. 验证消息流、状态、接口和核心抽象是否成立
4. 验证本阶段是否完成了进入下一阶段的前置条件
5. 把关键决策回写到 spec
6. 阶段完成后再进入下一阶段

总体验收的判断标准不是“做了多少功能点”，而是以下能力是否按顺序稳定建立：

- IM 底座是否稳定
- Message、Streaming 和用户隔离是否能支撑 Runtime
- 单 Agent Runtime 是否成立
- Code Agent 是否能安全操作环境
- Artifact 是否已平台化
- 自建 Agent 是否基于统一 runtime 运行
- 多 Agent 编排是否有调度系统支撑
- 高级自治是否建立在已有工程闭环之上

---

## 13. 后续拆 task 的方式

后续建议直接从本文档继续拆任务：

- 一级 task：使用阶段编号，例如 `Phase1-3`、`Phase2-4`、`Phase3-3`、`Phase6-2`
- 二级 task：从“要做什么”“接口/抽象”“完成标准”继续拆成实现任务、测试任务、联调任务
- 每个 task 都必须回到本 spec 的阶段边界，不允许因为局部实现方便而提前做下一阶段能力

例如：

- `Phase1-1-1` 实现会话列表、消息流和输入框
- `Phase1-2-1` 定义 streaming 事件协议并完成固定流式消息展示
- `Phase1-3-1` 封装统一 Message type、payload、metadata、status
- `Phase1-3-2` 移除 LLM 直接回复 UI 的旁路，WS 先返回固定 Agent 消息
- `Phase1-4-1` 实现最小登录态和会话用户隔离
- `Phase2-4-1` 实现 Tool 接口与 ToolRegistry
- `Phase2-5-1` 实现 ReAct Loop 状态机
- `Phase3-2-1` 定义 FilePatch 协议
- `Phase3-3-1` 生成 CodeDiffArtifact 并写入消息流
- `Phase4-2-1` 建立 Artifact metadata / content 分离存储
- `Phase6-1-1` 定义 TaskGraph 数据结构
- `Phase6-2-1` 设计 SharedContextBus 的共享边界

这样拆可以保证后续 task、编码和评审都继续严格以本 spec 为准。
