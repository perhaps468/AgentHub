# 虚拟文件系统（VFS）设计规范

> 本文件是 `实施计划.md` 的 VFS 子文档，详细定义 VFS 的数据结构、
> Redis 存储方案、Accept/Reject 流程、落盘策略以及前后端接口。

---

## 1. 设计理念

### 1.1 核心原则

- **安全隔离**：AI 生成的代码在获得人类用户明确的 "Accept" 指令前，绝不允许直接写入物理硬盘
- **内存主导**：项目的当前状态（VFS Tree）由后端在 Redis 中维护，磁盘仅为最终落盘目的地
- **用户主权**：所有涉及文件变更的操作（创建/修改/删除）必须经过用户确认
- **版本追踪**：每次 Accept 后文件 version 自增，支持版本回溯（未来扩展）

### 1.2 与物理文件系统的关系

```
┌──────────────────────────────────────────────┐
│                  Redis                        │
│  files:{project_id} → {                       │
│    "/src/index.html": {"content": "...",      │
│                       "version": 1,            │
│                       "updated_at": "..."},   │
│    "/src/style.css": {...}                     │
│  }                                             │
└──────────────────────────────────────────────┘
                         ▲
                         │ Accept
                         ▼
┌──────────────────────────────────────────────┐
│              /tmp/agent-projects/            │
│              {project_id}/                    │
│                ├── src/                       │
│                │   ├── index.html             │
│                │   └── style.css             │
│                └── package.json              │
└──────────────────────────────────────────────┘
```

---

## 2. 数据结构

### 2.1 VFS 内存模型

```python
class VFSNode:
    path: str              # 文件路径，如 "/src/index.html"
    content: str           # 文件内容
    version: int           # 版本号，每次 Accept 后自增
    updated_at: str        # ISO 时间戳

class VFSState:
    project_id: str
    files: dict[str, VFSNode]  # 路径 → VFSNode
```

### 2.2 Redis 存储格式

```
Key: files:{project_id}
Type: HASH
TTL: 无（持久化直到项目被删除）
```

**Hash Field 结构**：

| Field（文件路径） | Value（JSON 字符串） |
|-------------------|---------------------|
| `/src/index.html` | `{"content": "<!DOCTYPE html>...", "version": 1, "updated_at": "2026-05-20T10:00:00Z"}` |
| `/src/style.css` | `{"content": "body { ... }", "version": 2, "updated_at": "2026-05-20T10:05:00Z"}` |

**VFS 快照（存入 PostgreSQL `projects.vfs_state`）**：

```json
{
  "project_id": "proj_abc123",
  "file_tree": [
    {"path": "/src/index.html", "type": "file", "version": 1},
    {"path": "/src/style.css", "type": "file", "version": 2},
    {"path": "/src", "type": "directory"}
  ],
  "last_updated": "2026-05-20T10:05:00Z"
}
```

> 注意：`projects.vfs_state` 只存元数据（文件树结构、版本号），不存文件内容。
> 文件内容统一存在 Redis Hash 中。

---

## 3. VFSService 核心方法

```python
class VFSService:
    """VFS 核心服务，所有文件操作必须通过此类"""

    async def get_file(self, project_id: str, file_path: str) -> VFSNode | None:
        """从 Redis 读取单个文件内容"""

    async def get_tree(self, project_id: str) -> list[dict]:
        """获取项目的完整文件树（不含内容）"""

    async def apply_diff(self, diff: CodeDiff) -> VFSNode:
        """将 Diff 应用到 VFS（仅内存，不落盘）：
        1. 从 Redis 读取 old_content
        2. 替换为 new_content
        3. version++
        4. 写回 Redis
        """

    async def accept_diff(self, diff_id: str) -> list[str]:
        """用户 Accept Diff：
        1. 读取 Diff 信息
        2. apply_diff 更新 Redis
        3. 落盘到 /tmp/agent-projects/{project_id}/
        4. 更新 PostgreSQL code_diffs.status = 'accepted'
        5. 返回更新后的文件路径列表
        """

    async def reject_diff(self, diff_id: str) -> None:
        """用户 Reject Diff：
        1. 更新 code_diffs.status = 'rejected'
        2. 不修改 VFS
        """

    async def persist_to_disk(self, project_id: str, file_paths: list[str]) -> None:
        """将指定文件从 Redis 写入磁盘：
        1. 确保目录存在（os.makedirs）
        2. 写入文件（aiofiles 异步写）
        """

    async def delete_project(self, project_id: str) -> None:
        """删除项目：
        1. 删除 Redis VFS
        2. 删除磁盘文件
        3. 更新 PostgreSQL projects.status = 'deleted'
        """
```

---

## 4. Accept/Reject 完整流程

### 4.1 Accept 流程

