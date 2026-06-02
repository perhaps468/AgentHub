# Task: P5-1 用户自建 Agent 落地为统一 Agent 实体，并接入现有 Agent 管理单页

## 0. 文档定位

- 本文档基于 [openspec/specs/implementation-phases.md](/D:/code/ZiJieAI/AgentHub/openspec/specs/implementation-phases.md) 中的 `Phase5-1`，但严格采用本轮已确认方案，不再按原始 spec 引入独立 `AgentTemplate` / `Profile` 实体。
- 本文档复用 [openspec/specs/roadmap.md](/D:/code/ZiJieAI/AgentHub/openspec/specs/roadmap.md) 对 `Phase5` 的边界定义：本阶段目标是让平台从“仅支持内置 Agent”升级为“支持用户自建 Agent 的统一 Runtime 平台”。
- 本文档只拆 `P5-1` 的可执行任务，不扩展到 `P5-2`。
- 本文档吸收并固化以下已确认决策：
  - 内置 Agent 使用数据库统一管理，通过迁移脚本预置，使用 `is_builtin=true` 标记。
  - `Agent` 本身就是 `Profile`，不引入独立 `Profile` 实体。
  - `P5-1` 不实现 `Agent Template`，留到 `P5-2`。
  - `P5-1` 仅预留 `tool_permissions` 字段，不做运行时校验。
  - Agent 管理界面沿用现有单页，扩展 `AddAgentDialog` 字段：`System Prompt`、`模型`、`角色`。
  - `capability_tags` 与 `tool_permissions` 使用 JSON 字段存储。

## 1. 任务目标

- 将当前后端“内置 Agent 注册表 + `/api/agents/default`”的静态实现，收敛为数据库中的统一 `Agent` 实体。
- 让系统内置 Agent 与用户自建 Agent 共享同一套存储、查询、展示和运行入口。
- 让前端当前“本地 mock Agent 列表 + 本地添加弹窗”的实现升级为真实的 Agent 管理页面，并接入后端 API。
- 为 `Phase5-2` 预留 `tool_permissions`、`runtime factory`、`store/share` 所需的最小模型边界，但不提前实现权限校验或模板体系。

## 2. 当前范围

- 后端 `Agent` 数据模型、Schema、迁移脚本与内置数据预置。
- Agent 列表 / 创建 / 更新 / 详情接口。
- 现有默认 Agent 获取逻辑迁移到数据库查询。
- Runtime / WebSocket 默认 Agent 选择逻辑切到数据库 Agent。
- 前端 Agent store、API 模块、Agent 列表面板、`AddAgentDialog`、与现有单页接线。
- 自动化测试、联调约束与验收标准。

## 3. 不做什么

- 不实现独立 `Profile` 表。
- 不实现 `AgentTemplate`、模板派生、模板市场。
- 不实现 `tool_permissions` 的运行时校验、授权弹窗或权限隔离闭环。
- 不实现 Agent 分享、Store、公开市场、导入导出。
- 不实现复杂头像上传、富文本 Prompt 编辑器、版本管理。
- 不重做 Agent 管理页面结构，只在现有单页和弹窗上扩展。

## 4. 依赖与前置条件

- 当前后端已有静态内置 Agent 注册表与默认 Agent 接口：
  - [backend/app/agents/registry.py](/D:/code/ZiJieAI/AgentHub/backend/app/agents/registry.py)
  - [backend/app/api/agents.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/agents.py)
- 当前前端已有 Agent 管理入口，但数据仍是页面内 mock：
  - [frontend/src/components/zhu.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu.vue)
  - [frontend/src/components/zhu/AddAgentDialog.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu/AddAgentDialog.vue)
  - [frontend/src/components/zhu/AgentListPanel.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu/AgentListPanel.vue)
  - [frontend/src/store/module/useAgentStore.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/store/module/useAgentStore.ts)
- 当前数据层还没有 `Agent` 表；`session/message/workspace` 已按 `owner_id` 建立用户边界，可复用同样原则。
- 本阶段数据库变更需要显式迁移方案，且必须包含“预置内置 Agent”的落库步骤。

## 5. 需要改动的模块、数据模型、接口或配置

### 后端

- 新增数据模型：
  - `backend/app/models/agent.py`
- 更新模型导出：
  - [backend/app/models/__init__.py](/D:/code/ZiJieAI/AgentHub/backend/app/models/__init__.py)
