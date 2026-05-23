# 阶段 0+1：工程骨架 + IM 核心体验 — 详细实现指南

---

## 前置说明

### 技术决策汇总

| 决策项 | 选择 | 说明 |
|--------|------|------|
| 用户身份验证 | 极简方案 | MVP 只有 dev_user，WebSocket 通过 query 参数传 `user_id`，不引入 JWT |
| 前端 UI | 极简 CSS | 不引入 UI 库，用 minimal CSS 快速验证 IM 核心体验 |
| Project 创建时机 | 自动创建 | 创建 Session 时自动创建空白 Project 和 Redis VFS |
| Agent 回复策略 | Echo | 骨架阶段 Agent 直接 Echo 用户消息，不接 LLM |
| MySQL / Redis | 本地连接 | 连接宿主机本地 MySQL 8.0 + Redis 7，不使用 Docker |
| Alembic 迁移 | 直接运行 | `alembic upgrade head` 直接作用在本地数据库 |

### 依赖关系图

```
Step 1 (Monorepo 骨架)
    ↓
Step 2 (本地 MySQL/Redis 连接 + 建库 + 数据导入)
    ↓
Step 3 (FastAPI 入口 + 模块目录结构就位) ←→ Step 4 (Alembic 迁移)
    ↓
Step 5 (Session CRUD) ←→ Step 6 (Message 历史)
    ↓
Step 7 (WebSocket 连接管理) ←→ Step 8 (Echo 消息收发)
    ↓
Step 9 (前端极简 UI)
    ↓
Step 10: 前后端联调验收
```

---

## Step 1：Monorepo 工程骨架

### 目标

搭建 pnpm workspace + Turborepo 骨架，前后端可独立启动、相互独立。

### 新建文件

| 文件 | 用途 |
|------|------|
| `pnpm-workspace.yaml` | 定义 workspace 包含 `frontend` 和 `backend` |
| `package.json`（根） | 项目元信息、scripts、engines（node>=18, pnpm>=8） |
| `turbo.json` | Turborepo pipeline（dev / build / lint） |
| `.nvmrc` | Node 18 |
| `.gitignore` | node_modules/、__pycache__/、.venv/、.env、dist/ |
| `frontend/package.json` | Vue 3 + Vite + TypeScript + Vue Router + Pinia + Axios |
| `frontend/vite.config.ts` | path alias `@/` → `src/`，proxy `/api` 到 `localhost:8000` |
| `frontend/tsconfig.json` | path aliases、`strict: true` |
| `frontend/index.html` | `<div id="app">` |
| `frontend/src/main.ts` | `createApp(App).use(router).use(pinia).mount('#app')` |
| `frontend/src/App.vue` | `<router-view />` |
| `frontend/src/router/index.ts` | `/` → `/chat` 重定向 |
| `frontend/src/styles/base.css` | minimal reset + CSS vars |
| `shared/index.ts` | 跨端共享 TypeScript 类型（已有则跳过） |
| `shared/schemas/ws_messages.json` | WebSocket 消息协议 Schema（已有则跳过） |

### 验收标准

- `pnpm install` 成功，无冲突
- `pnpm --filter frontend dev` 启动前端，`localhost:5173` 可访问
- `pnpm -F backend` 显示可用（backend 目录存在）

---

## Step 2：本地 MySQL / Redis 连接 + 建库 + 数据导入

### 目标

连接到本机已安装的 MySQL 和 Redis，创建 `agenthub` 数据库，导入初始表结构，并塞入 seed 数据。

### 准备工作

**假设本机环境：**
- MySQL 8.0 监听 `localhost:3306`，root 密码 `root`
- Redis 7 监听 `localhost:6379`，无密码
- `mysql` 和 `redis-cli` 命令行工具已安装

**如果本机没有 MySQL / Redis：** 用户自行安装（brew install mysql redis / apt install mysql-server redis-server）。

### 步骤 1：创建数据库

