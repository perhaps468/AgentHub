<template>
  <div class="connection-status" :class="state">
    <span class="dot" />
    <span class="label">{{ label }}</span>
    <button v-if="state === 'failed'" class="retry-btn" type="button" @click="$emit('retry')">
      重试
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ConnectionState } from '@/utils/ws-client'

const props = defineProps<{
  state: ConnectionState
  reconnectAttempt?: number
}>()

defineEmits<{
  retry: []
}>()

const label = computed(() => {
  switch (props.state) {
    case 'connected':
      return '在线'
    case 'connecting':
      return '连接中...'
    case 'disconnected':
      return '已断开'
    case 'reconnecting': {
      const n = props.reconnectAttempt ?? 1
      return `重连中... (${n}/5)`
    }
    case 'failed':
      return '连接失败'
    default:
      return ''
  }
})
</script>

<style scoped>
.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: rgb(var(--surface-muted));
  border: 1px solid rgb(var(--border-color));
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* States */
.connection-status.connected .dot {
  background: rgb(var(--success-color, #22c55e));
}
.connection-status.connected .label {
  color: rgb(var(--success-color, #22c55e));
}

.connection-status.connecting .dot,
.connection-status.disconnected .dot {
  background: rgb(var(--text-muted));
}
.connection-status.connecting .label,
.connection-status.disconnected .label {
  color: rgb(var(--text-secondary));
}

.connection-status.reconnecting .dot {
  background: rgb(var(--warning-color, #f59e0b));
  animation: pulse 1.2s ease-in-out infinite;
}
.connection-status.reconnecting .label {
  color: rgb(var(--warning-color, #f59e0b));
}

.connection-status.failed .dot {
  background: rgb(var(--danger-color, #ef4444));
}
.connection-status.failed .label {
  color: rgb(var(--danger-color, #ef4444));
}

.retry-btn {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: rgb(var(--danger-color, #ef4444));
  background: transparent;
  border: 1px solid rgb(var(--danger-color, #ef4444));
  cursor: pointer;
}

.retry-btn:hover {
  background: rgba(var(--danger-color, #ef4444), 0.1);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
