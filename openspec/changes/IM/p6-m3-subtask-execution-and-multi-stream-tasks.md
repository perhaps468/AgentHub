# Task: P6 M3 子任务执行与多 Stream

## 0. 文档定位

- 本文档对应 [p6-orchestrated-group-chat-minimal-chain-plan.md](/D:/code/ZiJieAI/AgentHub/openspec/changes/IM/p6-orchestrated-group-chat-minimal-chain-plan.md) 中的 `M3 子任务执行与多 Stream`。
- 本文档只覆盖：
  - 同一 group session 下多个 orchestration task 的并行执行
  - 每个 task 独立的 `stream_id / message_id / runtime state`
  - 面向 task 的上下文隔离
  - 前端多 stream 渲染与状态归属
- 本文档不覆盖：
  - task 级 pending change 确认
  - run 汇总与完成判定
  - 群聊 UI 的完整重构

## 1. 背景

`M1 + M2` 完成后，系统已经可以在 group session 中创建 orchestration run，并把一次复合请求拆成多个 orchestration task。但这些 task 还只是“被规划出来”，没有进入真正可执行、可观察、可恢复的运行态。

当前代码仍然受以下约束：

- WebSocket 与 runtime 主链路默认按 `session_id` 做单飞保护，天然偏向“一个会话同一时刻只跑一个流”。
- 前端 `useChatStreamState` 默认按 session 维护单活跃 stream，多条子任务流会互相覆盖。
- runtime 读取历史时默认拉取整个 session history，无法隔离 sibling task 的执行上下文。
- 现有流式事件虽然已有 `stream_id`，但还不足以把一个 orchestration run 下的多条 task 执行链稳定地区分开。

如果不先解决这一层，后续的 task 级确认与 run 汇总都会建立在不稳定的执行语义上：用户无法同时看到多个子 Agent 的 `thinking...`，后端也无法保证每个 task 的上下文边界与状态归属。

因此，`M3` 的目标是把 `M1 + M2` 中“已规划的 tasks”推进到“可并行执行的 tasks”，并让前后端都明确以 `run_id + task_id + stream_id` 作为最小执行单元。

## 2. 目标

实现一条最小闭环：

1. group session 中已有一个 orchestration run 和多个 planned tasks。
2. 后端可为同一 run 下的多个 task 分别启动 runtime 执行。
3. 每个 task 拥有独立的 `stream_id`、执行消息和运行态。
4. 同一 session 内允许多个 task 并行进入 `thinking / running`。
5. 每个 task 在执行时只能读取自己的必要上下文，不读取 sibling task 的完整输出。
6. 前端可同时展示多个 task stream，且互不覆盖、互不串位。

## 3. 后端实施任务

### 3.1 调整执行入口与并发粒度

- 复查当前 `_IN_FLIGHT_GUARD` 或等价单飞保护逻辑。
- 保持“用户直接发消息进入 group session”的入口仍然串行，避免重复触发同一 run。
- 在 orchestration task 执行器层面放开并行能力，使同一 `session_id` 下多个 `task_id` 可以同时启动 runtime。
- 明确新的并发键粒度：
  - 用户入口：建议仍按 `session_id`
  - 子任务执行：按 `task_id` 或 `run_id + task_id`

### 3.2 新增 task 执行器

- 增加 orchestration task executor/service，用于从已落库的 task 启动 runtime。
- 执行器至少负责：
  - 读取 task、run、session、workspace、assigned agent 信息
  - 为当前 task 创建独立 `stream_id`
  - 为当前 task 创建独立 assistant message 或等价执行消息
  - 注入 task goal、assigned agent 身份、run/task metadata
  - 推进 task 状态：`planned -> running`
- 执行器要支持批量触发同一 run 下的多个 tasks，并允许实际并行运行。

### 3.3 统一事件 contract

- 在现有 runtime / websocket 事件上统一补充以下字段：
  - `run_id`
  - `task_id`
  - `agent_id`
  - `stream_id`
- 优先复用现有事件类型：
  - `message_start`
  - `runtime_state`
  - `message_delta`
  - `message_end`
  - 如已存在的其它 change preview 相关事件
- 要求所有事件在同一 task 执行链内字段保持稳定，便于前端按 `task_id` 和 `stream_id` 建立归属。

### 3.4 实现 task-aware history 过滤

- 在 runtime 加载上下文前增加 task-aware history builder/filter。
- 每个 task 可见上下文只应包含：
  - 用户原始请求
  - 主 Agent 规划消息摘要
  - 当前 task 自身的目标描述
  - 当前 task 自己的执行过程消息
- 默认不可见内容：
  - sibling task 的完整执行输出
  - sibling task 的中间推理状态
  - 主 Agent 最终汇总消息
- 该过滤逻辑应封装在 runtime 上下文构造层，不依赖前端规避。

### 3.5 任务状态更新与容错

