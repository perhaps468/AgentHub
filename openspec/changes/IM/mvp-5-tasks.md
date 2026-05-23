# Task: MVP-5 WebSocket 连接状态与基础重连契约

## 0. 文档定位

- 本文档基于 `openspec/specs/implementation-phases.md` 的 `MVP-5 连接状态与基础重连完成`。
- 本文档按 `task-planning-from-spec` 拆分后端/API 契约 task；不拆前端实现任务，不进入编码，也不评审 task。
- MVP-5 不新增 REST 接口，继续复用 `WS /ws/{session_id}`。
- MVP-5 不统一 WebSocket 业务消息协议，不改造当前 `chat_stream` 消息结构。

## 1. 任务目标

- 确认并固化后端 WebSocket 最小探活契约：客户端发送 `ping`，服务端返回 `pong`。
- 确认后端在 WebSocket 断开、非法消息、缺失会话等场景下返回稳定错误或正常清理连接。
- 为客户端连接状态、心跳、指数退避重连和失败后手动重试提供明确联调契约。
- 保证重连成功后，客户端仍可通过同一个 `WS /ws/{session_id}` 契约继续发送消息并收到 Echo 回复。

## 2. 当前范围

- WebSocket 端点：`WS /ws/{session_id}`。
- 客户端心跳消息：`{"type": "ping"}`。
- 服务端心跳响应：`{"type": "pong"}`。
- 服务端错误消息：`{"type": "error", "error_code": "...", "error_message": "..."}`。
- 客户端业务发送消息：`{"action": "send_message", "session_id": "...", "content": "..."}`。
- 服务端业务返回消息：当前后端实际 `chat_stream` 响应结构保持不变。
- 后端断连处理：捕获 WebSocket 断开，不产生未处理异常。

## 3. 不做什么

- 不新增 REST API。
- 不新增数据库表或字段。
- 不实现服务端主动心跳。
- 不实现 HTTP 轮询兜底。
- 不实现离线消息队列、断线消息缓存或补发。
- 不实现连接注册表、多人广播或多端同步。
- 不引入 P2-1 的 JWT 鉴权；后续 Auth 接入时只复用本阶段契约。
- 不重构 `shared` 中的理想化 WebSocket schema，也不在本阶段反向改造后端业务消息格式。
- 不拆前端组件、composable、UI 状态展示等实现任务。

## 4. 依赖与前置条件

- `MVP-3` 已提供 `WS /ws/{session_id}`。
- `MVP-4` 已支持 `send_message`，并能持久化 human 消息与 Echo agent 消息。
- 当前后端已存在 `backend/app/api/ws.py`。
- 当前后端测试已存在 `backend/tests/test_ws.py`。
- 客户端实现 MVP-5 状态机时，应遵守本文件的 WebSocket 契约：
  - `connected`：WebSocket `open` 后进入。
  - `reconnecting`：异常断开或心跳超时后进入。
  - `failed`：按客户端策略连续重连失败后进入。
  - 手动重试：重新连接同一个 `WS /ws/{session_id}`。

## 5. 需要改动的后端模块、接口或配置

- `backend/app/api/ws.py`
  保留或补齐 WebSocket 心跳、错误消息、断连清理与 `send_message` 处理。
- `backend/tests/test_ws.py`
  补齐 MVP-5 所需的 WebSocket 契约测试。
- `README.md`
  如当前说明不足，补充 WebSocket 心跳与重连联调说明。

不需要改动：

- 数据模型。
- REST 路由。
- 数据库迁移。
- Auth 配置。

## 6. 接口契约

### 6.1 WebSocket 建连

**请求方法与路径**

```text
WS /ws/{session_id}
```

**认证方式**

- MVP-5：无认证。
- P2-1 后：由 Auth 阶段另行接入 JWT，不在本 task 中实现。

**Path 参数**

| 字段 | 类型 | 必填 | 含义 | 取值 |
|------|------|------|------|------|
| `session_id` | string | 是 | 目标会话 ID | 已存在的会话 UUID 字符串 |

**成功行为**

