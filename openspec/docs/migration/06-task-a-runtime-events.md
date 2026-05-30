# Task A - P2 Runtime 事件观测与回放收口

> 本任务直接来源于 [06-p2-p3-acceptance-closure.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/06-p2-p3-acceptance-closure.md) 中的 `Task A`。
>
> 本任务只收口 P2 的最后一个关键缺口：`Runtime 事件可以被消息流观察和回放`。

---

## 1. 任务目标

把当前 Runtime 内部已经存在的运行时事件，正式接入 AgentHub 的消息流主链路，使其满足以下要求：

- runtime 关键过程可被前端观察
- runtime 关键过程可被最小回放
- 工具调用过程不再只是内部实现细节
- 不破坏现有 `message_start / message_delta / message_end / message_error` 协议兼容性

本任务完成后，应能直接支持 `implementation-phases.md` 中 P2 的前置条件：

- Runtime 事件可以被消息流观察和回放

---

## 2. 当前范围

本任务只覆盖以下内容：

- runtime 事件协议定义
- runtime 事件从后端到 WS 主链路的转发
- 前端对 runtime 事件的最小消费
- runtime 关键事件的最小回放模型

本任务不覆盖：

- workspace 正式建模
- diff / command 生命周期收口
- preview 主链路
- self-repair 状态机
- Artifact 独立存储

---

## 3. 当前现状

当前仓库已经具备以下基础：

- `EventBridge` 已能产出 `tool_event`
- `RuntimeAgentService` 已能向事件队列输出 `tool_event`
- `ws.py` 已经能消费标准 `message_*` 事件
- 前端已经有流式消息状态管理，能处理 `message_*` 事件

当前缺口在于：

- `tool_event` 仍未成为 WS 正式协议的一部分
- runtime 非文本事件没有统一前端状态模型
- 过程事件没有最小回放方案

因此目前只能证明“文本回复流成立”，还不能证明“runtime 过程可观察、可回放”。

---

## 4. 本任务不做什么

- 不重新设计整套聊天协议
- 不引入新的 Artifact schema
- 不在本任务中实现 terminal 事件全量体系
- 不在本任务中实现 preview 渲染
- 不在本任务中改造 workspace/session 数据模型
- 不在本任务中做多 Agent 事件总线

---

## 5. 依赖与前置条件

本任务默认以下条件已成立：

- `RuntimeAgentService` 已能工作
- `EventBridge` 已有 `tool_event` 能力
- `ws.py` 已有 runtime path feature flag
- 前端现有消息流状态机可继续扩展

依赖文档：

- `openspec/specs/implementation-phases.md`
- `openspec/docs/migration/02-implementation-guide.md`
- `openspec/docs/migration/06-p2-p3-acceptance-closure.md`

---

## 6. 涉及模块与文件

后端核心：

- `backend/app/runtime/event_bridge.py`
- `backend/app/runtime/runtime_agent_service.py`
- `backend/app/api/ws.py`

前端核心：

- `frontend/src/utils/ws-client.ts`
- `frontend/src/utils/useChatStreamState.ts`
- `frontend/src/types/agenthub.ts`
- 必要时补充对应渲染层组件或 store

测试核心：

- `backend/tests/runtime/test_event_bridge_tool_events.py`
- `backend/tests/runtime/test_runtime_agent_service.py`
- `backend/tests/api/test_ws_runtime_agent.py`
- `frontend/src/utils/useChatStreamState.spec.ts`

---

## 7. 接口契约

本任务涉及 WS runtime 事件扩展协议。

### 7.1 设计要求

- 保持现有 `message_*` 协议不变
- runtime 过程事件采用新增事件类型
- 新事件必须可被旧前端忽略，不导致连接失败

### 7.2 首批正式事件

建议首批只定义以下事件：

- `tool_event`
- `runtime_state`

其中：

- `tool_event` 用于表达工具开始与结束
- `runtime_state` 用于表达任务处于哪一个运行阶段

### 7.3 `tool_event` 契约

字段建议：

- `type`
  - 类型：`string`
  - 固定值：`tool_event`
- `stream_id`
  - 类型：`string`
  - 必填
- `message_id`
  - 类型：`string`
  - 必填
- `tool_name`
  - 类型：`string`
  - 必填
- `status`
  - 类型：`string`
  - 枚举：`started` / `finished`
- `arguments`
  - 类型：`object`
  - 必填
- `response`
  - 类型：`string | null`
  - `started` 时可为空
- `timestamp`
  - 类型：`string`
  - ISO8601

### 7.4 `runtime_state` 契约

字段建议：

