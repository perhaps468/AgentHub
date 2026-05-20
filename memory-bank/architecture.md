# AgentHub 系统架构与运行规范

> 本文件是 `实施计划.md` 的架构子文档，详细定义系统技术栈、核心流程和运行规范。
> 语言：强制中文（变量/函数/API 路径除外）。

---

## 1. 核心技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端框架 | Vue 3 (Composition API + `<script setup>`) + Vite | 轻量、响应式生态成熟 |
| UI 组件库 | Element Plus | 企业级 Vue 3 UI 组件库 |
| 状态管理 | Pinia | Vue 3 官方推荐，比 Vuex 更轻量 |
| 前端路由 | Vue Router 4 | SPA 路由管理 |
| HTTP 客户端 | Axios | REST API 调用 |
| 组合式函数 | VueUse | 常用工具 composable 集合 |
| 后端框架 | FastAPI | 异步优先，类型安全 |
| Agent 编排 | LangGraph | 基于状态机的多 Agent 协作 |
| 数据库 | PostgreSQL 16 + Redis 7 | 结构化存储 + VFS 内存缓存 |
| 实时通信 | WebSocket | 全双工流式消息 |
| ORM | SQLAlchemy 2.0 (asyncio) + asyncpg | 异步数据库操作 |
| AI Provider | Anthropic Claude API (MVP) | 适配器模式预留扩展位 |
| 数据库迁移 | Alembic | 版本化的数据库迁移管理 |

---

## 2. 开发环境端口约定

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 Dev Server | `http://localhost:5173` | Vite 开发服务器 |
| 后端 API | `http://localhost:8000` | FastAPI 应用 |
| 后端 Swagger | `http://localhost:8000/docs` | 自动生成的 API 文档 |
| PostgreSQL | `localhost:5432` | Docker 容器 |
| Redis | `localhost:6379` | Docker 容器 |
| VFS 预览服务 | `/api/preview/{project_id}/<path>` | 后端代理路由 |

---

## 3. 核心多 Agent 协同流程（SOP）

整个系统是一个基于 LangGraph 状态机的群聊流水线，分为四个阶段：

### 阶段 1：需求澄清（PM Agent）

- **触发条件**：用户在聊天框中发送新需求
- **执行逻辑**：PM Agent 接收需求，通过多轮追问澄清细节
- **输出终点**：输出 Markdown PRD，状态更新为 `phase_planning`，唤醒 Planner

### 阶段 2：任务拆解（Planner Agent）

- **触发条件**：PM Agent 完成 PRD 输出
- **执行逻辑**：Planner 读取 PRD，结合当前 VFS 快照，将项目拆解为 JSON 格式的任务 DAG
- **输出终点**：输出任务列表 JSON，状态更新为 `phase_coding`，唤醒 Coder（按 priority 依次）

### 阶段 3：编码迭代（Coder + Reviewer）

- **触发条件**：Planner 输出任务 DAG
- **执行逻辑**：
  - Coder 认领当前任务，严格只输出针对特定文件的 Code Diff（不直接写盘）
  - Reviewer 审查 Diff：
    - 通过 → 输出 `[APPROVE]`，等待用户验收
    - 不通过 → 输出 `[REJECT]` + 原因，打回 Coder 重新生成
- **输出终点**：用户点击 Accept → 触发 VFS 落盘

### 阶段 4：产物预览

- **触发条件**：VFS 中存在已落盘的 HTML 文件
- **执行逻辑**：后端提供预览路由，前端 iframe 嵌入展示
- **输出终点**：用户在聊天流中看到网页预览卡片

---

## 4. WebSocket 全双工通信规范

### 4.1 连接建立

```
前端 → ws://localhost:8000/ws/{session_id}?user_id={user_id}
```

### 4.2 流式策略

- 流式输出按**句子 chunk** 发送（遇到句号/换行/100 字符切分），不逐 token 发送
- 每个 chunk 携带 `stream_id`，用于前端识别属于哪条消息
- 最后一帧设置 `is_final: true`

### 4.3 断连处理

- 前端自动重连：WebSocket 断开后，每 3 秒重试一次，最多 5 次
- 后端必须捕获 `WebSocketDisconnect`，清理对应 session 的状态机内存，避免幽灵会话

---

## 5. 虚拟文件系统（VFS）交互规范

> **核心安全红线**：AI 生成的代码绝对不能直接覆盖物理文件，必须以 Diff 形式推给前端。
> 只有用户明确点击 "Accept" 后，才能更新 VFS 并落盘。

