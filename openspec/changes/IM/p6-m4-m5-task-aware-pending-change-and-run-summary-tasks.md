# Task: P6 M4+M5 Task 级 Pending Change 确认与 Run 汇总完成判定

## 0. 文档定位

- 本文档对应 [p6-orchestrated-group-chat-minimal-chain-plan.md](/D:/code/ZiJieAI/AgentHub/openspec/changes/IM/p6-orchestrated-group-chat-minimal-chain-plan.md) 中的 `M4 Task 级 Pending Change 确认` 和 `M5 Run 汇总与完成判定`。
- 本文档只覆盖：
  - pending change 从 session-aware 升级为 task-aware
  - 同一 run 下多个 task 的独立确认/取消
  - task 终态驱动的 run 状态聚合
  - 主 Agent 最终汇总消息的系统化生成与展示
- 本文档不覆盖：
  - 多 stream 执行能力本身
  - 群聊执行视图的完整 UI 升级
  - 联调整体收口与回归基线建设

## 1. 背景

`M3` 完成后，系统已经能够在同一个 group session 中并行执行多个 orchestration task，并为每个 task 维护独立的 `stream_id / message_id / runtime state`。但当前“执行完成后的确认与收尾”仍然停留在单条 session 流语义上，存在两个核心缺口：

- 现有 pending change 主要按 `session_id / message_id / stream_id` 关联，缺少 `run_id / task_id / agent_id` 维度，无法稳定表达“哪个子任务生成了哪个确认卡”。
- 现有链路缺少一个稳定的 run 聚合器，不能在多个 task 分别完成、取消或失败后，给出一致且可恢复的最终结论。

如果不补齐这两层，系统就只能做到“多个子任务同时跑”，但做不到：

- 多个确认卡同时出现且互不干扰
- 用户只确认某一个 task，而不误影响其它 task
- 刷新后恢复 task 与 pending change 的精确关联
- 在所有 task 进入终态后，稳定输出一次主 Agent 汇总

因此，`M4 + M5` 的目标是把 `M3` 的并行执行链路补齐成“可确认、可收尾、可恢复”的最小闭环，让系统以 `run -> tasks -> pending changes -> summary` 的结构完成一次复合请求。

## 2. 目标

实现一条最小闭环：

1. 同一 orchestration run 下多个 task 可分别生成 pending change。
2. 每个 pending change 都能明确归属到对应 `run_id / task_id / agent_id`。
3. 用户可分别对不同 task 的变更执行确认或取消。
4. task 状态会随 apply/reject 精确推进到终态。
5. 当所有 task 均进入终态后，系统自动计算 run 最终状态。
6. 系统生成一次主 Agent 汇总消息，并在前端正常展示与恢复。

本阶段的核心原则是：

- 确认动作按 task 精确归属，不做 session 级模糊更新。
- run 汇总基于结构化状态聚合，不依赖 LLM 再次推理。
- 第一版按“一个 task 一个确认批次”建模，避免提前引入复杂批次聚合器。

## 3. 本期范围

### 本期要做

- 为 pending change 增加 task-aware 归属字段
- task 执行产出 pending change 时写入 run/task/agent 关联
- task 状态接入 `waiting_confirmation / completed / rejected / failed / cancelled`
- session 维度恢复接口返回 task-aware pending change 数据
- 前端支持同一会话展示多个待确认卡，并精确更新对应 task
- run 监听 task 终态并聚合为最终 run.status
- 生成主 Agent 汇总消息并落库

### 本期不做

- 不做一个 task 内多个确认批次的复杂聚合交互
- 不做基于 DAG 依赖的部分完成传播
- 不做主 Agent 再次调用 LLM 生成总结
- 不做群聊 UI 的完整重构
- 不做 `M7` 级别的全链路回归收口

## 4. 后端实施任务

### 4.1 扩展 Pending Change 数据模型

在现有 `pending_changes` 基础上新增字段：

- `run_id`
- `task_id`
- `agent_id`
- 可选 `batch_id`

要求：

- `run_id`、`task_id`、`agent_id` 与 orchestration 结构保持一致
- 保持现有 `session_id / message_id / stream_id` 字段兼容，避免影响单聊与已有恢复链路
- 第一版允许 `batch_id` 为空，但数据结构上为后续一个 task 多个 change 预留扩展位

### 4.2 补齐 Pending Change 生成链路

- 在 task runtime 生成 pending change 时，写入：
  - `session_id`
  - `message_id`
  - `stream_id`
  - `run_id`
  - `task_id`
  - `agent_id`
- 保证同一 run 下多个 task 同时生成 change 时，不会发生归属串位。
- 保持现有 change preview / apply tool 主流程可继续复用，避免重写整套文件变更工具。

### 4.3 明确 Task 状态机

在 `M3` 的执行态基础上补齐 task 状态推进：

