<template>
  <div class="msg-box" :class="{ 'is-own': isOwn }">
    <template v-if="props.msg">
      <time-msg v-if="props.msg.isShowTime" :content="props.msg.createTime" class="msg-time" />
      <div v-if="props.msg.type === 'recall'" class="recall-msg">这条消息已撤回</div>
      <div v-else class="msg-box-wrapper">
        <Avatar :info="displayUser" size="40px" class="msg-avatar" :style="displayAvatarStyle" />
        <div class="msg-box-info">
          <div class="msg-user-row">
            <div v-if="!isOwn" class="msg-username">
              {{ displayUser?.name || '未知用户' }}
            </div>
            <div v-if="isGroup" class="msg-role">
              {{ roleLabel }}
            </div>
            <div v-if="props.msg.deliveryStatus === 'interrupted'" class="msg-status-badge interrupted">
              已中断
            </div>
            <div v-if="props.msg.isStreaming && props.msg.streamStatus === 'thinking'" class="msg-status-badge thinking">
              思考中...
            </div>
            <div v-if="props.msg.isStreaming && props.msg.streamStatus === 'streaming'" class="msg-status-badge streaming">
              <span class="streaming-dot"></span>
            </div>
          </div>
          <div class="msg-bubble-wrap">
            <msg_content :right="isOwn" :msg="props.msg" />
            <div class="msg-hover-actions">
              <button class="msg-hover-action" type="button" aria-label="引用" @click="handleQuote">
                <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M4 6h5M4 9h3M10 6h5M10 9h3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                </svg>
              </button>
              <span class="msg-hover-divider" aria-hidden="true"></span>
              <button class="msg-hover-action" type="button" aria-label="复制" @click="handleCopy">
                <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="5.25" y="3.25" width="7.5" height="9.5" rx="1.75" stroke="currentColor" stroke-width="1.5" />
                  <path d="M10.75 3.25V2.75C10.75 2.05964 10.1904 1.5 9.5 1.5H4.75C4.05964 1.5 3.5 2.05964 3.5 2.75V9.5C3.5 10.1904 4.05964 10.75 4.75 10.75H5.25" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { MessageSource } from '../../types/messageSource'
import { MessageType } from '../../types/messageType'
import { TextContentType } from '../../types/textContentType'
import { useAgentStore } from '../../store/module/useAgentStore'
import { useUserInfoStore } from '../../store/module/useUserStore'
import { useChatMsgStore } from '../../store/module/useChatMsgStore'
import { useToast } from '../useToast'
import Avatar from '../img/avatar.vue'
import msg_content from '../message-content/msg_content .vue'
import TimeMsg from '../message-content/TimeMsg.vue'

const props = defineProps({
  msg: Object,
  user: Object,
})

const userStore = useUserInfoStore()
const agentStore = useAgentStore()
const chatMsgStore = useChatMsgStore()
const showToast = useToast()
const isOwn = computed(() => props.msg?.fromId === userStore.userId)
const isGroup = computed(() => props.msg?.source === MessageSource.Group)
const displayUser = computed(() => props.user || props.msg?.fromInfo)

const displayAvatarStyle = computed(() => {
  const user = displayUser.value
  if (!user?.avatar) {
    return {
      background: 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)',
      color: '#fff',
    }
  }

  return undefined
})

const roleLabel = computed(() => agentStore.agent?.role ?? '成员')

const extractMessageText = (message) => {
  if (!message) return ''
  if (props.msg?.type !== MessageType.Text) {
    return message
  }

  try {
    const texts = JSON.parse(message)
    if (!Array.isArray(texts)) {
      return message
    }

    return texts
      .map((item) => {
        if (item?.type === TextContentType.At) {
          try {
            const atUser = JSON.parse(item.content)
            return `@${atUser.name ?? ''}`
          } catch {
            return `@${item.content ?? ''}`
          }
        }

        return item?.content ?? ''
      })
      .join('')
  } catch {
    return message
  }
}

