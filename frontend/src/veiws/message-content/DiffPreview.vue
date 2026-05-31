<template>
  <div class="diff-preview" :class="{ 'is-confirmed': isConfirmed, 'is-rejected': isRejected }">
    <div class="diff-header">
      <span class="diff-operation" :class="operation">
        {{ operationLabel }}
      </span>
      <span class="diff-path" :title="path">{{ fileName }}</span>
    </div>

    <div class="diff-content">
      <pre class="diff-code"><code>{{ unifiedDiff }}</code></pre>
    </div>

    <div v-if="status === 'pending_confirmation'" class="diff-actions">
      <button class="btn-confirm" type="button" :disabled="isLoading" @click="handleConfirm">
        {{ isLoading ? '应用中...' : '确认写入' }}
      </button>
      <button class="btn-cancel" type="button" @click="handleCancel">取消</button>
    </div>

    <div v-else-if="status === 'applied'" class="diff-result success">
      <span class="result-icon">&#10003;</span>
      <span>已写入成功 {{ path }}</span>
    </div>

    <div v-else-if="status === 'rejected'" class="diff-result error">
      <span class="result-icon">&#10007;</span>
      <span>写入已取消</span>
    </div>

    <div v-else-if="status === 'failed'" class="diff-result error">
      <span class="result-icon">&#10007;</span>
      <span>写入失败</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import type { PendingChange } from '../../types/agenthub'

const props = defineProps<{
  change: PendingChange
}>()

const emit = defineEmits<{
  (e: 'confirm', changeId: string): void
  (e: 'cancel', changeId: string): void
}>()

const isLoading = ref(false)

const operationLabel = computed(() => {
  const labels: Record<string, string> = {
    create: '创建',
    update: '更新',
    delete: '删除',
  }
  return labels[props.change.operation] || props.change.operation
})

const fileName = computed(() => {
  const parts = props.change.path.split(/[/\\]/)
  return parts[parts.length - 1] || props.change.path
})

const operation = computed(() => props.change.operation)
const path = computed(() => props.change.path)
const unifiedDiff = computed(() => props.change.unified_diff)
const status = computed(() => props.change.status)

const isConfirmed = computed(() => status.value === 'applied')
const isRejected = computed(() => status.value === 'rejected')

const handleConfirm = async () => {
  if (isLoading.value || isConfirmed.value) return
  isLoading.value = true
  try {
    emit('confirm', props.change.change_id)
  } finally {
    isLoading.value = false
  }
}

const handleCancel = () => {
  if (isConfirmed.value || isRejected.value) return
  emit('cancel', props.change.change_id)
}
</script>

<style scoped>
.diff-preview {
  margin: 8px 0;
  overflow: hidden;
  border: 1px solid rgb(var(--border-color));
  border-radius: 12px;
  background: rgb(var(--surface-color));
}

.diff-preview.is-confirmed {
  border-color: rgba(34, 197, 94, 0.5);
  background: rgba(34, 197, 94, 0.05);
}

.diff-preview.is-rejected {
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.05);
}

.diff-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid rgb(var(--border-color));
  background: rgba(var(--surface-secondary), 0.5);
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
  overflow: hidden;
  color: rgb(var(--text-color));
  font-size: 13px;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.diff-content {
  max-height: 300px;
  overflow: auto;
  padding: 12px 14px;
}

.diff-code {
  margin: 0;
  color: rgb(var(--text-color));
  font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.diff-actions {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  border-top: 1px solid rgb(var(--border-color));
  background: rgba(var(--surface-secondary), 0.3);
}

.btn-confirm {
  flex: 1;
  padding: 8px 16px;
  border: none;
  border-radius: 8px;
  background: rgb(var(--primary-color));
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-confirm:hover:not(:disabled) {
  filter: brightness(1.1);
}

.btn-confirm:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.btn-cancel {
  padding: 8px 16px;
  border: 1px solid rgb(var(--border-color));
  border-radius: 8px;
  background: transparent;
  color: rgb(var(--text-secondary));
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-cancel:hover {
  border-color: rgb(var(--text-muted));
  color: rgb(var(--text-color));
}

.diff-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 500;
}

.diff-result.success {
  color: rgb(34, 197, 94);
}

.diff-result.error {
  color: rgb(239, 68, 68);
}

.result-icon {
  font-size: 16px;
  font-weight: 700;
}
</style>
