<template>
  <main class="chat-shell">
    <ChatHeader
      :current-session="props.currentSession"
      :current-session-id="props.currentSessionId"
      :connection-state="props.connectionState"
      :reconnect-attempt="props.reconnectAttempt"
      :format-time="props.formatTime"
      :workspace="props.workspace"
      :selected-agents="selectedAgents"
      @open-left="$emit('open-left')"
      @retry="$emit('retry')"
      @pick-agent="handlePickAgent"
    />

    <section class="chat-stream-panel">
      <ChatShowArea
        ref="chatShow"
        :targetId="props.currentSessionId || ''"
        :isChatRecordLoading="props.isLoadingMessages"
        :isSendLoading="props.isSendLoading"
        :isComplete="false"
      />
    </section>

    <section class="chat-composer-panel">
      <ChatInputArea
        ref="chatRef"
        :sessionId="props.currentSessionId || ''"
        :disabled="!props.currentSessionId"
        :session-agent-options="sessionAgentOptions"
        @selection-change="handleSelectionChange"
        @send="$emit('send', $event)"
      />
    </section>
  </main>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'

import ChatInputArea from '../../veiws/Chat-input-area.vue'
import ChatShowArea from '../../veiws/Chat-show-area.vue'
import type {
  ComposerAgent,
  ComposerSubmitPayload,
  ConversationItem,
  SessionAgentOption,
  SessionMember,
  SessionMemberStatus,
  Workspace,
} from '../../types/agenthub'
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
  (e: 'send', payload: ComposerSubmitPayload): void
}>()

const chatRef = ref<{
  insertAgentChip?: (agent: ComposerAgent) => void
  getStructuredValue?: () => ComposerSubmitPayload
} | null>(null)
const selectedAgents = ref<ComposerAgent[]>([])

const statusRank: Record<SessionMemberStatus, number> = {
  online: 0,
  busy: 1,
  offline: 2,
}

const sessionAgentOptions = computed<SessionAgentOption[]>(() => {
  const members = props.currentSession?.members ?? []

  return members
    .filter((member): member is SessionMember => member.member_type === 'agent')
    .map((member) => ({
      id: member.member_id,
      name: member.agent_name || member.member_id,
      avatar: member.agent_avatar ?? null,
      status: member.status,
      role: member.agent_role ?? null,
      isPrimary: Boolean(member.is_primary),
    }))
    .sort((left, right) => {
      const rankDiff = statusRank[left.status] - statusRank[right.status]
      if (rankDiff !== 0) return rankDiff
      return left.name.localeCompare(right.name)
    })
})

function handlePickAgent(agent: ComposerAgent) {
  chatRef.value?.insertAgentChip?.(agent)
}

function handleSelectionChange(agents: ComposerAgent[]) {
  selectedAgents.value = agents
}
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

.chat-composer-panel {
  border-top: none;
  background: transparent;
  padding-top: 8px;
}
</style>
