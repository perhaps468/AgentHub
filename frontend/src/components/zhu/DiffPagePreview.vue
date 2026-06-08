<template>
  <div class="diff-page-preview">
    <div class="header">
      <span class="operation" :class="operation">{{ operationLabel }}</span>
      <span class="path" :title="path">{{ fileName }}</span>
      <div class="header-actions">
        <button
          class="action-btn"
          :class="{ active: viewMode === 'diff' }"
          type="button"
          @click="viewMode = 'diff'"
          title="查看变更"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 3v18M3 12h18"/>
          </svg>
          变更
        </button>
        <button
          class="action-btn"
          :class="{ active: viewMode === 'preview' }"
          type="button"
          @click="viewMode = 'preview'"
          title="预览页面"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
          预览
        </button>
      </div>
    </div>

    <!-- 变更视图 -->
    <pre v-show="viewMode === 'diff'" class="code-content"><code v-html="formattedDiff"></code></pre>

    <!-- 预览视图 -->
    <div v-show="viewMode === 'preview'" class="preview-content">
      <iframe
        v-if="previewHtml"
        class="preview-frame"
        :srcdoc="previewHtml"
        sandbox="allow-scripts"
      ></iframe>
      <div v-else class="preview-empty">
        <p>无法预览此文件类型</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

interface DiffPagePreviewProps {
  path: string
  operation: 'create' | 'update' | 'delete'
  unifiedDiff: string
}

const props = defineProps<DiffPagePreviewProps>()

const viewMode = ref<'diff' | 'preview'>('diff')

const operationLabel = computed(() => {
  const labels: Record<string, string> = {
    create: '创建',
    update: '更新',
    delete: '删除',
  }
  return labels[props.operation] || props.operation
})

const fileName = computed(() => {
  const parts = props.path.split(/[/\\]/)
  return parts[parts.length - 1] || props.path
})

// 生成预览 HTML
const previewHtml = computed(() => {
  const ext = props.path.split('.').pop()?.toLowerCase() || ''
  let content = ''

  if (props.operation === 'create') {
    content = extractNewContent(props.unifiedDiff)
  } else if (props.operation === 'update') {
    content = applyDiff(props.unifiedDiff, ext)
  } else {
    content = '<div style="padding: 20px; color: #ef4444;">【文件已删除】</div>'
  }

  return generatePreviewHtml(ext, content, props.path)
})

function generatePreviewHtml(ext: string, content: string, path: string): string {
  if (ext === 'html') {
    return wrapInFrame(content)
  }

  if (ext === 'vue') {
    const { html, css } = parseVueSFC(content)
    return generateVuePreview(html, css)
  }

  if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)) {
    return wrapInFrame(`<div style="padding: 20px;"><img src="${escapeHtmlAttr(content)}" alt="${escapeHtmlAttr(path)}" style="max-width: 100%;" /></div>`)
  }

  if (ext === 'md') {
    const htmlContent = simpleMarkdownToHtml(content)
    return wrapInFrame(htmlContent)
  }

  // 默认显示代码
  return wrapInFrame(`<pre style="padding: 20px; font-family: monospace; white-space: pre-wrap; word-break: break-all;">${escapeHtml(content)}</pre>`)
}

