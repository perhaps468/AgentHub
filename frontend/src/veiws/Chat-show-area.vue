<template>
  <div class="chat-show-area" ref="chatShowAreaRef">
    <div
      v-if="sessionStore.currentPageInfo.hasMore && !sessionStore.isLoadingMessages"
      class="load-more-row"
    >
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

const msgRecord = computed(() => {
  const historicalMessages: ChatMessage[] = sessionStore.messageMap[props.targetId] ?? []
  const streamingMessages = sessionStore.currentStreamingMessages

  const historicalRecords = historicalMessages.map((m) => {
    const isHuman = m.sender_type === 'human'
    const senderId = isHuman ? userInfoStore.userId : `agent_${m.sender_role ?? 'default'}`
    return {
      id: m.id,
      fromId: senderId,
      toId: props.targetId,
      fromInfo: {
        id: senderId,
        name: isHuman
          ? userInfoStore.userName || '我'
          : agentStore.agent?.name ?? m.sender_role ?? 'AI助手',
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
    }
  })

  const streamingRecords = streamingMessages
    .filter((s) => !s.message_id || !historicalMessages.some((m) => m.id === s.message_id))
    .map((s) => {
      const senderId = `agent_${s.sender_role ?? 'default'}`
      const runtimeState = (s.metadata?.runtime_state as string | undefined) ?? undefined
      const runtimeNodes = (s.metadata?.runtime_nodes as unknown[] | undefined) ?? undefined
      const displayContent =
        s.ui_status === 'thinking' ? `${s.sender_role || 'AI'} 正在思考...` : s.content

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
        runtimeState,
        runtimeNodes,
      }
    })

  return [...historicalRecords, ...streamingRecords]
})

watch(
  () => props.targetId,
  () => {
    newMsgCount.value = 0
  },
)

const handleLoadMore = async () => {
  const pageInfo = sessionStore.currentPageInfo
  if (!props.targetId || !pageInfo.hasMore) return
  await sessionStore.fetchMessages(props.targetId, {
    page: pageInfo.page + 1,
    page_size: 20,
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

watch(
  () => sessionStore.messageMap[props.targetId]?.length ?? 0,
  (newLen, oldLen) => {
    if (newLen > oldLen) {
      scrollToBottom()
    }
  },
)

watch(
  () => sessionStore.currentStreamingMessages,
  () => {
    const container = chatShowAreaRef.value
    if (container && sessionStore.currentStreamingMessages.length > 0) {
      container.scrollTop = container.scrollHeight
    }
  },
)

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

.chat-show-area::-webkit-scrollbar {
  width: 6px;
}

.chat-show-area::-webkit-scrollbar-track {
  background: transparent;
}

.chat-show-area::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.2);
  border-radius: 3px;
}

.load-more-row {
  display: flex;
  justify-content: center;
}

.load-more-btn {
  padding: 8px 18px;
  border-radius: 999px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  background: rgba(255, 255, 255, 0.6);
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
}

.load-more-btn:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.08));
  border-color: rgba(59, 130, 246, 0.4);
  color: #3b82f6;
  transform: translateY(-1px);
}

.loading-row {
  display: flex;
  width: 100%;
  justify-content: center;
  align-items: center;
}

.msg-item {
  display: flex;
  width: 100%;
}

.new-msg-count {
  position: sticky;
  bottom: 12px;
  align-self: center;
  padding: 8px 18px;
  border-radius: 999px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  color: #3b82f6;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.15);
}

.new-msg-count:hover {
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  color: #ffffff;
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.3);
}
</style>