### 5.1 VFS 存储结构

- **Redis**：`files:{project_id}` → JSON（文件路径 → 内容 + 版本）
- **磁盘**：`/tmp/agent-projects/{project_id}/`（仅在 Accept 后写入）

### 5.2 Accept 流程

```
用户点击 "Accept"
  → 前端发送 { "action": "accept_code", "diff_id": "xxx" }
  → 后端 VFSService.accept_diff()
      → 更新 Redis VFS（version++）
      → 落盘到 /tmp/agent-projects/{project_id}/
      → 推送 vfs_update 消息给前端
  → 前端刷新文件树
```

### 5.3 Reject 流程

```
用户点击 "Reject"
  → 前端发送 { "action": "reject_code", "diff_id": "xxx" }
  → 后端标记 diff 状态为 rejected
  → 唤醒 Coder 重新生成（携带拒绝原因）
```

---

## 6. Monorepo 跨端约定

### 6.1 shared 目录职责

- `shared/schemas/ws_messages.json`：WebSocket 消息协议的 JSON Schema 定义
- `shared/index.ts`：前端可导入的 TypeScript 类型（从 JSON Schema 自动生成或手动维护）
- **原则**：跨端共享的数据结构必须以 JSON Schema 为 source of truth，前后端各自生成类型

### 6.2 环境变量管理

所有环境变量通过 `.env` 文件管理（不提交到 git），后端通过 `pydantic-settings` 加载，前端通过 `vite.config.ts` 的 `.env` 加载。

### 6.3 数据库连接

- **开发环境**：通过 `docker-compose.yml` 启动的 PostgreSQL + Redis 容器
- **连接字符串**：通过 `DATABASE_URL` / `REDIS_URL` 环境变量注入
- **禁止硬编码**：任何连接信息必须来自环境变量

---

## 7. 前端路由设计

```
/                     → HomeView → 重定向到 /chat
/chat                 → ChatView（默认选中第一个会话）
/chat/:sessionId      → ChatView（打开特定会话）
/project/:projectId   → ProjectView（项目详情 + VFS 文件树）
/agents               → AgentListView（Agent 管理）
```

---

## 8. 错误处理规范

### 8.1 后端错误

- 所有 REST API 异常通过 FastAPI 的 `HTTPException` 统一处理
- WebSocket 异常必须捕获 `WebSocketDisconnect`，并清理状态机
- LLM API 超时：前端显示 "Agent 思考中..." 状态，后端最多等待 120 秒

### 8.2 前端错误

- Axios 请求统一拦截，401/403/500 等状态码弹出 Element Plus Message 提示
- WebSocket 断连时顶部显示重连提示条

---

## 9. 代码规范

### 9.1 命名约定

| 场景 | 约定 | 示例 |
|------|------|------|
| TypeScript 变量/函数 | camelCase | `sendMessage`, `sessionId` |
| TypeScript 类型/接口 | PascalCase | `ChatStreamMessage`, `TaskItem` |
| Python 变量/函数 | snake_case | `accept_diff`, `session_id` |
| Python 类 | PascalCase | `VFSService`, `ClaudeAdapter` |
| 文件名 | kebab-case | `chat-window.vue`, `chat_service.py` |
| API 路径 | kebab-case | `/chat-sessions`, `/code-diff` |
| 数据库表名 | snake_case（复数） | `chat_sessions`, `code_diffs` |
| Redis Key | colon-separated | `files:{project_id}` |

### 9.2 注释与语言

- 代码注释使用中文，解释**为什么**而非**是什么**
- 变量命名、函数命名、API 路径必须使用符合语义的英文
- 与用户交互的文案（按钮、提示）使用中文

---

## 10. Docker 环境

### 10.1 开发环境

```
docker-compose up -d postgres redis
```

启动 PostgreSQL 16 和 Redis 7 容器，数据持久化到 `./docker/data/` 目录。

### 10.2 生产环境（未来）

- 前端：构建 Docker 镜像，Nginx 托管静态文件
- 后端：Uvicorn 运行 FastAPI 应用，Gunicorn 多 worker
- 数据库：云托管 PostgreSQL 或 Docker

---

## 11. 版本兼容性要求

| 依赖 | 最低版本 |
|------|----------|
| Node.js | 18+ |
| Python | 3.11+ |
| pnpm | 8+ |
| PostgreSQL | 16+ |
| Redis | 7+ |
