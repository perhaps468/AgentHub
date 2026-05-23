# Task: MVP-3 + MVP-4 后端合并特例任务

## 0. 文档定位

- 本文档是一次性特例 task。
- 它将 `implementation-phases.md` 中的 `MVP-3 Session/Message 最小接口与 WebSocket 跑通` 和 `MVP-4 Echo 消息闭环与最小持久化跑通` 的后端部分合并为一个 task。
- 本次合并只为了当前阶段减少来回切换成本，不代表以后拆 task 的默认方式。
- 后续任何阶段继续拆 task 时，仍必须以 `implementation-phases.md` 的原始阶段边界为准，不能默认把 `MVP-4` 并入 `MVP-3`。

## 1. 任务目标

- 基于 `implementation-phases.md` 的 `MVP-3`，实现最小 Session REST 接口、Message 历史接口和按会话工作的 WebSocket。
- 基于 `implementation-phases.md` 的 `MVP-4`，实现 Echo 消息闭环所需的最小后端持久化能力。
- 提供可稳定联调的后端契约，让前端后续可以围绕固定接口完成最小聊天页、消息恢复和连接状态展示。
- 将当前后端运行方式收敛到 FastAPI + MySQL，避免再维护一套临时 Node HTTP 行为。
- 保留当前阶段最小边界，不提前实现多 Agent、Orchestrator、真实 LLM、群聊参与者管理和 Diff/VFS 能力。

## 2. 当前范围

- 实现健康检查接口 `GET /`、`GET /health`，并在迁移到 FastAPI 后保持语义稳定。
- 实现 `POST /api/sessions`、`GET /api/sessions`、`GET /api/sessions/{session_id}`、`PATCH /api/sessions/{session_id}`，其中归档能力以 `PATCH` 为主语义。
- 保留 `DELETE /api/sessions/{session_id}` 作为兼容接口，但其行为必须等价于“归档会话”，不能表达为真正删除产品能力。
- 实现 `GET /api/sessions/{session_id}/messages`，支持分页。
- 实现 `WS /ws/{session_id}`，支持连接校验、`ping/pong`、`send_message`。
- 实现最小数据持久化，只包含 `sessions`、`messages` 两张表。
- 实现 Echo 闭环：写入用户消息、生成 Echo Agent 消息、写入 Agent 消息、通过 WebSocket 返回 Agent 消息。
- 补齐启动方式、环境变量、数据库初始化说明和接口验证命令。

## 3. 不做什么

- 不接真实 LLM 或外部 Provider。
- 不做多 Agent 协作、Orchestrator、任务拆解、角色流水线。
- 不做群聊参与者管理或 `@Agent` 行为。
- 不引入 `users`、`agents`、`projects`、`tasks`、`code_diffs`、`session_participants` 等新表。
- 不实现复杂鉴权、登录、权限模型；`owner_id` 当前仅作为请求字段使用。
- 不做前端 UI、前端消息本地插入、前端重连逻辑或完整联调页面。
- 不做消息编辑、撤回、回复、引用、重新生成、附件、图片、Diff 卡片。
- 不做部署发布、VFS、文件系统产物管理。

## 4. 依赖与前置条件

- `openspec/specs/implementation-phases.md` 中 `MVP-3` 和 `MVP-4` 已确认，是本 task 的唯一阶段依据。
- 本地 MySQL 可用，建议数据库名为 `agenthub`。
- 后端目录允许切换到 Python/FastAPI 作为唯一主运行方式。
- 当前仅要求本地开发环境跑通，不要求生产部署配置。

## 5. 技术决策

- 后端框架使用 FastAPI。
- 数据库存储使用 MySQL。
- 当前阶段只维护 `sessions`、`messages` 两张表。
- 会话列表的产品语义是“归档”而不是“删除”。
- `PATCH /api/sessions/{session_id}` 中的 `is_archived` 是主归档入口。
- `DELETE /api/sessions/{session_id}` 仅作为兼容接口保留，其行为等价于设置 `is_archived=true`，不物理删除 session，也不物理删除 messages。
- `mode` 只允许 `single`、`group` 两个枚举值；当前虽允许存储 `group`，但不实现 group 专属行为。
- Echo 回复固定为最小实现：
  - `sender_type=agent`
  - `sender_role=PM`
  - `content_type=text`
  - `content=Echo: {用户输入}`