- 新增 Schema：
  - `backend/app/schemas/agent.py`
- 更新 API：
  - [backend/app/api/agents.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/agents.py)
- 更新默认 Agent 解析逻辑：
  - [backend/app/agents/registry.py](/D:/code/ZiJieAI/AgentHub/backend/app/agents/registry.py)
  - [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py)
  - 如有必要，同步 `runtime_agent_service` 的 Agent 构建入口
- 新增迁移或初始化脚本：
  - 例如 `backend/sql/p5_1_agents.sql` 或等价迁移文件

### 前端

- API 模块：
  - [frontend/src/api/modules/agents.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/api/modules/agents.ts)
- 类型：
  - [frontend/src/types/agenthub.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/types/agenthub.ts)
- Store：
  - [frontend/src/store/module/useAgentStore.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/store/module/useAgentStore.ts)
- 页面与组件：
  - [frontend/src/components/zhu.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu.vue)
  - [frontend/src/components/zhu/AddAgentDialog.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu/AddAgentDialog.vue)
  - [frontend/src/components/zhu/AgentListPanel.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu/AgentListPanel.vue)
  - 视情况补充 Agent 编辑弹窗或沿用同一弹窗支持编辑

### 测试

- 新增或修改后端测试：
  - `backend/tests/api/test_agents_api.py`
  - `backend/tests/test_agents.py`
  - 与默认 Agent / WS 行为相关测试
- 新增或修改前端测试：
  - `frontend/src/store/module/useAgentStore.spec.ts`
  - `frontend/src/components/zhu.spec.ts`
  - 如需拆分，新增 `frontend/src/components/zhu/AddAgentDialog.spec.ts`

## 6. 统一契约

### 6.1 Agent 持久化模型

`Agent` 作为 `P5-1` 唯一 Agent/Profile 实体，建议至少包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | Agent ID |
| `owner_id` | string \| null | 是 | 所属用户；内置 Agent 可为 `null` |
| `name` | string | 是 | 展示名称 |
| `role` | string | 是 | Agent 角色，如 `PM` / `Coder` |
| `model` | string | 是 | 模型标识 |
| `system_prompt` | string | 是 | System Prompt |
| `platform` | string | 是 | `claude-code` / `codex` / `opencode` / `custom` |
| `description` | string \| null | 否 | 简介 |
| `avatar_url` | string \| null | 否 | 头像地址 |
| `capability_tags` | JSON array[string] | 是 | 能力标签 |
| `tool_permissions` | JSON array[string] | 是 | 工具权限占位字段 |
| `is_builtin` | boolean | 是 | 是否内置 Agent |
| `is_active` | boolean | 是 | 是否可用 |
| `created_at` | datetime | 是 | 创建时间 |
| `updated_at` | datetime | 是 | 更新时间 |

约束：

1. `owner_id is null && is_builtin=true` 表示系统内置 Agent。
2. `owner_id=<current_user_id> && is_builtin=false` 表示用户自建 Agent。
3. `tool_permissions` 在本阶段只做存储与回传，不参与执行校验。
4. `capability_tags`、`tool_permissions` 必须保证接口层返回数组，不允许前端自己解析逗号字符串。
5. `system_prompt` 是 `P5-1` 的核心配置字段，不允许继续只存在前端本地状态。

### 6.2 Agent 列表查询契约

`GET /api/agents`

认证：

- 需要当前登录用户。

查询参数：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `include_builtin` | boolean | 否 | 默认 `true` |
| `include_inactive` | boolean | 否 | 默认 `false` |

响应 `items[*]` 最小字段：

```json
{
  "id": "pm-agent",
  "owner_id": null,
  "name": "PM Agent",
  "role": "PM",
  "model": "qwen-plus",
  "platform": "custom",
  "description": "内置产品经理 Agent",
  "avatar_url": null,
  "capability_tags": ["需求分析", "方案设计"],
  "tool_permissions": [],
  "system_prompt": "You are ...",
  "is_builtin": true,
  "is_active": true,
  "created_at": "2026-06-02T10:00:00Z",
  "updated_at": "2026-06-02T10:00:00Z"
}
```

规则：

1. 返回结果默认包含“当前用户自建 Agent + 全局内置 Agent”。
2. 用户不能看到其他用户的自建 Agent。
3. 前端 Agent 列表页使用该接口作为唯一真相源，不再在页面中内置 mock 列表。

### 6.3 Agent 创建契约

`POST /api/agents`

