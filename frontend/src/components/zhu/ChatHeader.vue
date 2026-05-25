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
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 76px;
  padding: 16px 24px;
  border-bottom: 1px solid rgb(var(--border-color));
}

.chat-header-main {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.chat-header-kicker {
  margin: 0 0 4px;
  color: rgb(var(--text-muted));
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.chat-header h2 {
  margin: 0 0 4px;
  font-size: 24px;
  line-height: 1.15;
}

.chat-header-subtitle {
  margin: 0;
  color: rgb(var(--text-secondary));
  font-size: 13px;
}

.header-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgb(var(--surface-muted));
  color: rgb(var(--text-secondary));
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
