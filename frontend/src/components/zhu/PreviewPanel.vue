<template>
  <aside class="blank-panel" :aria-hidden="previewState.type === 'empty'">
    <div v-if="previewState.type === 'empty'" class="preview-empty">
      <!-- 装饰性图标 -->
      <div class="empty-icon">
        <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="8" y="8" width="48" height="48" rx="12" stroke="currentColor" stroke-width="2" stroke-dasharray="4 4"/>
          <circle cx="32" cy="32" r="8" stroke="currentColor" stroke-width="2"/>
          <path d="M32 24v16M24 32h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
      </div>
      <span class="preview-empty-title">预览区</span>
      <span class="preview-empty-desc">选择代码、网页、文件或 Diff 后在这里查看</span>
    </div>
    <div v-else class="preview-content">
      <div class="preview-header">
        <div>
          <p class="preview-type">{{ previewState.type }}</p>
          <h3>{{ previewState.title || '预览' }}</h3>
        </div>
        <button class="preview-close" type="button" @click="$emit('close')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"/>
          </svg>
          关闭
        </button>
      </div>
      <pre v-if="previewState.type === 'code'" class="preview-code"><code>{{ previewState.code }}</code></pre>
      <iframe v-else-if="previewState.type === 'web' && previewState.url" class="preview-frame" :src="previewState.url" />
      <div v-else-if="previewState.type === 'diff'" class="preview-diff">
        <div class="diff-preview-header">
          <span class="diff-operation" :class="previewState.operation">{{ diffOperationLabel }}</span>
          <span class="diff-path" :title="previewState.path">{{ previewState.path }}</span>
        </div>
        <pre class="diff-content"><code v-html="formattedDiff"></code></pre>
      </div>
      <div v-else class="preview-placeholder">
        <p>{{ previewState.description || '该类型预览待接入。' }}</p>
        <a v-if="previewState.url" :href="previewState.url" target="_blank" rel="noreferrer">在新窗口打开</a>
      </div>
    </div>
  </aside>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import type { PreviewState } from '../../types/agenthub'

const props = defineProps<{
  previewState: PreviewState
}>()

defineEmits<{
  (e: 'close'): void
}>()

// M6: 计算 diff 操作标签
const diffOperationLabel = computed(() => {
  if (props.previewState.type !== 'diff') return ''
  const labels: Record<string, string> = {
    create: '创建',
    update: '更新',
    delete: '删除',
  }
  return labels[props.previewState.operation] || props.previewState.operation
})

// M6: 格式化 diff 为增绿删红样式
const formattedDiff = computed(() => {
  if (props.previewState.type !== 'diff') return ''
  const diff = props.previewState.unified_diff || ''
  // 对 unified diff 格式进行高亮处理
  return formatDiffWithColors(diff)
})

// 格式化 diff，添加增删颜色
function formatDiffWithColors(diff: string): string {
  if (!diff) return ''

  // HTML 转义
  const escaped = diff
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 清洗 unified diff：只保留变更内容（+ 或 - 开头的行）
  const lines = escaped.split('\n')
  const changeLines: string[] = []

  for (const line of lines) {
    // 跳过标准 unified diff metadata 行
    if (line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('@@') || line.startsWith('diff ')) {
      continue
    }
    // 跳过 context 行（空格开头）和空行
    if (line.startsWith(' ') || line === '') {
      continue
    }
    // 跳过 "No newline at end of file" 这类注释行
    if (line.includes('No newline at end of file')) {
      continue
    }
    // 跳过伪装成变更行的 metadata（形如 - --- 或 + +++ 或 - @@）
    // 这类是后端拼接异常产生的，不是真正的变更内容
    if (/^[+-]\s*(---|\+\+\+|@@|diff\s)/.test(line)) {
      continue
    }
    // 保留变更行（+ 或 - 开头）
    if (line.startsWith('+') || line.startsWith('-')) {
      changeLines.push(line)
    }
  }

  if (changeLines.length === 0) {
    // 如果没有找到变更行，显示原始内容（去掉 metadata）
    return lines
      .filter(line => !line.startsWith('---') && !line.startsWith('+++') && !line.startsWith('@@') && !line.startsWith('diff '))
      .map(line => `<span class="diff-context">${line}</span>`)
      .join('\n')
  }

  // 应用颜色样式
  return changeLines
    .map(line => {
      if (line.startsWith('+')) {
        return `<span class="diff-add">${line}</span>`
      } else if (line.startsWith('-')) {
        return `<span class="diff-del">${line}</span>`
      }
      return line
    })
    .join('\n')
}
</script>

