# Task B+C-1 - 会话工作区绑定与前端入口

> 本文整合原 `Task B` 中的工作区绑定主链路，以及原 `Task C` 的前置依赖部分。
>
> 目标不是先做完整 Code Agent，而是先把“所有会话强制绑定工作区”这条主链路打通，并让前端、会话模型、runtime、工具边界全部对齐。

---

## 1. 文档目标与范围

### 1.1 目标

实现以下最小闭环：

- 所有新建会话时必须选择一个文件夹作为工作区
- 前端创建会话时把工作区正式传给后端
- 会话创建成功后，聊天界面顶部能看到当前工作区
- 后端 runtime 与文件/命令工具统一使用当前会话绑定的工作区

### 1.2 本文覆盖内容

- workspace 数据模型或等价持久结构
- session 与 workspace 的正式绑定
- 前端新建会话时的文件夹选择
- 会话头部工作区展示
- runtime 与工具边界统一接线

### 1.3 本文不覆盖内容

- diff 展示细节
- 确认落盘交互细节
- HelloWorld.java 代码生成逻辑
- preview 主链路
- self-repair 状态机

---

## 2. 需求背景与当前约束

### 2.1 产品约束

已确认的规则如下：

- 所有会话都强制绑定工作区
- 前端直接选择本地文件夹路径
- 后端接收路径后创建或绑定 workspace
- 聊天界面顶部要显示当前工作区

### 2.2 当前代码现状

基于当前仓库，已经存在以下基础：

- 前端新建会话弹窗已经存在
- 该弹窗中已经出现了工作区选择相关代码雏形
- `ChatHeader` 已有工作区 badge 的展示雏形
- 后端已有 `WorkspaceGuard`
- `RuntimeAgentService` 已具备从正式 session 绑定解析 workspace 的部分实现
- 文件工具、写文件工具、patch 工具、命令工具都支持 `workspace_root`

### 2.3 当前缺口

当前仍缺少正式闭环：

- 所有会话强制工作区的约束没有被彻底收口
- 前端文件夹选择还不是稳定可交付方案
- session / workspace 契约还没有完全在前后端统一
- 会话展示、runtime、工具边界虽然有代码雏形，但还没有形成明确验收链路

---

## 3. 目标流程

### 3.1 新建会话时选择文件夹

用户点击“新建会话”后：

- 必须先选择一个文件夹作为工作区
- 文件夹选择成功后，前端先调用工作区创建或绑定接口
- 得到 `workspace_id` 后再创建 session

### 3.2 后端创建或绑定工作区

后端接收本地目录路径后：

- 校验路径是否合法
- 为当前用户创建或复用一个 workspace 记录
- 返回 `workspace_id`、`root_path`、可展示名称

### 3.3 创建会话并绑定工作区

前端随后调用创建会话接口：

- 请求中必须带 `workspace_id`
- 后端创建 session 时写入该绑定

### 3.4 会话内展示

进入会话后：

- 顶部展示当前工作区名称
- 可选展示完整路径或 hover 展示完整路径

### 3.5 runtime 与工具接线

后端在处理该会话的 runtime 请求时：

- 通过 `session_id -> workspace_id -> workspace.root_path` 解析边界
- 再统一注入读文件、搜索、写文件、patch、命令工具

---

## 4. 后端方案

### 4.1 workspace 数据模型

建议最小字段：

- `id`
- `owner_id`
- `name`
- `root_path`
- `created_at`

若当前已有等价模型，可复用；若没有，则补一个最小持久模型。

### 4.2 session 与 workspace 绑定

`ChatSession` 至少增加：

- `workspace_id`

要求：

- 新建会话必填
- 查询会话时能返回绑定结果
- session owner 与 workspace owner 必须一致

### 4.3 创建会话接口契约调整

创建会话请求至少包含：

- `title`
- `mode`
- `workspace_id`

后端校验：

- `workspace_id` 必填
- `workspace_id` 必须存在
- `workspace_id` 必须属于当前用户

### 4.4 查询会话接口返回工作区信息

会话详情接口建议补充最小 workspace 字段，至少包含：

- `workspace.id`
- `workspace.name`
- `workspace.root_path`

目的是让前端进入会话后无需自己猜测当前目录。

### 4.5 runtime workspace 解析链路

`RuntimeAgentService` 的正式链路应为：

- `session_id`
- 查询 `session.workspace_id`
- 查询 workspace
- 解析 `workspace.root_path`
- 注入工具构建

兼容 fallback 可以保留，但不能作为正式主方案。

### 4.6 文件与命令工具边界统一

以下工具统一使用 session 绑定得到的 workspace：

- `ReadFileTool`
- `ListDirectoryTool`
- `GlobTool`
- `GrepTool`
- `WriteFileTool`
- `ReplaceInFileTool`
- `UnifiedDiffTool`
- `RunCommandTool`

---

## 5. 前端方案

### 5.1 新建会话弹窗增加文件夹选择

直接复用当前新建会话弹窗，要求：

- 文件夹未选择时不能完成创建
- 选择文件夹后先创建或绑定 workspace
- workspace 创建成功后再允许提交

### 5.2 创建会话请求携带 `workspace_id`

前端在 `confirmCreate` 时：

- 必须把 `workspace_id` 放进创建会话请求
- 不允许仅传本地路径，不落后端

### 5.3 会话头部展示当前工作区

在 `ChatHeader` 中：

- 显示工作区文件夹名
- 推荐保留完整路径信息用于 tooltip、副标题或二级展示

推荐最小展示：

- `工作区：AgentHub`
- 完整路径作为悬浮说明或副文本

