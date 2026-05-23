# AgentHub 消息输入框模块 Skill 文档

## 1. 文档目标

本文档用于指导 `AgentHub` 项目中“消息输入框模块”的产品设计与前端实现。

该模块不是一个单纯的文本输入框，而是聊天主链路中的核心交互模块，负责承接：

- 文本输入
- 表情插入
- 群聊 `@成员`
- 群聊 `@Agent`
- 文件传输
- 消息发送
- 与会话、消息流、预览区、上传能力的协同

本文档同时覆盖两类目标：

1. **产品 / 交互设计目标**：明确输入框应该如何工作、如何反馈、用户如何理解
2. **前端开发实现目标**：明确组件拆分、状态设计、事件流、接口契约与实现边界

---

## 2. 设计范围

本 Skill 默认面向 **完整消息输入模块**，而不是只针对单一 `input.vue` 文件。

覆盖范围包括：

- 输入框容器组件
- 文本输入内核
- 工具栏按钮
- 表情面板
- `@` 候选面板
- 文件选择与上传入口
- 发送消息主链路
- 与消息列表 / 当前会话 / Agent 列表的联动

建议对应目录职责如下：

```text
src/
├── components/
│   └── chat/
│       ├── MessageComposer.vue          # 输入框容器
│       ├── ComposerToolbar.vue          # 工具栏
│       ├── ComposerEditor.vue           # 输入内核
│       ├── EmojiPanel.vue               # 表情面板
│       ├── MentionPanel.vue             # @候选面板
│       ├── UploadTrigger.vue            # 文件选择按钮
│       └── SelectedFileList.vue         # 已选择文件列表（如需要）
├── composables/
│   ├── useComposer.ts                   # 输入框主逻辑
│   ├── useMention.ts                    # @能力逻辑
│   ├── useEmoji.ts                      # 表情插入逻辑
│   └── useFileUpload.ts                 # 文件上传逻辑
├── stores/
│   └── modules/
│       ├── chat.ts
│       ├── agent.ts
│       └── message.ts
└── types/
    └── message.ts
```

> 如果当前项目仍保留 `src/veiws/input-content/input.vue` 这类旧结构，可先按“输入模块整体能力”设计，再逐步映射到现有文件。

---

## 3. 与现有文件的关系

根据当前代码，`src/veiws/input-content/input.vue` 已经承担了部分输入模块职责：

- 承载 `msg_input` 输入内核
- 调起文件传输
- 调起音视频邀请
- 暴露 `insertEmoji()` 与 `getNodeList()` 能力
- 通过 `handlerSubmitMsg` 向上触发发送

但它当前仍存在以下问题：

1. **职责过重**：输入、文件、邀请、事件监听耦合在一起
2. **命名不统一**：与 `spec.md` 中的组件命名和模块语义不一致
3. **`@` 能力抽象不完整**：只看到 `is-at-popup` 与 `getNodeList`，没有形成完整交互契约
4. **发送链路不够清晰**：缺少统一的数据结构与消息提交规范
5. **扩展性不足**：后续增加表情面板、文件列表、发送状态时容易继续堆积逻辑

因此，推荐将其视为“旧版输入模块容器”，后续按本 Skill 重构为更清晰的消息输入架构。

---

## 4. 来自 `spec.md` 的约束

根据 `src/spec.md`，消息输入模块属于 MVP 必做范围，必须支持：

- 文本输入
- 文件按钮
- 表情按钮
- 支持 `@Agent`
- 支持群聊 `@`
- 支持文字跟随光标最后一行、可删除
- 发送消息主链路

因此本模块必须满足两个原则：

### 4.1 IM 优先原则

输入框不是表单，而是 IM 会话流的一部分。

意味着：

- 输入必须快速
- 操作必须低阻力
- 键盘行为必须自然
- `@`、表情、文件都不能打断发送流程

### 4.2 可扩展消息协议原则

输入框输出的不应只是一个纯文本字符串，而应该是一个 **结构化消息草稿**。

这样才能同时支持：

- 纯文本消息
- 带 `@mention` 的文本消息
- 带附件的消息
- 引用消息
- 未来扩展代码片段、网页卡片、语音等能力

---

## 5. 核心用户故事

### 5.1 单聊发送文本消息

1. 用户进入某个单聊会话
2. 在输入框输入文字
3. 按 `Enter` 发送
4. 消息立即出现在消息流中
5. 后端确认后更新发送状态

