# AgentHub 数据库设计文档

> 状态：`future-reference`
>
> 本文件描述的是较完整的数据模型候选，适合后续阶段参考。
> 当前 MVP 不应直接采用本文全部表结构；若与 OpenSpec 的当前阶段范围冲突，以 OpenSpec 为准。

---

## 1. ER 关系图（文字版）

```
users (1) ──────< (N) projects
users (1) ──────< (N) chat_sessions
users (1) ──────< (N) agents
agents (N) >────< (N) chat_sessions  (via session_participants)

projects (1) ────< (N) chat_sessions
projects (1) ────< (N) messages
projects (1) ────< (N) tasks
projects (1) ────< (N) code_diffs

chat_sessions (1) ────< (N) messages
chat_sessions (1) ────< (N) tasks
chat_sessions (1) >────< (N) session_participants

messages (1) ────< (N) messages  (self-referential: parent_message_id)
messages (1) ────< (N) code_diffs
```

---

## 2. 表结构定义

### 2.1 users（用户表）

> MVP 阶段只预置一条 `dev_user` 记录，后续可扩展为完整用户体系。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | CHAR(36) | PRIMARY KEY, DEFAULT `(UUID())` | 用户唯一标识（MySQL UUID 格式） |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**MySQL DDL**:
```sql
CREATE TABLE users (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    username VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 2.2 agents（Agent 表）

> 存储所有 Agent 的配置信息，包括系统提示词、角色、能力等。
> MVP 阶段预置 4 个默认 Agent（PM、Planner、Coder、Reviewer）。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | CHAR(36) | PRIMARY KEY, DEFAULT `(UUID())` | Agent 唯一标识 |
| name | VARCHAR(100) | NOT NULL | 显示名称 |
| role | VARCHAR(50) | NOT NULL | 角色：PM/Planner/Coder/Reviewer |
| provider | VARCHAR(50) | NOT NULL | 提供者：claude/openai/ollama |
| model | VARCHAR(100) | | 具体模型，如 `claude-sonnet-4-20250514` |
| system_prompt | TEXT | | Agent 系统提示词 |
| avatar_url | VARCHAR(500) | | 头像 URL |
| capabilities | JSON | DEFAULT `('[]')` | 能力标签列表 `["code_generation", "review"]` |
| created_by | CHAR(36) | REFERENCES `users(id)` | 创建者（NULL 表示系统预置） |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**MySQL DDL**:
```sql
CREATE TABLE agents (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(100) NOT NULL,
    role VARCHAR(50) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    model VARCHAR(100),
    system_prompt TEXT,
    avatar_url VARCHAR(500),
    capabilities JSON DEFAULT ('[]'),
    created_by CHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_agents_created_by FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_agents_role ON agents(role);
CREATE INDEX idx_agents_created_by ON agents(created_by);
```

---

### 2.3 projects（项目表）

> 每个项目对应一个独立的 VFS 工作空间。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | CHAR(36) | PRIMARY KEY, DEFAULT `(UUID())` | 项目唯一标识 |
| owner_id | CHAR(36) | REFERENCES `users(id)` | 所有者 |
| name | VARCHAR(200) | NOT NULL | 项目名称 |
| description | TEXT | | 项目描述 |
| vfs_state | JSON | DEFAULT `('{}')` | 当前 VFS 的目录树快照（仅元数据，文件内容在 Redis） |
| status | VARCHAR(20) | DEFAULT `'active'` | 状态：active/archived/deleted |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**MySQL DDL**:
```sql
CREATE TABLE projects (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    owner_id CHAR(36),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    vfs_state JSON DEFAULT ('{}'),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_projects_owner FOREIGN KEY (owner_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_projects_owner ON projects(owner_id);
CREATE INDEX idx_projects_status ON projects(status);
```

---

### 2.4 chat_sessions（会话表）

> 每个会话归属于一个项目，支持单聊（single）和群聊（group，P2）两种模式。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | CHAR(36) | PRIMARY KEY, DEFAULT `(UUID())` | 会话唯一标识 |
| project_id | CHAR(36) | REFERENCES `projects(id)` ON DELETE CASCADE | 所属项目 |
| owner_id | CHAR(36) | REFERENCES `users(id)` | 创建者 |
| title | VARCHAR(200) | | 会话标题（可自动生成） |
| mode | VARCHAR(20) | DEFAULT `'single'` | single（单聊）/ group（群聊） |
| is_pinned | TINYINT(1) | DEFAULT 0 | 是否置顶（MySQL 使用 TINYINT 代替 BOOLEAN） |
| is_archived | TINYINT(1) | DEFAULT 0 | 是否归档 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**MySQL DDL**:
```sql
CREATE TABLE chat_sessions (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    project_id CHAR(36),
    owner_id CHAR(36),
    title VARCHAR(200),
    mode VARCHAR(20) DEFAULT 'single',
    is_pinned TINYINT(1) DEFAULT 0,
    is_archived TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_sessions_project FOREIGN KEY (project_id) REFERENCES projects(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_sessions_owner FOREIGN KEY (owner_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_sessions_project ON chat_sessions(project_id);
CREATE INDEX idx_sessions_owner ON chat_sessions(owner_id);
CREATE INDEX idx_sessions_updated ON chat_sessions(updated_at DESC);
```

---

### 2.5 session_participants（会话参与者表）

> P2 实现。记录群聊中参与的 Agent，支持多对多关系。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| session_id | CHAR(36) | REFERENCES `chat_sessions(id)` ON DELETE CASCADE | 会话 ID |
| agent_id | CHAR(36) | REFERENCES `agents(id)` ON DELETE CASCADE | Agent ID |
| joined_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 加入时间 |
| **PK** | | (session_id, agent_id) | 复合主键 |

**MySQL DDL**:
```sql
CREATE TABLE session_participants (
    session_id CHAR(36),
    agent_id CHAR(36),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (session_id, agent_id),
    CONSTRAINT fk_participants_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_participants_agent FOREIGN KEY (agent_id) REFERENCES agents(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

### 2.6 messages（消息表）

> 核心聊天记录表，支持多种内容类型和引用关系。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | CHAR(36) | PRIMARY KEY, DEFAULT `(UUID())` | 消息唯一标识 |
| session_id | CHAR(36) | REFERENCES `chat_sessions(id)` ON DELETE CASCADE | 所属会话 |
| sender_type | VARCHAR(20) | NOT NULL | 发送者类型：human/agent/system |
| sender_id | CHAR(36) | | 发送者 ID（user_id 或 agent_id） |
| sender_role | VARCHAR(50) | | 发送者角色：Human/PM/Planner/Coder/Reviewer/System |
| content | TEXT | NOT NULL | 消息内容 |
| content_type | VARCHAR(20) | DEFAULT `'text'` | 内容类型：text/code/image/file/diff/preview |
| metadata | JSON | DEFAULT `('{}')` | 附加信息：code_diff/file_path/preview_url 等 |
| is_pinned | TINYINT(1) | DEFAULT 0 | 是否置顶（长期上下文） |
| parent_message_id | CHAR(36) | REFERENCES `messages(id)` | 回复引用的消息 ID |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**MySQL DDL**:
```sql
CREATE TABLE messages (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    session_id CHAR(36),
    sender_type VARCHAR(20) NOT NULL,
    sender_id CHAR(36),
    sender_role VARCHAR(50),
    content TEXT NOT NULL,
    content_type VARCHAR(20) DEFAULT 'text',
    metadata JSON DEFAULT ('{}'),
    is_pinned TINYINT(1) DEFAULT 0,
    parent_message_id CHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_messages_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_messages_parent FOREIGN KEY (parent_message_id) REFERENCES messages(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_sender ON messages(sender_id);
CREATE INDEX idx_messages_created ON messages(created_at);
CREATE INDEX idx_messages_parent ON messages(parent_message_id);
```

---

### 2.7 tasks（任务表）

> 存储 Planner 输出的任务 DAG，支持父子任务关系。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | CHAR(36) | PRIMARY KEY, DEFAULT `(UUID())` | 任务唯一标识 |
| project_id | CHAR(36) | REFERENCES `projects(id)` ON DELETE CASCADE | 所属项目 |
| session_id | CHAR(36) | REFERENCES `chat_sessions(id)` | 关联会话 |
| parent_task_id | CHAR(36) | REFERENCES `tasks(id)` | 父任务 ID（支持任务嵌套） |
| title | VARCHAR(500) | NOT NULL | 任务标题 |
| description | TEXT | | 任务描述 |
| status | VARCHAR(20) | DEFAULT `'pending'` | 状态：pending/doing/done/rejected |
| assignee | VARCHAR(50) | | 负责人（Agent 角色） |
| priority | INT | DEFAULT 0 | 优先级（数字越大优先级越高） |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP | 更新时间 |

**MySQL DDL**:
```sql
CREATE TABLE tasks (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    project_id CHAR(36),
    session_id CHAR(36),
    parent_task_id CHAR(36),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    assignee VARCHAR(50),
    priority INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_tasks_project FOREIGN KEY (project_id) REFERENCES projects(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tasks_session FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tasks_parent FOREIGN KEY (parent_task_id) REFERENCES tasks(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_session ON tasks(session_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assignee ON tasks(assignee);
CREATE INDEX idx_tasks_parent ON tasks(parent_task_id);
```

---

### 2.8 code_diffs（代码 Diff 表）

> 存储 Coder Agent 生成的每一个 Code Diff 及其状态。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | CHAR(36) | PRIMARY KEY, DEFAULT `(UUID())` | Diff 唯一标识 |
| message_id | CHAR(36) | REFERENCES `messages(id)` ON DELETE CASCADE | 关联消息 |
| project_id | CHAR(36) | REFERENCES `projects(id)` ON DELETE CASCADE | 所属项目 |
| file_path | VARCHAR(500) | NOT NULL | 文件路径（相对于项目根目录） |
| old_content | TEXT | | 修改前内容（新增文件时为空） |
| new_content | TEXT | NOT NULL | 修改后内容（完整文件内容） |
| diff_summary | TEXT | | Diff 摘要描述 |
| status | VARCHAR(20) | DEFAULT `'pending'` | 状态：pending/accepted/rejected |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**MySQL DDL**:
```sql
CREATE TABLE code_diffs (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    message_id CHAR(36),
    project_id CHAR(36),
    file_path VARCHAR(500) NOT NULL,
    old_content TEXT,
    new_content TEXT NOT NULL,
    diff_summary TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_diffs_message FOREIGN KEY (message_id) REFERENCES messages(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_diffs_project FOREIGN KEY (project_id) REFERENCES projects(id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_diffs_project ON code_diffs(project_id);
CREATE INDEX idx_diffs_status ON code_diffs(status);
CREATE INDEX idx_diffs_message ON code_diffs(message_id);
```

---

## 3. Redis 数据结构

> Redis 用于存储 VFS 文件内容（高性能读写）和会话状态（TTL 管理）。

### 3.1 VFS 文件内容

```
Key: files:{project_id}
Type: HASH
Field: 文件路径 (如 "/src/index.html")
Value: JSON字符串 {"content": "...", "version": 1, "updated_at": "..."}
TTL: 无（持久化直到项目删除）
```

### 3.2 LangGraph 会话状态

```
Key: graph_state:{session_id}
Type: STRING (JSON)
Value: AgentState 序列化后的 JSON
TTL: 1小时（无活动自动清理）
```

### 3.3 WebSocket 在线状态

```
Key: ws_active:{session_id}
Type: SET
Members: [user_id, agent_ids...]
TTL: 与 WebSocket 连接生命周期同步
```

---

## 4. Alembic 迁移规范

### 4.1 迁移文件命名

```
{version}_{short_description}.py
示例：001_initial_schema.py, 002_add_agents_table.py
```

### 4.2 迁移原则

- **禁止手动修改已有迁移**：所有表结构变更必须通过新迁移文件
- **向后兼容**：ALTER TABLE 只允许 ADD COLUMN（禁止 DROP/RENAME 已有的列）
- **数据迁移**：涉及数据变更的迁移需在 `upgrade()` 和 `downgrade()` 中同时处理
- **MySQL 注意事项**：MySQL 的 VARCHAR 需要显式指定长度，JSON 类型需使用 `server_default` 或表达式默认值

### 4.3 种子数据

在 `alembic/seed_data/` 目录下存放 SQL 种子文件：
- `001_dev_user.sql`：预置 `dev_user`
- `002_default_agents.sql`：预置 PM/Planner/Coder/Reviewer 四个默认 Agent

---

## 5. MySQL 与 PostgreSQL 主要差异说明

| 差异点 | PostgreSQL | MySQL 8.0 |
|--------|------------|-----------|
| UUID 主键 | `UUID PRIMARY KEY DEFAULT gen_random_uuid()` | `CHAR(36) PRIMARY KEY DEFAULT (UUID())` |
| 布尔类型 | `BOOLEAN` | `TINYINT(1)`（MySQL 无原生 BOOLEAN alias） |
| JSON 类型 | `JSONB`（二进制，索引友好） | `JSON`（文本，函数处理） |
| 自动时间戳 | `TIMESTAMP DEFAULT NOW()` | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` |
| 自动更新时间 | 需触发器或手动维护 | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP` |
| 全文搜索 | `tsvector` + `ts_query` | `MATCH(...) AGAINST(...) IN NATURAL LANGUAGE MODE` |
| 字符集默认 | `UTF8`（3字节） | 建议 `utf8mb4`（4字节，支持 emoji） |
| 外键约束名 | 自动生成 | 建议显式命名以便维护 |

---

## 6. 索引设计说明

| 表 | 索引 | 用途 |
|----|------|------|
| agents | `idx_agents_role` | 按角色查询 Agent 列表 |
| chat_sessions | `idx_sessions_project` | 获取项目的所有会话 |
| chat_sessions | `idx_sessions_updated` | 按最近活动时间排序会话列表 |
| messages | `idx_messages_session` | 获取会话的所有历史消息 |
| messages | `idx_messages_parent` | 获取有引用的消息（回复功能） |
| tasks | `idx_tasks_session` | 获取会话关联的任务列表 |
| tasks | `idx_tasks_status` | 按状态筛选任务 |
| code_diffs | `idx_diffs_project` | 获取项目的所有 Diff |
| code_diffs | `idx_diffs_status` | 筛选待处理的 Diff（pending） |