### 5.4 失败与空状态处理

前端至少要处理：

- 文件夹路径获取失败
- workspace 创建失败
- session 创建失败
- 会话详情缺少 workspace 信息

---

## 6. 实现步骤

### Step 1：后端模型与接口对齐

- 补齐 workspace 最小模型或确认复用方案
- 为 session 增加 `workspace_id`
- 补齐创建会话与查询会话接口契约

### Step 2：前端新建会话接线

- 让弹窗内文件夹选择成为必经步骤
- 选择后调用 workspace 创建接口
- 用返回的 `workspace_id` 再创建 session

### Step 3：会话详情与头部展示接线

- 获取当前 session 的 workspace 信息
- 在 `ChatHeader` 中展示当前工作区

### Step 4：runtime / tools 正式接线

- runtime 从 session 正式解析 workspace
- 工具统一使用解析出的 root

### Step 5：主链路回归

- 回归会话创建
- 回归会话详情展示
- 回归 runtime 与工具工作区边界

---

## 7. 测试方案

### 7.1 后端模型与接口测试

至少覆盖：

- 创建 session 时必须带 `workspace_id`
- `workspace_id` 不存在时报错
- `workspace_id` 不属于当前用户时报错
- 查询 session 时返回 workspace 信息

### 7.2 runtime workspace 解析测试

至少覆盖：

- `RuntimeAgentService` 从 session 绑定解析 workspace
- 未绑定时报错
- owner 不一致时报错

### 7.3 工具边界测试

至少覆盖：

- 文件读取受当前 workspace 限制
- 写文件受当前 workspace 限制
- 命令执行受当前 workspace 限制

### 7.4 前端新建会话测试

至少覆盖：

- 不选文件夹不能创建
- 选择文件夹后先调 workspace 创建接口
- 创建会话时带 `workspace_id`

### 7.5 前端工作区展示测试

至少覆盖：

- 进入会话后显示当前工作区
- 会话缺失 workspace 时有明确降级行为

---

## 8. 验收条件

### 8.1 创建会话必须绑定工作区

- 所有新建会话都必须先选择文件夹
- 后端能拿到 `workspace_id`

### 8.2 聊天界面可见当前工作区

- 进入会话后顶部能看到当前工作区名称

### 8.3 runtime 与工具使用正确工作区边界

- runtime 从 session 获取 workspace
- 工具对文件与命令边界一致生效

---

## 9. 风险与回滚

### 9.1 风险点

- 前端只能选文件夹，但环境取不到绝对路径
- 前后端字段命名不一致
- 历史 session 缺少 workspace 绑定
- fallback 逻辑过重，掩盖正式主链路问题

### 9.2 回滚策略

- 保留 session 绑定前的兼容 fallback 作为短期回退
- 前端工作区展示失败时，不阻断已有只读页面渲染
- 如需回滚，只回滚创建入口强制约束，不回滚 guard 安全边界

---

## 10. 完成后下一步

本文完成后，下一步进入：

- `Task C-2：最小代码生成与确认落盘闭环`

---

## 11. 完成状态

### 11.1 验收条件完成情况

| 验收项 | 状态 | 说明 |
|--------|------|------|
| 创建会话必须绑定工作区 | ✅ 完成 | SessionCreate schema 强制要求 workspace_id |
| 后端校验 workspace 存在性 | ✅ 完成 | create_session API 校验 workspace 存在 |
| 后端校验 workspace 所有权 | ✅ 完成 | create_session API 校验 owner 一致性 |
| 会话详情返回 workspace 信息 | ✅ 完成 | SessionResponse 包含 WorkspaceSummary |
| 聊天界面可见当前工作区 | ✅ 完成 | ChatHeader 展示 workspace badge |
| runtime 从 session 解析 workspace | ✅ 完成 | RuntimeAgentService._resolve_workspace_root |
| 工具使用正确工作区边界 | ✅ 完成 | 工具通过 workspace_root 参数限制 |

### 11.2 实现文件清单

**后端：**
- `backend/app/models/workspace.py` - Workspace 数据模型
- `backend/app/models/session.py` - ChatSession 增加 workspace_id 字段
- `backend/app/schemas/workspace.py` - Workspace CRUD schemas
- `backend/app/schemas/session.py` - Session schemas 含 WorkspaceSummary
- `backend/app/api/workspaces.py` - Workspace API endpoints
- `backend/app/api/sessions.py` - Session API endpoints (含 workspace 校验)
- `backend/app/runtime/runtime_agent_service.py` - runtime workspace 解析

**前端：**
- `frontend/src/components/zhu/NewConversationDialog.vue` - 新建会话弹窗（workspace 选择）
- `frontend/src/components/zhu/ChatHeader.vue` - 会话头部（workspace badge 展示）
- `frontend/src/components/zhu/ChatWorkspace.vue` - 聊天工作区（传递 workspace）
- `frontend/src/components/zhu.vue` - 主容器（workspace 状态管理）
- `frontend/src/api/modules/workspace.ts` - Workspace API 调用
- `frontend/src/types/agenthub.ts` - TypeScript 类型定义

**测试：**
- `backend/tests/runtime/test_session_workspace_binding.py` - Session-Workspace 绑定测试
- `backend/tests/runtime/test_session_workspace_enforcement.py` - Workspace 强制校验测试
- `backend/tests/runtime/test_session_workspace_info.py` - Workspace 信息返回测试
- `backend/tests/runtime/test_workspace_runtime_resolution.py` - Runtime workspace 解析测试

### 11.3 完成日期

2026-05-30

