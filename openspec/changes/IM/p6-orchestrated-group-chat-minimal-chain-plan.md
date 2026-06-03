# Task: P6 最小群聊协作链路总方案

## 0. 文档定位

- 本文档用于替代当前不合理的 P6 群聊实现思路，定义一条更贴近当前代码现状的最小可落地链路。
- 本文档的目标不是直接实现“完整多 Agent 群聊系统”，而是先落地“主 Agent 规划 + N 个子任务并行执行 + 独立确认 + 主 Agent 汇总”的最小闭环。
- 本文档是后续拆分 `M1 ~ M7` 七个 task 的总纲。每个 `M` 都包含后端、前端、测试、验收标准。
- 本文档优先服从当前项目已有能力边界：
  - 已有 group session/member 模型
  - 已有 workspace 绑定
  - 已有 runtime 流式消息链路
  - 已有 pending change 确认链路
  - 当前仍是“单 session 单 WS 连接”模型

## 1. 核心目标

目标链路如下：

1. 用户在群聊模式发送一个复合任务请求
2. 主 Agent 先输出任务计划和分配方案
3. 系统将任务拆成 `N` 个子任务并分配给不同 Agent
4. 每个子任务在同一会话内以独立执行流运行，可并行展示 `thinking...`
5. 每个子任务产生自己的文件变更确认卡
6. 用户可分别确认或取消每个子任务
7. 当全部子任务进入终态后，主 Agent 输出最终汇总

本期最小验证场景：

- 用户在 group 会话说：
  - 创建 `hello.java`，内容为 Java Hello World
  - 创建 `hello.py`，内容为 Python Hello World
- 主 Agent 先给出任务计划
- 两个子 Agent 同时进入执行态
- 两个子任务各自产生确认按钮
- 用户确认或取消后，主 Agent 输出汇总结果

## 2. 总体设计原则

### 2.1 不是“完整群聊系统”，而是“会话内编排执行”

- 现有 group session 能力继续保留
- 本期重点不是群成员展示、健康状态、复杂群聊交互
- 本期重点是：
  - 编排 run
  - 子任务 task
  - 多 stream 并发
  - task 级确认
  - 汇总判定

### 2.2 从一开始支持 `1 -> N`，不写死双子任务

- 虽然第一条验收链路只有 2 个子任务
- 但模型和事件设计必须允许 `N` 个 task
- 本期不做复杂 DAG 调度
- 但为后续依赖关系预留 `parent_task_id`

### 2.3 第一版先由后端规则拆任务，不依赖主 Agent 真正规划

- 主 Agent 可以输出“计划文本”
- 但真正的 task 结构第一版由后端规则生成
- 避免第一版死在 LLM 计划解析不稳上

### 2.4 单 session 单 WS 连接保持不变

- 不引入“一个 Agent 一条 WS”
- 不引入“一个 task 一条 WS”
- 仍然保持“一个 session 一条 WS”
- 扩展的是：
  - 同一 session 内允许多个 `stream_id`
  - 新增 run/task 事件

### 2.5 子任务上下文必须隔离

- 当前 runtime 默认会读取整个 session 的文本历史
- 本期必须增加 task-aware history 过滤
- 防止 sibling task 相互污染上下文

### 2.6 模型支持一个 task 多个 change，但第一版交互按 task 批次确认

- 数据层允许 `task -> many pending_changes`
- 第一版 UI 和交互按“一个 task 一个确认批次”设计
- 降低状态聚合复杂度

## 3. 本期范围

### 本期要做

- 引入独立的 orchestration run / task 模型
- 主 Agent 计划展示
- 后端规则拆分 `N` 个子任务
- 同 session 多 stream 并发执行
- task 级待确认状态与确认按钮
- 主 Agent 的系统化汇总输出
- 刷新页面后的 run/task/pending change 恢复

### 本期不做

- 不做自由多 Agent 对话
- 不做复杂 DAG 调度器
- 不做主 Agent 切换
- 不做 task 自动再拆分
- 不做每个文件单独确认的复杂交互
- 不做群成员健康状态深化
- 不做多个用户同时在同一群会话内协作

## 4. 当前代码现状与约束

### 已有能力

- group session 成员持久化：
  - `backend/app/models/session_member.py`
  - `backend/app/api/sessions.py`
- group session 默认路由主 Agent：
  - `backend/app/api/ws.py`
- workspace 绑定与校验：
  - `backend/app/api/workspaces.py`
  - `backend/app/runtime/runtime_agent_service.py`
- runtime 流式消息：
  - `backend/app/runtime/runtime_agent_service.py`
  - `backend/app/runtime/event_bridge.py`