### 5.2 群聊中 `@成员`

1. 用户在群聊输入 `@`
2. 输入框下方弹出候选面板
3. 面板展示群成员与 Agent
4. 用户键盘上下选择、回车确认
5. 插入一个 mention 节点
6. 继续输入正文并发送

### 5.3 群聊中 `@Agent`

1. 用户输入 `@Codex` 或通过候选列表选择某 Agent
2. 输入框中插入 Agent mention 节点
3. 发送时消息结构里附带 mention 数据
4. 后端 / 编排层依据 mention 定向唤起对应 Agent

### 5.4 插入表情

1. 用户点击表情按钮
2. 弹出表情面板
3. 点击一个表情
4. 表情插入到当前光标位置
5. 焦点返回输入区，可继续输入

### 5.5 发送文件

1. 用户点击文件按钮
2. 选择一个或多个文件
3. 输入框上方或下方展示待发送文件列表
4. 用户可以删除某个待发送文件
5. 点击发送后，先上传文件，再发送文件消息 / 附件消息

---

## 6. 模块职责定义

### 6.1 `MessageComposer.vue`

作为输入模块总容器，负责：

- 组合工具栏、输入编辑器、表情面板、`@` 面板、文件列表
- 接收当前会话上下文
- 组织发送动作
- 处理禁用状态、发送中状态

不负责：

- 真正的富文本底层编辑实现
- 文件上传细节
- mention 搜索算法细节

### 6.2 `ComposerEditor.vue`

负责：

- 文本输入
- 光标维护
- 插入表情
- 插入 mention 节点
- 键盘发送
- 键盘选择 mention 候选项
- 导出结构化草稿内容

### 6.3 `EmojiPanel.vue`

负责：

- 展示表情列表
- 点击某表情后通知编辑器插入
- 支持关闭

### 6.4 `MentionPanel.vue`

负责：

- 根据当前关键字展示候选项
- 区分成员与 Agent
- 提供鼠标选择与键盘高亮
- 支持空状态

### 6.5 `useFileUpload.ts`

负责：

- 文件选择
- 文件合法性校验
- 上传过程管理
- 上传结果结构化输出

---

## 7. 交互设计规范

## 7.1 输入区基础布局

建议结构：

```text
┌──────────────────────────────────────────────┐
│ 引用条 / 文件列表（可选）                    │
├──────────────────────────────────────────────┤
│ [😊] [📎]  输入区域                    [发送] │
│              mention候选 / 表情面板浮层      │
└──────────────────────────────────────────────┘
```

推荐包含：

- 左侧工具按钮区
  - 表情按钮
  - 文件按钮
- 中间输入核心区
  - 文本输入
  - mention 节点
  - 占位提示
- 右侧发送按钮
- 输入区上方扩展区
  - 引用消息条
  - 文件待发送列表

---

## 7.2 表情按钮与表情面板

### 交互要求

- 点击表情按钮：打开 / 关闭表情面板
- 面板默认定位在输入框上方或按钮附近
- 点击面板外区域关闭
- 选择表情后插入当前光标位置
- 插入后不自动发送
- 插入后编辑器继续保持焦点

### MVP 建议

MVP 不需要做复杂分类，可以先实现：

- 常用表情分组
- 最近使用表情（可选）
- 点击插入

### 数据结构建议

```ts
interface EmojiItem {
  key: string
  char: string
  name: string
}
```

---

## 7.3 `@` 面板交互

### 触发规则

当满足以下条件时触发候选面板：

- 当前会话为群聊，输入 `@`
- 或当前会话允许 `@Agent`
- `@` 后连续输入关键词时，实时过滤候选项

### 候选数据来源

候选项应来自两个集合：

1. 当前群成员
2. 当前会话可用 Agent 列表

### 候选项展示字段

- 名称
- 类型（成员 / Agent）
- 头像或首字母
- Agent 平台 / 能力标签（可选）

### 键盘规则

- `ArrowDown`：下移选中项
- `ArrowUp`：上移选中项
- `Enter`：确认选中 mention
- `Escape`：关闭候选面板
- `Backspace`：当 mention 节点整体被选中时整块删除

### 插入结果

被选中的 mention 应作为结构化节点插入，而不是简单拼接纯文本。

推荐渲染效果：

- 视觉上是一个胶囊标签
- 文本显示如 `@Codex`
- 类型上保留 `agent` / `member`

### 建议数据结构