请求体：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | Agent 名称 |
| `role` | string | 是 | Agent 角色 |
| `model` | string | 是 | 模型名 |
| `system_prompt` | string | 是 | System Prompt |
| `platform` | string | 是 | 本阶段自建 Agent 默认 `custom` |
| `description` | string \| null | 否 | 简介 |
| `avatar_url` | string \| null | 否 | 头像 |
| `capability_tags` | string[] | 是 | 能力标签 |
| `tool_permissions` | string[] | 否 | 默认 `[]` |

响应：

- 返回完整 `AgentResponse`。

错误：

| 错误码 | 触发条件 |
|------|------|
| `400` | 字段缺失、标签格式非法、空名称、空 Prompt |
| `403` | 非法伪造 `is_builtin` 或 `owner_id` |
| `409` | 当前用户下名称冲突，若本阶段要求唯一 |

规则：

1. 后端必须忽略或拒绝客户端传入的 `is_builtin=true`。
2. 创建时 `owner_id` 强制绑定当前用户。
3. `tool_permissions` 未传时回填 `[]`。

### 6.4 Agent 更新契约

`PATCH /api/agents/{agent_id}`

规则：

1. 用户只能更新自己的自建 Agent。
2. 内置 Agent 在 `P5-1` 默认只读；若需要展示编辑入口，前端必须禁用保存。
3. 允许更新字段：
   - `name`
   - `role`
   - `model`
   - `system_prompt`
   - `description`
   - `avatar_url`
   - `capability_tags`
   - `tool_permissions`
   - `is_active`

错误：

| 错误码 | 触发条件 |
|------|------|
| `404` | Agent 不存在 |
| `403` | Agent 不属于当前用户，或尝试修改内置 Agent |

### 6.5 默认 Agent 契约调整

`GET /api/agents/default`

规则：

1. 不再从内存注册表返回，而是从数据库内置 Agent 中解析默认值。
2. 若未来需要支持“用户默认 Agent”，接口保持兼容空间；但 `P5-1` 仍可先固定返回内置 PM Agent。
3. WebSocket / Runtime 默认 Agent 选择逻辑必须与该接口一致，避免前台看到的默认 Agent 与运行实际 Agent 不一致。

## 7. Task 拆分

### P5-1-1 建立统一 Agent 数据模型与内置 Agent 预置机制

**任务目标**

将内置 Agent 从静态注册表迁移为数据库记录，并建立用户自建 Agent 与内置 Agent 共用的数据模型。

**当前范围**

- 新增 `Agent` ORM 模型
- 新增 schema / response model
- 新增数据库迁移或初始化脚本
- 预置内置 PM Agent

**不做什么**

- 不实现独立 `Profile` 表
- 不实现 Template
- 不做权限校验闭环

**详细实现步骤**

1. 新增 `backend/app/models/agent.py`。
2. 定义 JSON 字段 `capability_tags`、`tool_permissions`。
3. 约定内置 Agent 数据以迁移脚本落库，不再仅在 Python 模块中硬编码。
4. 迁移脚本至少写入当前默认 PM Agent 的一条记录。
5. 明确内置 Agent 的稳定 ID，避免测试和运行时随机生成。
6. 如当前项目仍依赖 `create_all()`，需补充本地开发库迁移策略，保证新增表和预置数据可重复初始化。

**测试方案**

- 模型测试：
  - `Agent` 表字段齐全
  - JSON 字段默认值正确
  - `is_builtin` / `owner_id` 组合符合约束
- 迁移测试：
  - 初始化后存在预置 PM Agent
  - 重复初始化不会插入重复内置 Agent

**验收标准**

- 代码库中不再只有“内存态内置 Agent”这一条主链路。
- 内置 Agent 与用户 Agent 可被同一张表表示。
- `system_prompt/model/role/capability_tags/tool_permissions` 已成为持久化字段。

### P5-1-2 提供 Agent 管理 API，并替换默认 Agent 读取链路

**任务目标**

为前端管理页提供真实 Agent API，并把默认 Agent 与运行入口切到数据库查询。

**当前范围**

- `GET /api/agents`
- `POST /api/agents`
- `PATCH /api/agents/{agent_id}`
- `GET /api/agents/{agent_id}`（如前端编辑需要）
- `GET /api/agents/default` 改造
- 默认 Agent 运行链路改造

**不做什么**

