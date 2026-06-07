# AgentHub 技术文档

## 1. 文档定位

本文档面向比赛评审与项目技术复盘，重点说明 AgentHub 当前版本已经真实落地的技术结构。文档不从产品愿景出发，而是聚焦三个问题：

- 模块怎么拆
- 数据怎么流
- 为什么这样设计

本文档的主要依据包括：

- `README.md`
- `openspec/specs/implementation-phases.md`
- 当前前后端目录结构与后端核心代码实现

其中，本文只描述当前仓库中已经具备代码落点的能力，不把仍处于规划中的高阶能力写成“已完成”。

---

## 2. 技术栈与工程结构

### 2.1 技术栈

AgentHub 采用前后端分离的 Monorepo 结构。

- 前端：Vue 3、TypeScript、Vite
- 后端：FastAPI、Python、SQLAlchemy、asyncio
- 实时通信：WebSocket
- 数据存储：MySQL
- 模型接入：统一 Provider 抽象，当前接入 `qwen_openai_compatible`、`doubao`、`glm`

### 2.2 工程目录

项目当前的目录分工如下：

- `frontend/`：前端应用，负责会话 UI、消息展示、状态管理、与后端 API / WebSocket 通信
- `backend/`：后端服务，负责会话接口、消息流、Agent Runtime、Provider 接入、多 Agent 编排、工作区与变更确认
- `shared/`：预留的共享协议/结构目录
- `openspec/`：产品规划、阶段路线图、任务拆解文档
- `tests/`：测试代码

其中，后端是当前技术实现的核心，前端主要承担聊天交互壳层和状态展示职责。

---

## 3. 系统架构设计

### 3.1 总体结构

当前版本的系统主链路可以概括为：

`用户输入 -> Session / Message 层 -> WebSocket / API -> Runtime / Orchestration -> Provider -> 事件回流 -> 前端展示`

这条链路的关键点不在于“把模型接进来”，而在于把消息、执行过程、任务状态、代码变更和群聊编排都纳入统一的数据流里。

### 3.2 为什么这样设计

项目没有直接把模型调用写死在 WebSocket 处理函数里，而是逐步拆成以下层次：

- API / WebSocket 层：负责接入、鉴权、协议收发
- Service 层：负责编排业务流程
- Runtime 层：负责单 Agent 执行、Prompt、工具、事件桥接
- Provider 层：负责统一对接不同模型平台
- Model 层：负责持久化会话、消息、任务、变更等状态

这样设计的核心原因是，聊天只是入口，真正复杂的是执行过程。如果不把运行时、Provider、编排状态与消息投影分开，后续扩展多 Agent、任务恢复、变更确认和统一模型调度时会出现大面积重构。

---

## 4. 前后端分层

### 4.1 前端分层

当前前端目录结构已经按职责拆分：

- `frontend/src/api`：封装 HTTP / WebSocket 相关请求
- `frontend/src/components`：聊天区、输入区、会话相关组件
- `frontend/src/store`：状态管理
- `frontend/src/router`：路由
- `frontend/src/types`：类型定义
- `frontend/src/utils`：工具函数
- `frontend/src/veiws`：页面视图

前端在当前版本中的角色是“统一消费消息流”。也就是说，前端不直接承载复杂业务决策，而是尽量依赖后端返回的标准事件和标准对象，完成消息展示、运行状态提示、任务结果呈现和变更确认交互。

### 4.2 后端分层

后端目录结构清晰对应不同职责：

- `backend/app/api`：REST API 与 WebSocket 入口
- `backend/app/models`：数据库模型
- `backend/app/schemas`：请求/响应 Schema
- `backend/app/services`：业务服务层
- `backend/app/runtime`：单 Agent Runtime、Prompt、工具与事件桥接
- `backend/app/providers`：模型平台适配层
- `backend/app/agents`：Agent 注册、内置 Agent、种子数据
- `backend/app/core`：配置、安全、数据库基础设施

这种拆分使得“接口协议”“运行时逻辑”“模型调用”“持久化状态”各自独立，从而能够支持单聊、多 Agent、编排、变更确认等不同场景复用同一套底层能力。

---

## 5. 核心数据模型

当前项目中，以下数据模型已经在代码层明确存在，并承担真实业务职责。

### 5.1 Session

`session` 是整个交互的顶层容器，用于承载一段单聊或群聊协作上下文。会话对象不仅表示一个聊天窗口，也决定：

- 当前是单聊还是群聊
- 绑定哪个 Agent
- 是否绑定工作区
- 后续消息、任务、变更、运行记录归属于谁

### 5.2 Message

`message` 是用户可见消息流的基础对象。它既用于保存用户消息，也用于保存 Agent 回复，还承担流式消息落库、任务摘要、群聊汇总结果等投影能力。