- pending change 预览与确认：
  - `backend/app/models/pending_change.py`
  - `backend/app/api/pending_changes.py`
- 前端流状态和 pending change 恢复：
  - `frontend/src/utils/useChatStreamState.ts`
  - `frontend/src/store/module/useSessionStore.ts`

### 当前关键约束

- WS 入口当前默认按 `session_id` 做单飞行保护
- 前端 `useChatStreamState` 当前默认同 session 只保留一条活跃流
- runtime 加载历史时会读取整段 session history
- pending change 当前只关联 `session_id/message_id/stream_id`

这些都是后续拆分 task 时必须先处理的真实约束。

## 5. 统一数据与事件设计

### 5.1 Orchestration Run

建议新增 `orchestration_runs`：

- `id`
- `session_id`
- `trigger_message_id`
- `planner_agent_id`
- `status`
  - `planned | running | waiting_confirmation | completed | partial | failed | cancelled`
- `summary`
- `created_at`
- `updated_at`
- `completed_at`

### 5.2 Orchestration Task

建议新增 `orchestration_tasks`：

- `id`
- `run_id`
- `parent_task_id` 可空，预留
- `sequence`
- `assigned_agent_id`
- `kind`
  - 第一版先支持 `file_write`
- `title`
- `goal`
- `input_payload`
- `result_payload`
- `error_payload`
- `status`
  - `planned | running | waiting_confirmation | completed | rejected | cancelled | failed`
- `created_at`
- `updated_at`
- `completed_at`

### 5.3 Pending Change 扩展字段

在现有 `pending_changes` 基础上扩展：

- `run_id`
- `task_id`
- `agent_id`
- 可选 `batch_id`

### 5.4 WS 事件扩展

在现有事件之上增加：

- `orchestration_run_started`
- `orchestration_task_started`
- `orchestration_task_updated`
- `orchestration_task_finished`
- `orchestration_run_finished`

第一版也允许先不新增太多专用事件，而是把 `task_id/run_id/agent_id` 挂到现有：

- `message_start`
- `runtime_state`
- `change_preview`
- `apply_result`

但事件 contract 必须统一，避免前端后面再返工。

### 5.5 子任务上下文隔离规则

每个子任务的 runtime 输入只应包含：

- 用户原始请求
- 主 Agent 输出的计划摘要
- 当前 task 自己的目标描述
- 当前 task 自己的执行过程消息

不能默认包含：

- 其他 sibling task 的完整输出
- 主 Agent 最终总结消息

## 6. 推荐实施顺序

1. `M1` 编排模型
2. `M2` 任务规划与派发
3. `M3` 子任务执行与多 stream
4. `M4` task 级 pending change 确认
5. `M5` run 汇总与完成判定
6. `M6` 前端最小视图升级
7. `M7` 测试与联调收口

---

## 7. M1 编排模型

### 7.1 目标

为群聊会话内编排增加独立的数据域，支持后续 `1 -> N` 子任务执行，不把 task 状态混进 session/message 基表。

### 7.2 后端实施任务

- 新增 `orchestration_runs` ORM 模型
- 新增 `orchestration_tasks` ORM 模型
- 增加数据库 migration / SQL
- 增加基础 schema：
  - `OrchestrationRunResponse`
  - `OrchestrationTaskResponse`
- 增加基础查询接口：
  - `GET /api/orchestration/runs/{run_id}`
  - `GET /api/sessions/{session_id}/runs/latest`
- 增加服务层：
  - 创建 run
  - 批量创建 tasks
  - 查询 run + tasks

### 7.3 前端实施任务

- `frontend/src/types/agenthub.ts` 增加：
  - `OrchestrationRun`
  - `OrchestrationTask`
- 新增编排 API 模块
- `useSessionStore` 增加：
  - 当前 active run
  - 当前 active tasks
  - run 查询与缓存方法

### 7.4 测试

后端：

- run 创建成功
- run 下可创建多个 task
- `sequence` 排序稳定
- `parent_task_id` 可空且不破坏主流程

前端：

- run/task 类型对齐
- store 可正确缓存并读取 run/task

### 7.5 验收标准

- 数据库中可创建一个 run 和任意多个 task
- 查询接口可返回完整 run + tasks 结构
- 前端可读取并缓存 run/task 数据
- 设计上未写死为“2 个 task”

---

## 8. M2 任务规划与派发

### 8.1 目标

让 group 会话中的主 Agent 先输出计划，再由后端规则生成 `N` 个子任务并保存。

### 8.2 后端实施任务