function wrapInFrame(content: string): string {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
    iframe { border: none; width: 100%; height: 100vh; }
  </style>
</head>
<body>${content}</body>
</html>`
}

function extractNewContent(diff: string): string {
  return diff.split('\n')
    .filter(line => {
      if (line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('@@') || line.startsWith('diff ')) return false
      if (line.includes('No newline at end of file') || /^-+$/.test(line)) return false
      return line.startsWith('+')
    })
    .map(line => line.slice(1))
    .join('\n')
}

function applyDiff(diff: string, ext: string): string {
  if (['html', 'vue', 'xml', 'svg'].includes(ext)) {
    return applyMarkupDiff(diff)
  }
  return applySimpleDiff(diff)
}

function applyMarkupDiff(diff: string): string {
  const lines = diff.split('\n')
  const result: string[] = []

  for (const line of lines) {
    if (line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('diff ')) continue
    if (line.startsWith('@@')) {
      result.push(`... (${line}) ...`)
      continue
    }
    if (line.includes('No newline at end of file') || /^-+$/.test(line)) continue
    if (line.startsWith('-')) continue
    if (line.startsWith('+')) {
      result.push(line.slice(1))
    } else if (line.startsWith(' ')) {
      result.push(line.slice(1))
    } else if (!line.startsWith('\\')) {
      result.push(line)
    }
  }

  return result.join('\n')
}

function applySimpleDiff(diff: string): string {
  return diff.split('\n')
    .filter(line => {
      if (line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('@@') || line.startsWith('diff ')) return false
      if (line.includes('No newline at end of file') || /^-+$/.test(line)) return false
      if (line.startsWith('-')) return false
      return true
    })
    .map(line => line.startsWith('+') ? line.slice(1) : line.startsWith(' ') ? line.slice(1) : line)
    .join('\n')
}

function parseVueSFC(content: string): { html: string; css: string } {
  const templateMatch = content.match(/<template>([\s\S]*?)<\/template>/)
  const html = templateMatch ? templateMatch[1].replace(/<\/?template[^>]*>/gi, '') : content

  const styleMatch = content.match(/<style[^>]*>([\s\S]*?)<\/style>/)
  const css = styleMatch ? styleMatch[1] : ''

  return { html, css }
}

function generateVuePreview(html: string, css: string): string {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script src="https://unpkg.com/vue@3/dist/vue.global.js"><\/script>
  <style>
    body { font-family: -apple-system, sans-serif; margin: 0; padding: 20px; }
    ${css}
  </style>
</head>
<body>
  <div id="app">${html}</div>
  <script>
    const { createApp } = Vue
    createApp({ data() { return {} }, methods: {} }).mount('#app')
  <\/script>
</body>
</html>`
}

function simpleMarkdownToHtml(md: string): string {
  return `<div style="padding: 20px; line-height: 1.6;">
    ${md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code style="background: #f5f5f5; padding: 2px 6px; border-radius: 4px;">$1</code>')
    .replace(/\n/g, '<br>')}
  </div>`
}

function escapeHtmlAttr(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// 格式化 diff 显示（增绿删红）
const formattedDiff = computed(() => {
  const diff = props.unifiedDiff
  if (!diff) return ''

  const escaped = diff
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  const lines = escaped.split('\n')
  const changeLines: string[] = []

  for (const line of lines) {
    if (line.startsWith('--- ') || line.startsWith('+++ ') || line.startsWith('@@') || line.startsWith('diff ')) continue
    if (line.startsWith(' ') || line === '') continue
    if (line.includes('No newline at end of file')) continue
    if (/^[+-]\s*(---|\+\+\+|@@|diff\s)/.test(line)) continue
    if (line.startsWith('+') || line.startsWith('-')) {
      changeLines.push(line)
    }
  }

  if (changeLines.length === 0) {
    return lines
      .filter(line => !line.startsWith('---') && !line.startsWith('+++') && !line.startsWith('@@') && !line.startsWith('diff '))
      .map(line => `<span class="diff-context">${line}</span>`)
      .join('')
  }

  return changeLines
    .map(line => {
      if (line.startsWith('+')) return `<span class="diff-add">${line}</span>`
      if (line.startsWith('-')) return `<span class="diff-del">${line}</span>`
      return `<span class="diff-context">${line}</span>`
    })
    .join('')
})
</script>

<style scoped>
.diff-page-preview {
  display: flex;
  height: 100%;
  flex-direction: column;
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
  overflow: hidden;
}

.header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
  background: rgba(59, 130, 246, 0.03);
}

.operation {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.operation.create {
  background: rgba(34, 197, 94, 0.15);
  color: rgb(34, 197, 94);
}

.operation.update {
  background: rgba(59, 130, 246, 0.15);
  color: rgb(59, 130, 246);
}

.operation.delete {
  background: rgba(239, 68, 68, 0.15);
  color: rgb(239, 68, 68);
}

.path {
  flex: 1;
  overflow: hidden;
  color: #475569;
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  background: transparent;
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.action-btn:hover {
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
}

.action-btn.active {
  background: rgba(59, 130, 246, 0.15);
  border-color: rgba(59, 130, 246, 0.4);
  color: #3b82f6;
}

.code-content {
  flex: 1;
  height: 100%;
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

.code-content code {
  font-family: inherit;
}

.preview-content {
  flex: 1;
  height: 100%;
  overflow: hidden;
}

.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
  background: white;
}

.preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  font-size: 14px;
}

/* 增绿删红样式 */
.code-content :deep(.diff-add) {
  color: rgb(34, 197, 94);
  background: rgba(34, 197, 94, 0.08);
  display: block;
}

.code-content :deep(.diff-del) {
  color: rgb(239, 68, 68);
  background: rgba(239, 68, 68, 0.08);
  display: block;
}

.code-content :deep(.diff-context) {
  color: #9ca3af;
  display: block;
}
</style>
