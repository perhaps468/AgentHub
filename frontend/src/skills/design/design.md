# AgentHub 前端架构规范

> 版本 1.0.0 | 更新日期 2026-05-22  
> *融合 Apple HIG 设计理念 —— 清晰、尊重、深度、简约*

---

## 关于本文档

本文档是 **AgentHub** 项目的前端架构规范（`spec.md`），涵盖技术栈、设计语言、开发流程以及配套的 AI 辅助开发 Skill。  
遵循 Apple 风格的设计哲学：**内容为先**、**留白呼吸**、**极简配色**。所有规范以「高级简约纯色」为核心，确保界面干净、专注、现代。

---

## 1. 项目概述

| 项目信息 | 内容 |
|---------|------|
| 项目名称 | AgentHub —— 多 Agent 协作平台 |
| 技术栈 | Vue 3 + Pinia + Axios + Element Plus + TypeScript + Tailwind CSS |
| 设计风格 | 高级简约纯色，白色为主，无渐变/无阴影 |
| 核心交互 | IM 聊天范式（对话即协作） |
| 设计灵感 | Apple 原生应用（信息、备忘录）的干净布局与克制美学 |

**设计目标**  
- 用户打开界面后 0.5 秒内理解信息层级  
- 聊天区域占比 ≥ 70%，干扰元素 ≤ 3 种颜色  
- 所有交互反馈默认使用位移动画（透明度/位移），禁用阴影与渐变  

---

## 2. 设计哲学（Apple 风格解读）

| Apple HIG 原则 | AgentHub 落地方式 |
|---------------|------------------|
| **清晰** | 纯白背景 + 灰阶文字，无彩色渐变，焦点完全在内容上 |
| **尊重** | 消息气泡仅使用浅灰背景，不抢占视觉；控件大小符合手指点按区域（44pt） |
| **深度** | 通过层级间距（16/24px）而非阴影表达层次；使用细边框（0.5px~1px）分隔区域 |

---

## 3. 设计规范（严格执行）

### 3.1 颜色系统

仅使用以下 5 种颜色（含中性色）：

| 用途 | 颜色值 | Tailwind 类名 | 说明 |
|------|--------|--------------|------|
| 主背景 | `#FFFFFF` | `bg-white` | 全局默认背景 |
| 次级背景 | `#F8F8F8` | `bg-gray-50` | 侧边栏 / 卡片悬停 |
| 主文字 | `#262626` | `text-gray-800` | 标题、正文重点 |
| 次要文字 | `#737373` | `text-gray-500` | 辅助信息、时间戳 |
| 边框/分割线 | `#F0F0F0` | `border-gray-100` | 卡片、列表分割 |
| 强调色 | `#1A1A1A` | `bg-primary` | 按钮、选中态、链接 |

> ❌ **禁止使用**  
> 任何彩色背景（蓝/红/绿）、渐变、阴影、超过 #e0e0e0 的深灰背景。

### 3.2 间距规范

采用 8px 网格系统，但**最小视觉间距为 16px**（特殊情况如头像群组可用 8px）。

| 场景 | 间距值 |
|------|--------|
| 页面内边距 | `24px` |
| 组件之间 | `24px` |
| 列表项之间 | `16px` |
| 消息气泡内边距 | `12px 16px` |
| 图标与文字 | `8px` |

### 3.3 圆角规范

所有圆角扁平、克制，禁止使用 >20px 的超大圆角。

| 元素 | 圆角值 |
|------|--------|
| 消息气泡（用户/Agent） | `16px` |
| 卡片（预览、部署） | `12px` |
| 按钮、输入框 | `8px` |
| 侧边栏 | `0` (直角，符合 Apple 风格) |

### 3.4 字体规范

| 属性 | 设置 |
|------|------|
| 英文字体族 | `Inter, -apple-system, BlinkMacSystemFont` |
| 中文字体族 | `PingFang SC, Hiragino Sans GB` |
| 正文字号/行高 | `14px / 1.5` |
| 标题字号 | `16px / 1.4` (二级)、`18px / 1.4` (一级)、`20px` (页面大标题) |
| 字重 | 仅使用 `400` (常规)、`500` (中等)、`600` (半粗) |
| ❌ 禁止 | 字重 300 及以下、斜体、全大写字母（除非专有名词） |

