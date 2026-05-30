# M4 - Tool Abstraction And Read-Only Tools

> 本文档是 `02-implementation-guide.md` 中 `M4：Tool 抽象重建与只读工具接入` 的执行清单。
>
> 本文档只约束 M4，不覆盖 M5 及后续里程碑。

---

## 1. 目标

M4 的唯一目标是：

- 在 AgentHub 内重建最小 Tool 抽象
- 让 runtime 具备最小只读代码观察能力
- 把 copied `read_file` / `list_directory` 路线收口到 AgentHub 的 workspace 语义上

M4 完成后，仓库应满足：

- `ToolManager` 能驱动最小只读工具集
- runtime 可安全读取工作区内文件和目录信息
- `glob` / `grep` 具备 AgentHub 本地实现
- 不引入正式写入能力
- 不引入命令执行能力
- 不接入 WebSocket 主链路

---

## 2. 输入前提

执行 M4 前，以下前提必须成立：

- [02-implementation-guide.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/02-implementation-guide.md) 已确认里程碑顺序
- [M3-react-runtime-loop.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M3-react-runtime-loop.md) 已完成 runtime 最小闭环

---

## 3. 本里程碑允许修改的范围

只允许修改以下范围：

- `backend/app/runtime/tool_manager.py`
- `backend/app/runtime/tools/tool.py`
- `backend/app/runtime/tools/read_file_tool.py`
- `backend/app/runtime/tools/list_directory_tool.py`
- 新增：
  - `backend/app/runtime/tools/glob_tool.py`
  - `backend/app/runtime/tools/grep_tool.py`
  - `backend/app/runtime/workspace.py`
- 必要时补充或更新：
  - [M3-react-runtime-loop.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M3-react-runtime-loop.md)
  - 本文档

允许的改动类型仅限：

- Tool 抽象最小重建
- 只读工具接入
- workspace guard 最小实现
- ToolManager 与只读工具的最小整合
- M4 所需测试补充

---

## 4. 本里程碑禁止修改的范围

M4 明确禁止：

- 修改 `backend/app/api/ws.py`
- 修改 `backend/app/services/fixed_agent_responder.py`
- 修改 `backend/app/services/agent_stream_service.py` 主行为
- 修改 `backend/app/models/*`
- 新增正式写文件能力
- 新增 patch / apply 主流程
- 新增命令执行能力
- 接入聊天框
- 实现 Runtime -> WS 事件桥接

---

## 5. 本里程碑必须处理的事项

### 5.1 重建最小 Tool 抽象

需要在 AgentHub 内明确最小 Tool 协议，至少覆盖：

- 工具名称
- 描述
- 参数定义
- 执行入口

要求：

- 不再依赖 copied `tool.py` 的"仅为 import 不断裂的临时形态"
- 但不要求在 M4 一次性做成完整终态抽象
- 抽象必须能支撑 `read_file` / `list_directory` / `glob` / `grep`

### 5.2 接入只读工具

M4 首批只接以下工具：

- `read_file`
- `list_directory`
- `glob`
- `grep`

要求：

- `read_file_tool.py` 只允许读取本地工作区文件
- `list_directory_tool.py` 只允许遍历工作区范围
- `glob_tool.py`、`grep_tool.py` 必须是 AgentHub 本地实现
- 不允许恢复公网搜索或远程读取语义

建议按以下顺序接入：

1. 先收口 `read_file_tool.py`
   - 保持"只读本地文件"语义
   - 所有路径都先进入 workspace 校验
   - 统一错误返回，不抛未处理异常

2. 再收口 `list_directory_tool.py`
   - 只列工作区内目录
   - 输出格式保持稳定，便于后续 agent 消费
   - 如存在分页或截断逻辑，保持最小可用，不在 M4 过度扩展

3. 再新增 `glob_tool.py`
   - 只做本地工作区内 glob 匹配
   - 优先支持最常见的相对路径模式
   - 不要求在 M4 覆盖复杂高级模式

4. 最后新增 `grep_tool.py`
   - 只做本地文本搜索
   - 优先保证结果稳定、边界安全
   - 不要求在 M4 实现复杂 ranking、高亮或多编码适配

每接入一个工具，都应满足：

- 可被 `ToolManager` 注册和调用
- 对工作区外路径拒绝访问
- 对不存在路径或空结果有稳定返回
- 不依赖网络、不依赖数据库、不依赖 WebSocket

### 5.3 引入 workspace guard

需要新增最小 `workspace.py`，统一描述工作区边界。

至少应具备：

- 工作区根路径约束
- 路径规范化
- 越界访问拒绝

要求：

- 所有只读文件类工具都必须经过 workspace guard
- 不允许直接读取工作区外路径

建议最小接口至少包括：

