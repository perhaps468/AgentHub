<template>
  <div class="chat-input-area">
    <!-- Reference bar -->
    <div v-if="referenceMsg" class="reference-msg">
      <div class="reference-copy">
        <svg class="ref-icon" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4 10h12M10 4l6 6-6 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div class="ref-content">
          <span class="reference-label">{{ referenceMsg.from }}</span>
          <span class="reference-text">{{ referenceMsg.text }}</span>
        </div>
      </div>
      <button class="reference-clear" type="button" aria-label="取消引用" @click="clearRef">
        <svg viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </button>
    </div>

    <!-- Main composer -->
    <div class="composer-row">

      <!-- Input editor -->
      <div class="composer-editor-wrap">
        <Input
          ref="msgInputRef"
          v-model:value="msgContent"
          :handlerSubmitMsg="handlerSubmitMsg"
          placeholder="输入消息..."
          @send="handlerSubmitMsg"
          @structured-change="handleComposerPayload"
        />
      </div>

      <!-- Send button -->
      <button
        type="button"
        class="send-btn"
        aria-label="发送消息"
        @click="handlerSubmitMsg"
      >
       ➤
      </button>
    </div>

    <!-- Emoji panel -->
    <transition name="emoji-slide">
      <div v-if="showEmoji" class="emoji-panel">
        <div class="emoji-grid">
          <button
            v-for="e in emojis"
            :key="e.icon"
            type="button"
            class="emoji-item"
            :title="e.name"
            @click="insertEmoji(e.icon)"
          >
            {{ e.icon }}
          </button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import emojis from '../utils/emoji/emoji'
import Input from './input-content/input.vue'

const props = defineProps<{
  sessionId: string
  disabled?: boolean
}>()

const emit = defineEmits<{
<<<<<<< Updated upstream
  send: [content: string]
=======
  send: [payload: ComposerSubmitPayload]
  'selection-change': [agents: ComposerAgent[]]
>>>>>>> Stashed changes
}>()

const msgContent = ref('')
const showEmoji = ref(false)
const referenceMsg = ref<{ from: string; text: string } | null>(null)
const msgInputRef = ref<any>(null)

const canSend = computed(() => msgContent.value.toString().trim().length > 0)

const clearRef = () => {
  referenceMsg.value = null
}

<<<<<<< Updated upstream
const handlerSubmitMsg = () => {
  if (!canSend.value || props.disabled) return
  const text = msgContent.value.trim()
  emit('send', text)
  msgContent.value = ''
=======
const handleComposerPayload = (payload: ComposerSubmitPayload) => {
  msgContent.value = payload.text
  selectedAgents.value = payload.selectedAgents
  emit('selection-change', payload.selectedAgents)
}

const clearComposerSelection = () => {
  selectedAgents.value = []
  emit('selection-change', [])
}

const handlerSubmitMsg = (payload?: ComposerSubmitPayload) => {
  const nextPayload = payload ?? msgInputRef.value?.getStructuredValue?.()
  if (!nextPayload || props.disabled) return
  handleComposerPayload(nextPayload)
  if (!nextPayload.text.trim()) return
  emit('send', nextPayload)
  msgContent.value = ''
  clearComposerSelection()
  msgInputRef.value?.clear?.()
>>>>>>> Stashed changes
  referenceMsg.value = null
}

const insertEmoji = (emoji: string) => {
  msgInputRef.value?.insertEmoji?.(emoji)
  showEmoji.value = false
}
</script>

<style scoped>
.chat-input-area {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0;
  background: rgb(var(--surface-color));
}

/* Reference bar */
.reference-msg {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid rgb(var(--border-color));
  background: rgb(var(--surface-muted));
}

.reference-copy {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.ref-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  margin-top: 2px;
  color: rgb(var(--primary-color));
}

.ref-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.reference-label {
  color: rgb(var(--primary-color));
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}

.reference-text {
  color: rgb(var(--text-secondary));
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.reference-clear {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  color: rgb(var(--text-muted));
  transition: all 0.15s ease;
}

.reference-clear svg {
  width: 14px;
  height: 14px;
}

.reference-clear:hover {
  color: rgb(var(--danger-color));
  background: rgba(239, 68, 68, 0.08);
}

/* Composer row */
.composer-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 16px;
  background: rgb(var(--surface-color));
}

/* Toolbar */
.composer-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  padding-bottom: 4px;
}

.tool-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm);
  color: rgb(var(--text-secondary));
  transition: all 0.15s ease;
}

.tool-btn svg {
  width: 18px;
  height: 18px;
}

.tool-btn:hover {
  color: rgb(var(--primary-color));
  background: rgb(var(--primary-soft));
}

/* Editor wrapper */
.composer-editor-wrap {
  flex: 1;
  min-width: 0;
}

/* Send button */
.send-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 45px;
  font-size: 20px;
  height: 45px;
  border-radius: var(--radius-sm);
  background: rgb(var(--primary-color));
  color: #fff;
  cursor: pointer;
  transition: all 0.18s ease;
}


.send-btn:hover {
  background: rgb(var(--primary-strong));
  transform: scale(1.05);
}

.send-btn.active:active {
  transform: scale(0.95);
}

/* Emoji panel */
.emoji-panel {
  position: absolute;
  left: 16px;
  bottom: calc(100% + 10px);
  z-index: 20;
  border-radius: var(--radius-md);
  border: 1px solid rgb(var(--border-color));
  background: rgb(var(--surface-color));
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.emoji-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 0;
  padding: 10px;
  gap: 4px;
}

.emoji-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  aspect-ratio: 1;
  border-radius: var(--radius-sm);
  font-size: 20px;
  line-height: 1;
  transition: all 0.12s ease;
  cursor: pointer;
}

.emoji-item:hover {
  background: rgb(var(--primary-soft));
  transform: scale(1.15);
}

.emoji-item:active {
  transform: scale(0.92);
}

/* Emoji panel animation */
.emoji-slide-enter-active,
.emoji-slide-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.emoji-slide-enter-from,
.emoji-slide-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
  transform-origin: bottom left;
}

@media (max-width: 720px) {
  .composer-row {
    flex-wrap: wrap;
  }

  .composer-toolbar {
    order: 1;
  }

  .composer-editor-wrap {
    order: 2;
    flex: 1 1 100%;
  }

  .send-btn {
    order: 3;
  }
}
</style>