### 3.5 图标与图片

- 所有图标使用 **纯线条图标**（stroke-width: 1.5），无填充色
- 图标颜色跟随文字色（`currentColor`）
- 头像圆角：`50%`（圆形），无边框无阴影

---

## 4. 技术栈约束

| 类别 | 技术选型 | 约束 |
|------|---------|------|
| UI 框架 | Vue 3 (Composition API) | 必须使用 `<script setup>` 语法 |
| 状态管理 | Pinia | 使用 `setup store` 风格 |
| 组件库 | Element Plus | **仅限** 复杂组件：Table、Dialog、Select (下拉) |
| 样式方案 | Tailwind CSS | 优先使用 utility classes；自定义样式仅用于复杂动画 |
| 语言 | TypeScript | `strict: true`，禁止 `any`，必须定义 Props/Emits 类型 |
| HTTP 请求 | Axios | 封装拦截器，统一错误处理 |

> ✅ **自行实现的组件**：按钮、输入框、消息气泡、卡片、侧边栏 —— 必须符合上述设计规范。

---

## 5. 组件开发模板（Apple 风格）

```vue
<script setup lang="ts">
// 1. 导入依赖（按类型分组）
import { ref, computed } from 'vue'
import type { Message } from '@/types'

// 2. Props 与 Emits
interface Props {
  message: Message
  isOwn?: boolean
}
const props = withDefaults(defineProps<Props>(), {
  isOwn: false
})

const emit = defineEmits<{
  (e: 'reply', content: string): void
  (e: 'copy', text: string): void
}>()

// 3. 响应式状态
const showActions = ref(false)

// 4. 计算属性
const bubbleClass = computed(() => [
  'rounded-2xl px-4 py-3 max-w-[70%]',
  props.isOwn ? 'bg-gray-100 text-gray-800' : 'bg-white border border-gray-100'
])

// 5. 方法
function handleCopy() {
  emit('copy', props.message.content)
}

// 6. 生命周期（如需要）
</script>

<template>
  <div class="flex" :class="isOwn ? 'justify-end' : 'justify-start'">
    <div :class="bubbleClass">
      <p class="text-sm leading-relaxed">{{ message.content }}</p>
      <button
        v-if="showActions"
        @click="handleCopy"
        class="mt-2 text-xs text-gray-500 hover:text-gray-800 transition-colors"
      >
        复制
      </button>
    </div>
  </div>
</template>
```

---

## 6. AgentHub 开发助手 Skill

为 AI 编码辅助提供的精确指令集，确保生成代码 100% 符合规范。

```yaml
name: agenthub-dev-assistant
description: AgentHub 项目开发助手，严格遵循高级简约纯色设计规范（Apple 风格子集）
version: 1.0.0
```

### 6.1 核心指令

```markdown
# AgentHub 开发规范 —— AI 执行检查点

## 角色定位
你是 AgentHub 的前端专家，所有输出必须通过以下检查。

## 技术栈约束
- Vue 3 Composition API + `<script setup>` 语法
- Pinia setup store
- Element Plus 仅用于 Table / Dialog / Select
- Tailwind CSS 优先，禁止内联 style
- TypeScript 严格模式，禁止 any

## 设计规范（强制执行）

### 颜色使用
- 背景：`bg-white` 或 `bg-gray-50`
- 边框：`border-gray-100` (#F0F0F0)
- 主文字：`text-gray-800` (#262626)
- 次要文字：`text-gray-500` (#737373)
- 强调色：`bg-primary` / `text-primary` (#1A1A1A)
- ❌ 禁止：渐变、阴影、彩色背景（如 bg-blue-500）

### 间距规范
- 最小间距：16px（例外：头像组 8px）
- 页面内边距：`p-6`
- 组件间距：`mb-6`
- 列表项间距：`mb-4`

### 圆角规范
- 消息气泡：`rounded-2xl` (16px)
- 卡片：`rounded-xl` (12px)
- 按钮/输入框：`rounded-lg` (8px)

### 字体规范
- 字号：正文 `text-sm` (14px)，标题 `text-base`/`text-lg`
- 行高：`leading-relaxed` (1.5)
- 字重：`font-normal`、`font-medium`、`font-semibold`

## 组件模板
按上述第 5 节提供的模板生成代码。

## 输出前自检清单
- [ ] 是否没有任何 `bg-gradient`、`shadow-*` 类？
- [ ] 是否所有间距 ≥ 4（即 1rem）？
- [ ] 颜色类是否仅限 gray/white/black？
- [ ] TypeScript 类型完整吗？
- [ ] 是否避免了 Element Plus 被用于简单组件（如 Button）？
```

