# AgentHub 前端开发 Skill

## 1. Skill 目标

本 Skill 用于辅助 AI 或开发者在 `AgentHub` 前端项目中进行稳定、统一、可落地的实现。

配套文档：

- `src/spec.md`

本 Skill 重点保证：

- 架构不跑偏
- 命名统一
- 组件职责清晰
- 优先实现 20 天 MVP 范围
- 输出代码适合 `Vue3 + Pinia + Axios + Element Plus + TypeScript + Tailwind CSS`

---

## 2. 项目定位

这是一个 **多 Agent 协作平台前端**，以 IM 聊天为核心交互。

AI 在实现功能时，必须始终围绕以下三大区域思考：

1. 左侧：会话 / 联系人导航区
2. 中间：聊天消息流与输入区
3. 右侧：代码 / 网页 / PPT 预览区

任何新增功能，都应该明确属于哪一个区域，或属于共享状态层。

---

## 3. 技术栈约束

严格遵循以下技术选型：

- `Vue 3`
- `TypeScript`
- `Pinia`
- `Axios`
- `Element Plus`
- `Tailwind CSS`

实现要求：

- 统一使用 Composition API
- 优先使用 `<script setup lang="ts">`
- 组件 props / emits 必须写清楚类型
- 共享业务状态必须进入 Pinia
- 请求统一走 `api/` 封装
- 不允许在页面组件中直接写大量 mock 结构体

---

## 4. 业务范围优先级

### P0：必须先做

- 三栏布局
- 会话列表 / 人员列表切换
- 聊天消息流
- 引用 / 复制 / 撤回
- 代码消息卡片
- 文件按钮 / 表情按钮 / 文本发送
- 右侧预览区
- `@Agent` 候选逻辑

### P1：有余力再做

- 会话置顶
- 会话归档
- Diff 卡片
- 重新生成
- 部署状态卡片

### P2：本期不主动扩展

- 真正复杂编排引擎
- 完整版本历史
- 多端深度适配
- 大型富文本编辑器

---

## 5. 推荐目录认知

AI 在输出代码时，应默认遵守以下目录职责：

```text
src/
├── api/
├── components/
│   ├── app/
│   ├── sidebar/
│   ├── chat/
│   ├── preview/
│   └── common/
├── composables/
├── stores/
├── types/
├── views/
├── mock/
└── utils/
```

规则：

- 页面组装写在 `views/`
- 三大主区域写在 `components/app/`
- 左侧域写在 `components/sidebar/`
- 聊天域写在 `components/chat/`
- 预览域写在 `components/preview/`
- 类型统一在 `types/`

---

## 6. 数据模型原则

AI 在定义类型时，必须复用统一业务模型，不要在不同组件里重复定义近似接口。

重点模型：

- `AgentProfile`
- `PersonProfile`
- `ConversationItem`
- `ChatMessage`
- `PreviewState`

约束：

1. 所有消息都要归属某个 `conversationId`
2. 所有可预览产物都要能映射成 `PreviewState`
3. 群聊下要区分 `agent`、`person`、`orchestrator`
4. 代码消息不要只存字符串，至少包含 `fileName`、`language`、`code`

---

## 7. Store 设计规则

建议拆分为：

- `useAppStore`
- `useConversationStore`
- `useAgentStore`
- `useMessageStore`
- `usePreviewStore`

实现原则：

- Store 只放共享状态
- 一次性页面局部开关，不要滥放 store
- Store action 可以调 API，但不要掺杂大量 DOM 行为
- Getter / computed 只做轻计算

示例约束：

- 当前激活会话：放 `conversationStore`
- 当前引用消息：放 `messageStore`
- 当前右侧预览对象：放 `previewStore`
- 当前左侧模式：放 `appStore`

---

## 8. 组件设计规则

### 8.1 单一职责

一个组件只处理一层业务。

正确示例：

- `MessageItem.vue`：只负责单条消息渲染
- `MessageInput.vue`：只负责输入与发送交互
- `PreviewCode.vue`：只负责代码预览

避免：

- 一个组件里同时维护会话列表、消息列表、预览区逻辑

### 8.2 Props / Emits 清晰

所有业务组件必须明确：

- 接收什么数据
- 抛出什么事件

例如：

- `MessageItem` 发出 `copy`、`quote`、`recall`
- `CodeMessageCard` 发出 `preview`

### 8.3 不过度抽象

