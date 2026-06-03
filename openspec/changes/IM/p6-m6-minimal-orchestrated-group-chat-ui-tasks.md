# Task: P6 M6 前端最小群聊执行视图

## 0. 文档定位

- 本文档对应 [p6-orchestrated-group-chat-minimal-chain-plan.md](/D:/code/ZiJieAI/AgentHub/openspec/changes/IM/p6-orchestrated-group-chat-minimal-chain-plan.md) 中的 `M6 前端最小群聊执行视图`。
- 本文档只覆盖：
  - 编排链路在聊天 UI 中的最小可理解展示
  - 主 Agent 计划、子任务执行、确认卡、最终汇总四类状态的前端组织
  - 页面刷新后的 active run 与相关 UI 状态恢复
- 本文档不覆盖：
  - orchestration 数据模型和任务规划本身
  - 多 stream 执行能力本身
  - task-aware pending change 与 run 汇总的底层状态机实现
  - 全量回归测试与联调整体收口

## 1. 背景

`M1 ~ M5` 完成后，系统理论上已经具备以下能力：

- group session 中可以创建 orchestration run 与多个 task
- 主 Agent 可以先输出计划消息
- 多个子任务可以并行执行并各自拥有独立 stream
- 每个 task 可以独立进入待确认态并被用户确认或取消
- 所有 task 进入终态后，系统可以生成最终汇总消息

但如果前端仍然沿用原本偏“单流单确认”的聊天视图，这条链路虽然存在，用户却很难真正理解当前发生了什么：

- 很难区分哪条消息是主 Agent 的计划，哪条是子 Agent 的执行流
- 多个子任务并行时，用户不知道当前 run 总共有多少任务、哪些在执行、哪些在等待确认
- 待确认卡虽然存在，但不容易看出它属于哪个 task、哪个 agent
- 最终汇总虽然落库，但如果没有和 run/task 状态放在统一视图里，闭环感仍然不足

因此，`M6` 的目标不是重做整个聊天产品，而是在当前 UI 结构上增加一个“最小但清晰”的编排视图，让用户可以在一个会话里看懂从计划到执行、确认、汇总的完整链路。

## 2. 目标

实现一套最小前端闭环：

1. 用户进入一个 group session 后，前端可恢复最近 active run。
2. 聊天区能够区分主 Agent 计划消息、子 Agent 执行流、task 确认卡、主 Agent 汇总消息。
3. 页面上存在一个最小任务面板或等价摘要区域，展示 run 总状态与 task 列表。
4. 同一 run 下多个 task 的执行与确认状态可以并行呈现，不互相覆盖。
5. 页面刷新后，计划、执行、确认、汇总四类状态都可恢复。
6. 单聊与非编排 group 会话体验不回归。

本阶段的核心原则是：

- 优先做“清晰表达状态”的最小 UI，不追求复杂视觉重构。
- 尽量复用现有聊天消息流和 store，不引入第二套状态来源。
- 视图只消费 `M1 ~ M5` 已建立的结构化状态，不自行推导业务真相。

## 3. 本期范围

### 本期要做

- 为会话恢复增加 active run 拉取入口
- 在聊天区识别四类 orchestration 消息/状态
- 新增最小任务面板或等价 run 摘要区
- 在 `ChatHeader` 或等价顶部区域展示 active run 摘要
- 页面刷新后恢复 run/task/pending change/summary 的展示
- 保持单聊和普通 group 会话兼容

### 本期不做

- 不做完整群聊产品化 redesign
- 不做复杂拖拽、折叠树、依赖图等高级任务视图
- 不做每个 task 的深度详情页
- 不做多用户实时协作可视化
- 不做 `M7` 级别的回归基线收口

## 4. 后端实施任务

### 4.1 补充 Active Run 恢复入口

为前端页面初始化提供最小恢复能力，二选一或并存：

- 在 session detail 接口中附带最近 active run 摘要
- 或新增：
  - `GET /api/sessions/{session_id}/active-run`

返回内容至少包含：

- `run_id`
- `status`
- `summary`
- `created_at`
- `updated_at`
- `tasks`
- `pending_changes`

要求：

- 恢复接口只返回前端渲染最小执行视图所需数据
- 不重复设计与 `GET /api/orchestration/runs/{run_id}` 冲突的第二套真相源
- owner 权限控制与现有 session 查询保持一致

### 4.2 统一恢复数据契约

确保页面刷新后前端能够通过已有接口组合拿回：

- 最近 active run
- run 下 tasks 及其状态
- 当前 session 下 task-aware pending changes
- 计划消息与汇总消息 metadata
- 必要的 agent 展示信息

要求：

- 恢复链路字段命名与 websocket 增量事件一致
- 避免前端为了恢复视图再自行拼装不稳定推断逻辑

### 4.3 兼容旧会话与非编排会话

- 对没有 active run 的 session 返回空值或空结构，而不是错误
- 普通单聊或未进入 orchestration 的 group 会话维持原有接口行为
- 历史消息缺少 orchestration metadata 时，前端仍可正常回退到普通消息展示

## 5. 前端实施任务

### 5.1 恢复 Active Run 到 Session Store

在 `useSessionStore` 或等价状态层新增：

- `activeRunBySession`
- `activeTasksByRun`
- `fetchActiveRun(sessionId)`
- `restoreOrchestrationState(sessionId)`

要求：