```ts
interface MentionEntity {
  id: string
  name: string
  mentionType: 'member' | 'agent' | 'all'
}
```

---

## 7.4 `@所有人` 规则

群聊中可支持 `@所有人` / `@everyone`：

- 输入 `@` 后候选列表第一项可固定为“所有人”
- 仅群聊中展示
- 发送时结构化输出为 mentionType = `all`

建议数据结构：

```ts
const everyoneMention = {
  id: 'all',
  name: '所有人',
  mentionType: 'all',
}
```

---

## 7.5 文件传输交互

### 入口

- 点击文件按钮打开文件选择器
- 支持拖拽到输入区（P1，可选）

### 选择后

- 展示待发送文件卡片
- 卡片包含：
  - 文件名
  - 大小
  - 文件类型图标
  - 删除按钮
  - 上传中状态（如走先上传）

### 发送策略

推荐采用两段式：

1. 选择文件后先进入待发送列表
2. 用户点击发送时统一上传并发送消息

这样更符合 IM 体验，也便于“文字 + 文件”一并发送。

### 校验建议

MVP 至少做：

- 文件大小限制
- 文件数量限制
- 文件类型黑名单 / 白名单

---

## 7.6 发送交互规范

### Enter / Shift + Enter

- `Enter`：发送消息
- `Shift + Enter`：换行

### 发送前校验

如果以下全部为空，则不发送：

- 文本内容为空
- mention 内容为空
- 附件为空

### 发送中表现

- 发送按钮进入 loading / disabled
- 输入区可选择继续编辑或临时禁用
- 推荐：发送后立即清空当前草稿，失败时恢复或提示失败

### 发送成功

- 清空草稿
- 清空待发送文件
- 关闭表情面板 / mention 面板
- 插入本地临时消息到消息流

### 发送失败

- Toast 提示失败
- 草稿保留
- 文件保留
- 允许重新发送

---

## 8. 消息草稿数据结构设计

结合 `src/skills/tasks.md` 当前后端契约，输入框对外不建议只输出 `string`，推荐输出一个“前端草稿对象 + 后端发送载荷”双层模型。

### 8.1 前端草稿结构

```ts
interface ComposerDraft {
  sessionId: string
  text: string
  nodes: ComposerNode[]
  mentions: MentionEntity[]
  files: ComposerFile[]
  replyTo?: {
    messageId: string
    summary: string
    senderName: string
  } | null
}

interface ComposerFile {
  uid: string
  file: File
  name: string
  size: number
  type: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  url?: string
}
```

说明：

- `sessionId`
  - 对齐 `tasks.md` 中的后端字段 `session_id`
  - 表示当前消息所属会话
- `text`
  - 发送给当前 MVP 后端的主文本内容
- `nodes`
  - 编辑器内部结构化节点，用于保留表情、mention、换行等信息
- `mentions`
  - 当前前端识别到的 `@成员` / `@Agent` 结构
- `files`
  - 待上传或已上传的文件列表
- `replyTo`
  - 前端引用消息元信息；当前后端契约尚未支持，可先在前端保留

### 8.2 编辑器节点结构

```ts
type ComposerNode =
  | { type: 'text'; text: string }
  | { type: 'emoji'; text: string }
  | { type: 'mention'; entity: MentionEntity }
  | { type: 'line-break' }
```

### 8.3 当前 MVP 后端发送载荷

根据 `src/skills/tasks.md` 第 8.9.2 节，当前 WebSocket `send_message` 只接受以下字段：

```ts
interface SendMessagePayload {
  action: 'send_message'
  session_id: string
  content: string
}
```

说明：

- `action`
  - 固定为 `send_message`
- `session_id`
  - 会话 ID
  - 必须与 WebSocket 路径中的 `session_id` 一致
- `content`
  - 当前阶段仅支持纯文本内容
  - 输入框需要把 `nodes`、`mentions`、`emoji` 最终归并为一个发送字符串

### 8.4 当前阶段的参数映射规则

由于 `tasks.md` 当前后端只支持 `text` 消息，因此输入框需要做“前端富能力、后端纯文本”的映射：

- `ComposerDraft.sessionId -> SendMessagePayload.session_id`
- `ComposerDraft.text -> SendMessagePayload.content`
- `ComposerDraft.mentions`
  - 当前阶段只在前端保留
  - 如需给后端消费，可先把 mention 文本渲染进 `content`
- `ComposerDraft.files`
  - 当前后端契约尚未支持附件消息
  - 前端可以先保留 UI、上传逻辑和待扩展数据结构，但不能假设后端已支持 `attachments`