如果某个按钮只在当前业务里用一次，不要急着抽成复杂通用组件。

优先：

- 清晰
- 易改
- 可读

---

## 9. 聊天域实现规范

### 9.1 消息展示

每条消息至少要考虑：

- 头像
- 名称
- 时间
- 文本内容
- 引用块
- 操作按钮
- 可能附带的代码 / 文件 / 预览卡片

### 9.2 自己的消息

- 靠右
- 支持撤回
- 视觉上与他人消息区分明显

### 9.3 Agent 消息

- 靠左
- 显示 Agent 名称与能力标签（群聊下优先）
- 支持代码消息卡片
- 可打开右侧预览

### 9.4 Orchestrator 消息

- 作为特殊发送者类型处理
- 适合显示为汇总说明、任务分派、整合结论
- 样式上应与普通 Agent 略有区分，但不要喧宾夺主

---

## 10. 输入区实现规范

输入区必须支持：

- 文本输入
- 回车发送
- `Shift + Enter` 换行
- 文件按钮
- 表情按钮
- 引用条展示
- `@Agent` 候选列表

规则：

1. 引用消息显示在输入框上方
2. 发送成功后清空引用状态
3. `@` 候选只针对 Agent 列表，不要混入普通人员
4. 如果是单聊 Agent，可弱化 `@` 逻辑

---

## 11. 预览区实现规范

右侧预览区是 AgentHub 的关键差异点，不能只做空白占位。

至少支持：

- 代码预览
- 网页预览
- PPT 预览
- 文件信息预览
- 空状态

统一规则：

- 所有预览都通过 `previewStore.currentPreview` 驱动
- 点击消息卡片中的“预览”按钮时，更新 `currentPreview`
- 关闭预览时，重置为空状态

---

## 12. API 层规范

API 必须统一封装在 `api/modules/` 中。

要求：

- 不在组件中直接写 `axios.get()`
- 方法名用动词 + 业务对象
- 返回值类型尽量标注清楚

推荐方法名示例：

- `fetchAgents`
- `fetchConversationList`
- `createConversation`
- `fetchConversationMessages`
- `sendConversationMessage`
- `recallMessage`
- `fetchPreviewDetail`

---

## 13. 样式实现规范

### 13.1 优先级

1. `Tailwind CSS` 优先完成布局与常规视觉
2. 必要时补充 scoped CSS
3. `Element Plus` 仅用于成熟复杂控件

### 13.2 风格关键词

- 简洁
- 轻量科技感
- 工具型工作台
- 信息分层清楚

### 13.3 避免问题

避免：

- 大面积花哨渐变
- 过度阴影
- 颜色过多
- 消息卡片视觉层级混乱

建议：

- 以浅色背景 + 白色面板为主
- 用边框、圆角、留白建立秩序
- Agent 标签用低饱和弱强调

---

## 14. 假数据开发规范

如果后端接口未准备完成，可以先使用 mock。

规则：

- mock 数据放在 `src/mock/`
- 组件不能直接 import mock 文件
- mock 只能由 store 或 api 适配层消费
- 真实接口准备好后，尽量无感替换

---

## 15. AI 输出代码时的检查清单

每次输出代码前，AI 都应该自检：

1. 是否符合 `Vue 3 + TS + script setup`？
2. 是否复用了统一类型，而不是重复造接口？
3. 是否把共享状态放进 Pinia？
4. 是否保持三大区域边界清晰？
5. 是否只实现当前 P0 / P1 范围，避免过度设计？
6. 是否考虑了复制、引用、撤回、预览这些核心交互？
7. 是否让代码能被后续 AI 和开发者轻松接手？

---

## 16. 推荐实现顺序

AI 若参与从零到一搭建，建议按以下顺序生成代码：

1. 建立 `types`
2. 建立 `stores`
3. 建立 `MainLayout`
4. 实现左侧列表
5. 实现中间消息流
6. 实现输入区
7. 实现右侧预览区
8. 接入 mock 数据
9. 再对接真实接口

---

## 17. 结论

本 Skill 的核心使命不是生成“花哨代码”，而是帮助 AgentHub 前端：

- 在 20 天内完成一个清晰、稳定、可演示的多 Agent 聊天协作产品
- 保持项目结构长期可维护
- 让后续 AI 继续开发时能快速理解上下文

如果出现需求不明确的情况，优先回到 `src/spec.md`，按其中的 MVP 边界和默认决策推进。

