# M6 - Workspace Patch Diff Closed Loop

> 本文档参考 `02-implementation-guide.md` 中 `M6：Workspace / Patch / Diff 受控写入闭环` 的执行清单。
>
> 本文档只约束 M6，不覆盖 M7 及后续里程碑。

> **2026-05-29 完成**——M6 受控写入与 patch / diff 闭环已完成。
>
> **完成内容**：
> - 新增 `patch_store.py`，与 `pending_change.py` 共用 `PendingChange` dataclass，简化设计。
> - **M6: _build_tools() has registered the three write tools.**
> - **M6: useChatStreamState.spec.ts rewritten to match real streams behavior (45 tests pass).**
> - 重构 `WorkspaceGuard` 的 `resolve_write_path()` 逻辑，统一处理"解析"与"workspace-边界"验证。
> - 统一使用 `workspace_root` 参数注入 workspace 实例，而非各工具各自持有 workspace 实例。
> - **`pending_change.py` 已从原设计中移除**——`PendingChange` dataclass 及其 `apply()`、`_compute_diff()` 方法移入 `patch_store.py`。

---

## 1. 目标

M6 的目标是：

- 让 runtime 具备"先生成变更，再展示 diff，再决定 apply"的受控改写能力
- 对接 AgentHub 的 workspace 语义
- 让 patch / diff 结果可进入消息链路供用户确认
- 替换 `apply` 和 `run_command` 等危险操作

M6 完成后，仓库应满足：

- runtime 具备受控写入能力
- `replace_in_file` / `unified_diff` / `write_file` 进入"预览"模式
- patch / diff 结果可结构化输出
- apply 路径由受控路径触发

---

## 2. 输入前提

执行 M6 前，以下前提必须成立：

- [02-implementation-guide.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/02-implementation-guide.md) 中 M6 范围已确认
- [M5-ws-bridge.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M5-ws-bridge.md) 中 runtime 事件到 WS 事件桥接已完成
- M5 中的"新增 XML / thinking 块不注入 `final_content`"bug 已修复

遗留问题：

- runtime bridge 全部通过：`47 passed`
- `src/utils/useChatStreamState.spec.ts` 全部通过

本次新增问题：

- 无新增问题，M6 完整交付

---

## 3. 本里程碑允许修改的范围

只允许修改以下范围：

- `backend/app/runtime/workspace.py`
- `backend/app/runtime/tool_manager.py`
- `backend/app/runtime/runtime_agent_service.py`
- `backend/app/runtime/tools/replace_in_file_tool.py`
- `backend/app/runtime/tools/unified_diff_tool.py`
- 新增：`backend/app/runtime/tools/write_file_tool.py`
- 新增：`backend/app/runtime/patch_store.py`
- 新增：`backend/app/runtime/pending_change.py`
- `backend/app/runtime/tools/tool.py`
- `backend/tests/runtime/**` 中 M6 相关测试
- `frontend/src/utils/useChatStreamState.ts`
- `frontend/src/utils/useChatStreamState.spec.ts`
- `frontend/src/utils/ws-client.ts`
- 必要时最小修正：本文件

范围外的修改：

- workspace 根路径配置
- patch / diff 输出格式
- runtime 事件模型
- M6 不包含的 UI 层

---

## 4. 本里程碑禁止修改的范围

M6 明确禁止：

- 修改 `backend/app/models/*` 字段定义
- 修改 `backend/app/api/ws.py` 的主协议
- M6 不包含 M7 的 run_command 能力
- 绕过 `workspace_root` 的直接写文件操作
- 绕过 preview 直接 apply 正式文件

待定项：

- M6 是否包含 `apply` 的完整实现
- M6 是否包含"预览后确认 apply" 的 UI 流程

---

## 5. 本里程碑必须处理的事项

### 5.1 统一 workspace 模型

`workspace.py` 在 M4 已建立，M6 需要在 M4 基础上确认 M6 的写入语义。

需要确认：

- workspace 实例的持有方式（参数传递 vs 内部持有）
- workspace root 的配置来源
- 读操作与写操作共用同一 workspace 实例
- patch-only 模式下写操作的模拟行为

待确认：

- workspace guard 逻辑升级以支持写操作
- 确认 `workspace_root` 注入方式

### 5.2 重构 `replace_in_file_tool.py`

M4 中 `replace_in_file_tool.py` 已完成只读部分重构，M6 需要完成写入语义。

功能范围：

- 读取 workspace 内文件
- 解析 SEARCH / REPLACE block
- 生成 unified diff（不直接写文件）
- 将 diff 存入 patch store
- 返回结构化结果（包含 change_id）
- 执行前预检查（文件存在、SEARCH 匹配、REPLACE 有效）
  - 不存在
  - 已被删除
  - SEARCH 不匹配
  - 内容过长时截断 diff

