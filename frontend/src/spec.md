# AgentHub 多 Agent 协作平台前端架构 spec

> 技术栈：Vue 3 + Pinia + Axios + Element Plus + TypeScript + Tailwind CSS  
> 核心范式：IM 聊天式多 Agent 协作  
> 页面形态：左侧导航与列表 + 中间聊天区 + 右侧产物预览区

---

## 1. 项目定位

AgentHub 是一个面向网页、Workflow、代码、文档、PPT 等产物生成的多 Agent 协作平台。用户通过类似飞书 / 微信的聊天方式，与 Claude Code、Codex、OpenCode、自建 Agent 或真实人员进行协作。

核心目标：

- 通过新建会话与不同 Agent 进行单聊。
- 在群聊中 `@` 多个 Agent，由 Orchestrator 拆解任务、分派子 Agent、聚合结果。
- 每个会话保留完整上下文，支持多轮迭代。
- Agent 回复可内联展示代码、文件、网页预览、PPT、Diff、部署状态等产物。
- 右侧统一预览 PPT、代码、网页等结果。

---

## 2. 技术架构

| 层级 | 技术 | 约束 |
|---|---|---|
| 框架 | Vue 3 | 使用 Composition API 与 `<script setup lang="ts">` |
| 状态 | Pinia | 拆分会话、消息、Agent、预览、用户模块 |
| 请求 | Axios | 统一实例、token 注入、错误拦截 |
| UI | Element Plus | 用于 Dialog、Select、Upload、Popover、Tooltip、Empty、Message |
| 样式 | Tailwind CSS | 优先 utility class，复杂局部样式用 scoped CSS |
| 类型 | TypeScript | 明确业务类型，避免 `any` |
| 构建 | Vite | 开发、构建、热更新 |

推荐目录：

```text
src/
  api/                # axios 接口层
  components/
    common/           # 搜索框、头像、按钮等
    layout/           # 三栏布局
    chat/             # 聊天头、消息、输入框、卡片
    preview/          # 代码/网页/PPT/文件预览
    agent/            # Agent 与人员列表
  store/modules/      # Pinia 模块
  types/              # Conversation/Message/Agent/Artifact 类型
  utils/              # 日期、文件、复制、ws 等工具
  views/              # 页面级组件
```

---

## 3. 整体页面布局

主工作台为三栏结构：

```text
┌───────────────┬────────────────────────────┬──────────────────────┐
│ 左侧导航与列表 │ 中间聊天区                   │ 右侧预览区             │
│ Nav + List    │ Header + Messages + Input  │ Code/Web/PPT Preview │
└───────────────┴────────────────────────────┴──────────────────────┘
```

尺寸建议：

| 区域 | 宽度 | 说明 |
|---|---:|---|
| 一级导航栏 | 64px | 头像、聊天按钮、人员按钮 |
| 二级列表区 | 280-320px | 聊天记录 / Agent / 人员列表 |
| 中间聊天区 | 自适应，最小 520px | 核心对话区域 |
| 右侧预览区 | 360-480px | 预览 PPT、代码、网页 |

样式原则：

- 页面高度 `100vh`，横向 `flex`。
- 背景使用 `bg-white`、`bg-gray-50`。
- 区域分割使用 `border-r border-gray-100`。
- 控件风格简洁，避免大面积高饱和色、渐变和重阴影。

---

## 4. 左侧区域

左侧由一级竖向导航栏和二级列表区组成。

### 4.1 一级导航栏

从上到下：

1. 当前用户头像。
2. 聊天按钮：切换到聊天记录列表。
3. 人员按钮：切换到 Agent / 人员列表。

交互：

- 激活项使用浅灰背景或深色图标。
- 按钮建议尺寸 `44px × 44px`。
- 用户头像点击可进入个人信息或设置。

### 4.2 聊天记录列表

顶部为搜索框，下方为聊天记录。

搜索框支持：

- 按会话名称、最近消息、Agent 名称搜索。
- 输入即时过滤。
- 清空关键词。

会话项展示：

- 会话头像。
- 会话名称。
- 最近消息摘要。
- 最近活跃时间。
- 未读数。
- 置顶标记。
- 单聊 / 群聊标识。

操作：

- 新建会话。
- 置顶 / 取消置顶。
- 归档。
- 点击切换当前会话。

排序：置顶优先，其余按 `updated_at` 倒序。

### 4.3 Agent / 人员列表

点击人员按钮后，二级列表切换为联系人视图。顶部仍为搜索框。

分组：

- Agent。
- 人员。

Agent 项：

```text
[头像] Claude Code
      Vue / React / Code Review
```

展示字段：头像、名称、能力标签、在线状态、平台来源。点击 Agent 后打开已有单聊，若没有则创建新单聊。

人员项：

```text
[头像] 张三
      前端开发
```

