# Task: P6 M1+M2 编排模型与任务规划派发

## 0. 文档定位

- 本文档对应 [p6-orchestrated-group-chat-minimal-chain-plan.md](/D:/code/ZiJieAI/AgentHub/openspec/changes/IM/p6-orchestrated-group-chat-minimal-chain-plan.md) 中的 `M1 编排模型` 和 `M2 任务规划与派发`。
- 本文档只覆盖：
  - 编排 run / task 数据模型
  - group 会话中的主 Agent 计划输出
  - 后端规则生成 task 并完成派发入库
  - 前端计划展示与 run/task 基础读取
- 本文档不覆盖：
  - 多 task 并行执行
  - 多 stream 展示
  - task 级 pending change 确认
  - run 汇总

## 1. 背景

当前项目已经具备以下基础能力：

- group session 成员落库与主 Agent 绑定
- group session 消息默认路由到主 Agent
- workspace 与 session 绑定
- runtime 消息流式输出
- pending change 确认链路

但目前缺少一个独立的“编排域模型”来表示：

- 一次用户复合请求对应的编排 run
- run 下拆解出的多个子任务
- 主 Agent 的计划消息与子任务的显式关联

如果没有这一层，后续的并行执行、task 级确认、最终汇总都会被迫混在 session/message 语义里，导致模型混乱且难以测试。

因此，`M1 + M2` 的目标不是实现完整多 Agent 协作，而是先把“主 Agent 规划一次任务，并把任务拆解为可追踪的 run + tasks”这层基础设施建立起来。

## 2. 目标

实现一条最小闭环：

1. 用户在 group 会话发送复合任务请求
2. 系统创建一个 orchestration run
3. 主 Agent 输出计划消息
4. 后端根据规则拆出 `N` 个 orchestration task
5. 前端可查询并展示该 run 及其 task 列表

本阶段的“规划”含义是：

- 主 Agent 会输出计划说明文本，供用户理解
- 但 task 结构第一版不依赖 LLM 解析
- task 由后端规则拆分并入库

## 3. 本期范围

### 本期要做

- 新增 orchestration run / task 模型
- 新增 run/task 查询接口
- group 消息入口接入“编排模式”
- 主 Agent 计划消息落库
- 后端规则拆解 task 并入库
- 前端读取并展示计划消息与 task 列表

### 本期不做

- 不做 task 并行执行
- 不做 task 状态推进到 `running` 之后的复杂流转
- 不做多 stream UI
- 不做 pending change 与 task 绑定
- 不做最终汇总消息

## 4. 后端实施任务

### 4.1 数据模型

新增 `orchestration_runs`：

- `id`
- `session_id`
- `trigger_message_id`
- `planner_agent_id`
- `status`
  - 第一版至少支持：`planned | running | failed | cancelled`
- `summary`
- `created_at`
- `updated_at`

新增 `orchestration_tasks`：

- `id`
- `run_id`
- `parent_task_id` 可空，预留后续扩展
- `sequence`
- `assigned_agent_id`
- `kind`
  - 第一版固定支持 `file_write`
- `title`
- `goal`
- `input_payload`
- `result_payload` 可空
- `error_payload` 可空
- `status`
  - 第一版至少支持：`planned`
- `created_at`
- `updated_at`

要求：

- run 与 session 建立明确关联
- task 与 run 建立明确关联
- 支持 `1 -> N` task，不允许写死为双任务
- `sequence` 保证前端可稳定排序

### 4.2 Schema 与服务层

新增 schema：

- `OrchestrationTaskResponse`
- `OrchestrationRunResponse`
- `LatestRunResponse` 或等价结构

新增服务层能力：

- 创建 run
- 批量创建 tasks
- 查询 run + tasks
- 获取 session 最近一个 run

### 4.3 API 接口

新增查询接口：

- `GET /api/orchestration/runs/{run_id}`
- `GET /api/sessions/{session_id}/runs/latest`

要求：

- 返回完整 run 信息
- 同时返回其 tasks
- 仅允许会话 owner 访问

### 4.4 Group 消息入口接入

在 group 会话消息入口增加编排模式分支：

- 接收到用户消息后
- 先创建 human message
- 再创建 orchestration run
- 再生成主 Agent 计划消息
- 最后按规则拆出 tasks 并入库

注意：

