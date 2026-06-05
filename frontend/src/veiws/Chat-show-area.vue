<template>
  <div class="chat-show-area" ref="chatShowAreaRef">
    <div v-if="sessionStore.currentPageInfo.hasMore && !sessionStore.isLoadingMessages" class="load-more-row">
      <button type="button" class="load-more-btn" @click="handleLoadMore">加载更多</button>
    </div>

    <div v-if="sessionStore.isLoadingMessages && msgRecord.length === 0" class="loading-row">
      <loading label="加载中" />
    </div>

    <div
      v-for="item in msgRecord"
      :key="item.id"
      class="msg-item"
      :class="{ right: item.fromId === userInfoStore.userId }"
    >
      <Msg :msg="item" :user="item.fromInfo" />
    </div>

    <div v-if="isSendLoading" class="loading-row">
      <loading label="发送中" />
    </div>

    <button v-if="newMsgCount > 0" class="new-msg-count" type="button" @click="scrollToBottom">
      {{ newMsgCount }} 条新消息
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

import { useAgentStore } from '../store/module/useAgentStore'
import { useSessionStore } from '../store/module/useSessionStore'
import { useUserInfoStore } from '../store/module/useUserStore'
import type { ChatMessage } from '../types/agenthub'
import Msg from './message-content/msg.vue'
import loading from './message-content/loading.vue'

const props = defineProps({
  targetId: {
    type: String,
    default: '',
  },
  isChatRecordLoading: Boolean,
  isSendLoading: Boolean,
  isComplete: Boolean,
})

const sessionStore = useSessionStore()
const agentStore = useAgentStore()
const userInfoStore = useUserInfoStore()
const chatShowAreaRef = ref<HTMLElement>()
const newMsgCount = ref(0)
const isFirstLoad = ref(true)

const pendingChangesForSession = computed(() => sessionStore.streamState.getPendingChanges(props.targetId))

function resolveAgentName(metadata: Record<string, unknown> | undefined, senderRole: string | null | undefined) {
  const currentSession = sessionStore.currentSession
  const metadataAgentId = typeof metadata?.agent_id === 'string' ? metadata.agent_id : null

  let resolvedAgentId: string | null = metadataAgentId
  if (!resolvedAgentId && currentSession?.mode === 'single' && currentSession.agent_id) {
    resolvedAgentId = currentSession.agent_id
  }

  if (resolvedAgentId) {
    const matchedAgent = agentStore.agents.find((agent) => agent.id === resolvedAgentId)
    if (matchedAgent?.name) return matchedAgent.name
  }

  return senderRole ?? 'AI助手'
}

function resolveAgentAvatar(metadata: Record<string, unknown> | undefined) {
  const currentSession = sessionStore.currentSession
  const metadataAgentId = typeof metadata?.agent_id === 'string' ? metadata.agent_id : null

  let resolvedAgentId: string | null = metadataAgentId
  if (!resolvedAgentId && currentSession?.mode === 'single' && currentSession.agent_id) {
    resolvedAgentId = currentSession.agent_id
  }

  if (resolvedAgentId) {
    const matchedAgent = agentStore.agents.find((agent) => agent.id === resolvedAgentId)
    if (matchedAgent?.avatar) return matchedAgent.avatar
  }

  return null
}

function getPendingDiffsForMessage(messageId?: string, streamId?: string) {  if (!messageId && !streamId) return []
  return pendingChangesForSession.value.filter((change) => {
    if (messageId && change.message_id === messageId) return true
    if (streamId && change.stream_id === streamId) return true
    return false
  })
}

