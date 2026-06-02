# Task: P6 基础群聊模式落地任务

## 0. 文档定位

- 本文档用于承接进入 P6 前的“最基础群聊模式”实施任务。
- 本次目标不是实现完整多 Agent 自动协作，而是在现有 IM 基础上补齐群聊所需的最小后端模型、接口契约和前端展示能力。
- 本文档采用“固定主 Agent + 用户可选其他 Agent”的方案，作为后续多 Agent 调度、`@Agent`、成员健康探测和动态编排的基础。
- 本文档只覆盖任务拆解，不直接进入实现。

## 1. 背景

当前系统已具备以下基础能力：

- 单用户会话模型
- 会话列表与消息历史
- WebSocket 消息链路
- Agent 列表与自建 Agent 管理

当前 `group` 模式仅存在于会话枚举层，尚未形成真正可运行的群聊模型，主要缺口包括：

- 没有真实的会话成员关系模型
- 没有“主 Agent”机制
- 群聊创建只停留在前端选择，后端没有完整接住
- 群聊会话列表与会话头部展示规则尚未定型
- Agent 健康状态没有展示位

本次 P6 基础群聊模式的核心目标是：

1. 系统始终存在一个固定主 Agent
2. 新建群聊时该主 Agent 自动加入且不可取消
3. 用户只选择其他参与 Agent
4. 群聊列表通过小标签标识，不单独分区
5. 群聊头部展示群成员与健康状态
6. 第一阶段群聊消息默认仅由主 Agent 响应

## 2. 方案检查与扩展性结论

结论：该方案利于后续扩展，适合作为 P6 起点。

原因如下：

- 采用“会话 + 成员 + 主 Agent”建模，后续可以自然扩展到 `@Agent`、动态加人、主 Agent 切换、多真人成员。
- “固定主 Agent”解决了早期多 Agent 抢答和调度混乱问题，同时为后续引入真实调度器保留了稳定入口。
- 前端不把群聊当成特殊列表分区，只作为会话的一种模式，避免未来 UI 规则继续分裂。
- “健康状态”先做占位字段，未来可以无缝接入真实 runtime / heartbeat 结果。

必须遵守的约束：

- 主 Agent 规则必须以后端为准，不能只写在前端。
- 群聊成员必须持久化存储，不能靠前端临时拼装。
- 第一阶段只允许主 Agent 默认响应，避免过早引入复杂编排。

## 3. 范围

### 本次要做

- 固定主 Agent 建模与初始化
- 群聊成员关系表
- 群聊创建接口扩展
- 群聊详情返回成员信息
- 群聊消息默认路由到主 Agent
- 前端群聊创建弹窗改造
- 前端会话列表增加群聊标签
- 前端会话头部展示群成员与健康状态

### 本次不做

- 不实现多 Agent 自动并发回复
- 不实现 `@Agent`
- 不实现主 Agent 切换
- 不实现动态添加/移除群成员
- 不实现真实健康探活
- 不实现多真人同时加入同一会话
- 不实现群聊专属消息类型

## 4. 统一产品规则

### 4.1 固定主 Agent

- 系统中新增一个始终存在的 builtin 主 Agent
- 建议固定 ID：`primary_pm_agent`
- 其职责是：
  - 理解用户目标
  - 拆解任务
  - 指派和协调其他 Agent
  - 汇总中间结果
  - 输出最终答复

### 4.2 群聊创建规则

- 当用户选择 `group` 模式时：
  - 主 Agent 自动加入
  - 主 Agent 不可取消
  - 用户只能额外勾选其他参与 Agent
- 最终群成员 = `主 Agent + 用户选择的其他 Agent`
- 即使用户不选择其他 Agent，也允许创建仅包含主 Agent 的群聊

### 4.3 群聊响应规则

- 第一阶段群聊消息只触发主 Agent 响应
- 其他 Agent 只作为成员展示存在
- 后续如需扩展多 Agent 发言，仍基于本次成员关系继续演进

### 4.4 前端展示规则

- 群聊在会话列表中不单独分区
- 群聊仅通过一个小标签标识
- 会话头部原有“已连接”展示改为“成员状态”
- 健康状态第一阶段统一展示为 `已连接`

## 5. 后端实施任务

### P6-1 固定主 Agent 初始化

**目标**

在后端建立一个始终存在的 builtin 主 Agent，并明确其提示词职责。

**实施内容**