- 时间字段统一使用 ISO 8601 字符串返回，例如 `2026-05-22T10:30:00Z`。
- ID 字段统一使用 UUID 字符串。

## 6. 需要改动的模块或文件

- `backend/package.json`
  调整启动命令，使其不再以 `src/server.mjs` 作为主入口，改为 FastAPI/Python 启动方式或代理脚本。
- `backend/app/main.py`
  FastAPI 应用入口，注册健康检查、REST 路由和 WebSocket 路由。
- `backend/app/core/config.py`
  读取 `DATABASE_URL`、`HOST`、`PORT` 等配置。
- `backend/app/core/database.py`
  建立数据库连接、会话工厂和依赖注入。
- `backend/app/api/sessions.py`
  Session 和 Message 历史 REST 接口。
- `backend/app/api/ws.py`
  WebSocket 端点与消息协议处理。
- `backend/app/models/session.py`
  Session ORM 模型。
- `backend/app/models/message.py`
  Message ORM 模型。
- `backend/app/schemas/session.py`
  Session 相关请求/响应 schema。
- `backend/app/schemas/message.py`
  Message 相关请求/响应 schema。
- `backend/sql/001_mvp3_schema.sql`
  初始化 `sessions`、`messages` 表的 MySQL DDL。
- `backend/.env.example`
  补充或更新 MySQL 与服务端口配置示例。
- `README.md`
  补充数据库初始化、后端启动、接口验证说明。

## 7. 统一数据契约

### 7.1 Session 对象

```json
{
  "id": "0d6f6d65-2ef6-44df-a63f-8cf1b3f2d8f7",
  "owner_id": "dev_user",
  "title": "New Session",
  "mode": "single",
  "is_pinned": false,
  "is_archived": false,
  "created_at": "2026-05-22T10:30:00Z",
  "updated_at": "2026-05-22T10:30:00Z"
}
```

字段定义：

- `id`
  - 类型：`string`
  - 格式：UUID
  - 含义：会话唯一标识。
- `owner_id`
  - 类型：`string`
  - 约束：非空，最大长度建议 `100`
  - 含义：当前会话所属用户标识。当前阶段不校验其是否真实存在于用户表。
- `title`
  - 类型：`string | null`
  - 约束：最大长度建议 `255`
  - 含义：会话标题。允许为空，前端可自行决定空标题展示文案。
- `mode`
  - 类型：`string`
  - 枚举：`single`、`group`
  - 含义：会话模式。当前阶段只做存储和返回，不实现 `group` 特殊行为。
- `is_pinned`
  - 类型：`boolean`
  - 含义：会话是否被置顶。当前阶段只提供字段读写，不要求前端展示完整置顶体验。
- `is_archived`
  - 类型：`boolean`
  - 含义：会话是否已归档。默认列表查询只返回 `false` 的会话。
- `created_at`
  - 类型：`string`
  - 格式：ISO 8601 datetime
  - 含义：会话创建时间。
- `updated_at`
  - 类型：`string`
  - 格式：ISO 8601 datetime
  - 含义：会话最近更新时间。用于会话列表排序。

### 7.2 Message 对象

```json
{
  "id": "f4d9d09f-1db8-4d77-8d79-e1791814ef8a",
  "session_id": "0d6f6d65-2ef6-44df-a63f-8cf1b3f2d8f7",
  "sender_type": "agent",
  "sender_role": "PM",
  "content": "Echo: hello",
  "content_type": "text",
  "created_at": "2026-05-22T10:35:00Z"
}
```

字段定义：

- `id`
  - 类型：`string`
  - 格式：UUID
  - 含义：消息唯一标识。
- `session_id`
  - 类型：`string`
  - 格式：UUID
  - 含义：消息所属会话 ID。