```
用户点击 "Accept"
    │
    ▼
前端发送 WebSocket 消息：
{
    "action": "accept_code",
    "diff_id": "diff_001"
}
    │
    ▼
后端 VFSService.accept_diff("diff_001")
    │
    ├─ 1. 从 code_diffs 表读取 Diff（old_content, new_content, file_path, project_id）
    │
    ├─ 2. 从 Redis 读取当前文件版本
    │
    ├─ 3. 验证 old_content 与 Redis 中的一致（防止并发冲突）
    │   └─ 不一致 → 返回 error 消息，提示 "文件已被其他 Diff 修改，请重新生成"
    │
    ├─ 4. 更新 Redis Hash：
    │      files:{project_id}[file_path] = {
    │          "content": new_content,
    │          "version": old_version + 1,
    │          "updated_at": NOW()
    │      }
    │
    ├─ 5. 创建目录结构（如果不存在）：
    │      /tmp/agent-projects/{project_id}/{file_path} 的父目录
    │
    ├─ 6. 异步落盘（aiofiles）：
    │      写入 /tmp/agent-projects/{project_id}/{file_path}
    │
    ├─ 7. 更新 PostgreSQL：
    │      code_diffs.status = 'accepted'
    │
    └─ 8. 推送 WebSocket 消息给前端：
           {
               "type": "vfs_update",
               "action": "update",
               "file_path": "/src/index.html",
               "version": 2,
               "diff_id": "diff_001"
           }
    │
    ▼
前端更新文件树，重新渲染 Diff 卡片状态为 "accepted"
```

### 4.2 Reject 流程

```
用户点击 "Reject"
    │
    ▼
前端发送 WebSocket 消息：
{
    "action": "reject_code",
    "diff_id": "diff_001"
}
    │
    ▼
后端 VFSService.reject_diff("diff_001")
    │
    ├─ 1. 更新 PostgreSQL code_diffs.status = 'rejected'
    │
    ├─ 2. 推送 WebSocket 消息给前端：
           {
               "type": "vfs_update",
               "action": "rejected",
               "diff_id": "diff_001"
           }
    │
    └─ 3. 触发 Coder 重新生成（携带拒绝原因）：
           将 [REJECT] 消息加入 messages，
           进入下一轮 coding → review 循环
    │
    ▼
前端更新 Diff 卡片状态为 "rejected"，等待新 Diff
```

### 4.3 并发冲突处理

如果用户 Accept 时，Redis 中的文件版本与 Diff 的 old_content 不一致（说明有其他 Diff 在此之前被 Accept），返回错误：

```json
{
    "type": "error",
    "message": "文件已被其他 Diff 修改，请等待新版本 Diff",
    "diff_id": "diff_001",
    "conflict_version": 3
}
```

前端收到后，提示用户"有新版本 Diff"，并请求后端重新生成针对最新版本的 Diff。

---

## 5. 预览服务

### 5.1 预览路由

```
GET /api/preview/{project_id}/<path:path>
```

示例：
- `GET /api/preview/proj_abc123/src/index.html` → 返回 `/tmp/agent-projects/proj_abc123/src/index.html`

### 5.2 响应头

```python
Content-Type: 根据文件扩展名推断
    .html → text/html
    .css  → text/css
    .js   → application/javascript
    .json → application/json
    其他  → text/plain

X-VFS-Version: <file_version>  # 文件当前版本号
```

### 5.3 错误处理

| 情况 | HTTP 状态码 | 响应 |
|------|-------------|------|
| 项目不存在 | 404 | `{"error": "Project not found"}` |
| 文件不存在 | 404 | `{"error": "File not found"}` |
| 文件未 Accept（仍在 VFS 内存中，未落盘） | 404 | `{"error": "File not yet persisted"}` |

---

## 6. 前端 VFS Panel

### 6.1 组件结构

```
ProjectView.vue
├── FileTree.vue          # 左侧文件树
│   ├── TreeNode.vue      # 递归文件树节点（文件夹/文件）
│   └── FileContextMenu.vue  # 右键菜单（新建/删除/重命名）
└── FileContent.vue       # 右侧文件预览（只读）
```

### 6.2 文件树交互

| 操作 | 前端行为 | 后端行为 |
|------|----------|----------|
| 点击文件 | 请求 `/api/preview/{project_id}/{file_path}` | 从磁盘读取文件内容返回 |
| 右键新建文件 | 弹出输入框 → `useVFS.createFile()` | 更新 Redis VFS（但不落盘，直到 Accept） |
| 右键删除文件 | 确认弹窗 → `useVFS.deleteFile()` | 从 Redis VFS 删除 |
| 展开文件夹 | 展示子文件列表 | 无需后端（前端根据树结构展开） |

### 6.3 Diff 卡片与文件树的联动

当 CodeDiffCard 收到 `pending` 状态的 Diff 时：
1. 在文件树中用黄色高亮显示目标文件
2. 显示 "待应用" 标签
3. 用户 Accept 后：
   - 黄色高亮变为绿色
   - 文件内容更新
   - 标签变为 "已应用 (v2)"

---

## 7. 目录结构模板

当用户新建项目时，自动创建以下基础结构（写入 Redis VFS，但不落盘）：

```json
{
  "file_tree": [
    {"path": "/index.html", "type": "file", "version": 0},
    {"path": "/src", "type": "directory"}
  ]
}
```

用户可以通过前端手动添加更多目录结构。