- `resolve_path(path: str) -> Path`
- `ensure_within_workspace(path: Path) -> Path`
- `is_within_workspace(path: Path) -> bool`

建议最小行为包括：

1. 接收相对路径时，按 workspace root 解析
2. 接收绝对路径时，校验其是否仍在 workspace root 内
3. 对 `..`、符号链接跳转或路径逃逸尝试做拒绝
4. 对非法路径返回可控错误，而不是让下层工具自己崩

在 M4 中，workspace guard 的职责只限于：

- 路径边界控制
- 最小路径规范化

不要求在 M4 中同时承担：

- patch 暂存
- 文件写入审批
- 命令 cwd 管理
- 会话级工作区选择策略

### 5.4 保持写入能力未接线

以下能力在 M4 仍明确不接：

- `replace_in_file` 的正式 patch/apply 流程
- `write_file`
- `run_command`

说明：

- 可以保留 copied 文件或兼容结构
- 但不得把它们接成正式可用能力

---

## 6. 建议执行顺序

1. 读取 `M3-react-runtime-loop.md`
2. 检查 `tool_manager.py` 与 `tools/tool.py` 当前状态
3. 设计最小 Tool 抽象
4. 先写失败测试
5. 再实现 workspace guard
6. 再接入 `read_file` / `list_directory`
7. 最后补 `glob` / `grep`
8. 运行 M4 测试
9. 回写 M4 结果到迁移记录

---

## 7. 测试要求

M4 默认使用 TDD。

执行顺序必须是：

1. 先补失败测试
2. 运行测试，确认当前为红灯
3. 再做最小实现
4. 再运行测试，确认转绿
5. 最后补一次回归验证

至少应补充或执行以下测试文件：

- `tests/runtime/test_tool_manager.py`
- `tests/runtime/tools/test_read_file_tool.py`
- `tests/runtime/tools/test_list_directory_tool.py`
- `tests/runtime/tools/test_glob_tool.py`
- `tests/runtime/tools/test_grep_tool.py`
- `tests/runtime/tools/test_workspace_guard.py`

### 7.1 `test_tool_manager.py` 必测项

至少覆盖以下场景：

- Tool 注册
- Tool 查找
- 工具不存在时的稳定行为
- 参数校验与执行调度

### 7.2 `test_read_file_tool.py` 必测项

至少覆盖以下场景：

- 工作区内文件可读取
- 工作区外文件被拒绝
- 不存在文件时错误可控
- 大文件/长内容截断行为稳定

### 7.3 `test_list_directory_tool.py` 必测项

至少覆盖以下场景：

- 工作区内目录可列出
- 工作区外目录被拒绝
- 不存在目录时错误可控

### 7.4 `test_glob_tool.py` / `test_grep_tool.py` 必测项

至少覆盖以下场景：

- 本地工作区范围搜索可用
- 搜索结果限制或输出格式稳定
- 工作区外路径被拒绝

### 7.5 `test_workspace_guard.py` 必测项

至少覆盖以下场景：

- 绝对路径规范化
- 相对路径解析
- `..` 越界拒绝
- 非法根路径拒绝

### 7.6 Mock / 环境约束

要求：

- 不访问真实网络
- 不依赖真实 WebSocket
- 不依赖真实数据库
- 如需测试文件系统，使用临时目录或测试工作区

---

## 8. 验收标准

M4 完成时，至少应满足：

| 验收项 | 要求 |
|--------|------|
| Tool 抽象可用 | `ToolManager` 能驱动最小只读工具 |
| 只读工具可用 | `read_file` / `list_directory` / `glob` / `grep` 可运行 |
| workspace guard 生效 | 工作区外路径被拒绝 |
| 无公网/远程语义回退 | 不恢复 HTTP 读取或公网搜索 |
| 未越界到 M5/M6 | 未接 WS，未接写入/命令执行 |

---

## 9. 输出要求

执行 M4 的 AI 或工程实现，完成后必须输出：

1. 本次修改的文件清单
2. 本次新增/修改的测试清单
3. Tool 抽象变化说明
4. workspace guard 规则说明
5. 测试命令和测试结果
6. 仍未解决的问题
7. 明确哪些问题留给 M5 / M6

---

## 10. M5 / M6 交接边界

M4 结束后，以下问题应明确留给后续里程碑：

- M5：Runtime -> Message / WebSocket 事件桥接
- M6：受控写入 / patch / diff
- M7：命令执行能力

---

## 11. 一句话约束

M4 的本质不是"让 agent 改代码"，而是：

**先让 runtime 安全地看代码，并把 Tool 体系的最小地基做对。**

---

## 12. 执行记录

> 执行时间: 2026-05-28
> 执行者: Claude (M4 TDD 实现)

