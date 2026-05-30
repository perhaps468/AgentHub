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
      <Input
        ref="msgInputRef"
        v-model:value="msgContent"
        :handlerSubmitMsg="handlerSubmitMsg"
        placeholder="输入消息..."
        @send="handlerSubmitMsg"
      />

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
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

import Input from './input-content/input.vue'

const props = defineProps<{
  sessionId: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  send: [content: string]
}>()

const msgContent = ref('')
const referenceMsg = ref<{ from: string; text: string } | null>(null)
const msgInputRef = ref<any>(null)

const canSend = computed(() => msgContent.value.toString().trim().length > 0)

const clearRef = () => {
  referenceMsg.value = null
}

const handlerSubmitMsg = () => {
  if (!canSend.value || props.disabled) return
  const text = msgContent.value.trim()
  emit('send', text)
  msgContent.value = ''
  referenceMsg.value = null
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
  gap: 12px;
  padding: 12px 16px;
  background: rgb(var(--surface-color));
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
  border-radius: 10px;
  background: rgb(var(--primary-color));
  color: #fff;
  cursor: pointer;
  transition: all 0.18s ease;
}


.send-btn:hover {
  background: rgb(var(--primary-strong));
  transform: scale(1.05);
}

@media (max-width: 720px) {
  .composer-row {
    flex-wrap: wrap;
  }

  Input {
    order: 1;
    flex: 1 1 100%;
  }

  .send-btn {
    order: 2;
  }
}
</style>