```sql
CREATE DATABASE IF NOT EXISTS agenthub
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 步骤 2：手动建表（等效于 Step 4 的 Alembic 迁移，MVP 阶段直接执行）

按外键依赖顺序执行以下 DDL（来自 `database-schema.md`）：

```sql
-- ① users（无外键）
CREATE TABLE users (
  id CHAR(36) PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  email VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ② agents（无外键）
CREATE TABLE agents (
  id CHAR(36) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  role VARCHAR(50) NOT NULL,
  provider VARCHAR(50),
  model VARCHAR(100),
  system_prompt TEXT,
  avatar_url VARCHAR(500),
  capabilities JSON,
  created_by CHAR(36),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ③ projects（依赖 users）
CREATE TABLE projects (
  id CHAR(36) PRIMARY KEY,
  owner_id CHAR(36) NOT NULL,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  vfs_state JSON,
  status VARCHAR(20) DEFAULT 'active',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_owner (owner_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ④ chat_sessions（依赖 users, projects）
CREATE TABLE chat_sessions (
  id CHAR(36) PRIMARY KEY,
  project_id CHAR(36) NOT NULL,
  owner_id CHAR(36) NOT NULL,
  title VARCHAR(255),
  mode VARCHAR(20) DEFAULT 'single',
  is_pinned TINYINT(1) DEFAULT 0,
  is_archived TINYINT(1) DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_owner (owner_id),
  INDEX idx_updated (owner_id, is_archived, is_pinned, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ⑤ messages（依赖 chat_sessions）
CREATE TABLE messages (
  id CHAR(36) PRIMARY KEY,
  session_id CHAR(36) NOT NULL,
  sender_type ENUM('human','agent','system') NOT NULL,
  sender_id CHAR(36),
  sender_role VARCHAR(50),
  content TEXT,
  content_type VARCHAR(20) DEFAULT 'text',
  metadata JSON,
  is_pinned TINYINT(1) DEFAULT 0,
  parent_message_id CHAR(36),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL,
  INDEX idx_session_time (session_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ⑥ tasks（依赖 projects, chat_sessions）
CREATE TABLE tasks (
  id CHAR(36) PRIMARY KEY,
  project_id CHAR(36) NOT NULL,
  session_id CHAR(36),
  parent_task_id CHAR(36),
  title VARCHAR(255) NOT NULL,
  description TEXT,
  status VARCHAR(20) DEFAULT 'pending',
  assignee VARCHAR(100),
  priority INT DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE SET NULL,
  FOREIGN KEY (parent_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
  INDEX idx_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ⑦ code_diffs（依赖 messages, projects）
CREATE TABLE code_diffs (
  id CHAR(36) PRIMARY KEY,
  message_id CHAR(36) NOT NULL,
  project_id CHAR(36) NOT NULL,
  file_path VARCHAR(1000) NOT NULL,
  old_content LONGTEXT,
  new_content LONGTEXT,
  diff_summary TEXT,
  status VARCHAR(20) DEFAULT 'pending',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
  FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
  INDEX idx_project (project_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ⑧ session_participants（依赖 chat_sessions, agents）
CREATE TABLE session_participants (
  session_id CHAR(36) NOT NULL,
  agent_id CHAR(36) NOT NULL,
  joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (session_id, agent_id),
  FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 步骤 3：导入 Seed 数据

创建 `backend/scripts/seed_data.sql`，手动执行以下 insert（等效于 Step 5 的 seed 脚本，MVP 阶段直接 SQL）：

```sql
-- 插入 dev_user，获取其 UUID（生成方式：SELECT UUID()）
INSERT INTO users (id, username, email)
VALUES ('<dev_user_uuid>', 'dev_user', 'dev@localhost');
-- 记下这个 UUID，填入 backend/.env 的 DEV_USER_ID

-- 插入 4 个 Agent（role, name, system_prompt, provider='claude', capabilities=[]）
INSERT INTO agents (id, name, role, provider, model, system_prompt, capabilities, created_by) VALUES
('<pm_uuid>', 'PM', 'PM', 'claude', 'claude-sonnet-4', '你是一个专业的产品经理...', '[]', '<dev_user_uuid>'),
('<planner_uuid>', 'Planner', 'Planner', 'claude', 'claude-sonnet-4', '你是一个专业的任务规划师...', '[]', '<dev_user_uuid>'),
('<coder_uuid>', 'Coder', 'Coder', 'claude', 'claude-sonnet-4', '你是一个专业的代码工程师...', '[]', '<dev_user_uuid>'),
('<reviewer_uuid>', 'Reviewer', 'Reviewer', 'claude', 'claude-sonnet-4', '你是一个专业的代码审查员...', '[]', '<dev_user_uuid>');
```

### 步骤 4：验证

```bash
mysql -uroot -proot -D agenthub -e "SHOW TABLES"
mysql -uroot -proot -D agenthub -e "SELECT username FROM users"
mysql -uroot -proot -D agenthub -e "SELECT role, name FROM agents"
redis-cli ping  # 应返回 PONG
```

### 验收标准

- `SHOW TABLES` 显示 8 张表
- `users` 表有 1 条 dev_user 记录，`agents` 表有 4 条记录
- `redis-cli ping` 返回 `PONG`
- `backend/.env` 中 `DEV_USER_ID` 已填入 dev_user 的 UUID

---

## Step 3：后端 FastAPI 项目初始化

### 目标

后端目录结构完整，所有核心模块目录就位，FastAPI 应用可启动，`/docs` 可访问。

### 新建文件

| 文件 | 用途 |
|------|------|
| `backend/app/__init__.py` | 空包 |
| `backend/app/main.py` | FastAPI 入口，注册路由、CORS 中间件、lifespan |
| `backend/app/core/__init__.py` | |
| `backend/app/core/config.py` | `Settings` 类，从 `.env` 读取所有配置 |
| `backend/app/core/database.py` | `async def get_db()` → `AsyncGenerator[AsyncSession, None]` |
| `backend/app/core/redis.py` | Redis 客户端初始化和关闭 |
| `backend/app/api/__init__.py` | |
| `backend/app/api/sessions.py` | Session 路由（占位 return []） |
| `backend/app/api/projects.py` | Project 路由（占位） |
| `backend/app/api/ws.py` | WebSocket 端点（占位） |
| `backend/app/schemas/__init__.py` | |
| `backend/app/schemas/session.py` | Session Pydantic 模型（占位） |
| `backend/app/schemas/project.py` | Project Pydantic 模型（占位） |
| `backend/app/schemas/message.py` | Message Pydantic 模型（占位） |
| `backend/app/models/__init__.py` | |
| `backend/app/models/session.py` | ChatSession ORM 模型（占位） |
| `backend/app/models/project.py` | Project ORM 模型（占位） |
| `backend/app/models/message.py` | Message ORM 模型（占位） |
| `backend/app/models/user.py` | User ORM 模型（占位） |
| `backend/app/models/agent.py` | Agent ORM 模型（占位） |
| `backend/app/services/__init__.py` | |
| `backend/app/services/session_service.py` | Session 业务逻辑（占位） |
| `backend/app/services/project_service.py` | Project 业务逻辑（占位） |
| `backend/app/agents/__init__.py` | |
| `backend/app/agents/echo_agent.py` | Echo Agent（骨架阶段用） |
| `backend/.env` | 环境变量（不提交 git） |

### `backend/app/core/config.py` 环境变量列表

| 变量名 | 示例值 | 说明 |
|--------|--------|------|
| `DATABASE_URL` | `mysql+aiomysql://root:root@localhost:3306/agenthub` | MySQL 连接字符串 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 URL |
| `DEV_USER_ID` | `a1b2c3d4-...` | dev_user 的 UUID（Step 2 获取后填入） |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Anthropic API Key（骨架阶段可为空） |
| `BACKEND_HOST` | `localhost` | 服务监听地址 |
| `BACKEND_PORT` | `8000` | 服务监听端口 |
| `PROJECT_ROOT` | `/tmp/agent-projects` | 项目文件根目录（VFS 挂载点） |

### 验收标准

- `cd backend && uvicorn app.main:app --reload` 启动无报错
- `GET http://localhost:8000/` 返回 `{"status": "ok"}`
- `GET http://localhost:8000/docs` 显示 Swagger UI

---

## Step 4：Alembic 数据库迁移（可选，MVP 阶段跳过）

> **说明**：如果 Step 2 已经手动执行了 DDL，Step 4 可以跳过。
> 如果想用 Alembic 管理 schema 变更（推荐在后续阶段使用），则：
> - 初始化 `cd backend && alembic init alembic`
> - 修改 `alembic.ini` 中的 `sqlalchemy.url`
> - 在 `alembic/versions/001_initial_schema.py` 中用 `op.create_table()` 重写 Step 2 的 DDL
> - 执行 `alembic upgrade head`

### 目标

用 Alembic 管理 schema 版本，支持后续增量迁移。

### 验收标准

- `alembic upgrade head` 成功
- `alembic history` 显示版本记录

---

## Step 5：Session CRUD 接口

### 目标

完整的会话增删改查 REST API。创建 Session 时同步创建空白 Project 和 Redis VFS。

### 接口一览

#### `POST /api/sessions` — 创建会话

**请求体：**

```json
{
  "owner_id": "string (UUID, 必填)",
  "title": "string (可选，默认 null)",
  "mode": "string (可选，默认 'single')"
}
```

**响应（201）：**

```json
{
  "id": "uuid-string",
  "project_id": "uuid-string",
  "owner_id": "uuid-string",
  "title": "string | null",
  "mode": "single",
  "is_pinned": false,
  "is_archived": false,
  "created_at": "2026-05-21T10:00:00Z",
  "updated_at": "2026-05-21T10:00:00Z"
}
```

**副作用：**
- 在 `projects` 表插入 1 条记录（owner_id=请求的 owner_id，name="New Project"）
- 在 Redis 设置 key `files:{project_id}` = `'{"project_id":"...","files":{}}'`

---

#### `GET /api/sessions` — 查询会话列表

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `owner_id` | string (UUID) | 必填 | 过滤属于该用户的会话 |
| `page` | int | 1 | 页码（从 1 开始） |
| `page_size` | int | 20 | 每页数量，最大 100 |

**响应（200）：**

```json
{
  "items": [
    {
      "id": "uuid",
      "project_id": "uuid",
      "owner_id": "uuid",
      "title": "string | null",
      "mode": "single",
      "is_pinned": false,
      "is_archived": false,
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

**排序规则：** `is_pinned DESC, updated_at DESC`（置顶优先，再按更新时间倒序）

**过滤规则：** `is_archived = false`

---

#### `GET /api/sessions/{session_id}` — 查询单个会话

**路径参数：**
- `session_id`: string (UUID)

**响应（200）：** 同 `POST /api/sessions` 返回的单个对象结构

**错误响应：**
- `404`：`{"detail": "Session not found"}`

---

#### `PATCH /api/sessions/{session_id}` — 更新会话

**路径参数：**
- `session_id`: string (UUID)

**请求体（全部可选，按需传入）：**

```json
{
  "title": "string (可选)",
  "is_pinned": "boolean (可选)",
  "is_archived": "boolean (可选)"
}
```

**响应（200）：** 更新后的完整会话对象

**副作用：**
- `is_pinned` 变更时，`updated_at` 自动更新为当前时间
- `is_archived` 变为 `true` 后，会话从 `GET /api/sessions` 的默认列表中消失

---

#### `DELETE /api/sessions/{session_id}` — 删除会话

> **MVP 阶段返回 501**，暂不实现。

**响应（501）：**

```json
{
  "detail": "Not implemented"
}
```

### 验收标准

- `POST /api/sessions` → chat_sessions + projects 各新增 1 条，Redis 新增 VFS key
- `GET /api/sessions?owner_id=xxx` → 按置顶/更新时间排序
- `PATCH /api/sessions/{id}` `{"is_pinned": true}` → `is_pinned=1`
- `PATCH /api/sessions/{id}` `{"is_archived": true}` → 归档后不在默认列表出现
- 新建会话出现在列表最顶部

---

## Step 6：Message 历史接口

### 目标

消息的历史查询与分页加载 REST API，支持聊天界面刷新恢复。

### 接口一览

#### `GET /api/sessions/{session_id}/messages` — 查询消息历史

**路径参数：**
- `session_id`: string (UUID)

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码（从 1 开始） |
| `page_size` | int | 20 | 每页数量 |

**响应（200）：**

```json
{
  "items": [
    {
      "id": "uuid",
      "session_id": "uuid",
      "sender_type": "human | agent | system",
      "sender_id": "uuid | null",
      "sender_role": "PM | Planner | Coder | Reviewer | null",
      "content": "string",
      "content_type": "text | markdown | code",
      "metadata": {},
      "is_pinned": false,
      "parent_message_id": "uuid | null",
      "created_at": "datetime"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "has_more": true
}
```

**排序规则：** `created_at ASC`（时间正序，早期消息在前）

**has_more 逻辑：** `(page-1)*page_size + len(items) < total`

### 验收标准

- 空会话 → `{"items": [], "total": 0, "has_more": false}`
- 消息列表按时间正序
- `page=1&page_size=20` 返回第 1-20 条，`page=2` 返回第 21-40 条
- `has_more` 正确反映是否有更多页

---

## Step 7：WebSocket 连接管理

### 目标

WebSocket 端点就绪，支持连接建立、心跳保活、断连清理。

### 连接 URL

```
ws://localhost:8000/ws/{session_id}?user_id={dev_user_id}
```

| 参数 | 说明 |
|------|------|
| `session_id` | 要加入的会话 UUID |
| `user_id` | 当前用户 UUID（dev_user 的 UUID） |

### 服务端消息类型（服务端 → 客户端）

| `type` | payload | 说明 |
|--------|---------|------|
| `pong` | `{}` | 服务端响应客户端心跳 |
| `agent_typing` | `{agent_role, is_typing}` | Agent 正在输入中 |
| `chat_stream` | `{message_id, stream_id, content_chunk, is_final, sender_role}` | 流式消息块 |
| `error` | `{code, message}` | 错误通知 |

### 客户端消息类型（客户端 → 服务端）

| `action` / `type` | payload | 说明 |
|-------------------|---------|------|
| `ping` | `{}` | 客户端心跳 |
| `send_message` | `{session_id, content}` | 发送新消息 |

### 心跳机制

- **客户端心跳**：前端每 30s 发 `{"type": "ping"}`，服务端回 `{"type": "pong"}`
- **MVP-5 边界**：本阶段不要求服务端主动心跳；连接健康由客户端心跳、超时关闭和前端重连状态机负责

### 验收标准

- 连接建立成功（`101 Switching Protocols`）
- 发送 `{"type": "ping"}` 立即收到 `{"type": "pong"}`
- 断开连接后后端无异常（`WebSocketDisconnect` 已捕获）

---

## Step 8：WebSocket 消息收发（Echo 阶段）

### 目标

用户发送消息 → Echo 回复 → 流式推送 → 消息持久化，全链路跑通。

### 消息发送流程（客户端 → 服务端）

```json
{
  "action": "send_message",
  "session_id": "uuid",
  "content": "用户输入的文字"
}
```

### Echo 回复流程（服务端 → 客户端）

```
收到 send_message
    ↓
写入 messages 表（sender_type=human, content=用户输入）
    ↓
推送 agent_typing: {"type": "agent_typing", "agent_role": "PM", "is_typing": true}
    ↓
生成 message_id（服务端 UUID）
    ↓
循环 chunk 推送（每个 50ms 间隔）:
  {"type": "chat_stream", "message_id": "xxx", "stream_id": "xxx",
   "content_chunk": "用户输入的文字", "is_final": false, "sender_role": "PM"}
    ↓
最后一条:
  {"type": "chat_stream", "message_id": "xxx", "stream_id": "xxx",
   "content_chunk": "", "is_final": true, "sender_role": "PM"}
    ↓
写入 messages 表（sender_type=agent, sender_role=PM, content=完整文字）
    ↓
推送 agent_typing: {"type": "agent_typing", "agent_role": "PM", "is_typing": false}
```

### 字段说明

| 字段 | 说明 |
|------|------|
| `message_id` | 消息唯一 ID（服务端生成），首条 chunk 时确定，后续 chunk 复用同一个 ID |
| `stream_id` | 流式会话 ID（用于前端归并同一个流的所有 chunk） |
| `content_chunk` | 本次推送的文本片段（最后一条为空字符串） |
| `is_final` | 是否是最后一条（`true` = 流式推送结束） |
| `sender_role` | Agent 角色（PM/Planner/Coder/Reviewer，骨架阶段固定 PM） |

### Echo Agent 逻辑（伪代码）

```
输入: user_content (string)
输出: 流式 chunk (AsyncGenerator[string, None])

1. 按句号/感叹号/问号切分 user_content，每段 50-100 字符
2. 每个 chunk yield 后 sleep 50ms（模拟打字速度）
3. 最后 yield 空字符串 + is_final=true
```

### 验收标准

- 发送消息后，人类消息气泡立即出现（sender_type=human）
- Agent Echo 回复显示（sender_type=agent，带 PM 角色标识）
- 刷新页面，消息历史正确恢复（已持久化到数据库）
- 快速发送多条消息，每条都正确渲染（无丢失、无乱序）

---

## Step 9：前端极简 UI

### 目标

极简 UI 实现会话列表 + 聊天界面，可完成 IM 核心体验验证，不依赖任何 UI 组件库。

### 页面结构

| 路由 | 组件 | 功能 |
|------|------|------|
| `/` | 重定向 | → `/chat` |
| `/chat` | `ChatView.vue` | 默认页：展示会话列表（无选中会话时） |
| `/chat/:sessionId` | `ChatView.vue` | 选中特定会话，展示聊天界面 |

### 核心组件职责

| 组件 | 职责 |
|------|------|
| `ChatLayout.vue` | 左右分栏布局：侧边栏 + 主聊天区 |
| `SessionList.vue` | 展示会话列表；点击新建按钮创建会话；点击会话跳转 |
| `ChatWindow.vue` | 消息气泡列表 + 底部输入框 + 发送逻辑 |
| `MessageBubble.vue` | 单条消息渲染；human 样式 vs agent 样式（角色标签、头像） |

### API 调用封装

```typescript
// chatService.ts
getSessions(owner_id: string, page?: number): Promise<PaginatedSessions>
createSession(body: {owner_id: string, title?: string}): Promise<Session>
updateSession(id: string, body: Partial<SessionUpdate>): Promise<Session>

// messageService.ts
getMessages(session_id: string, page?: number): Promise<PaginatedMessages>
```

### WebSocket 封装（useWebSocket.ts）

```typescript
// 接受: sessionId, userId
// 返回: { sendMessage(content), messages[], status, connect(), disconnect(), retry() }
// 内部: 维护消息 Map（stream_id → 消息对象），逐块追加 content
// 心跳: 每 30s 发 ping
// 断连: 自动重连（指数退避 1s/2s/4s/8s/16s，最多 5 次）
// 失败: 进入 failed 状态，显示最小提示并提供手动重试入口
```

> MVP-5 的连接状态与重连细化 task 以 `openspec/changes/IM/mvp-5-tasks.md` 为准；本 Step 9 只保留前端极简 UI 的总体位置。

### 验收标准

- 侧边栏显示会话列表，新建会话出现在最顶部
- 点击会话跳转到 `/chat/:sessionId`，消息列表正确加载
- 发送消息后，人类消息气泡出现（带右侧对齐样式）
- Agent Echo 回复出现在下方（带左侧对齐 + 角色标签样式）
- 刷新页面，消息历史正确恢复
- WebSocket 断连后自动重连

---

## Step 10：前后端联调验收

### 验收标准总表

| 类别 | 验收项 | 通过标准 |
|------|-------|---------|
| **工程骨架** | pnpm install | 无冲突 |
| | `pnpm --filter frontend dev` | `localhost:5173` 可访问 |
| **数据库** | 8 张表存在 | `SHOW TABLES` 返回 8 行 |
| | seed 数据就位 | users 1 条，agents 4 条 |
| | DEV_USER_ID 已填入 .env | 非空 UUID |
| **FastAPI 入口** | `uvicorn app.main:app --reload` | 启动无报错 |
| | `GET /` | 返回 `{"status": "ok"}` |
| | `GET /docs` | 显示 Swagger UI |
| **Session CRUD** | POST 创建会话 | 响应 201，chat_sessions + projects 各增 1 行 |
| | GET 会话列表 | 返回 items + total + 分页 |
| | PATCH 置顶 | `is_pinned` 变为 true |
| | PATCH 归档 | 会话从默认列表消失 |
| | 新建会话在顶部 | 列表第一项 |
| **Message 历史** | 分页加载 | page=1 / page=2 返回不同数据 |
| | has_more 正确 | 最后一页 has_more=false |
| | 刷新后消息恢复 | 数据库持久化正确 |
| **WebSocket** | 连接建立 | ws://localhost:8000/ws/{id}?user_id={uid} 连接成功 |
| | 心跳 ping-pong | 发 ping 回 pong |
| | 断连处理 | disconnect 后无异常 |
| **Echo 消息** | 发送 → Echo 回复 | 全链路跑通 |
| | 流式推送 | 消息逐块出现 |
| | 刷新恢复 | 历史消息持久化 |
| **前端 UI** | 会话列表渲染 | 列表 + 新建按钮正常 |
| | 聊天界面渲染 | human + agent 消息样式不同 |
| | WebSocket 状态 | 断连重连正常 |

---

## 附录：文件目录总览

```
AgentHub/
├── pnpm-workspace.yaml
├── package.json                 # 根 workspace
├── turbo.json
├── .nvmrc
├── .gitignore
│
├── shared/                      # 已有，保持不动
│   ├── index.ts
│   └── schemas/ws_messages.json
│
├── backend/
│   ├── .env                    # DEV_USER_ID=xxx（Step 2 后填入）
│   ├── requirements.txt        # pip 依赖
│   ├── pyproject.toml          # Python 项目定义
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 入口
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py       # Settings
│   │   │   ├── database.py     # AsyncSession
│   │   │   └── redis.py        # Redis 客户端
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py         # User ORM
│   │   │   ├── agent.py        # Agent ORM
│   │   │   ├── project.py     # Project ORM
│   │   │   ├── session.py      # ChatSession ORM
│   │   │   └── message.py     # Message ORM
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── session.py      # Session Pydantic
│   │   │   ├── project.py     # Project Pydantic
│   │   │   └── message.py     # Message Pydantic
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── session_service.py
│   │   │   └── project_service.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── sessions.py     # Session REST API
│   │   │   ├── projects.py    # Project REST API
│   │   │   └── ws.py          # WebSocket 端点
│   │   └── agents/
│   │       ├── __init__.py
│   │       └── echo_agent.py  # Echo Agent
│   │
│   ├── alembic/                 # Step 4 可选
│   │   ├── env.py
│   │   └── versions/
│   │
│   └── scripts/
│       └── seed_data.sql       # 手动执行的 seed SQL
│
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.ts
        ├── App.vue
        ├── router/index.ts
        ├── styles/base.css
        ├── api/
        │   ├── index.ts
        │   ├── chatService.ts
        │   └── messageService.ts
        ├── stores/chat.ts       # Pinia chat store
        ├── composables/
        │   └── useWebSocket.ts  # WebSocket 状态管理
        └── components/
            ├── ChatLayout.vue
            ├── ChatView.vue
            ├── SessionList.vue
            ├── ChatWindow.vue
            └── MessageBubble.vue
```
