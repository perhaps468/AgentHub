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
      <!-- Task C-2: Pending Changes 展示区 -->
      <div v-if="pendingChanges.length > 0" class="pending-changes-container">
        <DiffPreview
          v-for="change in pendingChanges"
          :key="change.change_id"
          :change="change"
          @confirm="handleConfirmChange"
          @cancel="handleCancelChange"
        />
      </div>

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
import DiffPreview from '../../veiws/message-content/DiffPreview.vue'
import type { ConversationItem, Workspace, PendingChange } from '../../types/agenthub'
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
  pendingChanges: PendingChange[]
}>()

const emit = defineEmits<{
  (e: 'open-left'): void
  (e: 'retry'): void
  (e: 'send', content: string): void
  (e: 'confirm-change', changeId: string): void
  (e: 'cancel-change', changeId: string): void
}>()

const handleConfirmChange = (changeId: string) => {
  emit('confirm-change', changeId)
}

const handleCancelChange = (changeId: string) => {
  emit('cancel-change', changeId)
}
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
  display: flex;
  flex-direction: column;
}

/* Task C-2: Pending Changes 容器样式 */
.pending-changes-container {
  flex-shrink: 0;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(var(--border-color), 0.5);
  background: rgba(var(--surface-color), 0.3);
  max-height: 200px;
  overflow-y: auto;
}

.chat-composer-panel {
  border-top: none;
  background: transparent;
  padding-top: 8px;
}
</style>