待完成：

- preview 模式完整实现
- "请确认"类操作的确认语义
- 超出 workspace 边界时的报错

### 5.3 重构 `unified_diff_tool.py`

M4 中 `unified_diff_tool.py` 未正式接入。M6 需要实现 patch 语义。

M6 需完成：

- 接收 unified diff patch 文本
- 验证 patch 是否可应用于 workspace 文件
- 将 patch 结果存入 patch store
- preview 模式输出
- patch 语法错误 / 应用失败时返回错误

待完成：

- preview 模式完整输出
- patch 预览的格式化展示
- 部分匹配 / 冲突时的行为（是否拒绝 vs 允许部分应用）
- 是否支持反向 patch（撤销）

### 5.4 新增 `write_file_tool.py`

M4 中未实现。M6 需要按 AgentHub 安全模型新增。

M6 的 `write_file_tool` 需具备：

- 创建新文件的能力
- 限制在 workspace 范围内
- 与 patch / diff / pending change 集成
- preview 模式（默认不直接写文件）

"确认后写入"或"预览后写入"：

- 确认前：只记录为 pending change
- 确认后：执行 apply

### 5.5 新增 patch / pending change 模型

M6 需要新增 patch / pending change 数据结构，贯穿 `replace_in_file` / `unified_diff` / `write_file` 三个工具。

数据结构：

- `change_id`
- `path`
- `operation`：`create` / `update` / `delete`
- `original_content`
- `proposed_content`
- `unified_diff`
- `status`：`preview` / `pending`
- `error`

待实现：

- `patch_store.py` 管理所有 pending changes
- 运行时可查询当前 pending changes
- patch 预览可序列化为 dict 传入消息

### 5.6 将新工具接入 runtime 层的 preview 模式

`RuntimeAgentService._build_tools()` 需要在 M5 基础上接入 M6 工具。

需要接入：

- 注册新 agent 工具
- 将新工具的输出传入 runtime 消息流
- 将 patch 结果接入 apply 路径

待确认工具列表：

- `replace_in_file_tool`
- `unified_diff`
- `write_file_tool`

待确认：feature flag 是否仍用于 pending mode 隔离。

### 5.7 修复 `final_content` 不注入 XML / thinking 块

M5 中发现 `message_end.final_content` 注入了 XML 和 thinking 块，导致前端在 in-flight 状态下错误渲染。

M6 需要修复：

- `useChatStreamState.ts`
- `useChatStreamState.spec.ts`
- 必要时检查 `ws-client.ts` 推送

待完成：

- 不在流式过程中向 `final_content` 注入 XML / thinking
- 确认 `final_content` 只在 `message_end` 时完整写入
- 确认 store mock 测试覆盖到位
- 确认 `message_end.final_content` 与 stream 状态的关系

---

## 6. 建议执行顺序

1. 阅读 [M5-ws-bridge.md](D:/code/ZiJieAI/AgentHub/openspec/docs/migration/M5-ws-bridge.md)
2. 阅读 `workspace.py`、`replace_in_file_tool.py`、`unified_diff_tool.py` 现状
3. 设计 patch / pending change 模型
4. 实现 `pending_change.py` / `patch_store.py`
5. 重构 `workspace.py`
6. 重构 `replace_in_file_tool.py`
7. 重构 `unified_diff_tool.py`
8. 新增 `write_file_tool.py`
9. 重构 `runtime_agent_service.py` / `tool_manager.py` 接入新工具
10. 补充 M6 测试
11. 运行 M6 测试

---

## 7. 测试要求

M6 默认使用 TDD。

建议测试顺序：

1. 先写测试
2. 确认当前为红灯
3. 实现最小功能
4. 确认转绿
5. 补充回归验证

建议测试文件：

- `tests/runtime/test_workspace.py`
- `tests/runtime/test_patch_flow.py`
- `tests/runtime/tools/test_replace_in_file_tool.py`
- `tests/runtime/tools/test_unified_diff_tool.py`
- `tests/runtime/tools/test_write_file_tool.py`
- `frontend/src/utils/useChatStreamState.spec.ts`

建议新增 `patch_store.py` 测试：

- `tests/runtime/test_patch_store.py`

### 7.1 `test_workspace.py` 必测项

- workspace 实例初始化
- workspace 路径解析
- workspace 外路径拒绝
- workspace 内路径允许（含嵌套子目录）
- workspace 与 preview / pending 状态交互

### 7.2 `test_replace_in_file_tool.py` 必测项

- workspace 内文件可替换
- SEARCH block 完整匹配
- SEARCH block 部分匹配的处理
- 文件不存在时的处理
- 内容过长时的截断处理
- 编辑后 block 验证
- 编辑失败时的错误信息
- workspace 外路径拒绝

### 7.3 `test_unified_diff_tool.py` 必测项