- 为 task 增加最小执行态流转：
  - `planned -> running`
  - `running -> completed` 或保留给后续 `waiting_confirmation`
  - `running -> failed`
  - `running -> cancelled`
- 单个 task 失败时，不自动中断同 run 下其它 task。
- 记录 task 失败原因到 `error_payload` 或等价字段，便于后续 run 汇总使用。

### 3.6 会话恢复接口补充

- 复查现有 session detail 或 orchestration run 查询接口，确保刷新页面后前端能拉回：
  - active run
  - 该 run 下 tasks
  - task 当前状态
  - 与 task 绑定的最新执行消息/stream 基础信息
- 如果现有接口不足，补充最小查询字段，但避免把 `M4/M5` 的职责提前混入。

## 4. 前端实施任务

### 4.1 扩展多 stream 状态模型

- 调整 `useChatStreamState`，移除“同一 session 仅保留一个活跃 stream”的默认假设。
- 将 stream 状态缓存从“按 session 单实例”改为“同 session 下按 `stream_id` 多实例”。
- 每条 stream 至少关联：
  - `run_id`
  - `task_id`
  - `agent_id`
  - `message_id`
  - `status`

### 4.2 建立 task 与 stream 的归属映射

- 在 session store 或等价状态层增加：
  - `taskId -> streamId`
  - `streamId -> task metadata`
- 处理 websocket 事件时，按 `task_id` 和 `stream_id` 精确更新，不再使用“当前 session 正在运行的唯一 stream”推断归属。
- 页面刷新或重新进入会话时，可根据 run/tasks 数据恢复映射关系。

### 4.3 更新聊天区与任务区渲染

- 在聊天区或最小任务面板中支持同时展示多个执行中 stream。
- 每条执行卡片至少展示：
  - agent 名称
  - task 标题
  - 执行状态：`thinking / running / completed / failed`
- 多条 task stream 同时存在时：
  - 不互相覆盖
  - 不因为新事件到达而清空旧 stream
  - 不因 session 切换逻辑误删同 session 其他活跃 stream

### 4.4 保持单聊兼容

- 单聊 session 继续按原有体验工作，不要求出现任务面板。
- 与 orchestration 无关的普通消息流不应被新的多 stream 状态模型破坏。
- 现有 `clearOtherSessionStreams` 或等价逻辑需要收敛到“仅清理其它 session 的流”，不能误删当前 session 的 sibling task streams。

## 5. 测试任务

### 5.1 后端测试

1. 同一 run 下 2 个 task 可被同时启动，并各自产生独立 `stream_id`。
2. 同一 run 下大于 2 个 task 也可并行执行，证明实现未写死“双任务”。
3. task 执行事件都会稳定带上 `run_id / task_id / agent_id / stream_id`。
4. 一个 task 失败时，其他 task 仍可继续执行。
5. task-aware history 过滤生效，当前 task 不读取 sibling task 的执行输出。
6. task 状态能从 `planned` 正确推进到 `running` 及终态。

### 5.2 前端测试

1. 同一 session 下多条 stream 可同时渲染。
2. 多条 stream 的增量消息不会互相覆盖。
3. 不同 task 的运行状态可独立更新。
4. `clearOtherSessionStreams` 或等价逻辑不会清掉当前 session 的 sibling task streams。
5. 刷新页面后可恢复 active run、tasks 与已存在 stream 的基础归属信息。
6. 单聊消息流与原有 UI 行为无回归。

### 5.3 联调验证

1. 在 group session 里发送一个可拆成至少 2 个文件任务的复合请求。
2. 主 Agent 输出规划消息后，系统启动多个子任务执行。
3. 前端可同时看到至少 2 个子 Agent 进入 `thinking...`。
4. 两个 task 的输出分别落入自己的执行卡片或消息流。
5. 人为让其中一个 task 失败，另一个 task 仍能继续完成。
6. 刷新页面后，run/task 与执行中或已完成状态仍可恢复展示。

## 6. 验收标准

- 同一 group session 中，一个 orchestration run 下的多个 task 可以真正并行执行。
- 每个 task 都有独立的 `stream_id`、消息归属和运行状态。
- 前端能稳定同时展示多个 task stream，且没有互相覆盖、串位或被误清理的问题。
- 子任务上下文彼此隔离，默认不会读取 sibling task 的完整输出。
- 单个 task 失败不会导致同 run 其它 task 被一并中断。
- 页面刷新后，当前 run、task 状态与多 stream 基础展示可恢复。
- 单聊链路无明显回归。

## 7. 与后续任务的边界

- `M3` 完成后，系统具备“已规划 tasks 的并行执行能力”。
- `M4` 再接入 task-aware pending change 确认，不在本任务中提前实现确认卡交互。
- `M5` 再实现 run 汇总与最终完成判定，不在本任务中要求生成最终总结消息。