const handleQuote = () => {
  if (!props.msg) return
  chatMsgStore.setReferenceMsg(props.msg)
  const composer = document.querySelector('.chat-input-area .msg-input-wrap textarea')
  if (composer) {
    composer.scrollIntoView({ behavior: 'smooth', block: 'center' })
    setTimeout(() => composer.focus(), 300)
  }
}

const handleCopy = async () => {
  const messageText = extractMessageText(props.msg?.message || '')
  await navigator.clipboard.writeText(messageText)
  showToast('复制成功')
}
</script>

<style scoped>
.msg-box {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
}

.msg-time {
  text-align: center;
  justify-content: center;
}

.msg-box-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.is-own .msg-box-wrapper {
  flex-direction: row-reverse;
}

.is-own .msg-avatar {
  margin-left: 0;
}

.recall-msg {
  margin-left: 52px;
  color: rgb(var(--text-muted));
  font-size: 12px;
}

.is-own .recall-msg {
  margin-left: 0;
  margin-right: 52px;
  text-align: right;
}

.msg-avatar {
  margin-top: 2px;
}

.msg-box-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.msg-user-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.msg-username {
  color: rgb(var(--text-color));
  font-size: 14px;
  font-weight: 600;
}

.msg-role {
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid rgb(var(--border-color));
  color: rgb(var(--text-secondary));
  font-size: 11px;
  line-height: 1.4;
}

.is-own .msg-role {
  border-color: rgba(var(--primary-color), 0.9);
  color: rgb(var(--text-color));
  background: rgb(var(--surface-color), 0.1);
}

.msg-status-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;
}

.msg-status-badge.interrupted {
  border: 1px solid rgba(215, 96, 96, 0.3);
  color: rgb(215, 96, 96);
  background: rgba(215, 96, 96, 0.08);
}

.msg-status-badge.thinking {
  border: 1px solid rgba(var(--primary-color), 0.3);
  color: rgb(var(--primary-color));
  background: rgba(var(--primary-color), 0.08);
}

.msg-status-badge.streaming {
  border: 1px solid rgba(var(--primary-color), 0.3);
  background: rgba(var(--primary-color), 0.08);
  padding: 4px 8px;
}

.streaming-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgb(var(--primary-color));
  animation: pulse 1.5s ease-in-out infinite;
}

.msg-bubble-wrap {
  position: relative;
  display: inline-flex;
  overflow: visible;
}

.msg-bubble-wrap:hover .msg-hover-actions,
.msg-hover-actions:focus-within {
  opacity: 1;
  transform: translateY(0);
  pointer-events: auto;
}

.msg-hover-actions {
  position: absolute;
  right: -12px;
  bottom: -31px;
  display: inline-flex;
  align-items: center;
  gap: 0;
  padding: 2px 4px;
  border-radius: 10px;
  border: 1px solid rgba(var(--border-color), 0.72);
  background: rgba(255, 255, 255, 0.88);
  box-shadow:
    0 8px 20px rgba(15, 23, 42, 0.1),
    0 1px 2px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(16px);
  opacity: 0;
  transform: translateY(2px);
  pointer-events: none;
  transition: opacity 0.15s ease, transform 0.15s ease;
  z-index: 4;
}

.is-own .msg-hover-actions {
  right: -12px;
  left: auto;
}

.msg-hover-action {
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  background: transparent;
  color: rgb(var(--text-secondary));
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color 0.15s ease, opacity 0.15s ease;
}

.msg-hover-action svg {
  width: 13px;
  height: 13px;
}

.msg-hover-action:hover,
.msg-hover-action:focus-visible {
  color: rgb(var(--primary-color));
  background: rgba(var(--primary-color), 0.08);
  border-radius: 6px;
  outline: none;
}

.msg-hover-divider {
  width: 1px;
  height: 12px;
  margin: 0 2px;
  background: rgba(var(--text-secondary), 0.22);
  flex-shrink: 0;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(0.8);
  }
}
</style>