- 不支持删除接口，除非现有 UI 已明确需要
- 不支持用户级默认 Agent 配置切换
- 不开放内置 Agent 编辑

**详细实现步骤**

1. 在 [backend/app/api/agents.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/agents.py) 中扩展 CRUD 风格接口。
2. 列表查询按当前用户过滤自建 Agent，同时合并系统内置 Agent。
3. `GET /api/agents/default` 从数据库读取默认 PM Agent。
4. 将 [backend/app/agents/registry.py](/D:/code/ZiJieAI/AgentHub/backend/app/agents/registry.py) 从“主真相源”降为兼容层或直接移除。
5. 审查 [backend/app/api/ws.py](/D:/code/ZiJieAI/AgentHub/backend/app/api/ws.py) 等运行入口，确保默认 Agent 解析使用数据库实体。
6. 统一响应字段命名，避免前端继续维护 `display_dict` 与新模型双轨。

**测试方案**

- API 测试：
  - 列表接口能返回内置 + 当前用户自建
  - 创建接口能落库并回传完整数据
  - 更新接口不能修改别人的 Agent
  - 内置 Agent 不能被普通更新接口修改
- 默认 Agent 测试：
  - `/api/agents/default` 返回数据库 PM Agent
  - WS/Runtime 链路使用同一默认 Agent

**验收标准**

- Agent 管理 API 已能支撑前端真实展示与创建。
- 默认 Agent 不再依赖静态注册表。
- 后端不存在“接口读数据库、运行时读内存注册表”的双真相源分叉。

### P5-1-3 前端 Agent Store 与列表页切换到真实数据源

**任务目标**

移除 `zhu.vue` 中的本地 Agent mock 列表，让 Agent 面板从真实 API 加载与刷新。

**当前范围**

- `useAgentStore`
- `agents.ts`
- `zhu.vue`
- `AgentListPanel.vue`

**不做什么**

- 不重做整页布局
- 不做分页、筛选条件持久化

**详细实现步骤**

1. 扩展 [frontend/src/api/modules/agents.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/api/modules/agents.ts)，增加列表、创建、更新接口。
2. 将 [frontend/src/store/module/useAgentStore.ts](/D:/code/ZiJieAI/AgentHub/frontend/src/store/module/useAgentStore.ts) 从“单个默认 Agent store”升级为“默认 Agent + Agent 列表 store”。
3. 将 [frontend/src/components/zhu.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu.vue) 中的 `sidebarAgents` mock 数据移除。
4. 由 Agent store 驱动 `AgentListPanel` 展示与搜索。
5. 区分内置 Agent 与自建 Agent 的展示态，至少支持：
   - 内置 Agent 标识
   - 自建 Agent 标识
6. 保持现有会话选择、Agent 选择流程可用，不在本阶段重做“按 Agent 创建会话”的整体逻辑。

**测试方案**

- store 测试：
  - 拉取列表成功后状态正确
  - 创建成功后列表追加或重新拉取
- 组件测试：
  - Agent 面板展示真实接口返回
  - 搜索基于 store 列表工作
  - 无数据时展示空态

**验收标准**

- 页面中不再硬编码 Agent 列表。
- Agent 面板刷新后仍能恢复真实 Agent 数据。
- 内置 Agent 与自建 Agent 均可在单页中展示。

### P5-1-4 扩展 AddAgentDialog，完成创建/编辑表单闭环

**任务目标**

将当前只支持 `名称 + 标签 + 简介` 的本地弹窗，升级为可创建真实自建 Agent 的表单。

**当前范围**

- [frontend/src/components/zhu/AddAgentDialog.vue](/D:/code/ZiJieAI/AgentHub/frontend/src/components/zhu/AddAgentDialog.vue)
- `zhu.vue` 对话框提交逻辑
- 必要的类型与表单校验

**不做什么**

- 不做高级 Prompt 编辑器
- 不做模板选择器
- 不做工具权限选择器，仅可隐藏传空数组或保留只读占位

**详细实现步骤**

1. 扩展 `AddAgentDialog` 字段：
   - `name`
   - `role`
   - `model`
   - `system_prompt`
   - `capability_tags`
   - `description`
2. 前端对 `capability_tags` 可继续提供逗号输入，但提交前必须转换为字符串数组。
3. 保存时调用真实 `POST /api/agents`，而不是本地 `push`。
4. 如本阶段顺手支持编辑，则复用同一弹窗承载“新建/编辑”两种模式。
5. 内置 Agent 若进入编辑态，前端需显式禁用保存或隐藏编辑入口。

