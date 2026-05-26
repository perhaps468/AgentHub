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
      <div v-else class="preview-placeholder">
        <p>{{ previewState.description || '该类型预览待接入。' }}</p>
        <a v-if="previewState.url" :href="previewState.url" target="_blank" rel="noreferrer">在新窗口打开</a>
      </div>
    </div>
  </aside>
</template>

<script lang="ts" setup>
import type { PreviewState } from '../../types/agenthub'

defineProps<{
  previewState: PreviewState
}>()

defineEmits<{
  (e: 'close'): void
}>()
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

@media (max-width: 1200px) {
  .blank-panel {
    display: none;
  }
}
</style>