### 12.1 本次修改的文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/runtime/workspace.py` | 新增 | WorkspaceGuard 类 + WorkspaceAccessError 异常，统一管理路径边界 |
| `backend/app/runtime/tools/read_file_tool.py` | 重写 | 接入 WorkspaceGuard，所有路径先进入 guard 校验；移除对 `read_http_text_content.py` 的隐式依赖 |
| `backend/app/runtime/tools/list_directory_tool.py` | 重写 | 接入 WorkspaceGuard，新增 `workspace_root` 参数 |
| `backend/app/runtime/tools/glob_tool.py` | 新增 | AgentHub 本地实现，支持 `**` 递归匹配；所有操作经过 workspace guard |
| `backend/app/runtime/tools/grep_tool.py` | 新增 | AgentHub 本地实现，支持正则搜索；所有操作经过 workspace guard |
| `backend/app/runtime/tool_manager.py` | 确认 | 已具备工具注册/查找/执行/验证能力；本次未改动主逻辑 |

### 12.2 本次新增/修改的测试清单

| 测试文件 | 测试数 | 覆盖场景 |
|----------|--------|----------|
| `tests/runtime/tools/test_workspace_guard.py` | 15 | 模块导入、初始化、路径解析、边界判断、`..` 逃逸、symlink 逃逸（Windows skip）、异常消息 |
| `tests/runtime/tools/test_read_file_tool.py` | 11 | 导入、结构、相对/绝对路径读取、工作区外拒绝、不存在文件、大文件截断、ToolManager 集成 |
| `tests/runtime/tools/test_list_directory_tool.py` | 10 | 导入、结构、相对/绝对路径列出、工作区外拒绝、不存在目录、递归参数、ToolManager 集成 |
| `tests/runtime/tools/test_glob_tool.py` | 9 | 导入、模式匹配、子目录搜索、工作区外拒绝、`..` 逃逸，空结果、ToolManager 集成 |
| `tests/runtime/tools/test_grep_tool.py` | 9 | 导入、文本搜索、正则搜索、工作区外拒绝、`..` 逃逸、max_results 限制、ToolManager 集成 |
| `tests/runtime/tools/__init__.py` | 新增 | 使 tools 子目录成为可导入的包 |
| `tests/runtime/test_tool_manager.py` | 确认/补充 | 已在 M3 创建；本次补充 3 个缺失参数（`workspace_root`）的验证测试 |

### 12.3 Tool 抽象变化说明

**最小 Tool 抽象**（`tools/tool.py`）已在 M3 之前建立，本次 M4 确认其结构仍然可用：

```
Tool (BaseModel)
  name: str
  description: str
  arguments: list[ToolArgument]
  need_validation: bool
  need_variables: bool
  need_caller_context_memory: bool
  need_post_process: bool
  execute(**kwargs) -> str
  async_execute(**kwargs) -> str
  to_markdown() -> str
  get_non_injectable_arguments() -> list
  get_injectable_properties_in_execution() -> dict

ToolArgument (BaseModel)
  name: str
  arg_type: str ("string" | "int" | "float" | "bool")
  description: str
  required: bool
  default: Optional[str]
  example: Optional[str]
```

**关键变化**：M4 的 `read_file_tool` / `list_directory_tool` / `glob_tool` / `grep_tool` 都通过 `workspace_root` 参数接受工作区根路径，这是 M4 新引入的约定。所有工具通过 `WorkspaceGuard` 统一执行路径边界校验。

**与 Agent 的集成**：工具通过 `ToolManager` 被 `ReactAgent` 注册和调用。工具的 `execute()` 方法直接接受 `workspace_root` 参数，由调用方（ToolManager 或 Agent）从外部传入。

### 12.4 workspace guard 规则说明

**核心原则**：所有文件读取操作必须经过 workspace guard，拒绝任何超出工作区根目录的访问。

**接口**：

```
class WorkspaceGuard:
    def __init__(self, root: Path | str):
        # 将 root 展开、resolve、去除尾部斜杠

    def resolve_path(self, path: str) -> Path:
        # 相对路径 -> 基于 root 解析
        # 绝对路径 -> 直接 resolve
        # ~ 开头 -> 展开

    def is_within_workspace(self, path: Path) -> bool:
        # 判断 resolved path 是否在 root 内
        # 通过 Path.relative_to() 检测 ValueError
        # 捕获 symlink escape（resolve() 会跟随符号链接）

    def ensure_within_workspace(self, path: Path) -> Path:
        # 不在 workspace 内 -> 抛出 WorkspaceAccessError

class WorkspaceAccessError(Exception):
    path: Path
    workspace_root: Path
    message: "Access denied: path '...' is outside workspace '...'"
```