- `ComposerDraft.replyTo`
  - 当前阶段仅前端本地态保留，不进入 WebSocket 发送载荷

因此，当前发送前建议统一执行：

```ts
function buildSendMessagePayload(draft: ComposerDraft): SendMessagePayload {
  return {
    action: 'send_message',
    session_id: draft.sessionId,
    content: draft.text,
  }
}
```

### 8.5 接收消息结构认知

根据 `tasks.md` 第 8.9.3 节，前端需要兼容如下服务端消息结构：

```ts
interface ChatStreamMessage {
  type: 'chat_stream'
  message_id: string
  session_id: string
  sender_type: 'agent'
  sender_role: string
  content: string
  content_type: 'text'
  created_at: string
}
```

同时，历史消息与本地消息模型建议至少兼容以下核心参数：

```ts
interface BaseChatMessage {
  id: string
  session_id: string
  sender_type: 'human' | 'agent' | 'system'
  sender_role: string | null
  content: string
  content_type: 'text'
  created_at: string
}
```

这意味着输入框在设计发送与本地回显时，涉及的数据类型参数应优先与以下命名保持一致：

- `session_id`
- `content`
- `sender_type`
- `sender_role`
- `content_type`
- `created_at`

而不是过早依赖尚未在当前 `tasks.md` 中落地的：

- `attachments`
- `replyToMessageId`
- `mentions` 后端入参
- 多种 `content_type`

---

## 10. 状态管理设计

推荐拆成三层状态。

### 10.1 本地 UI 状态

由输入组件自身管理：

- `draftText`
- `editorNodes`
- `emojiPanelVisible`
- `mentionPanelVisible`
- `mentionQuery`
- `mentionActiveIndex`
- `selectedFiles`
- `sending`

### 10.2 会话上下文状态

来自 `chat store` / `conversation store`：

- 当前会话 ID
- 当前会话类型（单聊 / 群聊）
- 当前会话成员列表
- 当前会话 Agents 列表
- 当前引用消息

### 10.3 业务发送状态

来自 `message store`：

- 本地临时消息队列
- 发送中消息
- 失败消息
- 文件上传状态

> 需要注意：当前 `tasks.md` 后端契约里并没有 `clientMessageId` 字段，因此前端如需临时消息对账，可在本地 store 中自行维护，不应写入当前 MVP 的 `SendMessagePayload`。

---

## 11. 推荐组件通信方式

### 容器向子组件传入

- 当前会话信息
- 候选 mention 列表
- 禁用状态
- 回复消息信息

### 子组件向容器抛出

- 输入变化
- 请求发送
- 插入表情
- 选择 mention
- 文件删除
- 文件选择完成

推荐事件：

```ts
'onSubmit'
'onChange'
'onSelectMention'
'onPickEmoji'
'onPickFiles'
'onRemoveFile'
'onCancelReply'
```

---

## 12. 推荐实现流程

## 12.1 发送文本消息流程

```text
用户输入文本
  -> 编辑器更新 nodes / text
  -> 生成 ComposerDraft
  -> 校验 draft 是否为空
  -> buildSendMessagePayload(draft)
  -> 前端本地插入临时消息（可选）
  -> 调用 WebSocket send_message
  -> 成功后等待 chat_stream 回推并更新消息流
  -> 失败后标记 error 并恢复草稿（按策略）
```

## 12.2 发送带文件消息流程

```text
用户选择文件
  -> selectedFiles 加入待发送列表
  -> 用户点击发送
  -> 前端上传文件（如果项目单独支持上传）
  -> 当前 MVP 后端若仍只支持 text，则把文件能力停留在前端占位或扩展链路
  -> 仅在后端补齐附件协议后，再将文件元数据拼入正式消息载荷
```

## 12.3 mention 插入流程

```text
用户输入 @
  -> 检测 mention trigger
  -> 打开 mention 面板
  -> 输入关键词过滤列表
  -> 回车 / 点击选择候选项
  -> 插入 mention 节点
  -> 光标移动到 mention 后
  -> 继续输入正文
```

---

## 13. 与现有 `input.vue` 的重构映射建议

当前 `src/veiws/input-content/input.vue` 中建议保留 / 调整如下：

### 可以保留的能力

- `insertEmoji()` 暴露方式
- `getNodeList()` 导出结构化节点能力
- 文件选择入口
- 上层 `handlerSubmitMsg` 回调语义

