<template>
  <div class="chat-input-area">
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

    <div v-if="selectedAgents.length > 0" class="selected-agent-strip">
      <span class="selected-agent-label">已选 Agent</span>
      <div class="selected-agent-list">
        <span
          v-for="agent in selectedAgents"
          :key="agent.id"
          class="selected-agent-pill"
        >
          <span class="selected-agent-dot" :class="`status-${agent.status}`"></span>
          <span class="selected-agent-name">@{{ agent.name }}</span>
        </span>
      </div>
    </div>

    <div class="composer-row">
      <div class="composer-editor-wrap">
        <Input
          ref="msgInputRef"
          v-model:value="msgContent"
          :handlerSubmitMsg="handlerSubmitMsg"
          :session-agent-options="props.sessionAgentOptions"
          placeholder="输入消息..."
          @send="handlerSubmitMsg"
          @structured-change="handleComposerPayload"
        />
      </div>
    </div>

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

import type { ComposerAgent, ComposerSubmitPayload, SessionAgentOption } from '../types/agenthub'
import emojis from '../utils/emoji/emoji'
import Input from './input-content/input.vue'

const props = defineProps<{
  sessionId: string
  disabled?: boolean
  sessionAgentOptions?: SessionAgentOption[]
}>()

const emit = defineEmits<{
  send: [payload: ComposerSubmitPayload]
  'selection-change': [agents: ComposerAgent[]]
}>()

const msgContent = ref('')
const showEmoji = ref(false)
const referenceMsg = ref<{ from: string; text: string } | null>(null)
const msgInputRef = ref<any>(null)
const selectedAgents = ref<ComposerAgent[]>([])

const canSend = computed(() => msgContent.value.toString().trim().length > 0)

const clearRef = () => {
  referenceMsg.value = null
}

const handleComposerPayload = (payload: ComposerSubmitPayload) => {
  msgContent.value = payload.text
  selectedAgents.value = payload.selectedAgents
  emit('selection-change', payload.selectedAgents)
}

const clearComposerSelection = () => {
  selectedAgents.value = []
  emit('selection-change', [])
}

const getStructuredValue = () => msgInputRef.value?.getStructuredValue?.()

const insertAgentChip = (agent: ComposerAgent) => {
  msgInputRef.value?.insertAgentChip?.(agent)
  const payload = getStructuredValue()
  if (payload) {
    handleComposerPayload(payload)
  }
}

const clearComposer = () => {
  msgContent.value = ''
  clearComposerSelection()
  msgInputRef.value?.clear?.()
}

const handlerSubmitMsg = (payload?: ComposerSubmitPayload) => {
  const nextPayload = payload ?? getStructuredValue()
  if (!nextPayload || props.disabled) return
  handleComposerPayload(nextPayload)
  if (!nextPayload.text.trim()) return
  emit('send', nextPayload)
  msgContent.value = ''
  clearComposerSelection()
  msgInputRef.value?.clear?.()
  referenceMsg.value = null
}

const insertEmoji = (emoji: string) => {
  msgInputRef.value?.insertEmoji?.(emoji)
  showEmoji.value = false
}

defineExpose({
  getStructuredValue,
  insertAgentChip,
  clear: clearComposer,
})
</script>

<style scoped>
.chat-input-area {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0;
  background: rgb(var(--surface-color));
}

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

.composer-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 12px 80px;
  background: rgb(var(--surface-color));
}

.selected-agent-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 80px 0;
  background: rgb(var(--surface-color));
}

.selected-agent-label {
  flex-shrink: 0;
  color: rgb(var(--text-muted));
  font-size: 12px;
  font-weight: 600;
}

.selected-agent-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  min-width: 0;
}

.selected-agent-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(0, 112, 243, 0.1);
  color: rgb(var(--primary-color));
  font-size: 12px;
  line-height: 1.2;
}

.selected-agent-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.selected-agent-dot.status-online {
  background: #22c55e;
}

.selected-agent-dot.status-busy {
  background: #f59e0b;
}

.selected-agent-dot.status-offline {
  background: #94a3b8;
}

.selected-agent-name {
  white-space: nowrap;
}

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

.composer-editor-wrap {
  flex: 1;
  min-width: 0;
}

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
}
</style>