---

## 7. 开发优先级与交付路线

| 优先级 | 模块 | 说明 | Apple 风格要点 |
|-------|------|------|----------------|
| **P0** | 基础布局 | 三栏布局（会话列表 → 聊天区 → 产物预览）+ 左侧边栏切换 | 1px 分割线，无阴影 |
| **P0** | 单聊功能 | 消息发送/展示/Agent 响应，气泡对齐 | 气泡圆角 16px，最大宽度 70% |
| **P0** | 产物预览 | 代码/网页预览卡片（代码高亮 + 内嵌 iframe 预览） | 卡片圆角 12px，内部无边框 |
| **P1** | 群聊功能 | 多 Agent + Orchestrator 消息路由 | 群成员头像横向排列（间距 8px） |
| **P1** | Agent 管理 | 列表展示、自建 Agent（名称/头像/描述） | 列表项高度 72px，分割线 gray-100 |
| **P2** | 部署发布 | 部署卡片 + 一键部署按钮 | 按钮高度 40px，圆角 8px，纯黑背景白色文字 |
| **P2** | 多端适配 | 响应式（≥1280px 最优）+ 桌面端 Electron 预备 | 断点使用 Tailwind 默认 `lg`、`xl` |

---

## 8. 代码检查清单（交付前必查）

用于开发者自检或 Code Review：

- [ ] **颜色**：页面中是否只有白、灰、黑？无任何彩色或渐变？
- [ ] **间距**：所有组件之间的距离是否 ≥ 16px（1rem）？
- [ ] **圆角**：消息气泡使用 16px，卡片 12px，按钮 8px？没有 20px+？
- [ ] **字体**：没有字重 300、没有斜体？
- [ ] **阴影**：全局搜索 `shadow-`、`drop-shadow`，结果应为 0。
- [ ] **TypeScript**：无 `any`，无隐式 `any`。
- [ ] **组件库使用**：Element Plus 只用于 Table/Dialog/Select。
- [ ] **可复用性**：同样的消息气泡是否抽取为独立组件？

---
## 9.必要
可以向我提问具体需求完成任务
-项目定位

AgentHub 是一个面向网页、Workflow、代码、文档、PPT 等产物生成的多 Agent 协作平台。用户通过类似飞书 / 微信的聊天方式，与 Claude Code、Codex、OpenCode、自建 Agent 或真实人员进行协作。

核心目标：

-- 通过新建会话与不同 Agent 进行单聊。
-- 在群聊中 `@` 多个 Agent，由 Orchestrator 拆解任务、分派子 Agent、聚合结果。
-- 每个会话保留完整上下文，支持多轮迭代。
-- Agent 回复可内联展示代码、文件、网页预览、PPT、Diff、部署状态等产物。
-- 右侧统一预览 PPT、代码、网页等结果。

---
---

## 附录 A：Apple 风格参考资源

- [Apple Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)
- SF Pro 字体替代：`Inter` (免费开源)
- 调色板工具：使用 `gray` 色阶（50, 100, 500, 800） + `#1A1A1A`

---
**规范版本管理**  
本文档是 AgentHub 项目的前端唯一权威规范。任何设计或技术偏离需提交 RFC 并经架构组批准。  
*—— 保持简约，传递清晰 ——*