const msgRecord = computed(() => {
  const historicalMessages: ChatMessage[] = sessionStore.messageMap[props.targetId] ?? []
  const streamingMessages = sessionStore.currentStreamingMessages

  const historicalRecords = historicalMessages.map((m) => {
    const isHuman = m.sender_type === 'human'
    const senderId = isHuman ? userInfoStore.userId : `agent_${m.sender_role ?? 'default'}`
    const pendingDiffs = getPendingDiffsForMessage(m.id)
    return {
      id: m.id,
      fromId: senderId,
      toId: props.targetId,
      fromInfo: {
        id: senderId,
        name: isHuman ? userInfoStore.userName || '我' : resolveAgentName(m.metadata, m.sender_role),
        avatar: isHuman ? (userInfoStore.avatar || null) : resolveAgentAvatar(m.metadata),
        type: isHuman ? 'User' : 'Agent',
        badge: null,
      },
      message: m.content,
      referenceMsg: m.reference ?? null,
      atUser: null,
      isShowTime: false,
      type: m.type ?? 'text',
      source: 'User',
      createTime: m.created_at,
      updateTime: m.created_at,
      deliveryStatus: m.status,
      isStreaming: false,
      metadata: m.metadata || {},
      pending_diffs: pendingDiffs,
    }
  })

  const streamingRecords = streamingMessages
    .filter((s) => !s.message_id || !historicalMessages.some((m) => m.id === s.message_id))
    .map((s) => {
      const senderId = `agent_${s.sender_role ?? 'default'}`
      const pendingDiffs = getPendingDiffsForMessage(s.message_id, s.stream_id)
      const displayContent = s.ui_status === 'thinking' ? `${s.sender_role || 'AI'} 正在思考...` : s.content

      return {
        id: s.message_id || s.stream_id,
        fromId: senderId,
        toId: props.targetId,
        fromInfo: {
          id: senderId,
          name: resolveAgentName(s.metadata, s.sender_role),
          avatar: resolveAgentAvatar(s.metadata),
          type: 'Agent',
          badge: null,
        },
        message: displayContent,
        referenceMsg: null,
        atUser: null,
        isShowTime: false,
        type: 'text',
        source: 'Agent',
        createTime: s.created_at,
        updateTime: s.created_at,
        isStreaming: true,
        streamStatus: s.ui_status,
        metadata: s.metadata || {},
        pending_diffs: pendingDiffs,
      }
    })

  return [...historicalRecords, ...streamingRecords]
})

watch(() => props.targetId, () => {
  newMsgCount.value = 0
  isFirstLoad.value = true
})

const handleLoadMore = async () => {
  const container = chatShowAreaRef.value
  const pageInfo = sessionStore.currentPageInfo
  if (!props.targetId || !pageInfo.hasMore) return
  const oldScrollHeight = container?.scrollHeight ?? 0
  await sessionStore.fetchMessages(props.targetId, { page: pageInfo.page + 1, page_size: 20 })
  nextTick(() => {
    const newContainer = chatShowAreaRef.value
    if (newContainer && oldScrollHeight > 0) {
      const heightDiff = newContainer.scrollHeight - oldScrollHeight
      newContainer.scrollTop += heightDiff
    }
  })
}

const scrollToBottom = () => {
  nextTick(() => {
    const container = chatShowAreaRef.value
    if (container) {
      container.scrollTop = container.scrollHeight
      newMsgCount.value = 0
    }
  })
}

watch(() => sessionStore.messageMap[props.targetId]?.length ?? 0, (newLen, oldLen) => {
  if (newLen > oldLen && isFirstLoad.value) {
    isFirstLoad.value = false
    scrollToBottom()
  }
})

watch(() => sessionStore.currentStreamingMessages, () => {
  const container = chatShowAreaRef.value
  if (container && sessionStore.currentStreamingMessages.length > 0) {
    container.scrollTop = container.scrollHeight
  }
})

const handleScroll = () => {
  const container = chatShowAreaRef.value
  if (!container) return
  if (container.scrollTop + container.clientHeight >= container.scrollHeight - 80) {
    newMsgCount.value = 0
  }
}

onMounted(() => {
  nextTick(() => {
    scrollToBottom()
    chatShowAreaRef.value?.addEventListener('scroll', handleScroll)
  })
})

onUnmounted(() => {
  chatShowAreaRef.value?.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.chat-show-area {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  padding: 20px 24px;
  background: transparent;
}
</style>
