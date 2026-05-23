# AgentHub

AgentHub 是一个 IM 聊天式多 Agent 协作平台。当前实现聚焦 MVP-3 + MVP-4 的后端闭环：Session REST、Message 历史、按会话工作的 WebSocket，以及最小 Echo 消息持久化。

## 目录职责

- `frontend`: Vue + Vite 前端应用。
- `backend`: FastAPI 后端服务，提供会话、消息历史和 WebSocket Echo 接口。
- `shared`: 前后端共享类型和协议定义。
- `openspec`: 产品规划、阶段说明和变更文档。

## 后端环境变量

复制 `backend/.env.example` 为 `backend/.env` 后按本地环境修改：

```bash
HOST=127.0.0.1
PORT=8000
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/agenthub
```

如果不创建 `backend/.env`，后端会使用以上默认值。

## 本地启动

安装前端 workspace 依赖：

```bash
pnpm install
```

安装后端 Python 依赖：

```bash
python -m pip install -r backend/requirements.txt
```

初始化 MySQL 数据库：

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS agenthub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p agenthub < backend/sql/001_mvp3_schema.sql
```

启动前端开发服务：

```bash
pnpm dev:frontend
```

启动后端开发服务：

```bash
pnpm dev:backend
```

默认后端监听 `http://127.0.0.1:8000`，健康检查地址为 `http://127.0.0.1:8000/health`。

## 后端接口

当前后端提供：

- `GET /`
- `GET /health`
- `GET /api/health`
- `POST /api/sessions`
- `GET /api/sessions`
- `GET /api/sessions/{session_id}`
- `PATCH /api/sessions/{session_id}`
- `DELETE /api/sessions/{session_id}`
- `GET /api/sessions/{session_id}/messages`
- `WS /ws/{session_id}`

`DELETE /api/sessions/{session_id}` 是兼容接口，行为等价于设置 `is_archived=true`，不会物理删除会话或消息。

## WebSocket 契约

`WS /ws/{session_id}` 在 MVP-5 阶段继续复用既有会话通道，不新增 REST 接口。

- 连接到存在的 `session_id` 后，客户端可以发送 `{"type":"ping"}`，服务端会返回 `{"type":"pong"}`。
- `ping/pong` 只用于连接保活，不会写入消息历史，也不会触发 Echo 回复。
- 业务消息继续使用：

```json
{
  "action": "send_message",
  "session_id": "<session_id>",
  "content": "hello"
}
```

- 服务端错误统一返回：

```json
{
  "type": "error",
  "error_code": "invalid_request",
  "error_message": "Invalid request"
}
```

当前稳定错误码包括：

- `session_not_found`：目标会话不存在。
- `invalid_request`：消息体不是合法的 `ping` 或 `send_message` 契约。
- `unknown`：服务端出现未预期异常。

MVP-5 的自动重连由客户端负责。客户端断开后，可以重新连接同一个 `WS /ws/{session_id}`，连接恢复后继续发送 `send_message` 并接收现有 `chat_stream` Echo 响应。

## 验证命令

健康检查：

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

创建会话：

```bash
curl -X POST http://127.0.0.1:8000/api/sessions -H "Content-Type: application/json" -d "{\"owner_id\":\"dev_user\",\"title\":\"New Session\",\"mode\":\"single\"}"
```

查询会话列表：

```bash
curl "http://127.0.0.1:8000/api/sessions?owner_id=dev_user"
```

归档会话：

```bash
curl -X PATCH http://127.0.0.1:8000/api/sessions/<session_id> -H "Content-Type: application/json" -d "{\"is_archived\":true}"
```

查询消息历史：

```bash
curl "http://127.0.0.1:8000/api/sessions/<session_id>/messages?page=1&page_size=20"
```

运行后端测试：

```bash
cd backend
python -m pytest tests -p no:cacheprovider
```