<style scoped>
/* ==================== 预览面板容器 ==================== */
.blank-panel {
  height: 100%;
  overflow: hidden;
  background: transparent;
}

/* ==================== 空状态 ==================== */
.preview-empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 16px;
  color: #94a3b8;
  text-align: center;
  padding: 32px;
}

/* 空状态图标 */
.empty-icon {
  width: 64px;
  height: 64px;
  color: rgba(59, 130, 246, 0.3);
  animation: floatIcon 4s ease-in-out infinite;
}

.empty-icon svg {
  width: 100%;
  height: 100%;
}

@keyframes floatIcon {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-8px) rotate(3deg);
  }
}

.preview-empty-title {
  color: #475569;
  font-size: 15px;
  font-weight: 600;
}

.preview-empty-desc {
  font-size: 13px;
  line-height: 1.6;
  max-width: 200px;
  color: #94a3b8;
}

/* ==================== 预览内容区 ==================== */
.preview-content {
  height: 100%;
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 16px;
  padding: 20px;
  box-sizing: border-box;
}

.preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.preview-type {
  margin: 0 0 6px;
  color: #94a3b8;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
}

.preview-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}

/* ==================== 关闭按钮 ==================== */
.preview-close {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  border: 1px solid rgba(59, 130, 246, 0.15);
  background: rgba(59, 130, 246, 0.05);
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
}

.preview-close svg {
  width: 14px;
  height: 14px;
}

.preview-close:hover {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
  color: #3b82f6;
  transform: translateY(-1px);
}

/* ==================== 代码预览区 ==================== */
.preview-code,
.preview-frame,
.preview-placeholder {
  flex: 1;
  min-height: 0;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
}

.preview-code {
  overflow: auto;
  margin: 0;
  padding: 16px;
  font-family: 'Fira Code', Consolas, Monaco, monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
}

.preview-frame {
  width: 100%;
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 32px;
  color: #64748b;
  font-size: 14px;
}

.preview-placeholder a {
  color: #3b82f6;
  font-weight: 500;
  transition: all 0.2s ease;
}

.preview-placeholder a:hover {
  color: #2563eb;
  transform: translateY(-1px);
}

/* ==================== Diff 预览样式（增绿删红） ==================== */
.preview-diff {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
  overflow: hidden;
}

.diff-preview-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  background: rgba(59, 130, 246, 0.03);
}

.diff-operation {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.diff-operation.create {
  background: rgba(34, 197, 94, 0.15);
  color: rgb(34, 197, 94);
}

.diff-operation.update {
  background: rgba(59, 130, 246, 0.15);
  color: rgb(59, 130, 246);
}

.diff-operation.delete {
  background: rgba(239, 68, 68, 0.15);
  color: rgb(239, 68, 68);
}

.diff-path {
  flex: 1;
  overflow: hidden;
  color: #475569;
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diff-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  margin: 0;
  padding: 14px;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-all;
}

.diff-content code {
  font-family: inherit;
}

/* 增绿删红样式 */
.diff-content :deep(.diff-add) {
  color: rgb(34, 197, 94);
  background: rgba(34, 197, 94, 0.08);
  display: block;
}

.diff-content :deep(.diff-del) {
  color: rgb(239, 68, 68);
  background: rgba(239, 68, 68, 0.08);
  display: block;
}

.diff-content :deep(.diff-hunk) {
  color: rgb(59, 130, 246);
  font-weight: 600;
  display: block;
}

.diff-content :deep(.diff-meta) {
  color: #6b7280;
  font-style: italic;
  display: block;
}

.diff-content :deep(.diff-context) {
  color: #9ca3af;
  display: block;
}

@media (max-width: 1200px) {
  .blank-panel {
    display: none;
  }
}
</style>