- 进入会话时优先恢复 active run
- 页面刷新或重新进入会话时可重建编排相关 UI 状态
- 不把 UI 状态和 websocket 临时流状态耦合死

### 5.2 新增最小任务面板

在 `ChatWorkspace` 或等价容器内新增最小任务面板，至少展示：

- 当前是否存在 active run
- run 总状态
- task 总数
- 每个 task 的：
  - 标题
  - agent
  - 当前状态

建议最小状态文案：

- `planned`
- `thinking`
- `running`
- `waiting_confirmation`
- `completed`
- `rejected`
- `cancelled`
- `failed`

要求：

- 面板是辅助理解，不应阻断原有聊天主流
- 当会话没有 active run 时，该区域可以隐藏或展示极简空态

### 5.3 聊天区识别四类编排状态

消息区需支持区分并渲染：

- 主 Agent 计划消息
  - 识别 `metadata.is_orchestration_plan`
- 子 Agent 执行流
  - 根据 `task_id / agent_id / run_id / stream_id` 展示归属
- task 级确认卡
  - 与对应 task 绑定显示
- 主 Agent 汇总消息
  - 识别 `metadata.is_orchestration_summary`

要求：

- 计划消息与汇总消息样式上应与普通 assistant message 有最小差异化
- 子任务执行流要能让用户看出“这是哪个 task / 哪个 agent 的输出”
- 确认卡优先贴近对应 task，而不是作为全局无归属弹层

### 5.4 更新 Header 或会话摘要区

在 `ChatHeader` 或等价顶部区域增加可选编排摘要：

- 当前 active run 状态
- active task 数量
- 是否存在待确认任务

要求：

- 仅在 orchestration 会话且存在 active run 时显示
- 单聊会话不显示多余信息

### 5.5 串联执行流、确认卡与汇总态

前端需把以下状态在同一会话中组织为可理解顺序：

1. 主 Agent 计划
2. 多个子任务执行流
3. 对应 task 的确认卡
4. run 汇总消息

要求：

- 不强制四者必须在单一组件中实现
- 但用户在页面上能够明显分辨其先后关系和归属关系
- 当一个 task 已完成或已取消时，对应展示要有明确状态反馈

### 5.6 页面刷新与重进恢复

页面刷新或重新进入会话后，需恢复：

- active run
- task 列表与状态
- 待确认卡
- 已存在的执行流基础归属
- 最终汇总消息

要求：

- 恢复逻辑优先依赖服务端已落库数据
- websocket 仅负责增量更新，不作为恢复唯一来源

### 5.7 单聊与非编排兼容

- 单聊 session 继续沿用原体验
- 非编排 group session 不显示无意义的 run/task 面板
- 老历史消息没有 orchestration metadata 时，不影响正常渲染

## 6. 测试

### 6.1 前端测试

状态恢复：

1. 进入一个存在 active run 的会话时，可自动恢复 run 与 task 列表。
2. 刷新页面后，计划消息、执行流、确认卡、汇总消息都能恢复。
3. 没有 active run 的会话不会错误展示任务面板。

UI 渲染：

1. 主 Agent 计划消息可被正确识别和渲染。
2. 多个子任务执行流可并行显示，且能看出 task/agent 归属。
3. 多个确认卡可同时显示，且归属清晰。
4. 主 Agent 汇总消息可被正确识别和渲染。
5. `ChatHeader` 可正确显示 active run 摘要。

兼容性：

1. 单聊会话不显示多余的 run/task UI。
2. 普通 group 会话未进入 orchestration 时不报错。
3. 缺少 orchestration metadata 的历史消息仍按普通消息渲染。

### 6.2 后端测试

1. active run 恢复接口在有 active run 时返回完整最小数据集。
2. active run 恢复接口在无 active run 时返回稳定空结构。
3. 恢复接口权限与 session owner 约束一致。
4. 恢复接口输出字段与前端约定一致，能支持页面完整恢复。

### 6.3 联调验证

1. 在 group session 中发送一个复合请求并生成 orchestration run。
2. 主 Agent 输出计划消息。
3. 两个子 Agent 同时进入执行态，前端可以清楚区分各自执行流。
4. 两个 task 各自产生确认卡，前端能展示其归属与状态。
5. 用户分别确认或取消后，任务面板与聊天区状态同步更新。
6. 主 Agent 汇总消息出现，run 总状态同步更新。
7. 刷新页面后，计划、执行、确认、汇总四类状态都能恢复。

## 7. 验收标准

### 7.1 视图清晰度

- 用户能在一个会话中明确区分主计划、子执行、确认卡和最终汇总
- 多个 task 并行时，归属关系清晰，不发生明显串位

### 7.2 恢复能力

- 页面刷新后不会丢失 active run、task 状态、确认卡和汇总消息
- 恢复后的 UI 与刷新前核心状态保持一致

### 7.3 兼容性

- 单聊体验不回归
- 非编排 group 会话不报错
- 老历史消息兼容展示

### 7.4 范围控制

- 本任务在不重做整个聊天 UI 的前提下完成最小可理解展示
- 当前设计没有引入第二套独立于 run/task/message 之外的前端真相源

## 8. 与后续任务的边界

- `M6` 完成后，编排链路在前端已具备“用户看得懂”的最小执行视图。
- `M7` 再负责把 `M1 ~ M6` 的能力收束为稳定的自动化测试和联调验收基线。