展示字段：头像、名称，可扩展角色、部门、在线状态。

---

## 5. 中间聊天区

中间区由聊天头、消息流、输入框组成。

### 5.1 聊天头

展示：

- 当前聊天名称。
- 单聊 / 群聊模式。
- 参与 Agent / 人员数量。
- 群聊成员头像组。
- 操作按钮：置顶、归档、设置、上下文管理。

单聊示例：`Claude Code`，副标题 `Vue / TypeScript / Refactor`。  
群聊示例：`官网落地页生成任务`，副标题 `Orchestrator + Claude Code + Codex`。

### 5.2 消息组

每组消息包含：

- 头像。
- 发送者名称。
- 发送时间。
- 引用摘要。
- 消息正文。
- 操作按钮：引用、复制。

自己的消息额外包含：撤回。  
Agent 消息额外包含：重新生成、复制代码、代码预览、应用 Diff、展开预览。

### 5.3 消息类型

| 类型 | 展示 |
|---|---|
| 文本 | 普通消息气泡 |
| 代码 | 代码卡片，显示文件名、语言、复制、预览 |
| 图片 | 缩略图，点击预览 |
| 文件 | 文件卡片，显示名称、大小、下载 |
| 网页预览 | 标题、描述、预览按钮 |
| Diff | 文件名、增删统计、应用按钮 |
| 部署状态 | 状态、日志、预览 URL |
| 系统消息 | 居中浅色提示 |

用户消息靠右，Agent 消息靠左，系统消息居中。

### 5.4 Agent 代码消息

代码卡片必须展示：

- 文件名，如 `src/components/UserCard.vue`。
- 文件格式 / 语言，如 `vue`、`ts`、`css`。
- 格式化代码内容。
- 复制按钮。
- 预览按钮。

点击预览后，右侧预览区切换为代码预览。

### 5.5 群聊协作流程

群聊中一次任务可能产生多条 Agent 消息：

1. 用户发送需求。
2. Orchestrator 理解意图并拆解任务。
3. Orchestrator 分派给 Claude Code、Codex、OpenCode 等子 Agent。
4. 子 Agent 依次或并行回复。
5. Orchestrator 汇总结果，并提示可在右侧预览。

Orchestrator 在前端表现为特殊 Agent，头像和名称固定，可展示任务拆解卡片。

### 5.6 底部输入框

包含：

- 文件发送按钮。
- 表情按钮。
- 多行文本输入框。
- 发送按钮。
- 可选 `@ Agent` 选择器。

输入规则：

- Enter 发送，Shift + Enter 换行。
- 空内容且无附件时禁用发送。
- 支持引用回复：输入框上方显示被引用消息摘要。
- 支持草稿：切换会话时保留当前输入。
- 发送后先本地插入用户消息，再等待 Agent 回复。

---

## 6. 右侧预览区

右侧用于预览 Agent 产物，支持代码、网页、PPT、文件、部署结果。

### 6.1 空状态

无内容时显示：

```text
暂无预览
点击 Agent 消息中的“预览”按钮后，在这里查看代码、网页或 PPT。
```

### 6.2 代码预览

展示：文件名、语言、代码、复制、下载、可选编辑按钮。P2 可扩展 Monaco Editor、Diff、版本历史、局部修改。

### 6.3 网页预览

展示：标题、URL、iframe、刷新、新窗口打开。iframe 地址必须来自可信 URL 或后端代理。

### 6.4 PPT 预览

展示：标题、当前页 / 总页数、上一页、下一页、缩略图、下载。P0 可用图片序列或 PDF 预览占位，P2 接入完整 PPT 渲染。

---

## 7. 核心类型设计

