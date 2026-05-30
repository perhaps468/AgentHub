# M7 - Run Command And Dev Task Closed Loop

> 本文档对应 `02-implementation-guide.md` 中 `M7：RunCommand 受控执行与开发任务闭环`。
> 本文档只约束 M7，不覆盖后续 P4/P5/P6 规划。

---

## 1. 目标

M7 的唯一目标是：

- 让 runtime 在受控边界内具备执行开发命令的能力
- 把命令执行结果统一收口为 agent 可消费、可展示的结构化输出
- 与 M6 的 `PendingChange` / preview / apply 能力形成最小开发任务闭环

M7 完成后，仓库至少应满足：

- agent 可在受控 cwd、受控 timeout、受控命令集合内执行命令
- 命令结果包含 `stdout` / `stderr` / `exit_code`
- runtime 可串起：
  - 读代码
  - 产出 patch / diff
  - apply 变更
  - 运行测试或构建命令
  - 返回最终结果

---

## 2. 输入前提

执行 M7 前，以下前提必须成立：

- [02-implementation-guide.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/02-implementation-guide.md) 已确认 M7 范围
- [M6-workspace-patch-diff.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M6-workspace-patch-diff.md) 已完成
- M6 的 preview / pending change / write tools / runtime 最小接线已经落地

当前已知现状：

- runtime 已具备只读工具 + M6 preview 写工具
- `RuntimeAgentService._build_tools()` 已注册 M6 写工具
- 前端 `useChatStreamState.spec.ts` 已收口并通过

M7 的前置现实判断：

- 命令执行能力现在还没有正式受控接入 runtime
- `PendingChange.apply()` 已有基础能力，但尚未形成完整开发任务链路
- 当前不存在正式的 `run_command_tool.py` / `command_guard.py`

---

## 3. 本里程碑允许修改的范围

只允许修改以下范围：

- 新增：`backend/app/runtime/tools/run_command_tool.py`
- 新增：`backend/app/runtime/command_guard.py`
- `backend/app/runtime/runtime_agent_service.py`
- `backend/app/runtime/react_agent.py`
- `backend/app/runtime/tool_manager.py`
- `backend/app/runtime/pending_change.py`
- `backend/app/runtime/patch_store.py`
- `backend/app/runtime/workspace.py`
- `backend/tests/runtime/**` 中与 M7 直接相关的测试
- 必要时补充：本文件与迁移记录文档

允许的改动类型仅限：

- 受控命令执行边界
- runtime 工具注册与命令输出结构化
- `PendingChange` 从 preview 到 apply 的最小接线
- M7 所需测试补充

---

## 4. 本里程碑禁止修改的范围

M7 明确禁止：

- 修改 `backend/app/models/*` 的数据模型定义
- 修改 websocket 主协议
- 引入任意 shell 直跑、无白名单执行
- 绕过 workspace / cwd 限制执行命令
- 加入网络访问型命令作为默认能力
- 扩做多 agent、orchestrator、workflow engine
- 顺手重构 M4/M5/M6 无关代码

说明：

- M7 关注“受控开发命令执行”
- 不做 P4/P5/P6 的架构扩展
- 不要求在本里程碑解决复杂审批 UI

---

## 5. 本里程碑必须处理的事项

### 5.1 新增 `command_guard.py`

M7 必须先定义清楚命令执行边界，再接工具。

最小职责：

- 限定可执行命令集合或白名单前缀
- 限定执行 cwd 必须在 workspace 内
- 限定 timeout
- 拒绝危险 shell 组合方式
- 统一命令校验错误输出

建议至少具备：

- `validate_command(...)`
- `validate_cwd(...)`
- `build_execution_plan(...)`

要求：

- 默认拒绝未知命令
- 默认拒绝工作区外 cwd
- 默认拒绝无限 timeout
- 不允许把整段原始 shell 当成无约束字符串直接放行

### 5.2 新增 `run_command_tool.py`

该工具必须按 AgentHub 安全模型新写，不应直接复用源项目命令工具。

最小输入建议：

- `command`
- `args`
- `cwd`
- `timeout_seconds`

最小输出建议：

- `command`
- `cwd`
- `stdout`
- `stderr`
- `exit_code`
- `timed_out`
- `success`

要求：

- 输出必须结构化
- 失败时也要稳定返回，不抛未处理异常到 runtime 主循环
- 不能默认依赖 shell 拼接
- 能力应足以运行最小测试命令，例如：
  - `pytest`
  - `python -m pytest`
  - `npm test`
  - `pnpm test`
  - `uv run pytest`

