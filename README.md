# AgentHub

AgentHub 是一个面向 AI 协作场景设计的 IM 式多 Agent 协作平台。它尝试把复杂的 Agent 调度、任务拆解、上下文承接与产物交付，收敛到用户最熟悉的聊天式交互中: 用户可以像使用即时通讯工具一样新建会话、切换会话、并行推进多个任务，也可以在同一会话里组织多个 Agent 协同完成复杂工作。项目当前默认接入阿里云百炼的 OpenAI-compatible 接口，围绕统一适配层设计，后续可平滑扩展到更多主流模型与 Agent 平台。

## 项目亮点

- IM 式多 Agent 协作体验: 仿照即时通讯聊天形式打造多 Agent 操作界面，以独立会话承载不同任务，支持多会话并行运行，大幅降低 AI 复杂工作流的使用与理解门槛。
- 实时通信：基于 WebSocket 搭建专属实时消息链路，内置连接校验、心跳保活机制，保障会话内消息收发稳定、低延迟。
- 多会话并行: 同时开启多个对话窗口，分别与不同 Agent 交流不同任务，形成类似 IM 多聊天窗口的并行工作体验。
- 群聊化协作思路: 采用调度中心 + 多 Agent 群聊协作架构，可将复杂需求自动拆分为多项子任务，并分发给对应角色 Agent 协同处理，适配各类复杂工作场景。
- 上下文连续与多轮迭代: 每个会话都保留独立消息历史，使 Agent 可以基于上下文持续理解用户意图，支撑多轮追问、补充与修改。
- 产物内联: Agent 的回复不仅限于文本，还可以内联展示代码 Diff、网页预览卡片、文件附件等富媒体产物，用户可直接在聊天流中预览与操作。
- 统一接入主流 Agent 平台: 通过统一适配器层屏蔽不同 API 的调用差异，并逐步支持用户自建 Agent 与自定义能力配置。

## 技术栈

- 前端: Vue 3、TypeScript、Vite
- 后端: FastAPI、Python、MySQL、asyncio
- 实时通信: WebSocket

## 目录结构

```text
frontend/    前端应用
backend/     后端服务
shared/      前后端共享协议与类型定义
openspec/    产品规划、路线图与阶段文档
tests/       测试相关内容
```

## 快速启动

### 1. 拉取代码

```bash
git clone https://github.com/perhaps468/AgentHub.git
cd AgentHub
```

### 2. 安装前端依赖

```bash
pnpm install
```

### 3. 安装后端依赖

```bash
pip install -r backend/requirements.txt
```

### 4. 配置后端环境变量

复制示例配置文件:

```bash
cp backend/.env.example backend/.env
```

然后根据本地环境修改 `backend/.env` 中的数据库、模型和服务配置。

### 5. 初始化数据库

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS agenthub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p < backend/sql/agenthub.sql
```

### 6. 启动后端

```bash
pnpm dev:backend
```

默认监听地址:

```text
http://127.0.0.1:8088
```

### 7. 启动前端

```bash
pnpm dev:frontend
```

启动后即可在浏览器中访问前端页面，并通过前后端联调体验基础会话与消息能力。

## 配置说明

### 阿里云百炼 API Key

当前默认接入阿里云百炼，后续可扩展其他 OpenAI-compatible provider。

后端核心配置文件位于:

```text
backend/.env
```

关键字段说明:

```env
QWEN_API_KEY=your_qwen_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-plus
```

- `QWEN_API_KEY`: 阿里云百炼 API Key
- `QWEN_BASE_URL`: OpenAI-compatible 接口基地址
- `QWEN_MODEL`: 默认使用的模型名称

如果未正确配置 `QWEN_API_KEY`，后端虽然可以启动，但在实际发送消息时会返回 provider 未配置相关错误。

### 接口地址修改位置

前端请求后端服务地址与 WebSocket 地址通过环境变量控制，核心入口位于:

- `frontend/src/api/client.ts`

对应变量为:

```text
VITE_HTTP_URL
VITE_WS_URL
```

说明:

- `VITE_HTTP_URL` 用于拼接前端请求的 HTTP API 地址
- `VITE_WS_URL` 用于拼接前端连接的 WebSocket 地址

后端服务监听地址配置位于:

- `backend/.env.example`
- `backend/.env`

对应字段为:

```env
HOST=127.0.0.1
PORT=8088
```

如果需要切换本地端口、局域网访问地址或对接其他环境，只需要同步修改以上配置项即可。

## 项目阶段与后续规划

当前版本已经完成了 AgentHub 的基础会话模型、消息链路、WebSocket 实时通信与默认 Agent 接入能力，能够支撑一个可运行的 IM 式 Agent 对话雏形。相比单纯的 Demo 页，这一版本更强调平台骨架的建立，包括统一 provider 接入、消息协议、会话边界和后续多 Agent 演进空间。

后续会重点完善以下能力:

- 代码版本历史
- 对话式局部修改
- 一键部署发布
- 更完整的多 Agent 编排与群聊协作体验
- 更丰富的产物预览、编辑与交付链路
