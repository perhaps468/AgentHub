<template>
  <div class="diff-preview" :class="{ 'is-confirmed': isConfirmed, 'is-rejected': isRejected, 'is-pending-review-only': isPendingReviewOnly }">
    <div class="diff-header">
      <span class="diff-operation" :class="operation">
        {{ operationLabel }}
      </span>
      <span class="diff-path" :title="path">{{ fileName }}</span>
    </div>
    <div v-if="pendingReviewInfo" class="pending-review-card">
      <div v-if="contentHtml" v-html="contentHtml" class="pending-review-html"></div>
      <div class="pending-review-meta">
        <div class="pending-review-title">待确认写入</div>
        <div class="pending-review-file">{{ pendingReviewInfo.fileName }}</div>
        <div class="pending-review-id">变更 ID: {{ pendingReviewInfo.changeId }}</div>
      </div>
      <!-- 科技风按钮区域 -->
      <div v-if="status === 'pending_confirmation'" class="diff-actions">
        <div class="action-left">
          <button class="btn btn-confirm" type="button" :disabled="isLoading" @click="handleConfirm">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12l5 5L20 7"/>
            </svg>
            {{ isLoading ? '应用中...' : '确认写入' }}
          </button>
        </div>
        <div class="action-right">
          <button class="btn btn-preview" type="button" @click="handlePreview" title="预览">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            预览
          </button>
          <button class="btn btn-cancel" type="button" @click="handleCancel" title="取消">
            <svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
            取消
          </button>
        </div>
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
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { applyPendingChange, rejectPendingChange } from '@/api/modules/pendingChanges'
import { useSessionStore } from '@/store/module/useSessionStore'
import { normalizeRuntimeTextForDisplay } from '../../utils/runtime-text'
import type { PendingChange } from '../../types/agenthub'

const emit = defineEmits<{
  (e: 'confirm', changeId: string): void
  (e: 'cancel', changeId: string): void
  (e: 'preview', change: PendingChange): void
}>()

const props = defineProps<{
  change: PendingChange
  contentHtml?: string
}>()

const sessionStore = useSessionStore()
const isLoading = ref(false)
const pendingReviewLoading = ref(false)
const pendingReviewStatus = ref<PendingChange['status']>('pending_confirmation')

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
const isPendingReviewOnly = computed(() => !props.change.unified_diff?.trim())

const isConfirmed = computed(() => status.value === 'applied')
const isRejected = computed(() => status.value === 'rejected')

watch(
  () => props.change.status,
  (newStatus) => {
    if (newStatus) {
      pendingReviewStatus.value = newStatus
    }
  },
  { immediate: true },
)

const pendingReviewInfo = computed(() => ({
  changeId: props.change.change_id,
  fileName: props.change.path.split(/[/\\]/).pop() || 'target file',
}))

const handleConfirm = async () => {
  if (isLoading.value || isConfirmed.value) return
  isLoading.value = true
  emit('confirm', props.change.change_id)
}

const handleCancel = () => {
  if (isConfirmed.value || isRejected.value) return
  emit('cancel', props.change.change_id)
}

const handlePreview = () => {
  emit('preview', props.change)
}

const handleConfirmPendingReview = async () => {
  const changeId = pendingReviewInfo.value.changeId
  if (!changeId || pendingReviewLoading.value) return

  pendingReviewLoading.value = true
  try {
    const sessionId = sessionStore.currentSessionId || undefined
    const result = await applyPendingChange({ change_id: changeId, session_id: sessionId })
    if (result.success || result.status === 'applied') {
      pendingReviewStatus.value = 'applied'
    } else {
      pendingReviewStatus.value = 'failed'
    }
  } catch (error) {
    console.error('确认写入失败', error)
    pendingReviewStatus.value = 'failed'
  } finally {
    pendingReviewLoading.value = false
  }
}

const handleCancelPendingReview = async () => {
  const changeId = pendingReviewInfo.value.changeId
  if (!changeId) return

  try {
    const sessionId = sessionStore.currentSessionId || undefined
    await rejectPendingChange({ change_id: changeId, session_id: sessionId })
    pendingReviewStatus.value = 'rejected'
  } catch {
    pendingReviewStatus.value = 'rejected'
  }
}
</script>

<style scoped>
.diff-preview {
  margin: 8px 0;
  overflow: hidden;
  border: 1px solid rgba(var(--primary-color), 0.2);
  border-radius: 12px;
  background: rgb(var(--surface-color));
}