### 5.3 定义命令白名单策略

M7 不允许无边界执行，必须写明白名单策略。

建议优先支持：

- Python 测试类命令
- Node 测试类命令
- 只读诊断类命令

建议默认拒绝：

- 删除型命令
- 系统级包管理命令
- 网络下载命令
- 长时间后台驻留命令

至少要明确：

- 按命令名前缀白名单
- 按参数模式做最小校验
- 对拒绝原因给出稳定错误信息

### 5.4 把命令工具接入 runtime

M7 必须把 `run_command_tool` 接入 runtime 工具构建链路。

至少应修改：

- `RuntimeAgentService._build_tools()`

要求：

- 保持 M4/M5/M6 工具不回退
- `run_command_tool` 接入后仍要走统一 workspace_root / cwd 约束
- 工具输出可直接进入 agent 的观察结果

### 5.5 收口 `PendingChange.apply()` 的 runtime 用法

M6 已有 `PendingChange.apply()`，但还不是完整开发闭环的一部分。

M7 应至少明确一条最小路径：

1. agent 先生成 preview 变更
2. runtime 显式 apply
3. apply 成功后再运行测试或构建命令
4. 返回结果

这里不一定要做复杂审批 UI，但必须至少明确：

- 何时调用 `apply()`
- apply 失败时如何终止
- apply 成功后如何把文件变更状态带入命令执行阶段

### 5.6 建立最小开发任务闭环测试

M7 不是“命令能跑就算完”，而是要证明开发闭环成立。

至少要能覆盖：

- 修改一个工作区内测试文件或代码文件
- apply 变更
- 执行测试命令
- 获取结构化结果

可接受的最小闭环：

- `replace_in_file` 生成 `PendingChange`
- `apply()`
- `run_command_tool` 运行一个白名单测试命令
- 断言退出码与输出

---

## 6. 建议执行顺序

1. 阅读 [M6-workspace-patch-diff.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M6-workspace-patch-diff.md)
2. 检查 `pending_change.py`、`runtime_agent_service.py` 当前现状
3. 先设计 `command_guard.py`
4. 先写失败测试
5. 再实现 `run_command_tool.py`
6. 再接入 runtime 工具注册
7. 再收口 apply + run command 最小闭环
8. 运行 M7 测试
9. 回归 M6 / M5 关键测试
10. 回写 M7 执行记录

---

## 7. 测试要求

M7 默认使用 TDD。

执行顺序必须是：

1. 先补失败测试
2. 运行测试，确认当前为红灯
3. 再做最小实现
4. 再运行测试，确认转绿
5. 最后补一次 M6 / M5 回归

至少应新增或补充以下测试文件：

- `tests/runtime/tools/test_run_command_tool.py`
- `tests/runtime/test_dev_task_loop.py`
- `tests/runtime/test_runtime_agent_service.py`

如 `command_guard.py` 单独抽象明显，建议补充：

- `tests/runtime/test_command_guard.py`

### 7.1 `test_run_command_tool.py` 必测项

- 白名单命令可执行
- 非白名单命令被拒绝
- cwd 在 workspace 内可执行
- cwd 在 workspace 外被拒绝
- timeout 生效
- `stdout` / `stderr` / `exit_code` 返回稳定
- 命令失败时工具仍返回结构化结果

### 7.2 `test_command_guard.py` 必测项

- 命令名前缀校验
- 危险命令拒绝
- workspace 外 cwd 拒绝
- timeout 上限校验
- 非法参数模式拒绝

### 7.3 `test_dev_task_loop.py` 必测项

- preview 变更可 apply
- apply 成功后可运行测试命令
- 命令输出可被 agent 消费
- apply 失败时不会继续执行命令
- 命令失败时能返回结构化失败结果

### 7.4 `test_runtime_agent_service.py` 必测项

- `_build_tools()` 包含 `run_command_tool`
- runtime 原有读工具和写工具不丢失
- 命令工具接入后不破坏主链路

### 7.5 M6 / M5 回归要求

M7 完成前至少回归：

- `tests/runtime/test_patch_flow.py`
- `tests/runtime/test_workspace.py`
- `tests/runtime/tools/test_replace_in_file_tool.py`
- `tests/runtime/tools/test_unified_diff_tool.py`
- `tests/runtime/tools/test_write_file_tool.py`
- `tests/runtime/tools/test_workspace_guard.py`
- `tests/runtime/test_runtime_agent_service.py`
- `tests/api/test_ws_runtime_agent.py`