1. 在 Agent 初始化或 seed 逻辑中新增固定主 Agent。
2. 使用稳定 ID，例如 `primary_pm_agent`。
3. 配置明确的 system prompt，强调任务理解、指派、协调和汇总职责。
4. 确保重复初始化不会产生重复主 Agent。
5. 明确该 Agent 对前端可见，并可在 Agent 列表中展示。

**涉及模块**

- `backend/app/models/agent.py`
- `backend/app/agents/seed.py`
- `backend/app/api/agents.py`
- 相关 SQL / migration 文件

### P6-2 群聊成员关系建模

**目标**

为群聊提供真实成员模型，避免群聊只停留在 `mode=group` 枚举层。

**实施内容**

1. 新增 `session_members` 表。
2. 建议字段：
   - `id`
   - `session_id`
   - `member_type`
   - `member_id`
   - `is_primary`
   - `health_status`
   - `created_at`
3. 为 `session_id + member_type + member_id` 建立唯一约束。
4. 为“一个会话只能有一个主 Agent”提供约束或服务层校验。
5. 第一阶段 `health_status` 默认写为 `connected`。

**涉及模块**

- `backend/app/models/`
- `backend/app/schemas/`
- `backend/sql/` 或 migration 文件

### P6-3 创建群聊接口扩展

**目标**

让后端真正接住“固定主 Agent + 额外参与 Agent”的群聊创建逻辑。

**实施内容**

1. 扩展 `POST /api/sessions` 请求体，支持 `participant_agent_ids`。
2. 当 `mode=group` 时：
   - 自动加入固定主 Agent
   - 将 `participant_agent_ids` 作为附加 Agent 成员写入
   - 自动去重，防止主 Agent 重复加入
3. 校验附加 Agent 是否存在、是否对当前用户可见。
4. 允许仅主 Agent 的群聊创建成功。
5. 单聊逻辑保持兼容，不产生回归。

**接口约束**

建议请求体示例：

```json
{
  "title": "多Agent协作",
  "mode": "group",
  "workspace_id": "workspace_xxx",
  "participant_agent_ids": ["coder_agent", "reviewer_agent"]
}
```

### P6-4 会话详情返回成员信息

**目标**

让前端可直接展示群成员与成员状态，而不是本地推断。

**实施内容**

1. 扩展 `GET /api/sessions/{session_id}`。
2. 返回群成员列表，建议每个成员至少包含：
   - `member_type`
   - `member_id`
   - `display_name`
   - `is_primary`
   - `health_status`
3. 可选补充：
   - `role`
   - `avatar_url`
4. 会话列表接口可保持轻量，不强制返回完整成员明细。

**建议返回结构**

```json
{
  "id": "session_xxx",
  "mode": "group",
  "title": "多Agent协作",
  "members": [
    {
      "member_type": "agent",
      "member_id": "primary_pm_agent",
      "display_name": "主Agent",
      "is_primary": true,
      "health_status": "connected"
    },
    {
      "member_type": "agent",
      "member_id": "coder_agent",
      "display_name": "Coder",
      "is_primary": false,
      "health_status": "connected"
    }
  ]
}
```

### P6-5 群聊消息默认路由到主 Agent

**目标**

在不引入复杂编排的前提下，形成可运行的最小群聊消息闭环。

**实施内容**

1. WebSocket 收到群聊消息后，从会话成员关系中解析主 Agent。
2. 默认只触发主 Agent 响应。
3. 其他 Agent 暂不自动发言。
4. 保持单聊消息链路不变。
5. 主 Agent 的解析以后端真实成员关系为准，不接受前端指定。

**涉及模块**

- `backend/app/api/ws.py`
- `backend/app/services/`
- `backend/app/runtime/`

### P6-6 成员健康状态占位支持

**目标**

为后续真实 runtime 健康状态接入预留模型与接口位置。

**实施内容**

1. 在成员返回结构中加入 `health_status`。
2. 第一阶段默认返回 `connected`。
3. 预留后续接入真实探活的位置，不在本次实现真实检查。

## 6. 前端实施任务

### P6-7 群聊创建弹窗改造

**目标**

让群聊创建交互明确区分“固定主 Agent”和“用户可选其他 Agent”。

**实施内容**

1. 修改群聊创建弹窗。
2. 群聊模式下新增“主 Agent”固定展示区。
3. 主 Agent 默认选中且不可取消。
4. 参与 Agent 多选列表中排除主 Agent。
5. 提交时只传 `participant_agent_ids`，不传主 Agent。
6. 若用户未选其他 Agent，也允许提交创建。

**涉及模块**

- `frontend/src/components/zhu/NewConversationDialog.vue`
- `frontend/src/types/agenthub.ts`
- `frontend/src/api/modules/session.ts`

