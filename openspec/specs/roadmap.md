# AgentHub 分期路线图（Phase1 ~ Phase7）

---

## 1. 文档定位

本文档用于定义 AgentHub 的阶段边界，是 `proposal.md` 与 `implementation-phases.md` 之间的分层说明文档。

它只解决三件事：

- 每个阶段的目标是什么
- 每个阶段做到什么程度算完成
- 哪些能力应该放在哪一层，哪些底层抽象必须提前建立

文档职责约定如下：

- `proposal.md` 负责讲“总愿景与最终能力”
- `roadmap.md` 负责讲“整体分几步做”
- `implementation-phases.md` 负责讲“每一步具体做哪些执行任务”

后续如果旧分期描述、旧 task 拆分或既有实现细节与本文档定义的主线冲突，以本文档为后续调整依据。

---

## 2. 总实现原则

### 2.1 总愿景与总实现方案优先

AgentHub 的 spec 是后续 task 拆分、编码和评审的唯一真相源。

后续任何实现不得静默扩大 scope，也不得绕过本文档重新定义阶段边界。若需要调整阶段顺序，必须先回到 spec 更新总愿景或总实现方案。

### 2.2 先闭环，再复杂

AgentHub 的实现必须优先保证工程闭环成立，再逐步增加智能程度与产品复杂度。

优先级顺序始终是：

```text
用户输入
-> Agent Runtime
-> Tool 调用
-> 产物生成
-> 消息流展示
-> 多 Agent 编排
-> 持续运行与自治
```

这意味着系统早期可以暂时缺少完整登录注册、复杂群聊和正式部署，但不能缺少会导致后续大重构的消息模型、流式协议、运行时边界和资产边界。

### 2.3 先工程，再智能

很多高阶能力看起来是“智能能力”，但真正决定系统能否持续演进的是工程结构是否成立。

因此实现顺序必须优先保障：

- 会话、消息、参与者、Agent、Artifact 等核心抽象
- 统一 Message + Streaming 协议
- 当前回复链路与 UI 解耦
- 用户归属与会话隔离边界
- Agent Runtime、Prompt、Context、Tool、Loop、State
- Workspace、Sandbox、Diff、Preview
- Artifact 资产化
- 多 Agent 编排
- 长生命周期、记忆与自治

而不是优先追求：

- 复杂视觉和消息操作体验
- 多 Agent 群聊效果
- 长期记忆
- 后台自治运行
- 高级调度和完整部署发布

### 2.4 抽象前置，产品能力后置

路线图区分两类工作：

- 底层抽象：会影响数据库、接口、消息协议和运行时边界，必须提前建立
- 产品能力：会影响用户可见体验和完整闭环，可以在底层抽象稳定后再补齐

典型例子：

- `Message` 统一封装要早于真实 LLM 回复接入
- 流式协议要早于 Runtime 事件流
- `owner_id / user_id` 要早于完整 Auth 体系
- `Workspace` 要早于正式 Code Agent 自修复闭环
- `Artifact` 主模型要早于完整预览、编辑和发布能力

### 2.5 当前阶段约束

结合当前 spec，路线图调整遵循以下约束：

- 以 `implementation-phases.md` 中的 `Phase1 ~ Phase7` 为唯一阶段顺序
- 本次路线图更新只收敛文档，不直接改动代码实现
- Phase1 必须先解决 IM 底座、streaming、错误链路改造和基础用户隔离
- 在 Phase1 完成前，不得提前把真实 LLM 执行链路固化为正式 Runtime 实现
- 在 Phase2 完成前，不得提前把多 Agent、复杂工具和长期运行混入当前阶段

---

## 3. 核心模型成熟顺序

AgentHub 后续演进不应以“聊天消息”作为唯一中心，而应逐步转向以 Runtime 为执行主语，以 Message 和 Artifact 作为用户可见投影。

核心模型成熟顺序如下：

```text
Conversation
-> Participant
-> Message
-> Streaming Protocol
-> User Ownership
-> Agent Runtime
-> Workspace
-> Artifact
-> Multi-Agent Orchestrator
-> Long-running Memory System
```

各模型的职责边界如下：