**测试方案**

- 表单测试：
  - 必填字段校验生效
  - 标签字符串能转换为数组
  - 提交成功后关闭弹窗并刷新列表
- 组件联调测试：
  - 新建 Agent 后立刻出现在 Agent 列表
  - 创建失败时能提示，不污染本地列表

**验收标准**

- “添加自建 Agent” 已从本地 UI 动作升级为真实后端创建。
- `System Prompt`、`模型`、`角色` 已进入创建主链路。
- 前端不再生成假 ID 或仅本地存在的自建 Agent。

### P5-1-5 完成前后端统一验证与阶段验收

**任务目标**

确保 `P5-1` 结束后，平台已具备真实的自建 Agent 基础闭环，而不是停留在 UI 假数据层。

**联调要求**

1. 初始化后，`GET /api/agents` 能看到内置 PM Agent。
2. 打开 Agent 面板时，列表来自后端接口。
3. 通过 `AddAgentDialog` 创建自建 Agent，刷新页面后仍可看到。
4. 创建的自建 Agent 含 `name/role/model/system_prompt/capability_tags` 完整配置。
5. `GET /api/agents/default` 与运行时默认 Agent 一致。
6. 用户 A 无法看到用户 B 创建的 Agent。
7. `tool_permissions` 即使未生效，也已稳定出现在模型与接口中。

**测试方案**

- 后端：
  - Agent 模型测试
  - 迁移/预置测试
  - Agent API 权限测试
  - 默认 Agent 一致性测试
- 前端：
  - Agent store 测试
  - AddAgentDialog 表单测试
  - 单页 Agent 面板联调测试

**验收标准**

- 系统已支持“数据库内置 Agent + 用户自建 Agent”共存。
- Agent 已成为统一配置实体，即本阶段的 Profile 载体。
- 现有 Agent 管理单页已完成最小真实化，不再依赖页面内 mock 数据。
- `P5-2` 可以在此基础上继续做 `tool_permissions` 校验、runtime factory、store/share，而无需推翻 `P5-1` 的数据模型。

## 8. 统一测试方案

- 模型 / 迁移层：
  - `Agent` 表创建
  - 内置 Agent 预置
  - JSON 字段默认值
- API 层：
  - 列表、详情、创建、更新
  - 用户隔离
  - 内置 Agent 只读约束
- Runtime 集成层：
  - 默认 Agent 查询与运行入口一致
- 前端 store 层：
  - 拉取 Agent 列表
  - 创建后刷新状态
- 前端组件层：
  - Agent 列表展示
  - AddAgentDialog 创建闭环

建议验证命令：

- `python -m pytest backend/tests/test_agents.py`
- `python -m pytest backend/tests/api/test_agents_api.py`
- 相关 WS/Runtime 测试文件
- 前端现有 vitest 命令下与 Agent store / Agent dialog / zhu 页面相关测试

## 9. 统一验收标准

- `Agent` 已成为数据库中的一等实体，而不是前端 mock 或后端静态注册表。
- 内置 Agent 与自建 Agent 使用同一模型与同一查询入口。
- `Agent = Profile` 的决策已落到代码边界，不存在并行的独立 Profile 设计。
- `AddAgentDialog` 已支持 `System Prompt`、`模型`、`角色` 字段并接真实创建接口。
- `capability_tags` 与 `tool_permissions` 已按 JSON 数组持久化与回传。
- `tool_permissions` 仅作为占位字段存在，未提前扩展到运行时校验。
- `P5-1` 不包含 Template，但不会阻塞 `P5-2` 在现有模型上继续演进。

## 10. 依赖或阻塞

- 若当前运行时强依赖 [backend/app/agents/registry.py](/D:/code/ZiJieAI/AgentHub/backend/app/agents/registry.py) 的 Python 对象结构，需要明确是“兼容保留一层适配”还是“直接切换为数据库实体转运行时配置”，避免过渡期双实现漂移。
- 若当前前端会话创建流程依赖硬编码 `sidebarAgents` 的若干平台字段，需要在切换真实数据前明确最小兼容字段集合。
- 若当前项目数据库初始化方式未统一，需先确定 `Agent` 表与内置数据的初始化落地方式，否则 `P5-1` 会停留在接口设计层。

## 11. 下一步

- 本 task 文档完成后，下一步进入 `task-review-from-spec`。