- `session_id` 存在时，服务端接受连接。
- 客户端可继续发送 `ping` 或 `send_message`。

**主要错误行为**

- `session_id` 不存在时，服务端发送错误消息并关闭连接，或拒绝连接。
- 如果发送错误消息，格式必须符合 `6.4 服务端错误消息`。

### 6.2 客户端心跳消息

**方向**

客户端 -> 服务端

**消息体**

```json
{
  "type": "ping"
}
```

**字段定义**

| 字段 | 类型 | 必填 | 含义 | 取值 |
|------|------|------|------|------|
| `type` | string | 是 | 心跳请求类型 | 固定为 `ping` |

**服务端响应**

服务端必须返回 `pong`：

```json
{
  "type": "pong"
}
```

### 6.3 服务端心跳响应

**方向**

服务端 -> 客户端

**消息体**

```json
{
  "type": "pong"
}
```

**字段定义**

| 字段 | 类型 | 必填 | 含义 | 取值 |
|------|------|------|------|------|
| `type` | string | 是 | 心跳响应类型 | 固定为 `pong` |

**约束**

- MVP-5 不要求服务端主动发送 `pong`。
- `pong` 只需要响应客户端 `ping`。

### 6.4 服务端错误消息

**方向**

服务端 -> 客户端

**消息体**

```json
{
  "type": "error",
  "error_code": "invalid_request",
  "error_message": "Invalid request"
}
```

**字段定义**

| 字段 | 类型 | 必填 | 含义 | 取值 |
|------|------|------|------|------|
| `type` | string | 是 | 消息类型 | 固定为 `error` |
| `error_code` | string | 是 | 稳定错误码 | `session_not_found`、`invalid_request`、`unknown` |
| `error_message` | string | 是 | 可读错误说明 | 非空字符串 |

**触发条件**

- `session_not_found`：连接或访问的会话不存在。
- `invalid_request`：消息体不是支持的 `ping` 或合法 `send_message`。
- `unknown`：服务端遇到未预期异常，但连接仍可尝试返回错误。

### 6.5 客户端发送消息

**方向**

客户端 -> 服务端

**消息体**

```json
{
  "action": "send_message",
  "session_id": "00000000-0000-0000-0000-000000000000",
  "content": "hello"
}
```

**字段定义**

| 字段 | 类型 | 必填 | 含义 | 取值 |
|------|------|------|------|------|
| `action` | string | 是 | 业务动作 | 固定为 `send_message` |
| `session_id` | string | 是 | 目标会话 ID | 必须与路径 `session_id` 一致 |
| `content` | string | 是 | 用户消息内容 | 非空字符串 |

**服务端成功行为**

- 写入 human 消息。
- 写入 Echo agent 消息。
- 返回当前后端实际 `chat_stream` 消息。

**主要错误响应**

- `invalid_request`：缺少 `content`、`content` 为空、`session_id` 与路径不一致，或 `action` 非法。

### 6.6 服务端业务消息

**方向**

服务端 -> 客户端

**当前响应结构**

```json
{
  "type": "chat_stream",
  "message_id": "00000000-0000-0000-0000-000000000000",
  "session_id": "00000000-0000-0000-0000-000000000000",
  "sender_type": "agent",
  "sender_role": "PM",
  "content": "Echo: hello",
  "content_type": "text",
  "created_at": "2026-05-22T10:30:00Z"
}
```

**字段定义**

| 字段 | 类型 | 必填 | 含义 | 取值 |
|------|------|------|------|------|
| `type` | string | 是 | 消息类型 | 固定为 `chat_stream` |
| `message_id` | string | 是 | Agent 消息 ID | UUID 字符串 |
| `session_id` | string | 是 | 所属会话 ID | UUID 字符串 |
| `sender_type` | string | 是 | 发送方类型 | 当前为 `agent` |
| `sender_role` | string | 是 | Agent 角色 | 当前为 `PM` |
| `content` | string | 是 | Echo 内容 | `Echo: {用户输入}` |
| `content_type` | string | 是 | 内容类型 | 当前为 `text` |
| `created_at` | string | 是 | 创建时间 | ISO 8601 字符串 |

