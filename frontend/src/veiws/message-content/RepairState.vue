<template>
  <div class="repair-state" :class="stateClass">
    <div class="repair-header">
      <span class="repair-icon">{{ stateIcon }}</span>
      <span class="repair-label">{{ stateLabel }}</span>
      <span v-if="attempt > 0" class="repair-attempt">
        尝试 {{ attempt }}/{{ maxAttempts }}
      </span>
    </div>

    <div v-if="message" class="repair-message">
      {{ message }}
    </div>

    <div v-if="isExhausted" class="repair-stop-reason">
      <span class="stop-icon">⚠️</span>
      <span>已达到最大尝试次数 ({{ maxAttempts }}次)，修复已停止</span>
    </div>

    <div v-if="isFinished" class="repair-result">
      <span v-if="isSuccess" class="result-icon success">✓</span>
      <span v-else class="result-icon failure">✗</span>
      <span>{{ isSuccess ? '修复成功' : '修复失败' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface RepairStateData {
  state: 'IDLE' | 'ANALYZING_FAILURE' | 'GENERATING_FIX' | 'AWAITING_CONFIRMATION' | 'APPLYING_FIX' | 'RERUNNING_COMMAND' | 'FINISHED' | 'ERROR'
  attempt: number
  max_attempts: number
  message: string
}

const props = defineProps<{
  repairState: RepairStateData
}>()

const state = computed(() => props.repairState.state || 'IDLE')
const attempt = computed(() => props.repairState.attempt || 0)
const maxAttempts = computed(() => props.repairState.max_attempts || 3)
const message = computed(() => props.repairState.message || '')

const stateLabel = computed(() => {
  const labels: Record<string, string> = {
    IDLE: '空闲',
    ANALYZING_FAILURE: '分析失败原因',
    GENERATING_FIX: '生成修复方案',
    AWAITING_CONFIRMATION: '等待确认',
    APPLYING_FIX: '应用修复',
    RERUNNING_COMMAND: '重新运行命令',
    FINISHED: '完成',
    ERROR: '错误',
  }
  return labels[state.value] || state.value
})

const stateIcon = computed(() => {
  const icons: Record<string, string> = {
    IDLE: '⏸',
    ANALYZING_FAILURE: '🔍',
    GENERATING_FIX: '🔧',
    AWAITING_CONFIRMATION: '⏳',
    APPLYING_FIX: '⚙️',
    RERUNNING_COMMAND: '▶️',
    FINISHED: '✅',
    ERROR: '❌',
  }
  return icons[state.value] || '❓'
})

const stateClass = computed(() => {
  if (state.value === 'FINISHED') return 'is-finished'
  if (state.value === 'ERROR') return 'is-error'
  if (state.value === 'IDLE') return 'is-idle'
  return 'is-repairing'
})

const isExhausted = computed(() => attempt.value >= maxAttempts.value && state.value !== 'FINISHED')
const isFinished = computed(() => state.value === 'FINISHED')
const isSuccess = computed(() => message.value.toLowerCase().includes('success') || message.value.includes('成功'))
</script>

<style scoped>
.repair-state {
  border: 1px solid rgb(var(--border-color));
  border-radius: 8px;
  background: rgb(var(--surface-color));
  overflow: hidden;
  margin: 8px 0;
  font-size: 13px;
}

.repair-state.is-idle {
  opacity: 0.7;
}

.repair-state.is-repairing {
  border-color: rgba(var(--primary-color), 0.4);
  background: rgba(var(--primary-color), 0.05);
}

.repair-state.is-finished {
  border-color: rgba(34, 197, 94, 0.4);
  background: rgba(34, 197, 94, 0.05);
}

.repair-state.is-error {
  border-color: rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.05);
}

.repair-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid rgb(var(--border-color));
}

.repair-icon {
  font-size: 16px;
}

.repair-label {
  font-weight: 600;
  color: rgb(var(--text-color));
}

.repair-attempt {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(var(--primary-color), 0.1);
  color: rgb(var(--primary-color));
}

.repair-message {
  padding: 10px 14px;
  color: rgb(var(--text-secondary));
  font-size: 12px;
  line-height: 1.5;
  border-bottom: 1px solid rgb(var(--border-color));
}

.repair-stop-reason {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  color: rgb(251, 191, 36);
  font-size: 12px;
  background: rgba(251, 191, 36, 0.08);
}

.stop-icon {
  font-size: 14px;
}

.repair-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 600;
}

.repair-result:has(.success) {
  color: rgb(34, 197, 94);
}

.repair-result:has(.failure) {
  color: rgb(239, 68, 68);
}

.result-icon {
  font-size: 16px;
  font-weight: 700;
}
</style>