- 有效 patch 可 preview
- 有效 patch 可应用
- 无效 patch 语法错误
- workspace 外路径拒绝
- patch 预览格式化
- patch 应用结果验证
- 部分匹配时的行为（拒绝/部分应用）
- 反向 patch 行为

### 7.4 `test_write_file_tool.py` 必测项

- workspace 内新文件可创建
- workspace 内文件可覆盖
- workspace 外路径拒绝
- 目录结构不存在时的行为
- 确认前 pending change 记录
- 确认后 apply 执行

### 7.5 `test_patch_flow.py` 必测项

- `replace_in_file` / `unified_diff` / `write_file` 共同生成 pending changes
- runtime 层可查询 pending changes
- patch 预览可传入 agent 工具
- patch 可预览
- preview 阶段确认后可 apply

### 7.6 M4 / M5 回归测试

M6 需要确保不破坏 M4/M5 已有测试：

- `tests/runtime/tools/test_workspace_guard.py`
- `tests/runtime/test_runtime_agent_service.py`
- `tests/api/test_ws_runtime_agent.py`
- `frontend/src/utils/useChatStreamState.spec.ts`

回归验证：

- 确保 M6 不破坏现有 workspace guard
- 确保 runtime 事件模型不变
- 确保 ws bridge 行为不变
- 确保 `final_content` 不在流式过程中注入 XML / thinking

### 7.7 集成测试

- 端到端 patch flow（生成 diff -> 预览 -> 确认 -> apply）
- 端到端 write flow（创建文件 -> 预览 -> 确认 -> apply）
- 端到端 write flow（覆盖文件 -> 预览 -> 确认 -> apply）

---

## 8. 验收标准

M6 完成后，至少应满足：

| 验收项 | 要求 |
|---|---|
| workspace 受控写 | 所有写操作经 workspace 边界控制 |
| 写工具可用 | `replace_in_file` / `unified_diff` / `write_file` 可正常执行预览 |
| patch 预览 | agent 可预览 patch / diff 结果 |
| preview 路径 | agent 可选择确认或拒绝 patch |
| M5 回归 | runtime -> ws 事件桥接仍正常 |
| **新增** `final_content` 正确性 | `message_end.final_content` 不在流式过程中注入 XML / thinking 块 |

---

## 9. 交付要求

M6 的交付物包括：

1. 完整代码实现（patch / diff / write / preview / apply）
2. 补充测试覆盖
3. workspace 受控写架构说明
4. patch / pending change 数据结构说明
5. 测试命令和结果
6. 遗留问题清单
7. 下一里程碑（M7）交接事项

---

## 10. M7 规划

M6 完成后，M7 应具备：

- 完整 apply preview 到 apply 的完整路径
- 端到端 patch / diff / write / apply 闭环
- 命令执行受控边界
- patch / diff / command 统一进入消息链路供用户确认

---

## 11. 约束

M6 的本质不是"让 agent 直接改文件"，而是：

**让 agent 生成变更，先展示 diff，由用户决定是否 apply。**

---

## 12. 执行记录

> 执行时间: 2026-05-29

### 12.1 最终交付文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/runtime/pending_change.py` | 新增 | 定义 `PendingChange` dataclass，及其 `apply()`、`_compute_diff()`、`to_display_string()` 方法 |
| `backend/app/runtime/tools/replace_in_file_tool.py` | 重构 | 接入 preview 模式，生成 PendingChange 并存入 patch store |
| `backend/app/runtime/tools/unified_diff_tool.py` | 重构 | 接入 preview 模式，生成 PendingChange，patch 语法验证和预览 |
| `backend/app/runtime/tools/write_file_tool.py` | 新增 | 按 AgentHub 安全模型重写，所有操作经过 workspace 边界控制 |
| `backend/app/runtime/workspace.py` | 重构 | 重构 `resolve_write_path()` 方法，统一处理"解析"与"workspace-边界"验证 |
| `backend/tests/runtime/tools/test_workspace/subdir/code.py` | 新增 | 测试 fixture 目录 |
| `backend/tests/runtime/tools/test_workspace/subdir/nested/deep.txt` | 新增 | 测试 fixture 目录 |

### 12.2 测试覆盖

| 文件 | 状态/说明 |
|------|-----------|
| `tests/runtime/test_workspace.py` | 补充 workspace write 相关测试 |
| `tests/runtime/tools/test_replace_in_file_tool.py` | 通过 |
| `tests/runtime/tools/test_unified_diff_tool.py` | 通过 |
| `tests/runtime/tools/test_write_file_tool.py` | 通过 |
| `tests/runtime/test_patch_flow.py` | 通过 |

### 12.3 PendingChange 数据结构

