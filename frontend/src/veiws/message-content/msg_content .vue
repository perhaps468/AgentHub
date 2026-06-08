<template>
  <div class="msg" :class="{ 'is-own': props.right }">
    <div
      class="msg-content"
      :class="{ 'is-own': props.right }"
    >

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
import { computed} from 'vue'

import { useChatMsgStore } from '../../store/module/useChatMsgStore'
import { useSessionStore } from '../../store/module/useSessionStore'
import type { PptPreviewModel } from '../../types/agenthub'
import type { MessageRecord } from '../../types/message'
import { MessageType } from '../../types/messageType'
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


const handlePreviewPpt = (payload: PptPreviewModel) => {
  sessionStore.streamState.setPreviewPpt(payload)
}


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

</style>