- `Conversation`：承载一次会话或协作空间
- `Participant`：描述参与方，包括 `user`、`agent`、`system`
- `Message`：面向用户展示的对话投影，必须支持文本和结构化消息
- `Streaming Protocol`：描述消息开始、增量、结束、失败等流式事件
- `User Ownership`：描述用户边界、会话隔离和资源归属
- `Agent Runtime`：描述单 Agent 的上下文构建、推理、执行、观察和回复过程
- `Workspace`：承载工作区边界和环境上下文
- `Artifact`：承载代码、Diff、预览、文档、部署结果等非纯文本产物
- `Multi-Agent Orchestrator`：承载任务拆分、调度、共享和汇总
- `Long-running Memory System`：承载长任务、唤醒、长期记忆和自治状态

从 Phase1 开始，后续 task 拆分必须优先检查这些模型是否已经具备最小字段和接口边界。

---

## 4. 阶段总览

### 4.1 Phase1：IM 聊天底座

目标：

先完成可持续承载后续 Agent 能力的 IM 底座，而不是继续扩展临时聊天 demo。

这一阶段关注：

- 聊天 UI 与实时消息流
- Streaming 流式输出协议
- 当前错误链路改造
- 基础用户登录与用户隔离
- 用户验证与阶段验收

这一阶段的关键约束是：

- 当前 LLM 不应继续直接回复 UI
- WS 接口应先走固定消息或固定流式片段，只验证统一消息流
- Message 必须先收敛为统一结构，避免干扰 Phase2

这一阶段完成后，系统应当是：

```text
一个具备统一消息流、基础流式协议和用户隔离能力的 IM 底座
```

### 4.2 Phase2：单 Agent Runtime

目标：

把系统从“能承载消息流的 IM 系统”升级为“最小单 Agent 执行平台”。

这一阶段关注：

- Runtime 基础抽象
- Prompt System
- Context Management
- Tool Calling
- ReAct Loop
- Runtime State、错误恢复与 Memory 雏形

这一阶段完成后，系统应当从：

```text
统一消息流 IM 底座
```

升级为：

```text
具备最小单 Agent 执行能力的 Runtime 系统
```

### 4.3 Phase3：Code Agent 能力

目标：

在单 Agent Runtime 稳定后，把 Agent 能力扩展到工作区、文件、命令和预览环境。

这一阶段关注：

- Workspace Runtime
- File Tool System
- Diff System
- Sandbox Runtime
- Terminal Runtime、Preview Runtime、Self-Repair Loop

这一阶段完成后，系统应当从：

```text
单 Agent Runtime
```

升级为：

```text
可安全操作代码环境的 Code Agent 系统
```

### 4.4 Phase4：Artifact 体系

目标：

让聊天流中的产物从“消息附属物”升级为可管理、可版本化、可操作的平台资产。

这一阶段关注：

- Artifact Schema
- Storage、Versioning、Renderer
- Permission、Action、Lifecycle

这一阶段完成后，系统应当从：

```text
可执行代码任务的 Agent 系统
```

升级为：

```text
具备独立 Artifact 资产层的平台系统
```

### 4.5 Phase5：用户自建 Agent

目标：

让平台从“内置 Agent 集合”升级为“用户可配置自己的 Agent 蓝图”。

这一阶段关注：

- Agent Template 与 Profile System
- Tool Permission、Runtime Factory、Store/Share

这一阶段完成后，系统应当从：

```text
仅支持内置 Agent 的平台
```

升级为：

```text
支持用户自建 Agent 的统一 Runtime 平台
```

### 4.6 Phase6：Orchestrator 多 Agent 编排

目标：

在 Runtime、Workspace、Artifact 和用户边界都已经建立后，再进入多 Agent 编排主线。

这一阶段关注：

- Task Graph 与 Planner
- Agent Selector、Parallel Runtime、Shared Context Bus
- Artifact Merge、Failure Recovery、Human Interrupt

这一阶段完成后，系统应当从：

```text
单 Agent / 自建 Agent 平台
```

演化为：

```text
多 Agent 编排与协作系统
```

### 4.7 Phase7：高级自治与持续运行

目标：

在多 Agent 编排稳定后，再把系统升级为可持续运行、可恢复、可唤醒、可长期积累记忆的 Agent OS。

这一阶段关注：

- 长生命周期 Runtime
- 高级记忆、反思与自治能力

这一阶段完成后，系统应当从：

```text
多 Agent 协作系统
```

演化为：

```text
具备持续运行能力的 Agent OS
```

---

## 5. 各阶段边界

### 5.1 Phase1 边界

Phase1 承诺：

