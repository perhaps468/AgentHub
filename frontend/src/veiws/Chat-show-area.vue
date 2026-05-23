<template>
  <div class="chat-show-area" ref="chatShowAreaRef">
    <!-- Load more -->
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

import { useSessionStore } from '../store/module/useSessionStore'
import { useUserInfoStore } from '../store/module/useUserStore'
import type { ChatMessage } from '../types/agenthub'
import eventBus from '../utils/EventBus'
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
const userInfoStore = useUserInfoStore()
const chatShowAreaRef = ref<HTMLElement>()
const newMsgCount = ref(0)

// Map ChatMessage (backend format) → MessageRecord (Msg component format)
const msgRecord = computed(() => {
  const messages: ChatMessage[] = sessionStore.messageMap[props.targetId] ?? []
  return messages.map((m) => {
    const isHuman = m.sender_type === 'human'
    const senderId = isHuman ? userInfoStore.userId : `agent_${m.sender_role ?? 'default'}`
    return {
      id: m.id,
      fromId: senderId,
      toId: props.targetId,
      fromInfo: {
        id: senderId,
        name: isHuman ? (userInfoStore.userName || '我') : (m.sender_role ?? 'AI助手'),
        avatar: null,
        type: isHuman ? 'User' : 'Agent',
        badge: null,
      },
      message: m.content,
      referenceMsg: m.reference ?? null,
      atUser: null,
      isShowTime: false,
      type: m.content_type === 'text' ? 'text' : m.content_type,
      source: 'User',
      createTime: m.created_at,
      updateTime: m.created_at,
    }
  })
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
      const container = chatShowAreaRef.value
      const isNearBottom =
        container && container.scrollTop + container.clientHeight >= container.scrollHeight - 80
      if (isNearBottom) {
        scrollToBottom()
      } else {
        newMsgCount.value += newLen - oldLen
      }
    }
  },
)

onMounted(() => {
  scrollToBottom()
})
</script>

<style scoped>
.chat-show-area {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
  padding: 20px 24px;
  background: rgb(var(--surface-muted));
}

.load-more-row {
  display: flex;
  justify-content: center;
}

.load-more-btn {
  padding: 6px 16px;
  border-radius: 999px;
  border: 1px solid rgb(var(--border-color));
  background: rgb(var(--surface-color));
  color: rgb(var(--text-secondary));
  font-size: 13px;
  cursor: pointer;
}

.load-more-btn:hover {
  background: rgb(var(--primary-soft));
  color: rgb(var(--primary-strong));
}

.msg-item {
  display: flex;
  width: 100%;
}

.loading-row {
  display: flex;
  width: 100%;
  justify-content: center;
  align-items: center;
}

.new-msg-count {
  position: sticky;
  bottom: 8px;
  align-self: center;
  padding: 6px 14px;
  border-radius: 999px;
  border: 1px solid rgba(var(--primary-color), 0.24);
  background: rgba(255, 255, 255, 0.96);
  color: rgb(var(--primary-strong));
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
</style>