- `running -> waiting_confirmation`
- `waiting_confirmation -> completed`，当用户 apply 成功
- `waiting_confirmation -> rejected` 或 `cancelled`，当用户 reject
- `running -> failed`，当执行过程中直接失败且未产生可确认变更

要求：

- 一个 task 的确认结果只能更新该 task，不得批量影响同 run 其它 task。
- 状态推进需可幂等，重复 apply/reject 请求要返回稳定结果。
- 失败原因、确认结果等信息要记录进 `result_payload` 或 `error_payload`，供后续汇总使用。

### 4.4 调整 Pending Change 查询与确认接口

复用或扩展现有 pending change API，至少满足：

- 按 `session_id` 查询时返回 task-aware 字段
- 查询单个 change 时返回 task-aware 字段
- apply/reject 后可带回对应 `run_id / task_id / agent_id`

如果需要补充响应结构，字段至少包含：

- `change_id`
- `session_id`
- `run_id`
- `task_id`
- `agent_id`
- `message_id`
- `stream_id`
- `path`
- `operation`
- `status`
- `created_at`
- `applied_at`

apply/reject 的响应与事件要求：

- apply 成功后返回 `status=applied`，并驱动 task 进入 `completed`
- reject 成功后返回 `status=rejected`，并驱动 task 进入 `rejected` 或 `cancelled`
- WebSocket `apply_result` 或等价事件中补齐 `run_id / task_id / agent_id`

### 4.5 新增 Run 聚合器

增加 orchestration run aggregator / finalizer：

- 监听 task 状态变化
- 仅在所有 task 均进入终态时触发最终聚合
- 计算 run.status

第一版聚合规则：

- 全部 `completed` -> `completed`
- 同时存在 `completed` 与 `rejected/cancelled/failed` -> `partial`
- 全部 `rejected/cancelled` -> `cancelled`
- 全部 `failed`，或 `failed` 与 `cancelled/rejected` 且没有 `completed` -> `failed`

要求：

- 聚合逻辑必须幂等，重复触发不会生成多份汇总。
- run.status 的计算不依赖消息文本解析。
- 聚合器应优先基于数据库中 task 终态计算，避免以内存状态作为唯一事实来源。

### 4.6 生成主 Agent 汇总消息

当 run 进入终态后，系统生成一条主 Agent 汇总消息并落库。

汇总消息至少包含：

- run 总状态
- 每个 task 的标题
- 每个 task 的最终结果
- 如适用，已确认/已取消/失败的文件结果摘要

要求：

- 汇总消息作为普通 message 落库，保持现有消息历史兼容
- message metadata 补齐：
  - `run_id`
  - `is_orchestration_summary: true`
- 每个 run 只允许生成一次最终汇总消息

### 4.7 页面恢复所需数据补充

复查并补齐页面刷新后的恢复能力，确保前端能重新拉回：

- active run 及其最终状态
- run 下 tasks 的终态
- 当前 session 下所有未决或已处理的 task-aware pending changes
- 汇总消息及其 metadata

如现有接口不足，可补充最小查询能力，但不要把 `M6` 任务面板的 UI 逻辑耦合进接口设计。

## 5. 前端实施任务

### 5.1 扩展类型与状态结构

在 `frontend/src/types/agenthub.ts` 或等价类型层补齐：

- pending change 的 `run_id / task_id / agent_id / batch_id`
- orchestration task 的 `waiting_confirmation / completed / rejected / cancelled / failed`
- orchestration run 的 `waiting_confirmation / completed / partial / failed / cancelled`

要求：

- 前后端字段命名保持一致
- 保持已有单聊 pending change 结构兼容

### 5.2 Session Store 接入 Task-Aware Pending Change

在 `useSessionStore` 或等价状态层新增或调整：

- `pendingChangesByTask`
- `taskStatusById`
- `runStatusById`
- 恢复 pending change 与 task/run 关联的方法

处理规则：

- 同一 session 下允许同时存在多个待确认卡
- apply/reject 只更新对应 `change_id` 和其关联的 `task_id`
- 不能再以“当前 session 只有一个待确认变更”的假设简化状态

### 5.3 更新确认卡渲染

pending change 卡片至少展示：

- task title
- agent 名称
- target path
- operation
- 当前状态

交互要求：

- 同一 run 下多个待确认卡可同时展示
- 用户点击确认/取消时，按钮 loading、结果提示和卡片状态只影响当前卡片
- 已确认、已取消、已失败的 task 应能在卡片或任务区显示明确结果

### 5.4 处理 Apply/Reject 结果同步

- 处理 REST 响应与 WebSocket `apply_result` 的双通道同步
- 以 `change_id + task_id` 为主键进行精确更新
- 如果页面刷新后先走恢复接口，再收到晚到事件，也不能把其它 task 状态覆盖掉

要求：

- 幂等处理重复事件
- 避免一个 task 的结果把同 run 其它卡片误清理