**约束**

- MVP-5 不修改该业务消息结构。
- 客户端状态机只需要将该消息视为普通业务消息，不应依赖它判断连接健康。

## 7. Task 拆分

### MVP-5-1 固化 WebSocket ping/pong 契约

**任务目标**

保证 `WS /ws/{session_id}` 对客户端心跳请求有稳定响应，作为前端判断连接健康的后端依据。

**当前范围**

- 支持客户端发送 `{"type": "ping"}`。
- 服务端返回 `{"type": "pong"}`。
- 不改变 `send_message` 行为。

**不做什么**

- 不做服务端主动心跳。
- 不做重连算法。
- 不做前端状态展示。

**依赖与前置条件**

- `backend/app/api/ws.py` 已可接受 WebSocket 连接。
- `backend/tests/test_ws.py` 可运行。

**需要改动的后端模块、数据模型、接口或配置**

- 可能改动：`backend/app/api/ws.py`。
- 必须测试：`backend/tests/test_ws.py`。
- 不改动数据模型、REST 接口或配置。

**接口契约**

- 使用 `6.1`、`6.2`、`6.3` 定义的 WebSocket 建连与心跳契约。

**详细实现步骤**

1. 检查 `ws.py` 是否在收到 `{"type": "ping"}` 时立即返回 `{"type": "pong"}`。
2. 如果已有行为满足契约，只补充或保留测试，不改业务代码。
3. 如果响应格式不一致，调整为固定 `{"type": "pong"}`。
4. 确保 `ping` 分支不会继续落入 `send_message` 校验。

**测试方案**

- 建立存在会话的 WebSocket 连接。
- 发送 `{"type": "ping"}`。
- 断言收到且仅收到 `{"type": "pong"}`。
- 发送多次 `ping`，断言每次都有 `pong` 响应。

**验收标准**

- `test_websocket_ping_pong` 通过。
- 多次 `ping` 不写入消息历史。
- `ping` 不触发 Echo 回复。

### MVP-5-2 固化 WebSocket 错误与断连清理契约

**任务目标**

保证客户端在连接失败、非法消息和断开连接时能获得稳定后端行为，从而支撑前端进入 `disconnected`、`reconnecting` 或 `failed` 状态。

**当前范围**

- 会话不存在时返回稳定错误或关闭连接。
- 非法消息返回 `invalid_request`。
- WebSocket 断开时后端捕获断连，不产生未处理异常。

**不做什么**

- 不保存连接状态到数据库。
- 不维护连接注册表。
- 不做多人广播。
- 不实现前端状态机。

**依赖与前置条件**

- MVP-5-1 的 `ping/pong` 契约稳定。
- 当前后端已有错误消息格式。

**需要改动的后端模块、数据模型、接口或配置**

- 可能改动：`backend/app/api/ws.py`。
- 必须测试：`backend/tests/test_ws.py`。
- 不改动数据模型、REST 接口或配置。

**接口契约**

- 错误消息使用 `6.4 服务端错误消息`。
- 非法 `send_message` 使用 `invalid_request`。
- 缺失会话使用 `session_not_found`。

**详细实现步骤**

1. 检查缺失会话路径是否返回 `session_not_found` 或明确关闭连接。
2. 检查非法消息是否返回 `invalid_request`。
3. 检查 WebSocket 断开是否捕获 `WebSocketDisconnect`。
4. 如有未捕获异常路径，收束到错误消息或断连清理。
5. 保持现有 `send_message` 成功路径不变。

**测试方案**

- 连接不存在的 `session_id`，断言返回 `session_not_found` 或连接被服务端关闭。
- 发送非法消息体，断言返回 `invalid_request`。
- 客户端主动关闭连接，断言测试进程无未捕获异常。

**验收标准**

- 缺失会话行为稳定。
- 非法消息错误码稳定。
- 客户端断开连接后后端无未处理异常。

### MVP-5-3 WebSocket 重连联调契约验收

**任务目标**