### 建议迁移出去的能力

- 音视频邀请逻辑
- EventBus 的收发监听
- 文件邀请弹窗的业务流程
- 与“当前目标用户”强耦合的逻辑

### 原因

消息输入框 Skill 的目标是 **聊天输入主链路**，不是通讯能力总入口。

音视频邀请可以保留在聊天页面级别，或作为独立工具按钮模块接入，而不要混在输入主逻辑里，否则会破坏输入模块边界。

---

## 14. MVP 开发优先级

### P0 必做

1. 纯文本输入
2. `Enter` 发送 / `Shift+Enter` 换行
3. 表情按钮 + 表情插入
4. 文件按钮 + 待发送文件列表
5. 群聊 `@成员`
6. 群聊 `@Agent`
7. 结构化草稿生成
8. 发送接口整合

### P1 增强

1. `@所有人`
2. 最近使用表情
3. 文件拖拽上传
4. 输入框自动高度增长
5. 上传进度展示
6. 输入中断恢复

### P2 暂缓

1. 完整富文本编辑器
2. Markdown 即时格式化
3. 复杂 Slash Commands
4. 语音输入

---

## 15. 开发落地建议

## 15.1 第一阶段：统一消息输入输出

先把 `MessageComposer` 的输入输出协议定下来，不急着美化 UI。

优先完成：

- `ComposerDraft` 数据结构
- 发送 payload 结构
- `Enter / Shift+Enter`
- mention 数据结构
- 文件待发送列表

## 15.2 第二阶段：补齐交互层

再实现：

- 表情面板
- mention 面板
- 文件删除
- 回复条
- 空状态与禁用态

## 15.3 第三阶段：重构旧组件

将现有：

- `src/veiws/input-content/input.vue`
- `src/veiws/input-content/msg_input.vue`

逐步收敛到：

- `src/components/chat/MessageComposer.vue`
- `src/components/chat/ComposerEditor.vue`
- `src/components/chat/EmojiPanel.vue`
- `src/components/chat/MentionPanel.vue`

---

## 16. 验收标准

当以下条件全部满足时，认为该 Skill 实现达标：

### 功能验收

- 能输入文本并发送
- `Enter` 发送，`Shift+Enter` 换行
- 可以点击按钮插入表情
- 群聊中输入 `@` 可以弹出候选列表
- 可区分 `@成员` 与 `@Agent`
- 可发送文件
- 可发送“文字 + 文件”组合消息
- 发送失败时保留草稿

### 交互验收

- 面板打开关闭自然
- mention 键盘选择顺畅
- 删除 mention 节点行为正确
- 文件卡片反馈清晰
- 输入区状态切换不突兀

### 架构验收

- 输入模块职责清晰
- 组件拆分合理
- 不把所有逻辑堆在单个 `.vue` 文件
- 发送数据结构可扩展
- 与 `spec.md` 的聊天 / Agent / 消息模型一致

---

## 17. 推荐给 AI / 开发协作助手的实现指令模板

后续如果要让 AI 继续按本 Skill 开发，可直接使用类似任务描述：

```md
请基于 `src/spec.md` 与 `src/skills/input/skill.md` 实现消息输入模块，要求：
1. 使用 Vue 3 + TypeScript
2. 以 `src/components/chat/MessageComposer.vue` 作为容器组件
3. 支持文本输入、表情按钮、表情面板、群聊 @成员、@Agent、文件上传、发送消息
4. 输出结构化 `ComposerDraft`
5. 与当前会话 store / message store 对接
6. 保持 Apple 风浅色主题一致
7. 不要把所有逻辑堆在一个文件里
```

---

## 18. 总结

消息输入框模块是 AgentHub 聊天主链路中最关键的用户输入入口。

它的本质不是一个普通输入框，而是一个 **结构化消息编辑器 + 多能力触发器 + 消息发送调度器**。

本 Skill 的目标不是把输入框做成复杂富文本系统，而是在 MVP 周期内，用最小复杂度实现：

- IM 风格输入体验
- 群聊 `@` 与 `@Agent`
- 表情插入
- 文件发送
- 可扩展的数据模型
- 与整体聊天架构一致的实现方案

如果后续继续迭代，建议始终坚持：

- 输入模块边界清晰
- 状态设计先于样式堆叠
- 结构化消息优先于纯字符串拼接
- `spec.md` 中的会话 / 消息 / Agent 模型保持统一