### 5.5 展示 Run 总状态与汇总消息

前端需要在消息区或最小任务区支持：

- 展示 run 总状态
- 识别并渲染 `metadata.is_orchestration_summary`
- 按不同 run 状态展示不同文案

建议最小文案：

- `全部任务完成`
- `部分任务完成`
- `任务已取消`
- `任务执行失败`

要求：

- 汇总消息显示在正常消息流中，不强依赖额外专用组件
- 页面刷新后能够恢复汇总消息与 run 最终状态

### 5.6 保持单聊与非编排会话兼容

- 单聊 pending change 交互不能因新增字段而报错
- 非 orchestration 的 group 会话不能出现异常空态或错误状态映射
- 老数据缺少 `run_id / task_id / agent_id` 时，前端应降级为兼容展示，而不是直接崩溃

## 6. 测试

### 6.1 后端测试

模型与状态机：

1. 同一 run 下两个 task 可分别创建 pending change，并写入正确的 `run_id / task_id / agent_id`。
2. task 从 `running` 进入 `waiting_confirmation` 的状态推进正确。
3. apply 后 task 进入 `completed`，reject 后 task 进入 `rejected` 或 `cancelled`。
4. 重复 apply/reject 请求返回稳定结果，不破坏已有终态。

接口与事件：

1. `GET /api/pending-changes?session_id=...` 返回 task-aware 字段。
2. `GET /api/pending-changes/{change_id}` 返回 task-aware 字段。
3. `POST /api/pending-changes/apply` 成功后返回正确 status，并带回 task/run 关联。
4. `POST /api/pending-changes/reject` 成功后返回正确 status，并带回 task/run 关联。
5. `apply_result` 或等价事件只更新对应 task，不影响其它 task。

run 聚合：

1. 全部 task `completed` 时，run 进入 `completed`。
2. 部分 `completed`、部分 `rejected/cancelled/failed` 时，run 进入 `partial`。
3. 全部 `rejected/cancelled` 时，run 进入 `cancelled`。
4. 无 `completed` 且全部失败或失败混合取消时，run 进入 `failed`。
5. 汇总消息只生成一次，重复触发聚合不会重复落库。

### 6.2 前端测试

状态恢复：

1. 刷新页面后可恢复多个 task-aware pending change 卡片。
2. 刷新页面后可恢复 task 终态和 run 总状态。
3. 汇总消息可从历史消息中正确识别并展示。

交互与同步：

1. 同一 session 下多个确认卡可同时渲染且互不干扰。
2. 点击一个确认卡的 apply/reject，只更新对应 task 与卡片状态。
3. 晚到的 `apply_result` 事件不会覆盖其它 task 状态。
4. 单个卡片进入 loading 时，不会阻塞其它卡片的操作。

兼容性：

1. 单聊 pending change 卡片仍可正常确认。
2. 非编排会话不显示异常 run 状态。
3. 缺少 orchestration 字段的历史 change 数据可兼容显示。

### 6.3 联调验证

1. 在 group session 中发送一个至少拆成 2 个文件任务的复合请求。
2. 等待两个 task 各自产生 pending change 卡。
3. 对第一个 task 执行 apply，对第二个 task 执行 reject。
4. 验证两个 task 分别进入 `completed` 与 `rejected/cancelled`。
5. 验证 run 自动进入 `partial`。
6. 验证系统生成一条主 Agent 汇总消息，内容与真实 task 终态一致。
7. 刷新页面后，确认卡结果、task 状态、run 状态和汇总消息都能恢复。

## 7. 验收标准

### 7.1 数据与状态

- pending change 已具备明确的 `run_id / task_id / agent_id` 归属
- task 可从执行态稳定推进到待确认态与终态
- run 总状态由 task 终态稳定聚合，不依赖 LLM 再判断

### 7.2 用户行为

- 同一 run 下多个 task 可分别确认或取消
- 一个 task 的确认结果不会影响其它 task
- 用户完成全部确认后，系统一定会输出最终汇总

### 7.3 前端表现

- 同一会话可同时展示多个 task 级确认卡
- apply/reject 结果只更新对应卡片与对应 task
- run 总状态和汇总消息可正常显示
- 页面刷新后，pending change、task 状态、run 状态、汇总消息都可恢复

### 7.4 兼容性

- 单聊 pending change 链路不回归
- 非编排 group 会话不报错
- 当前设计没有写死“一次只允许一个 pending change”
- 当前设计没有把 run 汇总绑定到“双子任务”场景

## 8. 与后续任务的边界

- `M4 + M5` 完成后，系统具备“多 task 并行执行后的独立确认与自动收尾能力”。
- `M6` 再负责把计划、执行、确认、汇总四类状态组织为更清晰的最小群聊执行视图。
- `M7` 再补齐更系统的回归测试、联调收口和验收基线。
