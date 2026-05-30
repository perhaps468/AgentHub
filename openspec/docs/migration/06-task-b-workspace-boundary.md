# Task B - P3 Workspace 与文件边界收口

> 本任务直接来源于 [06-p2-p3-acceptance-closure.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/06-p2-p3-acceptance-closure.md) 中的 `Task B`。
>
> 本任务只收口 P3 的 workspace 主链路缺口：让 Code Agent 的工作区边界从“隐式注入参数”升级为“会话级正式上下文”，并补齐最小前端创建与展示闭环。

---

## 1. 任务目标

把当前依赖 `workspace_root` 注入和环境变量的工程边界，升级为正式的会话级 workspace 主链路，使系统满足以下要求：

- 每个开发型会话都能定位到明确 workspace
- Code Agent 的文件读写、检索、命令执行边界来自正式会话上下文
- 用户边界与 workspace 边界同时成立
- runtime 不再主要依赖隐式全局 `WORKSPACE_ROOT`
- 前端创建开发型会话时有正式 workspace 选择入口
- 会话创建成功后，用户能知道当前会话绑定了哪个 workspace

本任务完成后，应能支撑 `implementation-phases.md` 中 P3 的这部分目标：

- Code Agent 可以在明确 workspace 边界内读取、修改、检索文件

---

## 2. 当前范围

本任务只覆盖以下内容：

- workspace 最小领域模型或等价正式抽象
- session 与 workspace 的绑定关系
- runtime 从 session 正式解析 workspace 上下文
- 文件工具与命令工具统一从正式 workspace 上下文取边界
- 新建会话的最小前端 workspace 选择入口
- 创建会话请求携带 `workspace_id`
- 会话内最小 workspace 展示

本任务不覆盖：

- diff / apply 生命周期收口
- preview 主链路
- self-repair 状态机
- Artifact 独立资源体系
- 多 workspace 编排
- 文件树浏览器
- 复杂 workspace 管理 UI

---

## 3. 当前现状

当前仓库已经具备以下基础：

- `WorkspaceGuard` 已存在
- 读文件、列目录、glob、grep、patch、写文件、命令执行工具都能接受 `workspace_root`
- `RuntimeAgentService` 构建工具时可注入 `workspace_root`
- 文件与命令边界在工程层面已有基本保护
- 前端已经有“新建会话”弹窗

当前缺口在于：

- `ChatSession` 没有正式 `workspace` 绑定
- workspace 还不是明确的后端领域对象
- runtime 对 workspace 的获取仍偏向环境变量或外部注入
- 当前“边界成立”更像工程约束，不是产品主链路约束
- 前端虽然已有新建会话入口，但还没有正式 workspace 选择与传参闭环
- 会话进入后也没有正式 workspace 展示

因此目前只能证明：

- 工具执行时可以被限制在某个 root 下

还不能证明：

- 某个会话天然归属某个 workspace
- 该 workspace 是 owner 边界的一部分
- 用户是在显式选择 workspace 后创建的开发型会话

---

## 4. 本任务不做什么

- 不实现完整 Artifact / Project / Repository 体系
- 不引入多租户 workspace 编排
- 不在本任务中改造 preview 或 terminal 事件流
- 不在本任务中做 diff / apply 产品化
- 不在本任务中做复杂 workspace UI
- 不在本任务中做目录浏览器或文件资源管理器

---

## 5. 依赖与前置条件

本任务默认以下条件已成立：

- 现有 runtime path 可运行
- `WorkspaceGuard` 已能工作
- 文件工具和命令工具已支持 `workspace_root`
- 前端已有新建会话弹窗可扩展

依赖文档：

- `openspec/specs/implementation-phases.md`
- `openspec/docs/migration/02-implementation-guide.md`
- `openspec/docs/migration/06-p2-p3-acceptance-closure.md`

---

## 6. 涉及模块与文件

后端核心：

- `backend/app/models/session.py`
- 新增或补充 workspace 相关模型 / schema / service
- `backend/app/runtime/runtime_agent_service.py`
- `backend/app/runtime/workspace.py`
- `backend/app/runtime/tools/*.py`
- session 创建、查询、序列化接口

前端核心：