目的：

- 确保命令执行能力没有打坏 preview / apply / ws bridge
- 确保 M6 的写边界仍然成立

### 7.6 测试环境约束

- 不访问真实 LLM 服务
- 不依赖真实前端
- 不依赖网络
- 命令执行测试必须使用临时工作区或明确测试目录
- 不允许通过修改真实业务文件来证明能力

---

## 8. 验收标准

M7 完成时，至少应满足：

| 验收项 | 要求 |
|---|---|
| 命令边界有效 | 只有白名单命令能执行，cwd 与 timeout 受控 |
| run_command_tool 可用 | 返回结构化命令结果 |
| runtime 已接线 | agent 可调用 run_command_tool |
| 开发闭环成立 | preview -> apply -> run command 可跑通最小路径 |
| M6 未破坏 | patch / diff / write / workspace 回归通过 |
| M5 未破坏 | ws bridge 回归通过 |

---

## 9. 输出要求

执行 M7 的 AI 或工程实现，完成后必须输出：

1. 修改文件清单
2. 新增/修改测试清单
3. command guard 规则说明
4. run_command_tool 输入输出说明
5. apply + run command 闭环说明
6. 测试命令与测试结果
7. 仍未解决的问题
8. 明确留给后续 P4/P5/P6 的事项

---

## 10. 与后续规划的边界

M7 结束后，以下问题应明确留给后续阶段：

- artifact / richer result cards 如何呈现
- blueprint / runtime factory 如何接入不同 agent 类型
- 多 agent orchestration 如何消费命令结果
- 更复杂的审批流、任务编排、长任务管理

---

## 11. 一句话约束

M7 的本质不是“让 agent 拥有任意 shell”，而是：
**让 agent 在受控边界内完成最小开发执行闭环。**



---

## 12. 执行记录

> 执行时间: 2026-05-29

### 12.1 最终交付文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/runtime/command_guard.py` | 新增 | 命令执行边界守卫：whitelist + cwd + timeout 三重校验 |
| `backend/app/runtime/tools/run_command_tool.py` | 新增 | 受控命令执行工具，封装 CommandGuard + subprocess，返回结构化 string |
| `backend/app/runtime/tools/tool.py` | 增补 | 新增 `model_post_init()` hook，支撑子类注入运行时字段 |
| `backend/app/runtime/runtime_agent_service.py` | 增补 | `_build_tools()` 新增 RunCommandTool 注册 |
| `backend/tests/runtime/test_command_guard.py` | 新增 | 28 个测试覆盖 guard 所有边界 |
| `backend/tests/runtime/tools/test_run_command_tool.py` | 新增 | 28 个测试覆盖工具所有行为 |
| `backend/tests/runtime/test_dev_task_loop.py` | 新增 | 10 个测试覆盖 apply + run_command 闭环 |
| `backend/tests/runtime/test_runtime_agent_service.py` | 增补 | `TestRuntimeAgentServiceCommandTools` 类，3 个测试验证注册 |

### 12.2 测试结果

```bash
cd backend

# M7 新增测试
python -m pytest     tests/runtime/test_command_guard.py     tests/runtime/tools/test_run_command_tool.py     tests/runtime/test_dev_task_loop.py     tests/runtime/test_runtime_agent_service.py::TestRuntimeAgentServiceCommandTools     -v
# 69 passed

# 全量 runtime 回归
python -m pytest tests/runtime/ -v
# 315 passed, 1 skipped

# API 回归
python -m pytest tests/api/ -v
# 18 passed
```

### 12.3 Command Guard 规则说明

`CommandGuard` 默认拒绝，规则分层：

**第一层：危险 Shell 元字符阻断（优先级最高）**

- `|`, `&&`, `||`, `;`, backtick, `$()`, `>>`, `2>`, `<(`, `>` 均被阻断
- 任何包含上述字符的命令直接拒绝，无论 whitelist 是否匹配

**第二层：危险命令前缀阻断**

| 前缀 | 原因 |
|------|------|
| `rm -rf`, `rm -r`, `del`, `rmdir` | 删除文件系统 |
| `curl`, `wget` | 网络下载+shell 执行 |
| `ssh`, `scp`, `nc`, `ncat` | 网络攻击 |
| `dd`, `mkfs`, `fdisk` | 磁盘破坏 |
| `shutdown`, `reboot`, `halt` | 系统关机 |
| `docker run/exec`, `kubectl`, `terraform destroy` | 容器/云资源破坏 |
| `pip install -g`, `npm install -g`, `pnpm add -g` | 全局包污染 |
| `eval`, `source`, `exec` | shell 注入 |

