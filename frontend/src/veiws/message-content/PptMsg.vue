<template>
  <div class="ppt-msg" :class="{ 'is-own': props.right }">
    <div class="ppt-msg-header">
      <span class="ppt-msg-icon">PPT</span>
      <div>
        <div class="ppt-msg-title">{{ previewModel?.title || 'PPT 消息' }}</div>
        <div class="ppt-msg-meta">{{ slideCountText }}</div>
      </div>
    </div>

    <button
      class="ppt-msg-preview"
      type="button"
      :disabled="!previewModel"
      @click="handlePreview"
    >
      预览 PPT
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { PptPreviewModel } from '../../types/agenthub'
import { buildPptPreviewModel } from '../../utils/ppt-data'

const props = withDefaults(
  defineProps<{
    msg: {
      message?: string
      payload?: Record<string, unknown>
      content?: string
    }
    right?: boolean
  }>(),
  {
    right: false,
  },
)

const emit = defineEmits<{
  preview: [payload: PptPreviewModel]
}>()

const previewModel = computed(() => {
  return buildPptPreviewModel(props.msg.payload || props.msg.message || props.msg.content)
})

const slideCountText = computed(() => {
  const count = previewModel.value?.slides.length ?? 0
  return count > 0 ? `${count} 页幻灯片` : '暂无可预览内容'
})

const handlePreview = () => {
  if (previewModel.value) {
    emit('preview', previewModel.value)
  }
}
</script>

<style scoped>
.ppt-msg {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 220px;
}

.ppt-msg-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ppt-msg-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 32px;
  border-radius: 10px;
  background: rgba(var(--primary-color), 0.14);
  color: rgb(var(--primary-strong));
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.ppt-msg-title {
  color: rgb(var(--text-color));
  font-size: 14px;
  font-weight: 700;
}

.ppt-msg-meta {
  color: rgb(var(--text-secondary));
  font-size: 12px;
  line-height: 1.4;
}

.ppt-msg-preview {
  align-self: flex-start;
  padding: 7px 12px;
  border-radius: 999px;
  border: 1px solid rgba(var(--primary-color), 0.38);
  background: rgba(var(--primary-color), 0.08);
  color: rgb(var(--primary-strong));
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.ppt-msg-preview:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
