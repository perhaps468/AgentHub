<template>
  <div class="chat-show-area" ref="chatShowAreaRef">
    <section v-if="activeRun" class="orchestration-panel">
      <div class="orchestration-header">
        <div>
          <h3>编排计划</h3>
          <p>Run #{{ activeRun.id }} · {{ activeRun.status }}</p>
        </div>
      </div>
      <div v-if="activeRun.summary" class="orchestration-summary">
        {{ activeRun.summary }}
      </div>
      <ul v-if="activeTasks.length" class="task-list">
        <li v-for="task in activeTasks" :key="task.id" class="task-item">
          <div class="task-meta">#{{ task.sequence }} · {{ task.status }}</div>
          <div class="task-title">{{ task.title }}</div>
          <div class="task-agent">{{ task.assigned_agent_id }}</div>
        </li>
      </ul>
    </section>

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

const activeRun = computed(() => sessionStore.activeRun)
const activeTasks = computed(() => sessionStore.activeTasks)
const pendingChangesForSession = computed(() => sessionStore.streamState.getPendingChanges(props.targetId))

function getPendingDiffsForMessage(messageId?: string, streamId?: string) {
  if (!messageId && !streamId) return []
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
        name: isHuman ? userInfoStore.userName || '我' : agentStore.agent?.name ?? m.sender_role ?? 'AI助手',
        avatar: null,
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
          name: agentStore.agent?.name ?? s.sender_role ?? 'AI助手',
          avatar: null,
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
.orchestration-panel {
  border: 1px solid rgba(59, 130, 246, 0.18);
  background: rgba(255, 255, 255, 0.72);
  border-radius: 18px;
  padding: 16px;
}
.task-list {
  display: grid;
  gap: 12px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.task-item {
  border-radius: 14px;
  padding: 12px;
  background: rgba(248, 250, 252, 0.95);
}
</style>