- 在 group session 消息入口增加“编排模式”分支
- 第一版由后端规则根据用户请求拆 task
- 主 Agent 仍输出计划文本，但不负责生成最终 task 结构
- 规则拆分产物至少包含：
  - task title
  - assigned agent
  - target file
  - goal
- 创建：
  - 1 个 orchestration run
  - N 个 orchestration task
- 主 Agent 不直接写文件
- 对非法 agent、非法 workspace、缺失绑定等情况返回稳定错误

### 8.3 前端实施任务

- 聊天流中支持显示主 Agent 的“计划消息”
- 计划消息 metadata 中带：
  - `run_id`
  - `is_orchestration_plan`
- 在任务面板或消息区显示 task 列表占位状态

### 8.4 测试

后端：

- 给一个复合请求可生成 run + N tasks
- 计划消息落库成功
- 主 Agent 计划生成后不会直接产生 pending change

前端：

- 计划消息能展示
- task 占位列表能和 run 关联

### 8.5 验收标准

- 用户发出复合请求后，主 Agent 先输出计划和分配方案
- 后端可稳定生成 run + tasks
- 此阶段不会直接开始文件写入
- 单聊链路不受影响

---

## 9. M3 子任务执行与多 Stream

### 9.1 目标

允许同一 session 内多个子任务并行执行，每个 task 有独立 stream/message/runtime 状态。

### 9.2 后端实施任务

- 调整当前 `_IN_FLIGHT_GUARD` 粒度：
  - 用户入口仍串行
  - 子任务执行允许并行
- 为每个 task 分配独立：
  - `stream_id`
  - `message_id`
- 增加 task 执行器：
  - 从 orchestration task 启动 runtime
  - 注入 assigned agent 身份
  - 注入 task 目标
- 增加 task-aware history 过滤
- 事件中补充：
  - `run_id`
  - `task_id`
  - `agent_id`

### 9.3 前端实施任务

- `useChatStreamState` 去掉“同 session 只保留一个 stream”的逻辑
- 支持同 session 多 stream 并存
- 每个 stream 能关联到：
  - `task_id`
  - `agent_id`
  - `run_id`
- 执行中消息卡显示：
  - agent 名称
  - task 标题
  - `thinking / running / waiting_confirmation / completed`

### 9.4 测试

后端：

- 同一 run 下 2 个 task 可同时启动
- 3 个以上 task 也可并行执行
- 子任务上下文不读取 sibling task 输出

前端：

- 同 session 多条 stream 同时显示
- 不会互相覆盖
- 不会被 `clearOtherSessionStreams` 清掉

### 9.5 验收标准

- 在同一个群聊会话中可同时看到多个子 Agent 进入 `thinking...`
- 每个 task 拥有独立 stream
- 一个 task 失败不导致其他 task 停止
- 任务上下文彼此隔离

---

## 10. M4 Task 级 Pending Change 确认

### 10.1 目标

把现有 pending change 机制升级为 task-aware，允许同一 run 下多个 task 各自产生确认卡并独立确认。

### 10.2 后端实施任务

- 扩展 `PendingChangeModel`：
  - `run_id`
  - `task_id`
  - `agent_id`
  - 可选 `batch_id`
- task 执行生成 pending change 时写入以上字段
- task 状态流转：
  - `running -> waiting_confirmation`
  - `apply -> completed`
  - `reject -> rejected/cancelled`
- 第一版按“一个 task 一个确认批次”处理
- 查询接口支持按 session 恢复 task-aware pending changes

### 10.3 前端实施任务

- pending change 卡片显示：
  - task title
  - agent name
  - target path
- 同一会话支持同时展示多个待确认卡
- 点击确认/取消时，精确更新对应 task
- 页面刷新后可恢复：
  - task 状态
  - pending change 卡片

### 10.4 测试

后端：

- 两个 task 同时产生 pending change
- 分别 apply/reject 后状态正确
- pending change 恢复时能带回 task/run 关联

前端：

- 多个确认卡互不干扰
- apply_result 只更新对应 task 卡片
- 刷新后卡片恢复正常

### 10.5 验收标准

- 同一 run 下多个 task 可分别确认或取消
- 一个 task 的确认结果不影响其他 task
- 待确认状态与确认结果可刷新恢复
- 当前实现没有写死“一次只允许一个 pending change”

---

## 11. M5 Run 汇总与完成判定

### 11.1 目标

当所有 task 进入终态后，由系统稳定输出主 Agent 汇总，不依赖 LLM 再总结。

### 11.2 后端实施任务

- 增加 run 聚合器
- 监听 task 状态变化
- 当全部 task 进入终态时计算 run.status：
  - 全部 completed -> `completed`
  - 既有 completed 又有 rejected/cancelled/failed -> `partial`
  - 全部失败或取消 -> `failed/cancelled`