- `type`
  - 类型：`string`
  - 固定值：`runtime_state`
- `stream_id`
  - 类型：`string`
  - 必填
- `message_id`
  - 类型：`string`
  - 必填
- `state`
  - 类型：`string`
  - 枚举建议：`thinking` / `calling_tool` / `observing` / `responding` / `finished` / `error`
- `timestamp`
  - 类型：`string`
  - ISO8601

### 7.5 错误处理要求

- 未识别 runtime 扩展事件时，前端必须忽略，不得中断主消息流
- 后端扩展事件发送失败时，不得破坏 `message_*` 主链路

---

## 8. 详细实现步骤

### Step 1：定义 runtime 扩展事件协议

- 明确 `tool_event` 与 `runtime_state` 的字段结构
- 在 shared / frontend types 中同步协议定义
- 明确它们与 `message_*` 的关系

输出要求：

- 类型定义统一
- 命名稳定
- 旧路径兼容

### Step 2：补齐后端事件桥接

- 在 `EventBridge` 中梳理 runtime 内部事件到正式扩展事件的映射
- 必要时补齐 `runtime_state` 产出
- 保证 `tool_event` / `runtime_state` 都能进入 `RuntimeAgentService` 队列

输出要求：

- runtime 内部事件不再只停留在内部 emitter 层

### Step 3：补齐 WS 主链路转发

- 在 `ws.py` 中显式处理 `tool_event`
- 如有 `runtime_state`，同步处理
- 保持原有 `message_*` 流程不回退

输出要求：

- runtime 扩展事件正式进入 WS 协议层

### Step 4：补齐前端最小消费能力

- 在 ws client 与流状态管理中识别新增 runtime 事件
- 建立最小 runtime event state
- 确保前端至少能展示或保留关键运行节点

输出要求：

- 事件不丢失
- 事件不打断主文本流

### Step 5：实现最小回放

- 明确什么叫“最小回放”
- 至少支持同一轮 stream 的关键过程节点被重新构建
- 可以通过 message metadata、event list 或受控临时存储承载

输出要求：

- 工具开始/结束与关键状态切换可被重建

### Step 6：主链路回归

- 回归现有 `message_*` 协议测试
- 回归 runtime path 测试
- 回归前端流式状态测试

---

## 9. 测试方案

### 9.1 后端单元测试

至少新增或补齐：

- `EventBridge` 对 `tool_event` / `runtime_state` 的映射测试
- `RuntimeAgentService` 对扩展事件的输出测试

重点断言：

- 事件结构稳定
- 事件顺序可预期
- 不影响 `message_end` 与错误路径

### 9.2 WS 集成测试

至少覆盖：

- runtime path 下能收到 `tool_event`
- runtime path 下能收到 `runtime_state`
- 扩展事件与 `message_*` 可共存

重点断言：

- 协议兼容
- 连接不断

### 9.3 前端状态测试

至少覆盖：

- 新事件被正确识别
- 流状态中可保留 runtime 过程信息
- 未识别事件可安全忽略

### 9.4 回放测试

至少覆盖：

- 给定一组 runtime 事件，可以恢复最小过程视图
- 文本消息最终态与过程态不会冲突

### 9.5 回归测试

必须回归：

- 现有 `message_delta` 处理测试
- runtime 文本回复路径测试
- 错误路径测试

---

## 10. 验收条件

本任务完成后，必须同时满足以下条件：

- runtime 扩展事件已正式进入 WS 主链路
- 工具调用过程可被前端观察
- 同一轮任务的关键运行节点可被最小回放
- 现有 `message_start / message_delta / message_end / message_error` 主链路未被破坏
- 可以据此证明 P2 的“Runtime 事件可以被消息流观察和回放”成立

---

## 11. 回滚点与风险

### 11.1 回滚点

- 通过 feature flag 或分支开关关闭 runtime 扩展事件输出
- 保留纯 `message_*` 流程可独立工作

### 11.2 主要风险

- 前端类型与后端协议不一致
- 事件过多导致状态机复杂化
- 回放方案做得过重，提前演化成完整事件溯源系统

### 11.3 风险控制策略

- 首批只做 `tool_event` 与 `runtime_state`
- 回放只做最小闭环，不做全量历史恢复
- 所有新增协议先补测试，再接主链路

---

## 12. 完成后下一步

本任务完成后，下一步应进入：

- `Task B：P3 Workspace 与文件边界收口`

如果继续细拆本任务，建议拆为：

- `Task A-1：Runtime 事件协议定义与 WS 转发`
- `Task A-2：前端 runtime 事件消费与最小回放`

