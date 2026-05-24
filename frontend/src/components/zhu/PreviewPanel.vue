<template>
  <aside class="blank-panel" :aria-hidden="previewState.type === 'empty'">
    <div v-if="previewState.type === 'empty'" class="preview-empty">
      <span class="preview-empty-title">预览区</span>
      <span class="preview-empty-desc">选择代码、网页、文件或 Diff 后在这里查看。</span>
    </div>
    <div v-else class="preview-content">
      <div class="preview-header">
        <div>
          <p class="preview-type">{{ previewState.type }}</p>
          <h3>{{ previewState.title || '预览' }}</h3>
        </div>
        <button class="preview-close" type="button" @click="$emit('close')">关闭</button>
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
.blank-panel {
  height: 100vh;
  overflow: hidden;
  background: rgb(var(--surface-color));
}

.preview-empty,
.preview-content {
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
}

.preview-empty {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  color: rgb(var(--text-muted));
  text-align: center;
}

.preview-empty-title {
  color: rgb(var(--text-secondary));
  font-size: 16px;
  font-weight: 600;
}

.preview-empty-desc {
  font-size: 13px;
  line-height: 1.6;
}

.preview-content {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 16px;
}

.preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.preview-type {
  margin: 0 0 4px;
  color: rgb(var(--text-muted));
  font-size: 12px;
  text-transform: uppercase;
}

.preview-header h3 {
  margin: 0;
  font-size: 16px;
}

.preview-close {
  border: 1px solid #ececec;
  border-radius: 8px;
  background: #fff;
  color: #262626;
  padding: 6px 10px;
  cursor: pointer;
}

.preview-code,
.preview-frame,
.preview-placeholder {
  flex: 1;
  min-height: 0;
  border: 1px solid #ececec;
  border-radius: 12px;
  background: #fafafa;
}

.preview-code {
  overflow: auto;
  margin: 0;
  padding: 14px;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  line-height: 1.6;
}

.preview-frame {
  width: 100%;
}

.preview-placeholder {
  padding: 16px;
  color: #666;
  font-size: 14px;
}

@media (max-width: 1200px) {
  .blank-panel {
    display: none;
  }
}
</style>
