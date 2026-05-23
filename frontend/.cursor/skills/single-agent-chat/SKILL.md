---
name: single-agent-chat
description: 指导 AgentHub 前端实现 1v1 单 Agent 对话、code 消息类型、页面代码块渲染，以及左侧会话列表的新建、置顶、归档、搜索、最近活跃排序。用于用户要求实现单 Agent 明确任务对话、代码消息展示或增强会话列表时。
disable-model-invocation: true
---

# Single Agent Chat Skill

## 使用场景

当用户要求在 AgentHub 前端实现或维护以下能力时使用本 Skill：

- 1v1 与单个 Agent 对话。
- 面向明确任务，例如“用 Claude Code 写一个 React 组件”。
- 新增 `code` 消息类型并在聊天页面渲染代码块。
- 左侧会话列表支持新建、置顶、归档、搜索、最近活跃排序。

## 项目上下文

当前项目是 Vue 3 + TypeScript + Pinia + Element Plus 前端。关键文件：

- `src/components/zhu.vue`：主聊天布局、左侧会话列表、当前聊天目标选择。
- `src/veiws/Chat-show-area.vue`：聊天消息展示和 mock 消息记录。
- `src/veiws/Chat-input-area.vue`：输入框与发送消息逻辑。
- `src/veiws/message-content/msg_content .vue`：消息内容分发。
- `src/veiws/message-content/text-msg.vue`：文本消息渲染。
- `src/types/messageType.ts`：消息类型常量。
- `src/types/message.ts`：消息相关 TypeScript 类型。

## 实现目标

1. 保留现有群聊、私聊、表情、通话、引用、撤回、输入框功能。
2. 新增单 Agent 会话入口，适合明确任务型对话。
3. 新增 `MessageType.Code = 'code'`。
4. 新增独立代码消息组件，不把代码块逻辑混入文本消息组件。
5. 左侧会话列表支持：
   - 新建单 Agent 会话。
   - 置顶会话。
   - 归档会话。
   - 搜索会话。
   - 按最近活跃时间排序。
6. 后端契约未确认时，使用前端 mock 或兼容 JSON 字符串，不阻塞 UI 验证。

## 不允许破坏的现有功能

- 不删除现有聊天组件。
- 不移除群聊入口。
- 不改变 `targetId === '1'` 表示群聊的现有判断。
- 不把所有私聊改造成 Agent 会话。
- 不修改现有接口语义，除非后端契约已确认。
- 不删除文件；确实需要删除时必须先向用户确认。

## 推荐改动路径

优先小步扩展，而不是重写：

1. 在 `src/types/messageType.ts` 新增 `Code: 'code'`。
2. 在 `src/types/message.ts` 中扩展消息内容类型，允许 `code`。
3. 新增 `src/veiws/message-content/code-msg.vue`。
4. 在 `src/veiws/message-content/msg_content .vue` 中新增 `MessageType.Code` 分支。
5. 在 `src/components/zhu.vue` 中增加单 Agent 会话的前端状态、过滤、排序和操作按钮。
6. 在 `src/veiws/Chat-show-area.vue` mock 一条 `code` 消息用于验证渲染。

## code 消息规范

后端未确认前，`message` 字段继续使用字符串，内容为 JSON 字符串：

```ts
interface CodeMessagePayload {
  language: string
  filename?: string
  content: string
}
```

约定：

- `type` 使用 `MessageType.Code`。
- `message` 使用 `JSON.stringify(CodeMessagePayload)`。
- 解析失败时按纯文本代码展示，避免页面崩溃。

## 代码块渲染规范

代码消息组件应满足：

- 顶部显示文件名和语言。
- 主体使用等宽字体。
- 支持横向滚动和保留换行。
- 支持复制按钮。
- 复制失败不阻塞主流程。
- UI 延续白色、浅灰、深灰的简洁纯色风格。

## 左侧会话列表规范

推荐前端模型：

```ts
interface AgentConversation {
  id: string
  title: string
  agentId: string
  agentName: string
  lastMessage: string
  lastActiveAt: string
  isPinned: boolean
  isArchived: boolean
  conversationType: 'single-agent'
}
```

排序规则：

1. 未归档会话默认展示。
2. 置顶会话排在非置顶之前。
3. 置顶内部按 `lastActiveAt` 倒序。
4. 非置顶内部按 `lastActiveAt` 倒序。
5. 归档会话默认隐藏，可通过“显示归档”查看。

搜索规则：

- 匹配会话标题。
- 匹配 Agent 名称。
- 匹配最近一条消息。

## 中文注释规范

- 文档和用户说明使用中文。
- 代码注释仅解释非显而易见的业务约束。
- 不写“定义变量”“调用函数”“返回结果”这类无意义注释。

## 验收清单

- 单 Agent 会话可以新建。
- 左侧单 Agent 会话支持置顶、归档、搜索、最近活跃排序。
- `code` 消息能在聊天区域显示为代码块。
- 代码块可以复制。
- 群聊、私聊、文本、表情、通话消息不受影响。
- 未删除任何文件。
