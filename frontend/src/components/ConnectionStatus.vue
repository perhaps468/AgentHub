<template>
  <div class="connection-status" :class="currentStatus">
    <!-- 状态指示灯 -->
    <span class="dot"></span>
    <span class="label">{{ label }}</span>
    <!-- 重试按钮 -->
    <button v-if="currentStatus === 'failed' && reconnectAttempt > 0" class="retry-btn" @click="$emit('retry')">
      重试
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  // 支持 state 或 status 两种属性名
  status?: 'connected' | 'connecting' | 'disconnected' | 'reconnecting' | 'failed'
  state?: 'connected' | 'connecting' | 'disconnected' | 'reconnecting' | 'failed'
  reconnectAttempt: number
}>()

defineEmits<{
  (e: 'retry'): void
}>()

// 兼容 state 和 status 两种属性名
const currentStatus = computed(() => props.status || props.state || 'disconnected')

const label = computed(() => {
  switch (currentStatus.value) {
    case 'connected':
      return '在线'
    case 'connecting':
      return '连接中'
    case 'disconnected':
      return '离线'
    case 'reconnecting':
      return `重连中 (${props.reconnectAttempt})`
    case 'failed':
      return '连接失败'
    default:
      return '未知'
  }
})
</script>

<style scoped>
/* ==================== 连接状态容器 ==================== */
.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.15);
  backdrop-filter: blur(10px);
  transition: all 0.25s ease;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ==================== 状态颜色 ==================== */
/* 已连接 - 绿色 */
.connection-status.connected .dot {
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.5);
}
.connection-status.connected .label {
  color: #22c55e;
}

/* 连接中 / 已断开 - 灰色 */
.connection-status.connecting .dot,
.connection-status.disconnected .dot {
  background: #94a3b8;
}
.connection-status.connecting .label,
.connection-status.disconnected .label {
  color: #94a3b8;
}

/* 重连中 - 橙色脉冲 */
.connection-status.reconnecting .dot {
  background: #f59e0b;
  animation: pulse 1.2s ease-in-out infinite;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.5);
}
.connection-status.reconnecting .label {
  color: #f59e0b;
}

/* 连接失败 - 红色 */
.connection-status.failed .dot {
  background: #ef4444;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
}
.connection-status.failed .label {
  color: #ef4444;
}

/* ==================== 重试按钮 ==================== */
.retry-btn {
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  cursor: pointer;
  transition: all 0.2s ease;
}

.retry-btn:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: #ef4444;
  transform: translateY(-1px);
}

/* ==================== 脉冲动画 ==================== */
@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}
</style>