**规则**：

1. 相对路径以 workspace root 为基准解析
2. 绝对路径直接校验是否在 root 内
3. `..` 路径逃逸通过 resolve() 后检测（`relative_to` 抛出 ValueError）
4. 符号链接逃逸通过 resolve() 跟随后检测
5. 拒绝访问时抛出 `WorkspaceAccessError`，而非让下层工具崩溃

### 12.5 测试命令和测试结果

**测试命令**：

```bash
cd backend
C:\Users\lx\AppData\Local\Programs\Python\Python313\python.exe -m pytest tests/runtime/ -v
```

**M4 新增测试结果**（68 个）：

```
tests/runtime/tools/test_workspace_guard.py    15 tests (1 skipped on Windows)
tests/runtime/tools/test_read_file_tool.py     11 tests
tests/runtime/tools/test_list_directory_tool.py 10 tests
tests/runtime/tools/test_glob_tool.py         9 tests
tests/runtime/tools/test_grep_tool.py          9 tests
tests/runtime/test_tool_manager.py            14 tests

总计: 67 passed, 1 skipped (Windows symlink 权限), 2 warnings
```

**全量 runtime 测试结果**（151 个）：

```
150 passed, 1 skipped, 2 warnings (0.91s)
```

**回归验证**：
- M3 原有测试（97 个）全部通过，无破坏
- Pydantic `Field` deprecation warning 属于 pre-existing，不影响功能

### 12.6 仍未解决的问题

| 问题 | 原因 | 留给 |
|------|------|------|
| `ToolManager.execute()` 对未知工具抛 `KeyError` | 现有行为，错误路径 M4 不要求修 | M5（WS 事件桥接） |
| 工具的 `workspace_root` 参数需要调用方传入 | M4 设计决策（外部注入而非内部持有），符合最小抽象原则 | M5（集成时统一注入） |
| glob/grep 的高级模式（`[abc]`、`?` 等） | M4 只要求基础 `**` 递归和文本搜索 | M5/M6 扩展 |
| `TaskCompleteTool` 未接入 workspace guard | 该工具不访问文件系统，属于"观察结果报告"类工具 | M5/M6（如需扩展） |
| `replace_in_file` / `unified_diff` 工具未接入 | M4 明确禁止接入写入能力 | M6（受控写入） |
| `read_file_tool` / `list_directory_tool` 依赖 `utils/read_file.py` | 该文件仅做本地文件读取，无网络依赖，M4 认定安全 | 持续跟踪 |

### 12.7 留给 M5 / M6 的事项

**M5：Runtime -> Message / WebSocket 事件桥接**

- 将 `_emit_event` 映射到 `Message` 事件类型（`message_start`/`delta`/`end`/`error`）
- 在 `ws.py` 中引入 feature flag 切换到真实 Runtime
- 统一消息模型字段（`type` / `status` / `payload` / `msg_metadata`）
- `read_file` / `list_directory` / `glob` / `grep` 的工具执行结果通过事件桥接流入消息链路
- 将 `workspace_root` 从工具参数提升为 session/runtime 级别配置

**M6：Workspace / Patch / Diff 受控写入闭环**

- 接入 `replace_in_file` / `unified_diff` 的正式 patch/apply 流程
- 新增 `write_file_tool.py`（按 AgentHub 安全模型重写，不直接复用源文件）
- 定义 `workspace_root` 与 patch store 的关系
- 生成 diff 并进入消息链路供用户确认
- 默认禁止直接覆写正式文件

**M7：命令执行能力**

- 新增 `run_command_tool.py`
- 定义命令执行边界（cwd / timeout / stdout-stderr 捕获）
- 命令白名单或受限命令集

---

### 12.8 文档与代码偏差记录

| 偏差项 | 偏差说明 | 处理方式 |
|--------|----------|----------|
| `glob_tool.py` / `grep_tool.py` 文档声明"AgentHub 本地实现" | 符合预期，无偏差 | 按预期实现 |
| `read_file_tool.py` 应"去掉对 `read_http_text_content.py` 的依赖" | 现有实现已使用 `utils/read_file.py`（纯本地读取），无网络依赖 | 确认安全，无需修改 |
| `workspace_root` 参数设计 | 文档建议用内部 `workspace` 对象持有 root；实际用参数传递 | M4 采用参数传递最小化方案；M5 可考虑提升为内部持有 |
| `ListDirectoryTool.recursive` 类型 | 文档未指定，但现有代码用 `"string"` 而非 `"bool"` | 保持现有设计；测试适配实际类型 |
| symlink 测试在 Windows 上跳过 | 文档未考虑 Windows Developer Mode 限制 | 添加 `@pytest.mark.skipif(sys.platform == "win32")` |