.diff-preview.is-confirmed {
  border-color: rgba(0, 212, 255, 0.3);
  background: rgba(0, 212, 255, 0.03);
}

.diff-preview.is-rejected {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.03);
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
  background: rgba(16, 185, 129, 0.15);
  color: rgb(16, 185, 129);
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

  &::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  &::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 3px;
  }

   /* 滚动条滑块（蓝色） */
   &::-webkit-scrollbar-thumb {
    background:#7fabf0;       /* 明亮的蓝色 */
    border-radius: 3px;
  }

  /* 滑块 hover 效果 */
  &::-webkit-scrollbar-thumb:hover {
    background: #2563eb;       /* 深一点的蓝 */
  }
}

.diff-preview.is-pending-review-only .pending-review-card {
  margin-top: 0;
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

/* ========== 科技风按钮 ========== */
.diff-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  padding: 5px 5px;
  border-top: 1px solid rgb(var(--border-color));
  position: relative;
}

.action-left {
  flex: 1;
  margin-right: 30px;
}

.action-right {
  display: flex;
  gap: 10px;
}


.btn {
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  font-family: inherit;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

/* 确认按钮占满左侧 */
.action-left .btn {
  flex: 1;
  max-width: 200px;
}

.btn-icon {
  height: 16px;
  flex-shrink: 0;
  display: flex;
  justify-content: space-between; 
  align-items: center; 
}

/* 光效扫过动效 */
.btn-confirm::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(15, 15, 15, 0.08),
    transparent
  );
  transition: left 0.5s;
}

.btn:hover::before {
  left: 100%;
}

/* 主按钮 - 渐变发光 */
.btn-confirm {
  border: none;
  padding: 10px 16px;
  background:  rgb(var(--primary-color));
  color: #ffffff;
  box-shadow: 0 0 20px rgba(0, 150, 255, 0.2);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

.btn-confirm:hover:not(:disabled) {
  background-color: rgba(0, 150, 255, 0.8);;
  transform: translateY(-2px);
}

.btn-confirm:active:not(:disabled) {
  transform: translateY(0);
}

.btn-confirm:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

/* 取消按钮 - 毛玻璃描边 */
.btn-cancel {
  color:  #111111;
}
.btn-cancel:hover {
  color: #fa5a5a;
  
}


/* 预览按钮 - 科技蓝边框 */
.btn-preview {
  color:  #111111;
}
.btn-preview:hover {
  color:  #7fabf0;
}


/* ========== 状态提示条 ========== */
.diff-result {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  font-size: 13px;
  font-weight: 500;
  border-top: 1px solid rgba(0, 212, 255, 0.08);
}

.diff-result.success {
  color: #10b981;
  background: rgba(16, 185, 129, 0.05);
  border-top-color: rgba(16, 185, 129, 0.15);
}

.diff-result.error {
  color: #f87171;
  background: rgba(248, 113, 113, 0.05);
  border-top-color: rgba(248, 113, 113, 0.15);
}

.result-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
}

.diff-result.success .result-icon {
  background: rgba(16, 185, 129, 0.15);
}

.diff-result.error .result-icon {
  background: rgba(248, 113, 113, 0.15);
}

.pending-review-card {
  margin-top: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(var(--border-color), 0.9);
  border-radius: 14px;
  background: rgba(var(--surface-secondary), 0.55);
  position: relative;
  z-index: 2;
  pointer-events: auto;
}

.pending-review-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pending-review-title {
  color: rgb(var(--text-color));
  font-size: 13px;
  font-weight: 700;
}

.pending-review-file {
  color: rgb(var(--text-color));
  font-size: 14px;
  font-weight: 600;
}

.pending-review-id {
  color: rgb(var(--text-secondary));
  font-size: 12px;
}

.pending-review-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

.pending-review-confirm,
.pending-review-cancel {
  border: 0;
  border-radius: 999px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  position: relative;
  z-index: 3;
  pointer-events: auto;
}

.pending-review-confirm {
  background: rgb(var(--primary-color));
  color: #fff;
}

.pending-review-confirm:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.pending-review-cancel {
  background: rgba(var(--surface-color), 0.9);
  color: rgb(var(--text-secondary));
  border: 1px solid rgba(var(--border-color), 0.9);
}

.pending-review-status {
  font-size: 13px;
  font-weight: 600;
}

.pending-review-status.success {
  color: rgb(34, 197, 94);
}

.pending-review-status.error {
  color: rgb(239, 68, 68);
}

.pending-review-status.muted {
  color: rgb(var(--text-secondary));
}
</style>