项目没有把消息仅做成“纯文本字符串”，而是保留了 `type`、`status`、`payload`、`metadata` 等扩展位，为后续承载结构化状态做准备。

### 5.3 Agent

`agent` 模型统一承载内置 Agent 和用户自建 Agent。它至少包含：

- `provider`
- `model`
- `system_prompt`
- `capability_tags`
- `tool_permissions`

这意味着 Agent 在系统中不是“一个名字”，而是完整的运行配置对象。这样做的好处是，单聊、多 Agent 编排、默认 Agent 选择、模型切换都可以围绕同一 Agent 模型工作。

### 5.4 SessionMember

`session_members` 用于保存群聊成员关系。它解决的问题是：群聊不再是前端临时拼出来的 UI 概念，而是后端可持久化、可恢复、可校验的真实结构。

该模型承担以下职责：

- 记录哪些 Agent 属于当前群聊
- 标识谁是主 Agent
- 保存成员健康状态

### 5.5 OrchestrationRun / OrchestrationTask

多 Agent 编排通过两层模型承接：

- `OrchestrationRun`：一次编排运行的顶层记录
- `OrchestrationTask`：本次运行中拆出的子任务

其中，`OrchestrationRun` 保存会话、触发消息、主规划 Agent、整体状态和摘要；`OrchestrationTask` 保存任务顺序、分配 Agent、任务目标、输入载荷、执行结果和错误信息。

这样设计的原因是：群聊编排必须可查询、可恢复、可审计，不能只存在于一次性消息输出中。

### 5.6 PendingChange / Workspace

对于代码类任务，项目引入了工作区与待确认变更模型：

- `workspace` 负责定义当前会话实际操作的项目边界
- `pending_change` 负责保存待用户确认的文件变更和 diff

这意味着系统不会把 AI 文件写入直接当作“最终结果”，而是通过“生成变更 -> 用户确认 -> 再落地”的方式保持人在回路中的控制权。

---

## 6. 消息流与 WebSocket 设计

### 6.1 为什么用统一消息流

当前项目的一个核心技术选择，是将“普通聊天回复”“Runtime 状态”“工具调用”“变更预览”“任务状态”“编排运行状态”尽量统一回收到同一条 WebSocket 事件链中。

这样做的主要原因有三点：

- 前端只需要围绕一套事件协议消费状态
- 单 Agent 与多 Agent 可以复用同一套展示通道
- 刷新恢复时，数据库消息与运行状态能对齐

### 6.2 WebSocket 入口职责

`backend/app/api/ws.py` 是当前实时链路的核心入口，主要负责：

- 建立会话级 WebSocket 连接
- 校验用户是否拥有该会话访问权
- 接收用户消息
- 根据会话模式判断走单聊回复还是群聊编排
- 把运行时事件转换为标准 WebSocket 事件返回前端

这层代码没有直接承载完整 Agent 逻辑，而是把真正的执行过程交给 `RuntimeAgentService`、`FixedAgentResponder` 和 `OrchestrationExecutor` 等服务。

### 6.3 已落地的 WebSocket 事件

从当前代码可以看到，系统已经定义并使用了一批标准事件，包括：

- `message_start`
- `message_delta`
- `message_end`
- `message_error`
- `tool_event`
- `runtime_state`
- `change_preview`
- `preview_result`
- `repair_state`
- `task_start`
- `task_end`
- `task_error`
- `orchestration_run_started`
- `orchestration_run_updated`
- `orchestration_run_finished`
- `session_member_status`
- `apply_result`

这说明当前系统中的“聊天”已经不只是文本返回，而是带有过程语义和任务语义的事件流。

### 6.4 消息流主链路

当前单次消息处理的大致流程是：

1. 前端通过 WebSocket 向某个 `session_id` 发送用户消息
2. 后端落库用户消息，并更新会话时间
3. 后端根据会话模式判断单聊 / 群聊
4. 单聊时进入 `RuntimeAgentService` 或固定 responder
5. 群聊时在满足条件下进入 orchestration 流程
6. 执行过程产生标准事件
7. WebSocket 将事件逐步发送给前端
8. 最终消息、任务结果、变更预览等被持久化，可供刷新恢复

这种设计避免了“实时展示一套、刷新恢复一套”的双轨状态。

---

## 7. Runtime / Prompt / Tool 体系

### 7.1 Runtime 的职责

当前项目已经形成了相对独立的 Runtime 层，核心目录位于 `backend/app/runtime`。这层的职责不是“调接口”，而是承接单 Agent 执行过程，主要包括：

- 会话历史注入
- Prompt 组织
- 工具注册与执行
- Runtime 状态变化
- 事件桥接
- 消息落库与最终输出