- 基础聊天 UI 与消息历史恢复
- 会话级实时消息流
- 统一 streaming 协议
- `Message` 的最小通用封装
- 当前错误链路收敛
- 基础用户登录与用户隔离

Phase1 不承诺：

- 正式 `AgentRuntime`
- Prompt、Context、Tool、ReAct Loop
- 多 Agent 编排
- Code Agent、Workspace、Diff、Artifact 生命周期
- 完整 Auth、RBAC、组织体系

### 5.2 Phase2 边界

Phase2 承诺：

- 完整单 Agent Runtime 主线
- Prompt、Context、Tool、Loop、State 的最小统一架构
- 真实 LLM 回复通过 Runtime 接管 Phase1 消息流

Phase2 不承诺：

- Code Agent 环境能力
- Artifact 平台化
- 多 Agent 编排
- 长期后台运行

### 5.3 Phase3 边界

Phase3 承诺：

- Workspace 边界
- 文件读写与检索能力
- Diff 展示与用户确认主链路
- 受控命令执行
- 预览与有限自修复

Phase3 不承诺：

- Artifact 独立资产化
- 用户自建 Agent
- 多 Agent 编排
- 长生命周期自治

### 5.4 Phase4 边界

Phase4 承诺：

- Artifact 独立主模型
- Artifact 存储、版本与渲染
- Artifact 权限、动作与生命周期

Phase4 不承诺：

- 用户自建 Agent 产品化
- 多 Agent 编排
- 长期后台运行与完整部署发布

### 5.5 Phase5 边界

Phase5 承诺：

- 用户自建 Agent 蓝图
- 自建 Agent 的运行时工厂与工具权限边界
- Store / Share 的基础骨架

Phase5 不承诺：

- 多 Agent 编排
- 长生命周期自治
- 完整 Agent 商店产品化

### 5.6 Phase6 边界

Phase6 承诺：

- 多 Agent 的任务图、选择、并行与共享上下文主线
- 多 Agent 结果合并
- 失败恢复和人工介入的最小编排能力

Phase6 不承诺：

- 长任务后台运行
- 周期唤醒
- 长期记忆产品化
- 完整部署发布

### 5.7 Phase7 边界

Phase7 承诺：

- 长生命周期任务
- 周期唤醒或事件触发
- 高级记忆、反思与自治能力

Phase7 不承诺：

- 在没有权限、安全、可观测边界下直接增加自治程度

---

## 6. 阶段进入与退出原则

进入下一阶段前，必须满足：

- 当前阶段闭环成立
- 当前阶段已有稳定验收路径
- 当前阶段关键抽象已收口，不再频繁重写
- 下一阶段能力不是靠临时绕过当前阶段缺口硬接上去

禁止出现以下情况：

- `Message` 未统一封装就提前接入正式 Runtime 事件
- 当前 LLM 仍直接回复 UI，就提前进入 Phase2
- 用户隔离未明确，就提前沉淀会话、Artifact、Workspace 的真实资产状态
- Runtime 未成型就提前做复杂多 Agent
- Workspace、Diff、Sandbox 未成型就提前做完整 Code Agent 闭环
- Artifact 未收口就提前做一键部署主线
- 为了展示效果，把高阶段能力提前塞回低阶段

---

## 7. 近期执行结论

结合当前 spec，近期阶段判断如下：

- 当前应以 `Phase1` 为准推进 IM 底座收敛
- `Phase1` 的优先级顺序是：
  1. 聊天 UI 与实时消息流
  2. Streaming 流式输出
  3. 当前错误链路改造
  4. 基础用户登录与用户隔离
  5. 用户验证与阶段验收
- 在 `Phase1` 完成前，不应直接把真实 LLM 链路扩成正式 AgentRuntime
- `Phase2` 才承接真实单 Agent Runtime
- `Phase3` 之后再进入 Code Agent、Artifact、自建 Agent、多 Agent 编排和长期自治主线

---

## 8. 与 implementation-phases 的关系

本文档定义的是：

```text
整体阶段顺序与阶段边界
```

`implementation-phases.md` 基于本文档继续展开执行任务：

- `roadmap.md` 说明每个阶段是什么
- `implementation-phases.md` 说明每个阶段具体做什么
- 如果执行任务和路线图边界冲突，以路线图边界为准先回收 scope
- 如果路线图边界和总愿景冲突，必须先更新更高层 spec，再调整执行文档
