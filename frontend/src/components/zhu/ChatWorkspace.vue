<template>
  <main class="chat-shell">
    <ChatHeader
      :current-session="currentSession"
      :current-session-id="currentSessionId"
      :connection-state="connectionState"
      :reconnect-attempt="reconnectAttempt"
      :format-time="formatTime"
      :workspace="workspace"
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
import { computed } from 'vue'

import ChatInputArea from '../../veiws/Chat-input-area.vue'
import ChatShowArea from '../../veiws/Chat-show-area.vue'
import { useSessionStore } from '../../store/module/useSessionStore'
import type { ConversationItem, Workspace } from '../../types/agenthub'
import type { ConnectionState } from '../../utils/ws-client'
import ChatHeader from './ChatHeader.vue'

const props = defineProps<{
  currentSession: ConversationItem | null | undefined
  currentSessionId: string
  connectionState: ConnectionState
  reconnectAttempt: number
  isLoadingMessages: boolean
  isSendLoading: boolean
  formatTime: (iso: string) => string
  workspace: Workspace | null
}>()

const emit = defineEmits<{
  (e: 'open-left'): void
  (e: 'retry'): void
  (e: 'send', content: string): void
}>()

const sessionStore = useSessionStore()
</script>

<style scoped>
.chat-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  overflow: hidden;
  background: transparent;
}

/* Original Chat Panels */
.chat-stream-panel {
  min-height: 0;
  flex: 1;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.5);
  margin: 0 4px;
  display: flex;
  flex-direction: column;
}

.chat-composer-panel {
  border-top: none;
  background: transparent;
  padding-top: 8px;
}
</style>