- 新建会话弹窗组件
- 会话创建 API 调用模块
- 会话头部或会话详情展示组件
- 前端 session 类型定义
- 如需要，workspace 列表拉取或候选数据源模块

测试核心：

- `backend/tests/runtime/test_workspace.py`
- `backend/tests/runtime/tools/test_workspace_guard.py`
- 新增 session-workspace 绑定测试
- 新增 runtime workspace 解析测试
- 新增前端新建会话 workspace 选择测试
- 新增前端创建会话传参测试

---

## 7. 接口契约

本任务核心是会话级 workspace 绑定契约，以及与之对应的最小前端创建与展示契约。

### 7.1 设计要求

- workspace 必须有正式主身份
- session 必须能明确指向一个 workspace
- runtime 必须通过 session 上下文解析 workspace，而非默认读全局环境变量
- 所有工具边界来源必须一致
- 前端必须有正式创建入口，而不是靠后端默认注入

### 7.2 最小 Workspace 抽象

建议最小字段：

- `id`
  - 类型：`string`
  - 必填
- `owner_id`
  - 类型：`string`
  - 必填
- `root_path`
  - 类型：`string`
  - 必填
- `created_at`
  - 类型：`datetime`
  - 必填

如当前阶段不单独建表，也必须有等价正式对象或持久字段承载以上语义。

### 7.3 Session 与 Workspace 绑定

`ChatSession` 至少要具备以下之一：

- `workspace_id`
- 或能稳定解析到唯一 workspace 的正式字段组合

要求：

- 新建开发型 session 时能绑定 workspace
- 查询 session 时能恢复该绑定
- 无绑定时要有明确失败或 fallback 策略

### 7.4 前端创建入口契约

前端必须提供开发型会话的最小 workspace 选择入口。

最小要求：

- 在现有“新建会话”弹窗中增加 workspace 选择
- 创建开发型会话时，请求体带上 `workspace_id`
- workspace 未选择时，前端要么阻止提交，要么显式展示将使用的默认 workspace

建议字段：

- `workspace_id`
  - 类型：`string`
  - 开发型会话必填
  - 非开发型会话可为空或不传

### 7.5 会话内展示契约

会话创建成功并进入会话后，前端至少要能显示当前绑定 workspace 的最小信息。

最小展示要求：

- workspace 名称或目录标识
- 如需要，可显示简化 root path

目的不是做复杂 UI，而是让用户明确知道：

- 这个会话当前绑定的是哪个 workspace

### 7.6 Runtime 解析契约

`RuntimeAgentService` 必须：

- 接收 `session_id`
- 通过正式 session / workspace 关系解析 `workspace_root`
- 再将解析出的边界注入工具构建流程

不允许继续作为正式方案依赖：

- 仅从 `os.environ["WORKSPACE_ROOT"]` 获取
- 调用方随意传任意 root 而不绑定 session

### 7.7 错误处理要求

至少要明确以下错误场景：

- session 不存在
- session 不属于当前用户
- session 未绑定 workspace
- workspace 不存在
- workspace 不属于当前用户
- workspace root 非法或不可访问
- 前端未选择 workspace 但尝试创建开发型会话
- 前端展示的 workspace 与后端实际绑定不一致

---

## 8. 详细实现步骤

### Step 1：定义最小 workspace 正式模型

- 明确 workspace 作为正式领域对象的最小字段
- 决定当前阶段是新增表、补字段，还是用受控等价模型
- 保证 owner 边界可以在后端校验

输出要求：

- workspace 不再只是字符串路径

### Step 2：建立 session -> workspace 绑定

- 为 session 增加 workspace 绑定字段或等价约束
- 在 session 创建流程中写入绑定
- 在 session 查询流程中返回绑定信息或内部可解析信息

输出要求：

- 某个会话可以稳定定位到唯一 workspace

### Step 3：补齐前端创建入口

- 在现有新建会话弹窗中增加 workspace 选择
- 创建开发型会话时把 `workspace_id` 传给后端
- 明确未选择时的前端阻止或默认策略

输出要求：

- workspace 绑定有真实用户入口

### Step 4：改造 runtime workspace 解析链路

- 在 `RuntimeAgentService` 中优先从 session 正式解析 workspace
- 保留必要兼容 fallback，但不能把 fallback 当正式主链路
- 日志与错误输出要能区分“未绑定”“越权”“路径非法”

