# Task: P6 M7 测试与联调收口

## 0. 文档定位

- 本文档对应 [p6-orchestrated-group-chat-minimal-chain-plan.md](/D:/code/ZiJieAI/AgentHub/openspec/changes/IM/p6-orchestrated-group-chat-minimal-chain-plan.md) 中的 `M7 测试与联调收口`。
- 本文档只覆盖：
  - `M1 ~ M6` 相关能力的测试补齐
  - 最小群聊协作链路的联调验证
  - 后续扩展 `N` 子任务编排的回归基线建设
- 本文档不覆盖：
  - 新的业务能力设计
  - 超出本期范围的多用户协作、DAG 调度、自由多 Agent 对话
  - 新的产品交互方案

## 1. 背景

到 `M6` 为止，系统已经分别具备：

- run/task 结构化建模
- 主 Agent 计划消息
- 多 task 并行执行与多 stream
- task-aware pending change 确认
- run 汇总与完成判定
- 前端最小执行视图与刷新恢复

但这些能力如果只是分散存在于不同模块而缺少统一测试与联调收口，风险仍然很高：

- 某个字段改动可能悄悄打断 run/task/pending change/summary 之间的契约
- 前端可能分别通过单测，但在真实 websocket + REST 混合链路下出现状态错位
- 当前最小场景只验证 2 个 task，如果没有专门的回归基线，后续扩展到 `N > 2` 容易退化为写死双子任务
- 单聊兼容性和旧会话兼容性容易在后续重构中被破坏

因此，`M7` 的目标不是再引入新功能，而是把这条“主 Agent 规划 + 多子任务执行 + 独立确认 + 自动汇总 + 可恢复 UI”的最小闭环固化为可重复运行、可持续回归的工程基线。

## 2. 目标

建立一套覆盖 `M1 ~ M6` 的测试与联调基线：

1. 后端关键模型、状态机、服务与接口具备可重复的自动化测试。
2. 前端关键状态管理、消息渲染、确认交互与恢复链路具备自动化测试。
3. 存在一条稳定的联调脚本或联调步骤，覆盖最小场景完整闭环。
4. 最小场景跑通后，能够证明架构没有写死为 2 个子任务。
5. 单聊与非编排 group 会话兼容性被纳入回归范围。

本阶段的核心原则是：

- 测试优先覆盖状态边界、恢复场景和跨模块契约，而不是只测 happy path。
- 联调验收必须以真实链路为准，不能只靠单元测试代替。
- 结论以验证结果为准，宣称完成前必须先验证。

## 3. 本期范围

### 本期要做

- 补齐后端模型、状态机、服务、API 测试
- 补齐前端 store、stream、确认卡、汇总消息、恢复测试
- 建立最小场景联调步骤
- 明确 `N > 2` 的验证样例
- 纳入单聊与非编排 group 兼容回归

### 本期不做

- 不新增新的 orchestration 能力
- 不做新的 UI 方案探索
- 不做复杂性能压测体系
- 不做跨用户并发协作测试

## 4. 后端实施任务

### 4.1 补齐模型与状态机测试

围绕 `orchestration_runs`、`orchestration_tasks`、`pending_changes` 补齐：

- run 创建与查询
- task 批量创建与排序
- task 状态推进
- run 状态聚合
- pending change 与 run/task/agent 归属关系

重点覆盖：

- `planned -> running -> waiting_confirmation -> completed/rejected/cancelled/failed`
- run 的 `completed / partial / failed / cancelled`
- 重复 apply/reject 的幂等行为

### 4.2 补齐 Orchestration Service 测试

为 orchestration 相关 service 或 executor 补齐：

- group 消息触发 run 创建
- 主 Agent 计划消息落库
- task 规则拆分
- 多 task 启动执行
- task-aware pending change 生成
- run 聚合器生成汇总消息

要求：

- 尽量覆盖跨服务状态传递，而不是只测单个函数
- 关键断言以数据库状态和事件契约为主

### 4.3 补齐 API 与恢复测试

补齐至少以下接口的测试：

- `GET /api/orchestration/runs/{run_id}`
- `GET /api/sessions/{session_id}/runs/latest`
- `GET /api/sessions/{session_id}/active-run` 或等价恢复接口
- `GET /api/pending-changes?session_id=...`
- `GET /api/pending-changes/{change_id}`
- `POST /api/pending-changes/apply`
- `POST /api/pending-changes/reject`