### 7.2 RuntimeAgentService

`runtime_agent_service.py` 是 Runtime 和 WebSocket / 数据库之间的桥梁。它做了几件关键事情：

- 从数据库加载会话历史
- 解析工作区根目录
- 构建 Agent 和工具集
- 创建数据库中的 Agent 消息占位
- 启动运行时执行
- 把 Runtime 内部事件转成 WebSocket 可消费事件
- 把最终结果、失败状态、待确认变更持久化

也就是说，它解决的是“纯 Runtime 世界”和“用户可见消息世界”之间的映射问题。

### 7.3 Prompt 组织

当前项目没有把系统提示词写死在某个函数内部，而是采用模板化组织方式。`backend/app/runtime/prompts.py` 根据不同 `agent_mode` 选择模板文件，例如：

- `chat_system_prompt.j2`
- `code_system_prompt.j2`
- `doc_system_prompt.j2`
- `system_prompt.j2`

这种做法的意义在于：

- Prompt 结构可维护
- 不同能力模式可以切换
- 运行时配置和提示词模板解耦

### 7.4 工具体系

当前 Runtime 已接入一批真实工具，集中位于 `backend/app/runtime/tools/`，包括：

- 读文件
- 列目录
- glob 检索
- grep 检索
- 文件替换
- 写文件
- 统一 diff
- 运行命令
- 应用变更
- 任务完成

这说明当前 Agent 已具备“在工作区内执行代码相关任务”的最小工具闭环，而不是只能做纯文本回答。

### 7.5 EventBridge 的作用

`event_bridge.py` 用于把 Runtime 内部事件桥接为 WebSocket 协议事件。这是一个很关键的设计点。

如果没有这层桥接，Runtime 的执行状态、工具调用、错误处理、变更预览都会散落在不同调用分支里。通过 EventBridge，系统把以下两层拆开了：

- Runtime 内部事件语义
- 前端消费的 WebSocket 事件语义

这保证了后续替换执行逻辑或扩展事件种类时，不需要推翻整个消息展示层。

---

## 8. 统一大模型 API 接入设计

### 8.1 设计目标

AgentHub 当前并不是只绑定一个固定模型，而是通过 Provider 抽象层统一接入不同平台。这部分代码主要位于：

- `backend/app/providers/`
- `backend/app/services/agent_runtime.py`

### 8.2 Provider 抽象

当前代码中已经存在统一注册表 `_PROVIDER_REGISTRY`，可按 `provider_id` 获取具体 Provider 实例。当前已落地的 Provider 包括：

- `qwen_openai_compatible`
- `doubao`
- `glm`

其中，Qwen 通过 OpenAI-compatible 协议接入，说明系统在模型接入策略上采用了“统一上层接口 + 不同下游实现”的方案。

### 8.3 Agent 与 Provider 绑定方式

`agent` 表直接保存：

- `provider`
- `model`

运行时通过 `get_provider_for_agent(agent)` 解析出当前 Agent 应使用的具体模型平台与模型名。这样带来的好处是：

- 同一个系统可挂接多个模型平台
- 不同 Agent 可绑定不同模型
- 群聊中不同子 Agent 可以走不同模型配置
- 模型切换不会破坏上层会话与消息结构

### 8.4 为什么不让前端直接决定模型调用

当前设计没有让前端直接携带真实密钥或随意指定底层调用逻辑，而是把最终的 Provider 解析收敛在后端。这主要是出于以下原因：

- 安全性：API Key 不暴露给前端
- 一致性：统一审计与错误处理
- 可维护性：模型切换不影响上层协议
- 可扩展性：后续接入更多 provider 时前端无需重构

---

## 9. 群聊编排与多 Agent 编排设计

### 9.1 群聊与单聊的边界

当前系统在会话层支持 `single` 与 `group` 两种模式。群聊不是单聊的 UI 变体，而是后端真正持久化成员关系和编排状态的独立运行模式。

### 9.2 群聊成员模型

群聊成员通过 `SessionMember` 模型保存，至少包括：

- 会话 ID
- 成员类型
- 成员 ID
- 是否主 Agent
- 成员健康状态

这样，群聊中的“谁在群里、谁负责主持、是否可被分配任务”都能在后端严格校验，而不是由前端随意决定。

### 9.3 主 Agent 与 Planner

当前群聊模式下，会优先解析主 Agent。主 Agent 的职责不是简单回答，而是：

- 理解用户请求
- 判断是否需要编排
- 生成结构化任务计划
- 为每个任务分配执行 Agent

`orchestration_planner.py` 中的 planner prompt 明确要求输出结构化 JSON，包含：

- 规划摘要
- 规划模式
- 子任务列表
- 任务标题、目标、分配 Agent、依赖关系、输入载荷