### P6-8 会话列表展示调整

**目标**

让群聊在列表中只作为会话类型展示，不形成新的分区规则。

**实施内容**

1. 移除群聊单独分区或排到最后的规则。
2. 单聊与群聊统一排序：
   - 先按 `is_pinned`
   - 再按 `updated_at desc`
3. 在群聊会话标题旁增加小标签，如 `群聊`。
4. 不增加额外视觉层级，保持列表简洁。

**涉及模块**

- `frontend/src/components/zhu/MessageListPanel.vue`
- `frontend/src/store/module/useSessionStore.ts`

### P6-9 会话头部成员状态展示

**目标**

用“成员状态”取代当前群聊场景下的简单连接文案。

**实施内容**

1. 调整会话头部组件。
2. 群聊场景展示：
   - 主 Agent
   - 其他参与 Agent
   - 对应健康状态
3. 主 Agent 需要有明显标识，如 `主Agent` 或 `Primary`。
4. 第一阶段健康状态统一展示为：
   - 绿点 + `已连接`
   - 或 `connected`
5. 单聊场景保持兼容，不破坏现有体验。

**涉及模块**

- `frontend/src/components/zhu/ChatHeader.vue`
- `frontend/src/components/zhu/ChatWorkspace.vue`

### P6-10 前端会话详情与成员数据接线

**目标**

确保前端成员展示完全依赖后端返回，而不是靠本地推断。

**实施内容**

1. 扩展会话详情类型定义。
2. 在 session store 中缓存群成员信息。
3. 创建群聊成功后拉取并展示真实成员数据。
4. 刷新页面后仍能恢复群成员显示。
5. 前端不得自行硬编码“谁是主 Agent”，仅展示后端确认结果。

**涉及模块**

- `frontend/src/types/agenthub.ts`
- `frontend/src/store/module/useSessionStore.ts`
- `frontend/src/components/zhu.vue`

## 7. 测试任务

### 7.1 后端测试

1. 固定主 Agent 初始化成功。
2. 重复初始化不会产生重复主 Agent。
3. 创建群聊时自动加入主 Agent。
4. 前端重复传入主 Agent 时不会重复落库。
5. 非法 `participant_agent_ids` 创建群聊时报错。
6. 仅主 Agent 的群聊可成功创建。
7. 会话详情能正确返回成员列表。
8. 群聊消息默认仅由主 Agent 响应。
9. 单聊接口与消息流无回归。

### 7.2 前端测试

1. 群聊创建弹窗默认展示固定主 Agent。
2. 主 Agent 不可取消。
3. 参与 Agent 列表不包含主 Agent。
4. 群聊会话列表展示 `群聊` 标签。
5. 群聊不再单独分区。
6. 群聊会话头部正确展示成员与默认健康状态。
7. 单聊 UI 未受影响。

### 7.3 联调测试

1. 创建仅主 Agent 的群聊成功。
2. 创建“主 Agent + 多参与 Agent”的群聊成功。
3. 群聊详情页可展示完整成员。
4. 群聊发消息后 WebSocket 正常返回主 Agent 回复。
5. 刷新页面后群成员信息仍可恢复。

## 8. 验收标准

### 8.1 数据与规则

- 系统中存在一个固定 builtin 主 Agent。
- 新建群聊时主 Agent 总会自动加入。
- 主 Agent 不可被前端取消，也不会被重复加入。
- 群聊成员关系由后端真实存储，不依赖前端拼接。

### 8.2 前端表现

- 群聊创建界面能清晰区分“固定主 Agent”和“其他参与 Agent”。
- 会话列表中群聊仅通过小标签标识，不单独分区。
- 群聊头部可展示所有 Agent 成员及健康状态。
- 第一阶段健康状态可统一显示为 `已连接`。

### 8.3 消息行为

- 群聊发送消息后，默认仅主 Agent 响应。
- 单聊行为保持不变。
- WebSocket 链路稳定，无明显回归。

### 8.4 可扩展性

当前方案落地后，应能支持后续继续扩展：

- `@Agent`
- 多 Agent 调度
- 动态成员管理
- 主 Agent 切换
- 真实健康探测
- 多真人成员

## 9. 建议实施顺序

1. 固定主 Agent seed
2. `session_members` 表与模型
3. 群聊创建接口扩展
4. 会话详情成员返回
5. 群聊消息路由到主 Agent
6. 前端创建弹窗改造
7. 前端会话列表群聊标签改造
8. 前端会话头部成员状态展示
9. 联调与回归测试