输出要求：

- runtime 不再主要依赖环境变量驱动 workspace

### Step 5：统一工具边界来源

- 所有文件工具与命令工具统一使用正式解析出的 workspace root
- 清理各工具对隐式 root 的分散依赖
- 保证 guard、tool、runtime 三层使用一致的边界来源

输出要求：

- 同一会话下所有工具共享同一正式 workspace 上下文

### Step 6：补会话内最小展示

- 在会话头部或等价区域显示当前 workspace
- 确保展示数据来自后端正式绑定结果，而不是前端本地猜测

输出要求：

- 用户进入会话后能知道当前工作目录归属

### Step 7：补 owner / workspace 联合校验

- session owner 和 workspace owner 要同时被校验
- 避免“用户有 session，但误指向其他人的 workspace”这类越权路径

输出要求：

- 用户边界与 workspace 边界一起成立

### Step 8：主链路回归

- 回归现有 workspace guard 测试
- 回归 runtime 工具构建测试
- 回归 session 主链路
- 回归前端新建会话与会话头部展示链路

---

## 9. 测试方案

### 9.1 模型与绑定测试

至少新增或补齐：

- session 与 workspace 成功绑定测试
- 无 workspace 绑定的错误测试
- workspace owner 不匹配测试

重点断言：

- 绑定关系稳定
- 越权不可通过

### 9.2 前端入口测试

至少覆盖：

- 新建会话弹窗能选择 workspace
- 创建开发型会话时会携带 `workspace_id`
- 未选择 workspace 时按预期阻止或回退
- 会话进入后能展示当前 workspace

### 9.3 runtime 解析测试

至少覆盖：

- `RuntimeAgentService` 能从 session 解析 workspace
- 缺少绑定时能明确失败
- fallback 存在时不会覆盖正式绑定

### 9.4 工具注入测试

至少覆盖：

- 读文件工具使用正式 workspace root
- 写文件 / patch 工具使用正式 workspace root
- `RunCommandTool` 使用正式 workspace root

### 9.5 安全与边界测试

至少覆盖：

- workspace 不属于当前用户时拒绝
- 路径穿越仍被 guard 拦截
- 非法 root path 被拒绝

### 9.6 回归测试

必须回归：

- `WorkspaceGuard` 现有测试
- 文件工具现有测试
- runtime service 现有测试
- 新建会话与会话展示前端测试

---

## 10. 验收条件

本任务完成后，必须同时满足以下条件：

- 每个开发型会话都能定位到明确 workspace
- 新建开发型会话时，前端存在正式 workspace 选择入口
- 创建会话请求会正式传递 `workspace_id`
- 进入会话后，用户能看到当前绑定 workspace 的最小信息
- runtime 从正式会话上下文解析 workspace，而不是主要依赖环境变量
- 文件读写、检索、命令执行边界统一来自该 workspace
- 用户边界与 workspace 边界同时成立
- 可以据此证明 P3 的“明确 workspace 边界”成立

---

## 11. 回滚点与风险

### 11.1 回滚点

- 保留现有注入式 `workspace_root` 作为短期兼容 fallback
- session / workspace 正式绑定链路可通过开关回退

### 11.2 主要风险

- session 数据模型改动影响现有 API
- 历史 session 缺少 workspace 信息导致兼容问题
- fallback 逻辑过重，反而继续模糊正式主链路
- 前后端字段命名不一致导致绑定失败
- 前端只做选择 UI，但未形成真实落库闭环

### 11.3 风险控制策略

- 先建立最小正式模型，不做完整 project 体系
- 历史 session 明确迁移策略或兼容策略
- 所有工具统一边界来源，避免多套 root 解析逻辑并存
- 前端展示数据必须来自后端正式响应

---

## 12. 完成后下一步

本任务完成后，下一步应进入：

- `Task C：P3 Diff / Command / Message Flow 收口`

如果继续细拆本任务，建议拆为：

- `Task B-1：workspace 模型与 session 绑定`
- `Task B-2：前端新建会话 workspace 选择与展示接线`
- `Task B-3：runtime / tools 正式 workspace 上下文接线`