```ts
export type SidebarMode = 'conversations' | 'contacts'
export type ConversationMode = 'single' | 'group'
export type SenderType = 'human' | 'agent' | 'system'
export type PreviewType = 'empty' | 'code' | 'web' | 'ppt' | 'file' | 'deploy'

export interface AgentProfile {
  id: string
  name: string
  avatar?: string | null
  platform: 'Claude Code' | 'Codex' | 'OpenCode' | 'Custom'
  capabilityTags: string[]
  status?: 'online' | 'offline'
  systemPrompt?: string
  tools?: string[]
}

export interface PersonProfile {
  id: string
  name: string
  avatar?: string | null
  role?: string
}

export interface ConversationItem {
  id: string
  owner_id: string
  title: string | null
  mode: ConversationMode
  is_pinned: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
  last_message?: string
  unread_count?: number
  avatar?: string | null
}

export interface MessageReference {
  id: string
  senderName: string
  summary: string
}

export type MessageContentType = 'text' | 'code' | 'image' | 'file' | 'web_preview' | 'diff' | 'deploy'
export type ArtifactType = 'code' | 'web' | 'ppt' | 'file' | 'diff' | 'deploy'

export interface ChatMessage {
  id: string
  session_id: string
  sender_type: SenderType
  sender_role: string | null
  sender_name?: string
  sender_avatar?: string | null
  content: string
  content_type: MessageContentType
  created_at: string
  reference?: MessageReference | null
  artifacts?: MessageArtifact[]
  status?: 'sending' | 'success' | 'failed' | 'revoked'
}

export interface MessageArtifact {
  id: string
  type: ArtifactType
  title: string
  fileName?: string
  language?: string
  code?: string
  url?: string
  description?: string
  fileSize?: string
  fileType?: string
  slides?: string[]
  diff?: DiffFile[]
  deployStatus?: DeployStatus
}

export interface DiffFile {
  fileName: string
  additions: number
  deletions: number
  patch: string
}

export interface DeployStatus {
  status: 'pending' | 'building' | 'success' | 'failed'
  url?: string
  logs?: string[]
}

export interface PreviewState {
  type: PreviewType
  title: string
  language?: string
  code?: string
  url?: string
  description?: string
  fileName?: string
  fileSize?: string
  fileType?: string
  slides?: string[]
  currentSlideIndex?: number
}
```

---

## 8. Pinia 状态模块

### 8.1 `useConversationStore`

状态：

- `conversations`：会话列表。
- `currentConversationId`：当前会话。
- `sidebarMode`：`conversations` 或 `contacts`。
- `keyword`：搜索关键词。

方法：

- `fetchConversations()`。
- `createConversation(payload)`。
- `selectConversation(id)`。
- `pinConversation(id)`。
- `archiveConversation(id)`。
- `searchConversations(keyword)`。

### 8.2 `useMessageStore`

状态：

- `messageMap`：按会话 ID 缓存消息。
- `replyTarget`：当前引用消息。
- `draftMap`：各会话草稿。
- `loadingSessionIds`：正在加载的会话。

方法：

- `fetchMessages(sessionId)`。
- `sendMessage(payload)`。
- `receiveMessage(message)`。
- `revokeMessage(messageId)`。
- `regenerateMessage(messageId)`。
- `setReplyTarget(message)`。
- `clearReplyTarget()`。

### 8.3 `useAgentStore`

状态：

- `agents`：Agent 列表。
- `people`：人员列表。
- `keyword`：联系人搜索关键词。

方法：

- `fetchAgents()`。
- `fetchPeople()`。
- `createCustomAgent(payload)`。
- `openAgentConversation(agentId)`。

### 8.4 `usePreviewStore`

状态：

- `preview`：当前预览内容。
- `visible`：预览区是否展示。

方法：

- `openCodePreview(artifact)`。
- `openWebPreview(artifact)`。
- `openPptPreview(artifact)`。
- `openFilePreview(artifact)`。
- `openDeployPreview(artifact)`。
- `clearPreview()`。

---

## 9. API 设计

### 9.1 会话 API

```ts
getConversations(params?: { keyword?: string; archived?: boolean })
createConversation(payload: {
  title?: string
  mode: 'single' | 'group'
  agentIds?: string[]
  memberIds?: string[]
})
updateConversation(id: string, payload: {
  title?: string
  is_pinned?: boolean
  is_archived?: boolean
})
```

### 9.2 消息 API

```ts
getMessages(sessionId: string, params?: { page?: number; pageSize?: number })
sendMessage(payload: {
  sessionId: string
  content: string
  mentions?: string[]
  files?: string[]
  referenceMessageId?: string
})
revokeMessage(messageId: string)
regenerateMessage(messageId: string)
```

### 9.3 Agent API

```ts
getAgents(params?: { keyword?: string })
createCustomAgent(payload: {
  name: string
  avatar?: string
  systemPrompt: string
  tools: string[]
  capabilityTags: string[]
})
```

### 9.4 文件与产物 API

```ts
uploadFile(file: File)
getArtifact(artifactId: string)
deployArtifact(artifactId: string)
```

---

## 10. WebSocket 实时消息

Agent 回复建议通过 WebSocket 或 SSE 支持流式输出。

客户端发送：

```ts
export interface SendMessagePayload {
  action: 'send_message'
  session_id: string
  content: string
  mentions?: string[]
  files?: string[]
  reference_message_id?: string
}
```

服务端推送：

```ts
export interface WsIncomingMessage {
  type:
    | 'message.created'
    | 'message.delta'
    | 'message.completed'
    | 'message.failed'
    | 'artifact.created'
    | 'deploy.updated'
  message?: ChatMessage
  data?: unknown
}
```

规则：

- `message.created` 创建 Agent 占位消息。
- `message.delta` 增量追加内容。
- `message.completed` 标记完成。
- `artifact.created` 插入代码、网页、PPT、文件等产物卡片。
- `message.failed` 显示失败状态和重试按钮。