重点覆盖：

- owner 权限校验
- 无 active run / 无 pending change 的稳定返回
- task-aware 字段完整性
- apply/reject 后 task 与 run 的联动更新

### 4.4 增加 `N > 2` 场景验证

在后端测试中明确加入：

- 至少 3 个 task 的拆分与执行
- 至少 3 个 task 的状态聚合
- 混合结果下 run 的稳定判定

要求：

- 明确证明架构未写死为双子任务
- 避免只用 2 个 task 的 happy path 得出错误结论

## 5. 前端实施任务

### 5.1 补齐 Store 与状态恢复测试

围绕 `useSessionStore`、`useChatStreamState` 或等价状态层补齐：

- active run 恢复
- active tasks 恢复
- 多 stream 并存
- task-aware pending change 恢复
- run 总状态恢复

重点覆盖：

- 页面刷新后恢复
- 重新进入会话恢复
- 晚到 websocket 事件与 REST 恢复的竞态

### 5.2 补齐渲染与交互测试

补齐：

- 主 Agent 计划消息渲染
- 多子任务执行流渲染
- 多确认卡独立交互
- 汇总消息渲染
- `ChatHeader` 或任务面板状态显示

重点覆盖：

- 多条 stream 不互相覆盖
- 多张确认卡不互相干扰
- apply/reject 只更新对应 task
- 汇总消息与 run 状态显示一致

### 5.3 补齐兼容性测试

补齐：

- 单聊会话不回归
- 非编排 group 会话不显示异常 UI
- 历史消息缺少 orchestration metadata 时的兼容渲染
- 老 pending change 数据缺少 task-aware 字段时的兼容处理

## 6. 测试方案

### 6.1 后端自动化测试方案

1. 创建 group session 与必要 agent/workspace 绑定。
2. 发送复合请求，生成 run + `N` tasks。
3. 校验主 Agent 计划消息落库。
4. 启动多 task 并行执行。
5. 生成多个 task-aware pending changes。
6. 分别执行 apply/reject，校验 task 状态推进。
7. 校验 run 状态自动聚合。
8. 校验汇总消息只生成一次。

### 6.2 前端自动化测试方案

1. 渲染存在 active run 的 group 会话。
2. 校验计划消息与任务面板显示。
3. 注入多个 task stream 事件，校验并存渲染。
4. 注入多个确认卡，分别执行 apply/reject。
5. 注入汇总消息，校验 run 状态与消息显示一致。
6. 模拟刷新或重新进入会话，校验状态恢复。
7. 运行单聊与非编排 group 会话兼容回归。

### 6.3 联调验收链路

1. 用户在 group 会话发送复合任务请求。
2. 主 Agent 输出计划消息。
3. 至少 2 个子 Agent 同时进入 `thinking...`。
4. 两个 task 各自产生确认卡。
5. 用户分别确认或取消不同 task。
6. task 状态与 run 状态实时更新。
7. 主 Agent 输出最终汇总消息。
8. 刷新页面后，run/task/pending change/summary 状态可恢复。

### 6.4 扩展性验证链路

1. 构造一个可拆成 3 个以上文件任务的复合请求。
2. 验证系统可以生成 `N > 2` 个 task。
3. 验证多个 task 可并行执行并分别进入确认态。
4. 验证混合完成结果下 run 状态判定仍然稳定。

## 7. 验收标准

### 7.1 自动化测试覆盖

- `M1 ~ M6` 的关键状态流转均有自动化测试覆盖
- 后端接口、状态机、聚合器和恢复能力均被验证
- 前端多 stream、多确认卡、汇总消息和恢复能力均被验证

### 7.2 联调闭环

- 最小场景链路完整跑通
- 联调结果与结构化状态一致
- 刷新页面后状态可恢复

### 7.3 架构稳定性

- `N > 2` 时架构不需要推倒重来
- 单聊不回归
- 非编排会话不回归

### 7.4 完成定义

- 文档中定义的测试已实际运行并记录结果
- 在关键验证未通过前，不宣称该链路完成

## 8. 与后续任务的边界

- `M7` 完成后，P6 最小群聊协作链路具备稳定的工程回归基线。
- 后续如果继续扩展 DAG、更多 task 类型或更复杂群聊交互，应在本基线之上增量扩展，而不是绕过已有测试与联调链路。