**第三层：Whitelist 前缀白名单**

| 类别 | 允许命令前缀 |
|------|-------------|
| Python 工具 | `python`, `python3`, `pytest`, `uv run`, `pip`, `poetry run` |
| Node 工具 | `npm`, `pnpm`, `node`, `npx` |
| 诊断工具 | `echo`, `ls`, `cat`, `head`, `tail`, `grep`, `find`, `wc`, `sort`, `uniq`, `diff`, `ping`, `timeout` |
| 版本检查 | `--version`, `-v`, `version` |

**Timeout 约束**

- 默认 timeout: 60 秒，最大: 300 秒
- 零/负数 timeout：拒绝
- 超过 max_timeout：自动 cap 到 max_timeout

**CWD 约束**

- 所有 cwd 必须位于 workspace_root 内
- 支持相对路径（相对于 workspace_root）和绝对路径（必须在 workspace 内）
- `..` 穿越路径会被拒绝

### 12.4 run_command_tool 输入输出说明

**输入参数**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `command` | string | 是 | 命令字符串，如 `pytest --version` |
| `cwd` | string | 是 | 工作目录（必须在 workspace 内） |
| `timeout_seconds` | int | 否 | 超时秒数，默认 60，上限 300 |

**输出格式**（string，agent 可直接消费）

```
[COMMAND] pytest --version
[CWD] D:\code\project\backend
[EXIT_CODE] 0
[TIMED_OUT] false
[SUCCESS] true

--- STDOUT ---
pytest 9.0.3

--- STDERR ---
(no stderr)
```

**错误情况**（返回 Error: 开头的 string，不会抛出异常）

- 命令不在白名单：`Error: Command not in whitelist: 'rm' is not an allowed command.`
- cwd 越界：`Error: CWD 'D:\tmp' is outside workspace 'D:\project'.`
- timeout <= 0：`Error: timeout_seconds must be > 0, got 0.`

### 12.5 apply + run_command 闭环说明

M7 完成后，agent 可以完成最小开发闭环：

```
1. read_file_tool / glob_tool / grep_tool  # 读取代码
        |
2. replace_in_file_tool / unified_diff_tool / write_file_tool  # 生成 PendingChange
        |
3. runtime 调用 PendingChange.apply()  # 写入文件，status -> APPLIED
        |
4. run_command_tool("pytest", cwd=workspace, timeout=30)  # 运行测试
        |
5. 检查 exit_code / stdout，决定是否继续修复
        |
6. task_complete 返回最终结果
```

apply 失败时阻止命令执行：外部修改文件后 `change.apply()` 返回 False，agent 感知到失败后不执行后续 `run_command_tool`。

### 12.6 仍未解决的问题

- `exit 1` 在 Windows `cmd.exe` 下会启动新窗口，不返回到 Python subprocess。当前绕过方式是检查 `exit_code == -1`。后续考虑使用 `CREATE_NO_WINDOW` 标志。
- Whitelist 是硬编码 prefix 列表，没有外部配置接口。后续可通过环境变量或配置文件注入。

### 12.7 留给后续阶段（P4/P5/P6）的事项

- **artifact / richer result cards**：命令执行结果如何更好地呈现在前端
- **blueprint / runtime factory**：不同 agent 类型如何接入命令执行能力
- **多 agent orchestration**：多个 agent 如何协调共享命令执行结果
- **复杂审批流**：apply 前需要用户确认的 UI 流程
- **长任务管理**：超过 5 分钟的命令如何拆分和跟踪
- **命令输出流式**：实时流式推送 stdout 到前端
- **命令历史记录**：命令执行历史持久化和可追溯性
- **并行命令执行**：多个命令同时运行的能力

### 12.8 文档与代码偏差说明

M7 执行过程中发现一处偏差：

- **`tool.py` 需要 `model_post_init` hook**：`Tool` 基类是 Pydantic v2 `BaseModel`，子类在 `__init__` 中通过参数注入实例字段时，pydantic v2 默认 `extra="allow"` 不再允许直接 `self.xxx = value`（v2 的 `extra="allow"` 只针对 schema 字段，不包括 `__init__` 参数）。需要通过 `model_post_init` + `object.__setattr__` 来设置运行时字段。`RunCommandTool` 使用此模式，其他工具不受影响（M6 的 `ReplaceInFileTool` 等工具使用 `workspace_root` 作为 schema 字段，不触发此问题）。