---

## 11. 组件拆分

页面级：

| 组件 | 职责 |
|---|---|
| `AgentHubWorkspace.vue` | 三栏主工作台 |
| `LeftSidebar.vue` | 左侧导航与列表容器 |
| `ChatPanel.vue` | 中间聊天容器 |
| `PreviewPanel.vue` | 右侧预览容器 |

左侧：

| 组件 | 职责 |
|---|---|
| `PrimaryNav.vue` | 用户头像、聊天按钮、人员按钮 |
| `ConversationList.vue` | 聊天记录列表 |
| `ConversationItem.vue` | 单个会话项 |
| `ContactList.vue` | Agent 与人员列表 |
| `AgentItem.vue` | Agent 头像、名称、能力标签 |
| `PersonItem.vue` | 人员头像、名称 |
| `SearchInput.vue` | 搜索框 |

聊天区：

| 组件 | 职责 |
|---|---|
| `ChatHeader.vue` | 聊天名称、成员、操作 |
| `MessageList.vue` | 消息列表和滚动 |
| `MessageGroup.vue` | 一组消息基础布局 |
| `UserMessage.vue` | 用户消息 |
| `AgentMessage.vue` | Agent 消息 |
| `SystemMessage.vue` | 系统消息 |
| `MessageActions.vue` | 引用、复制、撤回、重新生成 |
| `CodeArtifactCard.vue` | 代码卡片 |
| `FileArtifactCard.vue` | 文件卡片 |
| `WebPreviewCard.vue` | 网页卡片 |
| `DiffArtifactCard.vue` | Diff 卡片 |
| `DeployStatusCard.vue` | 部署状态卡片 |
| `ChatComposer.vue` | 输入框、文件、表情、发送 |

预览区：

| 组件 | 职责 |
|---|---|
| `EmptyPreview.vue` | 空状态 |
| `CodePreview.vue` | 代码预览 |
| `WebPreview.vue` | iframe 网页预览 |
| `PptPreview.vue` | PPT 预览 |
| `FilePreview.vue` | 文件预览 |
| `DeployPreview.vue` | 部署结果 |

---


切换会话时同步更新路由，刷新后可恢复当前会话。

---

## 13. P0 / P1 / P2 计划

### P0：基础 IM 与单 Agent

- 三栏布局。
- 聊天记录列表。
- Agent / 人员列表。
- 文本消息收发。
- Agent 文本回复。
- 代码卡片。
- 右侧代码预览。

### P1：群聊与富消息

- 群聊模式。
- `@ Agent`。
- Orchestrator 协调消息。
- 多 Agent 顺序回复。
- 文件发送。
- 表情。
- 引用、复制、撤回。
- 网页预览。

### P2：编辑、Diff、部署

- PPT 预览。
- Diff 视图。
- 一键应用 Diff。
- 版本历史。
- 代码编辑器。
- 选中代码后对话式局部修改。
- 部署状态卡片。
- 一键部署、预览 URL、源码打包下载。

---

## 14. 验收标准

### 左侧

- 展示当前用户头像。
- 聊天按钮可切换聊天记录列表。
- 人员按钮可切换 Agent / 人员列表。
- 每个列表顶部都有搜索框。
- Agent 项包含头像、名称、能力标签。
- 人员项包含头像、名称。

### 中间

- 顶部显示聊天名称。
- 每组消息包含头像、时间、引用、复制。
- 自己的消息支持撤回。
- Agent 消息支持代码块。
- 代码块显示文件名和语言。
- 代码消息提供预览按钮。
- 输入框包含文件发送、表情和发送能力。

### 右侧

- 可预览代码。
- 可预览网页。
- 可预览 PPT 或 PPT 占位内容。
- 无预览时显示空状态。

---

## 15. 推荐开发顺序

1. 定义核心类型：Conversation、Message、Agent、Preview、Artifact。
2. 搭建 `AgentHubWorkspace.vue` 三栏页面。
3. 实现左侧一级导航与列表切换。
4. 实现聊天记录、Agent 列表、人员列表。
5. 实现聊天头、消息列表、消息组。
6. 实现底部输入框、文件按钮、表情按钮。
7. 实现代码卡片和右侧代码预览。
8. 接入 Axios API。
9. 接入 WebSocket 实时消息。
10. 扩展群聊 Orchestrator、网页预览、PPT、Diff、部署。

---

## 16. 总结

AgentHub 前端的核心是一个 IM 化的多 Agent 协作工作台。左侧解决“找会话、找对象”，中间解决“持续对话和上下文协作”，右侧解决“预览与操作 Agent 产物”。本规格围绕 Vue 3 + Pinia + Axios + Element Plus + TypeScript + Tailwind CSS，给出了布局、组件、状态、接口、实时消息、阶段计划与验收标准，可直接作为后续实现依据。
