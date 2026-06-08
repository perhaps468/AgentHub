<template>
  <div class="msg" :class="{ 'is-own': props.right }">
    <div
      class="msg-content"
      :class="{ 'is-own': props.right }"
      @contextmenu.prevent="handleContextMenu"
    >
      <div v-if="referenceInfo" class="msg-reference">
        <span class="msg-reference-icon">"</span>
        <span class="msg-reference-text">引用: {{ referenceInfo }}</span>
      </div>

      <TextMsg v-if="props.msg.type === MessageType.Text" :msg="props.msg" :right="props.right" />
      <EmojiMsg v-else-if="props.msg.type === MessageType.Emoji" :src="props.msg.message" />
      <call_msg v-else-if="props.msg.type === MessageType.Call" :msg="props.msg" :right="props.right" />
      <PptMsg
        v-else-if="props.msg.type === MessageType.PptData"
        :msg="props.msg"
        :right="props.right"
        @preview="handlePreviewPpt"
      />
    </div>

    <teleport to="body">
      <transition name="menu-fade">
        <div
          v-if="menuVisible"
          class="ctx-menu"
          :style="menuStyle"
          @click.stop
        >
          <button class="ctx-menu-item" type="button" @click="handlerSetReference">
            <span class="ctx-icon">"</span>
            <span>引用</span>
          </button>
          <button class="ctx-menu-item" type="button" @click="handlerCopy">
            <span class="ctx-icon">⧉</span>
            <span>复制</span>
          </button>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'

import { useChatMsgStore } from '../../store/module/useChatMsgStore'
import { useSessionStore } from '../../store/module/useSessionStore'
import type { PptPreviewModel } from '../../types/agenthub'
import type { MessageRecord } from '../../types/message'
import { MessageType } from '../../types/messageType'
import { TextContentType } from '../../types/textContentType'
import call_msg from '../message-content/callMsg.vue'
import EmojiMsg from '../message-content/emoji-msg.vue'
import PptMsg from '../message-content/PptMsg.vue'
import TextMsg from '../message-content/text-msg.vue'

const msgStore = useChatMsgStore()
const sessionStore = useSessionStore()

type ContextMessage = Partial<MessageRecord> & {
  id: string
  type: string
  message: string
  payload?: Record<string, unknown>
  content?: string
  metadata?: Record<string, unknown>
}

const props = withDefaults(
  defineProps<{
    msg: ContextMessage
    right?: boolean
  }>(),
  {
    right: false,
  },
)

const referenceInfo = computed(() => {
  const ref = props.msg.metadata?.reference as { content?: unknown; sender?: string } | undefined
  if (!ref) return null

  const raw = ref.content
  const text = typeof raw === 'string' ? raw : raw != null ? JSON.stringify(raw) : ''
  const display = text.slice(0, 60) + (text.length > 60 ? '...' : '')
  return display || null
})

const menuVisible = ref(false)
const menuStyle = ref<Record<string, string>>({})

let closeMenuHandler: (() => void) | null = null

const handleContextMenu = (e: MouseEvent) => {
  menuStyle.value = {
    position: 'fixed',
    left: `${e.clientX}px`,
    top: `${e.clientY}px`,
  }

  menuVisible.value = true

  nextTick(() => {
    const menu = document.querySelector('.ctx-menu') as HTMLElement | null
    if (!menu) return

    const rect = menu.getBoundingClientRect()
    const vw = window.innerWidth
    const vh = window.innerHeight

    let left = e.clientX
    let top = e.clientY

    if (rect.right > vw) {
      left = vw - rect.width - 8
    }
    if (rect.bottom > vh) {
      top = vh - rect.height - 8
    }

    menuStyle.value = {
      position: 'fixed',
      left: `${left}px`,
      top: `${top}px`,
    }
  })

  closeMenuHandler = () => {
    menuVisible.value = false
    closeMenuHandler = null
  }
  document.addEventListener('click', closeMenuHandler, { once: true })
  document.addEventListener('contextmenu', closeMenuHandler, { once: true })
}

const handlerSetReference = () => {
  msgStore.setReferenceMsg(props.msg as MessageRecord)
  menuVisible.value = false
}

const handlerCopy = () => {
  let msg = ''
  if (props.msg.type === MessageType.Text) {
    try {
      const texts = JSON.parse(props.msg?.message)
      texts.forEach((item: { type: string; content: string }) => {
        if (item.type === TextContentType.At) {
          msg += '@' + JSON.parse(item.content).name
        } else {
          msg += item.content
        }
      })
    } catch {
      msg = props.msg?.message
    }
  } else {
    msg = props.msg?.message || ''
  }
  navigator.clipboard.writeText(msg)
  menuVisible.value = false
}

const handlePreviewPpt = (payload: PptPreviewModel) => {
  sessionStore.streamState.setPreviewPpt(payload)
}

onBeforeUnmount(() => {
  if (closeMenuHandler) {
    document.removeEventListener('click', closeMenuHandler)
    document.removeEventListener('contextmenu', closeMenuHandler)
  }
})
</script>

<style scoped>
.msg {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  max-width: min(680px, 100%);
}

.msg.is-own {
  align-items: flex-end;
}

.msg-content {
  position: relative;
  width: fit-content;
  max-width: 100%;
  padding: 12px 14px;
  border-radius: 18px;
  border: 1px solid rgb(var(--border-color));
  border-color: rgba(var(--primary-color), 0.45);
  background: rgb(var(--surface-color));
  color: rgb(var(--text-color));
  font-size: 14px;
  line-height: 1.7;
  word-break: break-word;
}

.msg-content.is-own {
  background: rgba(var(--primary-color), 0.1);
  border-color: rgba(var(--primary-color), 0);
}

.msg-reference {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding-bottom: 8px;
  margin-bottom: 6px;
  border-bottom: 1px solid rgba(var(--border-color), 0.5);
}

.msg-reference-icon {
  font-size: 16px;
  font-weight: 700;
  color: rgb(var(--primary-color));
  line-height: 1.5;
  flex-shrink: 0;
}

.msg-reference-text {
  font-size: 12px;
  color: rgb(var(--text-secondary));
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

<style>
.ctx-menu {
  position: fixed;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  min-width: 148px;
  padding: 6px;
  border-radius: 12px;
  background: rgb(var(--surface-color));
  border: 1px solid rgb(var(--border-color));
  box-shadow:
    0 4px 6px -1px rgba(15, 23, 42, 0.06),
    0 10px 24px rgba(15, 23, 42, 0.08),
    0 0 0 0.5px rgba(15, 23, 42, 0.04);
  user-select: none;
}

.ctx-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 8px;
  color: rgb(var(--text-color));
  font-size: 14px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s ease, color 0.12s ease;
}

.ctx-menu-item:hover {
  background: rgb(var(--primary-soft));
  color: rgb(var(--primary-strong));
}

.ctx-icon {
  font-size: 15px;
  font-weight: 600;
  line-height: 1;
  flex-shrink: 0;
}

.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.14s ease, transform 0.14s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
  transform: scale(0.94);
  transform-origin: top left;
}
</style>