- `sender_type`
  - 类型：`string`
  - 枚举：`human`、`agent`、`system`
  - 含义：消息发送主体类别。当前阶段实际写入 `human` 和 `agent`。
- `sender_role`
  - 类型：`string | null`
  - 约束：最大长度建议 `50`
  - 含义：发送角色名称。用户消息可为空；Echo Agent 固定为 `PM`。
- `content`
  - 类型：`string`
  - 约束：非空
  - 含义：消息文本内容。
- `content_type`
  - 类型：`string`
  - 枚举：当前只允许 `text`
  - 含义：消息内容类型，为后续图片、文件、Diff 卡片预留抽象。
- `created_at`
  - 类型：`string`
  - 格式：ISO 8601 datetime
  - 含义：消息创建时间。历史消息按该字段正序返回。

### 7.3 列表分页对象

Session 列表与 Message 历史统一采用分页响应结构：

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20,
  "has_more": false
}
```

字段定义：

- `items`
  - 类型：`array`
  - 含义：当前页数据。
- `total`
  - 类型：`integer`
  - 含义：满足当前筛选条件的总记录数。
- `page`
  - 类型：`integer`
  - 含义：当前页码，从 `1` 开始。
- `page_size`
  - 类型：`integer`
  - 含义：当前每页大小。
- `has_more`
  - 类型：`boolean`
  - 含义：是否还有下一页。Session 列表可选返回；Message 历史建议返回。

### 7.4 会话归档语义

- `is_archived=false`
  - 含义：会话处于默认活跃列表中。
- `is_archived=true`
  - 含义：会话已归档，不应出现在默认会话列表中，但仍可被详情接口和历史接口读取。
- 当前阶段的产品能力是“归档/取消归档”，不是“物理删除会话”。
- 为兼容某些客户端或历史约定，可保留 `DELETE /api/sessions/{session_id}`，但它只允许执行归档语义。

## 8. 详细接口定义

### 8.1 `GET /`

用途：

- 基础存活检查，用于确认服务已启动。

成功响应 `200`：

```json
{
  "service": "agenthub-backend",
  "status": "ok",
  "health": "/health"
}
```

字段定义：

- `service`
  - 类型：`string`
  - 含义：服务名称，固定用于标识后端实例。
- `status`
  - 类型：`string`
  - 枚举：当前固定 `ok`
  - 含义：服务基础状态。
- `health`
  - 类型：`string`
  - 含义：健康检查接口路径提示。

### 8.2 `GET /health`

用途：

- 健康检查接口，用于监测后端是否可响应。

成功响应 `200`：

```json
{
  "service": "agenthub-backend",
  "status": "ok",
  "timestamp": "2026-05-22T10:30:00Z"
}
```

字段定义：

- `service`
  - 类型：`string`
  - 含义：服务名称。
- `status`
  - 类型：`string`
  - 枚举：当前固定 `ok`
  - 含义：健康状态。
- `timestamp`
  - 类型：`string`
  - 格式：ISO 8601 datetime
  - 含义：服务端生成本次响应的时间。

### 8.3 `POST /api/sessions`

用途：

- 创建一个新的会话。

请求体：

```json
{
  "owner_id": "dev_user",
  "title": "New Session",
  "mode": "single"
}
```

请求字段定义：

- `owner_id`
  - 类型：`string`
  - 必填：是
  - 含义：会话所属用户标识。
- `title`
  - 类型：`string | null`
  - 必填：否
  - 含义：会话标题；未传时可为空或由后端写入默认标题。
- `mode`
  - 类型：`string`
  - 必填：是
  - 枚举：`single`、`group`
  - 含义：会话模式。

成功响应 `201`：

- 返回完整 Session 对象。

错误响应：

- `400`
  - 请求字段缺失、类型错误或枚举非法。

### 8.4 `GET /api/sessions`

用途：

- 查询指定 `owner_id` 的会话列表。

查询参数：

- `owner_id`
  - 类型：`string`
  - 必填：是
  - 含义：需要查询的用户标识。
- `include_archived`
  - 类型：`boolean`
  - 必填：否
  - 默认值：`false`
  - 含义：是否包含已归档会话。默认不包含。
- `page`
  - 类型：`integer`
  - 必填：否
  - 默认值：`1`
  - 约束：`>= 1`
- `page_size`
  - 类型：`integer`
  - 必填：否
  - 默认值：`20`
  - 约束：建议 `1-100`

排序与过滤规则：

- 按 `updated_at DESC` 排序。
- `include_archived=false` 时，只返回 `is_archived=false` 的会话。
- `include_archived=true` 时，返回当前 `owner_id` 下的全部会话。

成功响应 `200`：

```json
{
  "items": [
    {
      "id": "0d6f6d65-2ef6-44df-a63f-8cf1b3f2d8f7",
      "owner_id": "dev_user",
      "title": "New Session",
      "mode": "single",
      "is_pinned": false,
      "is_archived": false,
      "created_at": "2026-05-22T10:30:00Z",
      "updated_at": "2026-05-22T10:35:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "has_more": false
}
```

错误响应：

- `400`
  - 缺少 `owner_id`、分页参数非法。

### 8.5 `GET /api/sessions/{session_id}`

用途：

- 查询单个会话详情。

路径参数：

- `session_id`
  - 类型：`string`
  - 格式：UUID
  - 含义：目标会话 ID。

成功响应 `200`：

- 返回完整 Session 对象。

错误响应：

- `404`
  - 会话不存在。

### 8.6 `PATCH /api/sessions/{session_id}`

用途：

- 更新会话的最小可编辑字段，也是主归档/取消归档入口。

路径参数：

- `session_id`
  - 类型：`string`
  - 格式：UUID

请求体：

```json
{
  "title": "Updated title",
  "is_pinned": true,
  "is_archived": false
}
```

请求字段定义：

- `title`
  - 类型：`string | null`
  - 必填：否
  - 含义：更新后的标题。
- `is_pinned`
  - 类型：`boolean`
  - 必填：否
  - 含义：是否置顶。
- `is_archived`
  - 类型：`boolean`
  - 必填：否
  - 含义：是否归档。`true` 表示归档，`false` 表示取消归档。

成功响应 `200`：

- 返回更新后的完整 Session 对象。

错误响应：

- `400`
  - 请求体为空、字段类型错误。
- `404`
  - 会话不存在。

### 8.7 `DELETE /api/sessions/{session_id}`

用途：

- 提供兼容接口，但产品语义上等价于“归档会话”。

路径参数：

- `session_id`
  - 类型：`string`
  - 格式：UUID

服务端行为：

- 将 `is_archived` 设置为 `true`。
- 更新 `updated_at`。
- 不物理删除 `sessions` 记录。
- 不物理删除 `messages` 记录。
- 不提供真正删除或恢复已删除数据的能力。

成功响应 `200`：

```json
{
  "archived": true,
  "mode": "archive_alias",
  "session_id": "0d6f6d65-2ef6-44df-a63f-8cf1b3f2d8f7"
}
```

字段定义：

- `archived`
  - 类型：`boolean`
  - 含义：是否成功执行本次归档语义。
- `mode`
  - 类型：`string`
  - 固定值：`archive_alias`
  - 含义：明确这是兼容接口，行为等价于归档而不是删除。
- `session_id`
  - 类型：`string`
  - 含义：被归档的会话 ID。

错误响应：

- `404`
  - 会话不存在。

### 8.8 `GET /api/sessions/{session_id}/messages`

用途：

- 查询指定会话的消息历史。

路径参数：

- `session_id`
  - 类型：`string`
  - 格式：UUID

查询参数：

- `page`
  - 类型：`integer`
  - 默认值：`1`
  - 约束：`>= 1`
- `page_size`
  - 类型：`integer`
  - 默认值：`20`
  - 约束：建议 `1-100`

排序规则：

- 按 `created_at ASC` 返回，保证消息历史从旧到新。

成功响应 `200`：

```json
{
  "items": [
    {
      "id": "1b3a41d8-04d7-418a-b6a7-9b5cc4e31234",
      "session_id": "0d6f6d65-2ef6-44df-a63f-8cf1b3f2d8f7",
      "sender_type": "human",
      "sender_role": null,
      "content": "hello",
      "content_type": "text",
      "created_at": "2026-05-22T10:35:00Z"
    },
    {
      "id": "f4d9d09f-1db8-4d77-8d79-e1791814ef8a",
      "session_id": "0d6f6d65-2ef6-44df-a63f-8cf1b3f2d8f7",
      "sender_type": "agent",
      "sender_role": "PM",
      "content": "Echo: hello",
      "content_type": "text",
      "created_at": "2026-05-22T10:35:01Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20,
  "has_more": false
}
```

错误响应：

- `404`
  - 会话不存在。
- `400`
  - 分页参数非法。

### 8.9 `WS /ws/{session_id}`

用途：

- 为指定会话提供实时消息通道。

连接地址：

```text
ws://localhost:8000/ws/{session_id}
```

连接规则：

- 路径中的 `session_id` 必须存在。
- 当前不要求鉴权。
- 当前不要求 `user_id` query 参数。
- 若会话不存在，服务端可以直接拒绝连接，或在连接后立即发送错误消息并关闭连接；实现方式需在 README 中写清。

#### 8.9.1 客户端消息：`ping`

```json
{
  "type": "ping"
}
```

字段定义：

- `type`
  - 类型：`string`
  - 固定值：`ping`
  - 含义：心跳请求。

服务端响应：

```json
{
  "type": "pong"
}
```

字段定义：

- `type`
  - 类型：`string`
  - 固定值：`pong`
  - 含义：心跳响应。

#### 8.9.2 客户端消息：`send_message`

```json
{
  "action": "send_message",
  "session_id": "0d6f6d65-2ef6-44df-a63f-8cf1b3f2d8f7",
  "content": "hello"
}
```

字段定义：

- `action`
  - 类型：`string`
  - 固定值：`send_message`
  - 含义：客户端请求发送一条消息。
- `session_id`
  - 类型：`string`
  - 格式：UUID
  - 含义：目标会话 ID，必须与连接路径中的 `session_id` 一致。
- `content`
  - 类型：`string`
  - 含义：用户发送的文本内容。

服务端行为：

1. 校验消息结构是否合法。
2. 校验 `session_id` 与 WebSocket 路径一致。
3. 写入一条用户消息：
   - `sender_type=human`
   - `sender_role=null`
   - `content_type=text`
4. 生成 Echo 回复内容：`Echo: {content}`。
5. 写入一条 Agent 消息：
   - `sender_type=agent`
   - `sender_role=PM`
   - `content_type=text`
6. 将 Agent 消息通过 WebSocket 发回客户端。

#### 8.9.3 服务端消息：`chat_stream`

```json
{
  "type": "chat_stream",
  "message_id": "f4d9d09f-1db8-4d77-8d79-e1791814ef8a",
  "session_id": "0d6f6d65-2ef6-44df-a63f-8cf1b3f2d8f7",
  "sender_type": "agent",
  "sender_role": "PM",
  "content": "Echo: hello",
  "content_type": "text",
  "created_at": "2026-05-22T10:35:01Z"
}
```

字段定义：

- `type`
  - 类型：`string`
  - 固定值：`chat_stream`
  - 含义：服务端推送一条聊天消息。当前阶段虽然名称叫 `chat_stream`，但不要求真正分片流式输出。
- `message_id`
  - 类型：`string`
  - 格式：UUID
  - 含义：本次返回的 Agent 消息 ID。
- `session_id`
  - 类型：`string`
  - 格式：UUID
  - 含义：消息所属会话 ID。
- `sender_type`
  - 类型：`string`
  - 固定值：当前为 `agent`
  - 含义：消息发送主体类别。
- `sender_role`
  - 类型：`string`
  - 固定值：当前为 `PM`
  - 含义：Echo Agent 的角色名。
- `content`
  - 类型：`string`
  - 含义：Agent 返回的文本内容。
- `content_type`
  - 类型：`string`
  - 固定值：当前为 `text`
  - 含义：内容类型。
- `created_at`
  - 类型：`string`
  - 格式：ISO 8601 datetime
  - 含义：Agent 消息创建时间。

#### 8.9.4 服务端消息：`error`

```json
{
  "type": "error",
  "error_code": "invalid_request",
  "error_message": "Invalid request"
}
```

字段定义：

- `type`
  - 类型：`string`
  - 固定值：`error`
  - 含义：错误消息类型。
- `error_code`
  - 类型：`string`
  - 含义：稳定错误码，供前端分支处理。
- `error_message`
  - 类型：`string`
  - 含义：面向调试与联调的人类可读说明。

至少覆盖的错误码：

- `session_not_found`
- `invalid_request`
- `unknown`

## 9. 数据模型与 MySQL DDL

### 9.1 `sessions` 表

```sql
CREATE TABLE IF NOT EXISTS sessions (
  id CHAR(36) PRIMARY KEY,
  owner_id VARCHAR(100) NOT NULL,
  title VARCHAR(255),
  mode VARCHAR(20) NOT NULL DEFAULT 'single',
  is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
  is_archived BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_sessions_owner_updated (owner_id, updated_at),
  INDEX idx_sessions_archived (owner_id, is_archived)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 9.2 `messages` 表

```sql
CREATE TABLE IF NOT EXISTS messages (
  id CHAR(36) PRIMARY KEY,
  session_id CHAR(36) NOT NULL,
  sender_type VARCHAR(20) NOT NULL,
  sender_role VARCHAR(50),
  content TEXT NOT NULL,
  content_type VARCHAR(20) NOT NULL DEFAULT 'text',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_messages_session_created (session_id, created_at),
  CONSTRAINT fk_messages_session
    FOREIGN KEY (session_id)
    REFERENCES sessions(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 9.3 字段约束

- `sessions.mode`
  - 只接受 `single`、`group`。
- `messages.sender_type`
  - 只接受 `human`、`agent`、`system`。
- `messages.content_type`
  - 当前只允许 `text`。
- `messages.sender_role`
  - 用户消息可为空，Echo Agent 固定为 `PM`。

## 10. 详细实施步骤

1. 将后端主入口切换到 FastAPI，并把现有 `GET /`、`GET /health` 行为迁移过去。
2. 补齐后端配置读取，至少支持 `DATABASE_URL`、`HOST`、`PORT`。
3. 编写 `backend/sql/001_mvp3_schema.sql`，创建 `sessions`、`messages` 两张表。
4. 实现数据库连接层、会话依赖和最小 ORM 模型。
5. 实现 Session 请求/响应 schema，并对字段类型、长度、枚举做基础校验。
6. 实现 Session REST 接口：
   - 创建
   - 列表
   - 详情
   - 更新
   - 归档/取消归档
   - `DELETE` 兼容归档别名
7. 实现 Message 历史接口，支持分页、总数和 `has_more`。
8. 实现 WebSocket 接口：
   - 连接 session 校验
   - `ping/pong`
   - `send_message`
   - 错误消息返回
9. 实现 Echo 闭环：
   - 用户消息入库
   - Echo Agent 消息生成
   - Agent 消息入库
   - Agent 消息回推
10. 更新 `.env.example` 与 `README.md`，保证其他人能按文档完成启动与验证。
11. 使用 HTTP 客户端和 WebSocket 客户端按验收清单逐项验证。

## 11. 测试方案

### 11.1 接口校验测试

- 创建会话时校验 `owner_id` 缺失、`mode` 非法、字段类型错误。
- 更新会话时校验空请求体、布尔字段类型错误、目标会话不存在。
- 消息历史接口校验分页参数非法情况。

### 11.2 数据持久化测试

- 创建会话后可从详情接口和列表接口读到相同数据。
- 归档会话后默认列表不再返回该会话。
- 使用 `include_archived=true` 时可以重新查询到已归档会话。
- 使用 `PATCH` 将 `is_archived` 改回 `false` 后，会话重新回到默认列表。
- 发送消息后，用户消息与 Echo Agent 消息都能从历史接口重新读出。

### 11.3 WebSocket 行为测试

- 正常连接存在的 `session_id`。
- 连接不存在的 `session_id` 时返回错误或关闭连接。
- 发送 `ping` 后收到 `pong`。
- 发送合法 `send_message` 后收到 `chat_stream`。
- 发送非法结构时收到 `error`。

### 11.4 回归测试

- `GET /` 返回 `status=ok`。
- `GET /health` 返回 `status=ok`。
- FastAPI 迁移后仍能正常监听配置端口。

## 12. 验收标准

- 执行后端启动命令后，服务可正常监听配置端口。
- `GET /` 返回 `200`，且响应体包含 `service`、`status`、`health`。
- `GET /health` 返回 `200`，且响应体包含 `service`、`status`、`timestamp`。
- `POST /api/sessions` 可以成功创建会话，并返回完整 Session 对象。
- `GET /api/sessions?owner_id=dev_user` 可以按 `updated_at DESC` 返回会话列表。
- `GET /api/sessions?owner_id=dev_user&include_archived=false` 默认不返回已归档会话。
- `GET /api/sessions?owner_id=dev_user&include_archived=true` 可以返回包含已归档会话的完整列表。
- `GET /api/sessions/{session_id}` 可以返回对应会话详情。
- `PATCH /api/sessions/{session_id}` 可以更新 `title`、`is_pinned`、`is_archived`，并作为主归档/取消归档接口使用。
- `DELETE /api/sessions/{session_id}` 执行后会话被归档，默认列表不再返回它，且该接口语义明确为归档别名而非删除。
- `GET /api/sessions/{session_id}/messages?page=1&page_size=20` 可以按时间正序返回消息历史。
- `WS /ws/{session_id}` 可以连接成功。
- WebSocket 发送 `ping` 后可以收到 `pong`。
- WebSocket 发送 `send_message` 后：
  - 用户消息写入 MySQL
  - Echo Agent 消息写入 MySQL
  - Agent 消息通过 WebSocket 返回客户端
- 再次请求 Message 历史接口时，可以读到刚才写入的用户消息和 Echo 回复。
- README 中的启动与验证步骤足以让其他开发者在本地复现上述验收结果。

## 13. Assumptions

- 本次是特殊合并 task，只合并 `MVP-3` 与 `MVP-4` 的后端部分。
- 后续拆 task 时仍以 `implementation-phases.md` 为准，不把 Echo 默认并入 `MVP-3`。
- 当前 `owner_id` 仅是字符串字段，不引入用户表和认证系统。
- Echo Agent 固定为 `PM`，只用于完成最小消息闭环，不代表 P1 多 Agent 已实现。
- 当前 Message 历史只要求 `text` 类型，不要求图片、文件、Diff 或卡片类消息。
- `proposal.md` 中会话列表的产品能力是“归档”，因此本文档不把“删除会话”视为用户侧主能力。

## 14. 下一步

- 本 task 文档更新后，下一步进入 `task-review-from-spec`。

## 15. 实现记录

- 后端主运行方式已切换为 FastAPI，入口为 `backend/app/main.py`，本地启动代理为 `backend/run.py`。
- 数据层采用 SQLAlchemy ORM；生产默认读取 `DATABASE_URL` 指向 MySQL，测试使用 SQLite 内存库覆盖。
- 当前只创建并维护 `sessions`、`messages` 两张表，MySQL 初始化脚本位于 `backend/sql/001_mvp3_schema.sql`。
- `DELETE /api/sessions/{session_id}` 已按归档别名实现，不物理删除 session 或 messages。
- WebSocket `send_message` 会写入 human 消息和固定 `PM` Echo agent 消息，并更新 session 的 `updated_at`，保证会话列表仍按最近活跃排序。
- 已补充后端契约测试，覆盖健康检查、Session REST、Message 历史、WebSocket ping/pong、Echo 持久化和错误消息。
- 验证命令：`node scripts/run-python.mjs -m pytest tests -p no:cacheprovider`，结果为 `13 passed`。
