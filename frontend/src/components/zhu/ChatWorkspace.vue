<template>
  <main class="chat-shell">
    <ChatHeader
      :current-session="currentSession"
      :current-session-id="currentSessionId"
      :connection-state="connectionState"
      :reconnect-attempt="reconnectAttempt"
      :format-time="formatTime"
      @open-left="$emit('open-left')"
      @retry="$emit('retry')"
    />

    <section class="chat-stream-panel">
      <ChatShowArea
        ref="chatShow"
        :targetId="currentSessionId || ''"
        :isChatRecordLoading="isLoadingMessages"
        :isSendLoading="isSendLoading"
        :isComplete="false"
      />
    </section>

    <section class="chat-composer-panel">
      <ChatInputArea
        ref="chatRef"
        :sessionId="currentSessionId || ''"
        :disabled="!currentSessionId"
        @send="$emit('send', $event)"
      />
    </section>
  </main>
</template>

<script lang="ts" setup>
import ChatInputArea from '../../veiws/Chat-input-area.vue'
import ChatShowArea from '../../veiws/Chat-show-area.vue'
import type { ConversationItem } from '../../types/agenthub'
import type { ConnectionState } from '../../utils/ws-client'
import ChatHeader from './ChatHeader.vue'

defineProps<{
  currentSession: ConversationItem | null | undefined
  currentSessionId: string
  connectionState: ConnectionState
  reconnectAttempt: number
  isLoadingMessages: boolean
  isSendLoading: boolean
  formatTime: (iso: string) => string
}>()

defineEmits<{
  (e: 'open-left'): void
  (e: 'retry'): void
  (e: 'send', content: string): void
}>()
</script>

<style scoped>
/* ==================== 聊天区主容器 ==================== */
.chat-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  overflow: hidden;
  background: transparent;
}

.chat-stream-panel {
  min-height: 0;
  flex: 1;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  margin: 0 4px;
}

.chat-composer-panel {
  border-top: none;
  background: transparent;
  padding-top: 8px;
}
</style>