定义 MVP-5 与客户端重连状态机的联调验收要求，确认后端契约足以支撑客户端连接状态和重连体验。

**当前范围**

- 后端只提供稳定 WebSocket 契约。
- 客户端按 `implementation-phases.md` 的 MVP-5 决策实现状态机：
  - `connected`
  - `disconnected`
  - `reconnecting`
  - `failed`
  - 30 秒客户端心跳
  - 5 次指数退避重连
  - 手动重试
- 联调关注契约是否满足体验，不拆客户端代码任务。

**不做什么**

- 不规定客户端文件结构。
- 不实现客户端状态机。
- 不要求服务端知道客户端重连次数。
- 不新增服务端状态查询接口。

**依赖与前置条件**

- MVP-5-1 和 MVP-5-2 通过。
- MVP-4 的 `send_message` 与 Echo 返回可用。
- 客户端已按 MVP-5 决策实现连接状态和重连。

**需要改动的后端模块、数据模型、接口或配置**

- 通常不需要新增后端改动。
- 如联调发现契约缺口，只允许在 `backend/app/api/ws.py` 和 `backend/tests/test_ws.py` 内收束后端行为。

**接口契约**

- 建连、心跳、错误、发送消息均使用第 `6` 节契约。

**详细实现步骤**

1. 启动后端服务。
2. 创建或选择一个已存在会话。
3. 客户端连接 `WS /ws/{session_id}`，确认连接成功。
4. 客户端发送 `ping`，确认收到 `pong`。
5. 客户端发送 `send_message`，确认收到 Echo `chat_stream`。
6. 模拟 WebSocket 断开，确认客户端能基于断连事件进入重连流程。
7. 恢复服务或网络后，客户端重新连接同一路径。
8. 重连成功后再次发送 `send_message`，确认仍可收到 Echo。

**测试方案**

- 后端自动化测试覆盖 `ping/pong`、非法消息、缺失会话。
- 联调手工测试覆盖断开、重连、失败后手动重试、重连后发送消息。
- 若具备前端 e2e 环境，可补充端到端场景，但不是本后端/API task 的硬性要求。

**验收标准**

- 客户端可以通过 `ping/pong` 判断连接健康。
- 客户端断线后可以重新连接同一个 `WS /ws/{session_id}`。
- 服务端不需要保存重连次数，也不需要新增查询接口。
- 重连成功后 `send_message` 仍可正常工作。
- 后端契约未引入新的 REST API 或数据模型变更。

## 8. 统一测试方案

- 运行后端 WebSocket 契约测试。
- 覆盖存在会话的 `ping/pong`。
- 覆盖不存在会话的错误行为。
- 覆盖非法消息的错误行为。
- 覆盖合法 `send_message` 在重连后仍可使用的手工联调场景。

建议命令：

```bash
cd backend
python -m pytest tests/test_ws.py
```

如项目当前使用 npm/pnpm 包装 Python 测试命令，则使用仓库 README 中记录的等价命令。

## 9. 统一验收标准

- `WS /ws/{session_id}` 对存在会话可连接。
- 客户端发送 `{"type": "ping"}` 后，服务端返回 `{"type": "pong"}`。
- `ping/pong` 不写入消息表，不触发 Echo。
- 缺失会话返回稳定错误或关闭连接，行为可被客户端识别为连接失败。
- 非法消息返回稳定 `invalid_request` 错误。
- 客户端断开 WebSocket 时，后端没有未处理异常。
- 重连后继续发送 `send_message`，仍能收到当前后端实际 `chat_stream` Echo 回复。
- 本阶段没有新增 REST API、数据库表、数据库字段或 Auth 逻辑。

## 10. 依赖或阻塞

- 如果客户端尚未完成最小聊天页，本 task 仍可先完成后端/API 契约测试；联调验收需等待客户端状态机接入聊天页。
- 如果后续决定统一 `shared` WebSocket schema 与后端实际响应结构，应另开协议收束 task，不能混入 MVP-5。

## 11. 下一步

- 本 task 文档完成后，下一步进入 `task-review-from-spec`。
