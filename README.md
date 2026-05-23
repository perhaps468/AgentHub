# AgentHub

AgentHub 是一个 IM 聊天式多 Agent 协作平台。当前实现 P1-1 阶段：单 Provider（千问 OpenAI 兼容接口）+ 单内置 PM Agent + WebSocket 真实消息链路。

## 目录职责

- `frontend`: Vue + Vite 前端应用。
- `backend`: FastAPI 后端服务，提供会话、消息历史、WebSocket 真实 Agent 消息和 Agent 身份接口。
- `shared`: 前后端共享类型和协议定义。
- `openspec`: 产品规划、阶段说明和变更文档。

## 后端环境变量

复制 `backend/.env.example` 为 `backend/.env` 后按本地环境修改。真实密钥只放本地 `.env`，不要提交到 GitHub。

```bash
# Database
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/agenthub

# Server
HOST=127.0.0.1
PORT=8088

# Qwen Provider (千问 OpenAI 兼容接口)
QWEN_API_KEY=your_qwen_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

未配置 `QWEN_API_KEY` 时后端仍可启动，但发送消息会返回 `provider_not_configured` 错误。

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
- `GET /api/agents/default`
- `GET /api/sessions/{session_id}/messages`
- `WS /ws/{session_id}`

`DELETE /api/sessions/{session_id}` 是兼容接口，行为等价于设置 `is_archived=true`，不会物理删除会话或消息。

## WebSocket 契约

`WS /ws/{session_id}` 使用真实 PM Agent 响应，不再使用 Echo。

- 连接到存在的 `session_id` 后，客户端可以发送 `{"type":"ping"}`，服务端会返回 `{"type":"pong"}`。
- `ping/pong` 只用于连接保活，不会写入消息历史，也不会触发 Agent 回复。
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
- `provider_not_configured`：QWEN_API_KEY 未配置。
- `provider_request_failed`：上游调用失败。
- `provider_response_invalid`：上游响应无有效内容。
- `unknown`：服务端出现未预期异常。

默认 Agent 为 `PM Agent`，可通过 `GET /api/agents/default` 获取身份信息（不包含模型名）。

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

查询默认 Agent 信息：

```bash
curl http://127.0.0.1:8000/api/agents/default
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