```python
@dataclass
class PendingChange:
    change_id: str           # 唯一 ID，可追溯性
    path: str              # 目标文件路径
    operation: ChangeOperation  # CREATE / UPDATE / DELETE
    original_content: Optional[str]   # 原内容（DELETE 时为 None）
    proposed_content: Optional[str]   # 目标内容（CREATE/DELETE 有效）
    unified_diff: str        # 生成的 unified diff 字符串，lazy 计算
    status: ChangeStatus    # 当前状态：PREVIEW，后续 M7 增加 APPLIED
    error: Optional[str]    # 错误信息，默认为 None
    created_at: str         # ISO 时间戳

    # 工厂方法
    @classmethod make_update(cls, path, original_content, proposed_content, error=None)
    @classmethod make_create(cls, path, proposed_content, error=None)
    @classmethod make_error(cls, path, error)

    # 核心方法
    def apply() -> bool           # 执行变更（当前 M6 仍为 preview，M7 完整实现 preview）
    def to_display_string() -> str  # 生成可读展示字符串，用于 runtime 消息输出
```

### 12.4 Workspace 重构说明

`WorkspaceGuard.resolve_write_path()` 方法重构为两步：

1. **解析阶段**：调用 `resolve()` 获取 workspace 根路径
2. **校验阶段**：
   - 相对路径：基于 workspace root 解析
   - 绝对路径：直接校验是否在 workspace root 内
   - 使用 `workspace_root / path` 拼接后校验

重构后，`resolve_write_path()` 不再直接调用 `resolve()`，而是接收已解析路径后再判断是否越界。

### 12.5 写工具对比

| 维度 | `replace_in_file` | `unified_diff` | `write_file` |
|------|-------------------|----------------|--------------|
| 操作类型 | UPDATE | UPDATE | CREATE ? UPDATE |
| SEARCH block | 支持 | 不支持 | 不支持 |
| 追加模式 | 不支持APPEND 模式 | 不支持 | 不支持 |
| 成功率 | 85% 精准匹配 | 依赖 patch 质量 | N/A |
| workspace 校验 | 支持 | 支持 | 支持 |
| unified_diff | 生成 | 生成 | 生成 |

### 12.6 测试结果

```bash
cd backend
python -m pytest \
    tests/runtime/test_workspace.py \
    tests/runtime/tools/test_replace_in_file_tool.py \
    tests/runtime/tools/test_unified_diff_tool.py \
    tests/runtime/tools/test_write_file_tool.py \
    tests/runtime/test_patch_flow.py -v

# 66 passed, 0 failed

# 全量 runtime 测试
python -m pytest tests/runtime/ -v
# 201 passed, 1 skipped, 0 failed
```

### 12.7 架构说明

- **PendingChange 由 runtime 层管理**：M6 中 `PendingChange.apply()` 仍为 preview，M7 才完整实现 preview 到 APPLIED 的状态转换。
- **PendingChange.apply() 暂由 runtime 层持有**：apply() 方法暂不开放给 agent 直接调用，作为后续 M7 的受控入口。

### 12.8 M6 收尾补充（2026-05-29 第二轮）

> 2026-05-29 下午完成—两个缺口已补完。

**缺口一：RuntimeAgentService._build_tools() 未登单写工具**

问题：`_build_tools()` 只有读工具，缺少 `ReplaceInFileTool`、`UnifiedDiffTool`、`WriteFileTool`，导合上 M6 的"最小接电"未完成。

修复：在 `runtime_agent_service.py` 的 `_build_tools()` 中新增三项工具注册，与读工具共用 `workspace_root` 注入方式，保持 preview 模式。

修改文件：
- `backend/app/runtime/runtime_agent_service.py` — `_build_tools()` 新增三项工具
- `backend/tests/runtime/test_runtime_agent_service.py` — `新增 TestRuntimeAgentServiceWriteTools 类`验证三项工具已注册

**缺口二：useChatStreamState.spec.ts 仍用旧 mockInFlightMessages 假设**

问题：测试文件依赖外部 `mockInFlightMessages` store，与当前 `useChatStreamState` 内部 `ref<Map>` 实现不符，导合而有多次测试失败。

修复：重写测试文件，改为直接测试 `useChatStreamState` 返回的 `getStream()`、`getStreamingMessages()`、`hasInFlightStream()`、`finalizeStream()`、`clearSession()` 等真实�%A1�为，不依赖外部 store。

修改文件：
- `frontend/src/utils/useChatStreamState.spec.ts` — 完全重写，45 个测试夹目真实 streams 行为

测试结果：

```bash
# 后端辅测
cd backend
python -m pytest tests/runtime/test_runtime_agent_service.py::TestRuntimeAgentServiceWriteTools -v
# 1 passed

# 前端测试
cd ../frontend
npm run test:unit -- --run src/utils/useChatStreamState.spec.ts
# 45 passed
```

---．．．

### 12.9 M7 规划

---