- 第一版不要求从计划消息文本反解析 task
- task 结构由后端规则直接生成
- 计划消息仅用于用户展示

### 4.5 规则拆分器

新增一个最小 task planner / splitter：

- 输入：
  - 用户原始请求
  - session/workspace 信息
  - group 成员 agent 列表
- 输出：
  - task 列表

第一版要求：

- 能覆盖“多个文件创建请求”的规则拆分
- 每个 task 至少包含：
  - `title`
  - `assigned_agent_id`
  - `goal`
  - `input_payload`

可以接受的第一版限制：

- 先做规则匹配，不做通用自然语言规划器
- agent 分配可按固定规则进行

### 4.6 主 Agent 计划消息

主 Agent 计划消息需要：

- 正常落为 message
- 标记 metadata：
  - `run_id`
  - `is_orchestration_plan: true`

内容建议至少包含：

- 总目标
- task 列表摘要
- 分配方案

但该文本只负责展示，不承载后续系统真实状态来源。

## 5. 前端实施任务

### 5.1 类型定义

在 `frontend/src/types/agenthub.ts` 新增：

- `OrchestrationRun`
- `OrchestrationTask`

字段应与后端 response 对齐。

### 5.2 API 模块

新增编排查询 API：

- 获取单个 run
- 获取 session 最近一个 run

### 5.3 Store 接入

在 `useSessionStore` 或等价 store 中新增：

- `activeRun`
- `activeTasks`
- `fetchLatestRun(sessionId)`
- `fetchRun(runId)`

要求：

- 切换会话时可拉取最新 run
- 刷新会话详情后可恢复 run/task 基础信息

### 5.4 计划展示

前端聊天区支持识别并展示主 Agent 计划消息：

- 根据 `metadata.is_orchestration_plan` 渲染
- 显示 run 基本信息
- 显示 task 列表摘要

第一版可接受：

- 复用现有消息卡样式
- 不强制新增复杂任务面板

### 5.5 Task 列表展示

在计划消息附近或会话辅助区域展示 task 列表：

- `sequence`
- `title`
- `assigned_agent_id` 或展示名
- `status`

第一版状态只要求能展示 `planned`。

## 6. 测试

### 6.1 后端测试

模型与服务层：

1. 创建 run 成功
2. 在一个 run 下创建多个 task 成功
3. `sequence` 保持稳定顺序
4. `parent_task_id` 为空时不影响主流程

API：

1. `GET /api/orchestration/runs/{run_id}` 返回完整 run + tasks
2. `GET /api/sessions/{session_id}/runs/latest` 返回最近 run
3. 非 owner 访问被拒绝

编排入口：

1. group 消息触发后成功创建 run
2. 主 Agent 计划消息落库成功
3. 后端按规则生成 `N` 个 tasks
4. 当前阶段不会直接创建 pending change

### 6.2 前端测试

类型与 API：

1. run/task 类型与后端 response 对齐
2. API 查询结果可正确解析

Store：

1. `fetchLatestRun` 成功缓存 run/task
2. 切换 session 后状态正确更新

UI：

1. 计划消息可识别并渲染
2. task 列表可正常显示
3. 当没有 run 时，界面保持兼容

## 7. 验收标准

### 7.1 数据与接口

- 数据库中可创建一个 orchestration run 和多个 orchestration task
- run 与 session、task 与 run 的关系明确且可查询
- 查询接口能返回完整 run + tasks
- 设计没有写死成“双任务”

### 7.2 行为

- group 会话收到复合请求后，会创建一个 run
- 主 Agent 会先输出计划消息
- 后端会基于规则生成 `N` 个 tasks 并入库
- 当前阶段不会直接进入文件写入或 pending change

### 7.3 前端表现

- 当前会话可读取最近一个 run
- 聊天区能识别主 Agent 计划消息
- 可展示该 run 下的 task 列表及 `planned` 状态
- 页面刷新后，run/task 基础信息可恢复

### 7.4 兼容性

- 单聊链路不回归
- 普通 group 会话无编排时不报错
- 现有消息历史与 session 详情接口保持兼容

## 8. 后续衔接

本任务完成后，后续任务可以在此基础上继续推进：

1. `M3` 子任务执行与多 Stream
2. `M4` Task 级 Pending Change 确认
3. `M5` Run 汇总与完成判定

本任务的交付重点是把“规划结果”从临时文本提升为“可追踪的 run/task 结构化状态”。

