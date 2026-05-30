# Phase 3：Code Agent 能力

> 本文档描述 Phase 3 的具体实施步骤：让 Agent 具备文件操作、Diff 和 Workspace 隔离能力。

## 3.1 FileTool 实现

### 3.1.1 工具列表

Phase3 需要实现的文件操作工具：

| 工具名 | quantalogic 来源 | 说明 |
|--------|-----------------|------|
| `read_file` | `ReadFileTool` | 读取文件内容，支持路径限制 |
| `write_file` | `WriteFileTool` | 写入文件内容，支持创建/覆盖 |
| `edit_file` | `ReplaceInFileTool` | 替换文件中指定内容 |
| `list_directory` | `ListDirectoryTool` | 列出目录内容 |
| `read_file_block` | `ReadFileBlockTool` | 读取文件的指定行范围 |

### 3.1.2 ReadFileTool 适配

**quantalogic 原版**（无沙盒限制）：

```python
class ReadFileTool(Tool):
    def __init__(self):
        super().__init__(name="read_file", ...)

    def execute(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
```

**AgentHub 适配版**（带沙盒 + ToolContext）：

```python
# agents/tools/file_tool.py
class ReadFileTool(Tool):
    def __init__(self):
        super().__init__(
            name="read_file",
            description="Read the complete contents of a file from the file system.",
            ...
        )

    def execute(self, file_path: str, context: ToolContext | None = None) -> str:
        path = Path(file_path)

        # 沙盒检查
        if context is not None and not context.is_path_allowed(path):
            return f"Error: Access denied. Path '{file_path}' is outside workspace."

        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File '{file_path}' not found."
        except PermissionError:
            return f"Error: Permission denied when reading '{file_path}'."
        except UnicodeDecodeError:
            return f"Error: Unable to decode '{file_path}' as UTF-8."
```

### 3.1.3 WriteFileTool 适配

**AgentHub 适配版**（带沙盒 + 安全检查）：

```python
class WriteFileTool(Tool):
    def __init__(self):
        super().__init__(
            name="write_file",
            description="Create or overwrite a file with the given content.",
            ...
        )

    def execute(
        self,
        file_path: str,
        content: str,
        context: ToolContext | None = None,
    ) -> str:
        path = Path(file_path)

        # 沙盒检查
        if context is not None and not context.is_path_allowed(path):
            return f"Error: Access denied. Path '{file_path}' is outside workspace."

        # 安全检查：禁止写入可执行文件
        forbidden_extensions = {".sh", ".bat", ".ps1", ".exe", ".dll"}
        if path.suffix.lower() in forbidden_extensions:
            return f"Error: Writing files with extension '{path.suffix}' is not allowed."

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to '{file_path}' ({len(content)} bytes)"
        except PermissionError:
            return f"Error: Permission denied when writing '{file_path}'."
```

## 3.2 Diff System 实现

### 3.2.1 UnifiedDiffTool

基于 quantalogic 的 `UnifiedDiffTool`，适配沙盒和 ToolContext：

```python
# agents/tools/diff_tool.py
class UnifiedDiffTool(Tool):
    """Compute unified diff between two files or file versions."""

    def __init__(self):
        super().__init__(
            name="unified_diff",
            description="Compute a unified diff between two file versions.",
            ...
        )

    def execute(
        self,
        file_path: str,
        original_content: str,
        modified_content: str,
        context: ToolContext | None = None,
    ) -> str:
        path = Path(file_path)

        if context is not None and not context.is_path_allowed(path):
            return "Error: Access denied."

        import difflib
        diff = difflib.unified_diff(
            original_content.splitlines(keepends=True),
            modified_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )
        return "".join(diff) or "No differences found."
```

### 3.2.2 Diff 状态追踪

在 Agent 级别追踪文件变更状态：

```python
# agents/models/diff_state.py
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum

class FileState(Enum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    CREATED = "created"
    DELETED = "deleted"

@dataclass
class FileDiff:
    path: Path
    state: FileState
    original_content: str | None = None
    modified_content: str | None = None
    diff_text: str | None = None

class DiffTracker:
    """追踪 Agent 运行期间的文件变更"""

    def __init__(self):
        self._diffs: dict[str, FileDiff] = {}

    def record_write(self, path: Path, content: str, context: ToolContext) -> None:
        """记录写操作"""
        key = str(path)
        existing = self._diffs.get(key)
        original = existing.modified_content if existing else ""
        diff_text = self._compute_diff(path, original or "", content, context)
        self._diffs[key] = FileDiff(
            path=path,
            state=FileState.CREATED if not existing else FileState.MODIFIED,
            original_content=original,
            modified_content=content,
            diff_text=diff_text,
        )

    def get_summary(self) -> list[dict]:
        """获取变更摘要"""
        return [
            {
                "path": str(d.path),
                "state": d.state.value,
                "diff": d.diff_text,
            }
            for d in self._diffs.values()
        ]
```

## 3.3 Workspace 隔离与 Sandbox

### 3.3.1 Workspace 模型

AgentHub 需要一个 Workspace 概念作为 Agent 的"工作目录"：

```python
# agents/models/workspace.py
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Workspace:
    id: str
    name: str
    base_path: Path           # 沙盒根路径
    project_id: str
    owner_id: str
    created_at: datetime

    def resolve_path(self, relative_path: str) -> Path:
        """将相对路径解析为沙盒内绝对路径"""
        return (self.base_path / relative_path).resolve()

    def is_safe_path(self, path: Path) -> bool:
        """检查路径是否在沙盒内"""
        try:
            path.resolve().relative_to(self.base_path.resolve())
            return True
        except ValueError:
            return False
```