这意味着当前系统里的群聊编排不是“多个 Agent 顺序发言”，而是已经具备任务拆解与分派语义。

### 9.4 Executor 与任务执行

`OrchestrationExecutor` 负责接管子任务执行过程。其主要职责包括：

- 构建任务上下文
- 将任务状态从 `planned` 更新为 `running / completed / failed / waiting_confirmation`
- 为每个任务建立独立流式事件
- 将任务执行结果与变更、消息、摘要关联到 `run_id / task_id / agent_id`

执行器还负责生成编排摘要消息，把多 Agent 的中间执行状态重新汇总为用户能理解的最终结果。

### 9.5 为什么要有 Run / Task 两层模型

如果没有 `Run / Task` 两层，群聊执行就会退化成一堆普通消息，无法回答以下问题：

- 本次群聊到底拆了哪些任务
- 哪个任务分配给了哪个 Agent
- 哪个任务成功，哪个失败
- 页面刷新后如何恢复执行态

因此，多 Agent 编排的本质不是“多发几条消息”，而是把协作过程升级为可追踪、可恢复的任务系统。

### 9.6 已落地的编排查询接口

当前后端已提供与编排状态相关的 REST 查询能力，包括：

- 获取指定 run
- 获取某会话最近一次 run

这说明系统已经考虑到“编排不是只在 WebSocket 中瞬时存在”，而是需要落库并可在前端刷新后重新恢复。

---

## 10. 工作区、变更确认与代码任务闭环

### 10.1 工作区绑定

Runtime 并不是对任意路径直接读写，而是优先通过 session 绑定的 workspace 解析工作区根路径。`RuntimeAgentService` 中专门实现了工作区解析与边界校验逻辑。

这么做的原因是：

- 限制 Agent 只在合法目录内工作
- 让会话、工作区、变更对象归属关系清晰
- 为后续预览、命令执行、变更回放打基础

### 10.2 Pending Change 机制

当前代码不是把模型写文件直接作为最终结果，而是通过 `change_preview` 事件和 `pending_change` 持久化模型先产出待确认变更。这样可以让前端展示 diff，并要求用户显式确认。

这体现了当前项目在代码执行场景中的一个重要设计原则：人在回路中，AI 可以提出变更，但不能无条件直接写入最终结果。

### 10.3 命令执行与预览结果

从 Runtime 事件和工具体系可以看到，系统已经具备：

- 运行命令
- 返回命令结果
- 发送预览结果事件
- 发送修复状态事件

这说明当前代码类任务不只是“写文件”，而是开始具备“写文件 -> 执行 -> 产出运行反馈 -> 返回前端”的闭环雏形。

---

## 11. 当前实现边界

为了保证文档和代码一致，以下能力虽然在规划文档中有明确方向，但本文不作为“已完整交付能力”表述：

- 长生命周期自治运行
- 完整长期记忆系统
- 完整 Artifact 平台化生命周期
- 完整云端部署发布体系
- 高复杂度 DAG 调度器
- 完整多租户权限系统

当前版本已经真实落地的重点，是：

- IM 式会话与消息底座
- WebSocket 流式消息与状态事件
- 单 Agent Runtime 桥接
- 统一 Prompt / Tool / Provider 组织方式
- 工作区与待确认变更机制
- 群聊成员模型
- 多 Agent 编排的 Run / Task 主线

---

## 12. 部署与运行方式

根据 `README.md`，项目当前的基础运行方式如下：

- 前端通过 `pnpm dev:frontend` 启动
- 后端通过 `pnpm dev:backend` 启动

后端依赖 `.env` 中的模型与服务配置，当前默认围绕 Qwen 的 OpenAI-compatible 接口组织，也支持 Doubao 与 GLM 的接入配置。前端通过环境变量配置 HTTP 与 WebSocket 地址。

从比赛交付角度看，当前版本已经具备本地启动、前后端联调和消息流展示的基础条件。

---

## 13. 技术总结

AgentHub 当前版本的技术重点，不是追求一次性完成所有 Agent 平台能力，而是优先建立一个可演进的底座。这个底座包括：

- 会话与消息模型
- WebSocket 事件流
- Runtime 与 WebSocket 桥接
- 统一 Provider 抽象
- 群聊成员关系
- 编排运行记录
- 工作区与变更确认机制

从工程角度看，这些能力共同回答了三个关键问题：

- 模块怎么拆：接口层、运行时层、Provider 层、编排层、持久化层各自独立
- 数据怎么流：消息、任务、变更和运行状态统一通过数据库与 WebSocket 回流
- 为什么这样设计：为了保证单聊、多 Agent、代码任务和模型切换都能在同一架构内持续扩展，而不是依赖临时 Demo 逻辑堆叠

