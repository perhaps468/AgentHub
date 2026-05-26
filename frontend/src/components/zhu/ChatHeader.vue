<template>
  <header class="chat-header">
    <div class="chat-header-main">
      <button class="header-icon mobile-only" type="button" @click="$emit('open-left')">☰</button>
      <div>
        <p class="chat-header-kicker">
          {{ currentSession?.mode === 'group' ? '群聊协作' : '单聊会话' }}
        </p>
        <h2>{{ currentSession?.title || '选择或新建会话' }}</h2>
        <p class="chat-header-subtitle">
          {{ currentSession ? `创建于 ${formatTime(currentSession.created_at)}` : '点击左侧新建会话开始聊天' }}
        </p>
      </div>
    </div>
    <ConnectionStatus
      v-if="currentSessionId"
      :state="connectionState"
      :reconnectAttempt="reconnectAttempt"
      @retry="$emit('retry')"
    />
  </header>
</template>

<script lang="ts" setup>
import ConnectionStatus from '../ConnectionStatus.vue'
import type { ConversationItem } from '../../types/agenthub'
import type { ConnectionState } from '../../utils/ws-client'

defineProps<{
  currentSession: ConversationItem | null | undefined
  currentSessionId: string
  connectionState: ConnectionState
  reconnectAttempt: number
  formatTime: (iso: string) => string
}>()

defineEmits<{
  (e: 'open-left'): void
  (e: 'retry'): void
}>()
</script>

<style scoped>
/* ==================== 聊天头部 ==================== */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 72px;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
  background: rgba(255, 255, 255, 0.5);
}

.chat-header-main {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.chat-header-kicker {
  margin: 0 0 4px;
  color: #94a3b8;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}

.chat-header h2 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.2;
}

.chat-header-subtitle {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
}

.header-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.08);
  color: #64748b;
  font-size: 16px;
  transition: all 0.25s ease;
}

.header-icon:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(99, 102, 241, 0.1));
  color: #3b82f6;
  transform: scale(1.05);
}

.mobile-only {
  display: none;
}

@media (max-width: 900px) {
  .mobile-only {
    display: inline-flex;
  }
}
</style>
