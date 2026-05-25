<template>
  <Teleport to="body">
    <Transition name="dialog-fade">
      <div v-if="modelValue" class="dialog-overlay" @click.self="handleClose">
        <div class="dialog-container">
          <div class="dialog-header">
            <span class="dialog-title">{{ title }}</span>
            <button class="dialog-close" type="button" @click="handleClose">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="dialog-body">
            <slot />
          </div>

          <div class="dialog-footer">
            <slot name="footer">
              <button class="dialog-btn" type="button" @click="handleClose">取消</button>
              <button class="dialog-btn primary" type="button" @click="handleConfirm">确定</button>
            </slot>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean
  title: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: []
  close: []
}>()

const handleClose = () => {
  emit('update:modelValue', false)
  emit('close')
}

const handleConfirm = () => {
  emit('confirm')
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: rgba(0, 0, 0, 0.4);
}

.dialog-container {
  position: relative;
  width:500px;
  height: 500px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.dialog-title {
  font-size: 13px;
  font-weight: 500;
  color: #1a1a1a;
}

.dialog-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: none;
  background: transparent;
  color: #8c8c8c;
  cursor: pointer;
  border-radius: 4px;
  transition: background-color 0.2s, color 0.2s;
}

.dialog-close:hover {
  background: #f5f5f5;
  color: #1a1a1a;
}

.dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  padding: 6px 8px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.dialog-btn {
  min-width: 48px;
  padding: 4px 10px;
  border: 1px solid #e0e0e0;
  border-radius: 5px;
  background: #fff;
  color: #262626;
  font-size: 12px;
  line-height: 1.5;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s;
}

.dialog-btn:hover {
  background: #f5f5f5;
  border-color: #c0c0c0;
}

.dialog-btn.primary {
  border-color: #1a1a1a;
  background: #1a1a1a;
  color: #fff;
}

.dialog-btn.primary:hover {
  background: #333;
}

.dialog-btn.primary:active {
  background: #000;
}

/* Transition */
.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-fade-enter-active .dialog-container,
.dialog-fade-leave-active .dialog-container {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}

.dialog-fade-enter-from .dialog-container,
.dialog-fade-leave-to .dialog-container {
  transform: scale(0.95);
  opacity: 0;
}
</style>