- 生成主 Agent 汇总消息
- 汇总消息作为普通 message 落库
- metadata 增加：
  - `run_id`
  - `is_orchestration_summary`

### 11.3 前端实施任务

- 计划卡或任务面板展示 run 总状态
- 汇总消息在聊天区正常显示
- 文案按状态区分：
  - `全部任务完成`
  - `部分任务完成`
  - `任务已取消`
  - `任务执行失败`

### 11.4 测试

后端：

- 全部完成时输出 `completed`
- 部分成功部分取消时输出 `partial`
- 汇总消息只生成一次

前端：

- run 总状态展示正确
- 汇总消息展示正确

### 11.5 验收标准

- 所有 task 结束后，一定会生成最终汇总
- 汇总结果和 task 真正终态一致
- 不依赖 LLM 再次推理即可给出稳定结果

---

## 12. M6 前端最小群聊执行视图

### 12.1 目标

在不重做整个聊天 UI 的前提下，把编排链路的计划、执行、确认、汇总四种状态清晰展示出来。

### 12.2 后端实施任务

- 会话详情接口可选返回最近 active run 摘要
- 或提供：
  - `GET /api/sessions/{session_id}/active-run`
- 确保页面刷新时前端能拉回恢复所需最小数据

### 12.3 前端实施任务

- `ChatWorkspace` 增加最小任务面板
- 消息区支持区分：
  - 主 Agent 计划消息
  - 子 Agent 执行流
  - task 级确认卡
  - 主 Agent 汇总消息
- `ChatHeader` 可选显示：
  - active run
  - active task 数
- `zhu.vue` / `useSessionStore` 接入 active run 恢复

### 12.4 测试

前端：

- 进入会话后可恢复最近 active run
- 刷新后计划消息、执行流、确认卡、汇总消息都能恢复
- 单聊会话不显示不必要的任务面板

### 12.5 验收标准

- 用户能在一个会话里清楚区分主计划、子执行、确认卡和最终总结
- 页面刷新后不会丢失链路状态
- 单聊体验不回归

---

## 13. M7 测试与联调收口

### 13.1 目标

把这条最小群聊协作链路变成后续扩展 `N` 子任务编排的稳定回归基线。

### 13.2 后端实施任务

- 补齐模型和状态机测试
- 补齐 orchestration service 测试
- 补齐多 task 并行执行测试
- 补齐 task-aware pending change 测试
- 补齐 run 汇总测试

### 13.3 前端实施任务

- 补齐多 stream 渲染测试
- 补齐多 pending change 独立确认测试
- 补齐 run 状态恢复测试
- 补齐单聊兼容测试

### 13.4 测试方案

后端：

1. 创建 group session
2. 发送复合请求
3. 生成 run + N tasks
4. 多 task 并行执行
5. 生成多个 task-aware pending changes
6. apply/reject 后更新 task 与 run
7. 生成最终汇总消息

前端：

1. 计划消息渲染
2. 多 stream 并存渲染
3. 多确认卡独立交互
4. 汇总消息渲染
5. 刷新恢复
6. 单聊不回归

联调验收链路：

1. 用户在 group 会话发送复合任务
2. 主 Agent 输出计划
3. 至少 2 个子 Agent 同时显示 `thinking...`
4. 两个 task 各自产生确认卡
5. 用户分别确认或取消
6. 主 Agent 输出最终汇总
7. 刷新页面后状态可恢复

### 13.5 验收标准

- 最小场景链路完整跑通
- `N > 2` 时架构不需要推倒重来
- 单聊不回归
- run/task/pending change/summary 均可恢复

## 14. 统一验收标准

- group 会话内可创建一个编排 run 和多个子任务
- 主 Agent 先输出计划，再进入子任务执行
- 同一 session 内支持多个 task 并行 stream
- 每个 task 可独立进入待确认态
- 每个 task 可独立确认或取消
- 所有 task 结束后，主 Agent 输出最终汇总
- 刷新页面后，状态可恢复
- 单聊不回归
- 本期设计没有把系统写死为“双子任务”

## 15. 后续拆分建议

建议后续按以下七个独立 task 文档拆分：

1. `M1 编排模型`
2. `M2 任务规划与派发`
3. `M3 子任务执行与多 Stream`
4. `M4 Task 级 Pending Change 确认`
5. `M5 Run 汇总与完成判定`
6. `M6 前端最小群聊执行视图`
7. `M7 测试与联调收口`

每个子 task 继续沿用本文档中的：

- 目标
- 后端实施任务
- 前端实施任务
- 测试
- 验收标准