### 3.3.2 Sandbox 实现

每个 Workspace 对应一个真实目录（或容器），Agent 的所有文件操作都限制在该目录内：

```
# Workspace 目录结构
/workspaces/{workspace_id}/
├── .agent_history/          # Agent 运行历史
├── .cache/                  # 临时缓存
└── {project_files}/         # 用户项目文件
```

**安全边界**：

1. **路径限制**：所有 Tool 调用时，工具实现必须检查 `context.is_path_allowed()`
2. **禁止符号链接逃逸**：解析真实路径后再次检查是否在 base_path 内
3. **禁止危险操作**：`.sh` / `.bat` / `.ps1` / `.exe` 等文件禁止写入
4. **禁止父目录遍历**：Tool 实现禁止 `../` 路径遍历

### 3.3.3 Workspace 创建时机

```python
# agents/adapters/workspace_manager.py
class WorkspaceManager:
    """Workspace 生命周期管理"""

    def __init__(self, base_dir: Path = Path("/workspaces")):
        self._base_dir = base_dir
        self._workspaces: dict[str, Workspace] = {}

    async def create_workspace(
        self,
        workspace_id: str,
        project_id: str,
        owner_id: str,
    ) -> Workspace:
        workspace_path = self._base_dir / workspace_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        workspace = Workspace(
            id=workspace_id,
            name=f"workspace-{workspace_id[:8]}",
            base_path=workspace_path,
            project_id=project_id,
            owner_id=owner_id,
            created_at=datetime.utcnow(),
        )
        self._workspaces[workspace_id] = workspace
        return workspace

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        return self._workspaces.get(workspace_id)
```

## 3.4 ToolContext 与 Session/Project 模型绑定

### 3.4.1 绑定关系

```
User
  └── Project（项目，一个用户可以有多个项目）
        └── Workspace（工作空间，对应一个沙盒目录）
              └── Session（会话，一次对话）
                    └── Message（消息历史）
                          └── ToolContext（在 Agent 运行时携带）
```

### 3.4.2 ToolContext 创建流程

```python
# agents/adapters/workspace_manager.py
def create_tool_context(
    session_id: str,
    workspace: Workspace,
    user_id: str,
) -> ToolContext:
    """为一次 Agent 运行创建 ToolContext"""
    return ToolContext(
        workspace_id=workspace.id,
        project_id=workspace.project_id,
        session_id=session_id,
        user_id=user_id,
        base_path=workspace.base_path,
        allowed_patterns=["*"],
        denied_patterns=["../", "/etc/", "/root/", "/.ssh/"],
    )
```

### 3.4.3 工具注入 ToolContext

在 Agent 执行工具时，将 ToolContext 注入：

```python
# agents/runtime/agent.py 修改
async def _async_execute_tool(
    self,
    tool_name: str,
    tool: Tool,
    arguments_with_values: dict,
) -> tuple[str, Any]:
    # 将 ToolContext 注入到参数中
    if hasattr(tool, "supports_context"):
        arguments_with_values["context"] = self._tool_context

    # 执行工具
    response = await tool.async_execute(**arguments_with_values)
    return tool.name, response
```

### 3.4.4 Session 历史持久化

Agent 的 `AgentMemory` 需要与 AgentHub 的 `Message` 模型对接：

```python
# agents/adapters/memory_persister.py
class MemoryPersister:
    """将 Agent 运行时记忆持久化到数据库"""

    def __init__(self, db: Session):
        self._db = db

    def load_history(self, session_id: str) -> list[Message]:
        """从数据库加载会话历史到 AgentMemory"""
        messages = self._db.query(Message).filter(
            Message.session_id == session_id
        ).order_by(Message.created_at).all()
        return [Message(role=m.sender_type, content=m.content) for m in messages]

    def save_message(self, session_id: str, role: str, content: str) -> None:
        """保存单条消息到数据库"""
        msg = Message(
            session_id=session_id,
            sender_type=role,
            content=content,
            type="text",
            status="completed",
        )
        self._db.add(msg)
        self._db.commit()
```

## 3.5 实施步骤

### Step 1：实现基础文件工具

1. 创建 `agents/tools/file_tool.py`（ReadFileTool / WriteFileTool / ListDirectoryTool）
2. 每个 Tool 实现都接收 `context: ToolContext` 参数
3. 实现路径安全检查

### Step 2：实现 Diff 系统

1. 创建 `agents/tools/diff_tool.py`（UnifiedDiffTool）
2. 创建 `agents/models/diff_state.py`（DiffTracker）
3. 在 Agent 运行结束后生成变更摘要

### Step 3：实现 Workspace 隔离

1. 创建 `agents/models/workspace.py`（Workspace 数据类）
2. 创建 `agents/adapters/workspace_manager.py`（WorkspaceManager）
3. 实现目录创建、路径安全检查

### Step 4：集成 ToolContext

1. 修改 Agent 的 `_async_execute_tool`，注入 ToolContext
2. 修改 `agents/tools/` 下所有工具，支持 context 参数
3. 实现 `MemoryPersister` 对接数据库

### Step 5：端到端测试

1. 通过 ws.py 发送消息，验证 Agent 能读取/写入沙盒内文件
2. 验证 `../` 路径遍历被拦截
3. 验证 Diff 变更摘要正确生成
