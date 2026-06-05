<template>
  <Teleport to="body">
    <Transition name="dialog-pop">
      <div v-if="modelValue" class="dialog-overlay" @click.self="handleClose">
        <div class="dialog-container">
          <!-- 装饰背景 -->
          <div class="dialog-bg-gradient"></div>

          <div class="dialog-header">
            <div class="header-left">
              <span class="header-icon">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </span>
              <span class="dialog-title">{{ title }}</span>
            </div>
            <button class="dialog-close" type="button" @click="handleClose">
              <span class="close-icon">
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                  <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
                </svg>
              </span>
            </button>
          </div>

          <div class="dialog-body">
            <slot />
          </div>

          <div class="dialog-footer">
            <slot name="footer">
              <button class="dialog-btn secondary" type="button" @click="handleClose">取消</button>
              <button class="dialog-btn primary" type="button" @click="handleConfirm">
                <span class="btn-text">确定</span>
                <span class="btn-shine"></span>
              </button>
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

<style scoped lang="less">
/* 遮罩层 */
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  padding: 20px;
}

/* 弹窗容器 */
.dialog-container {
  position: relative;
  width: 700px;
  max-width: 95vw;
  max-height: 85vh;
  background: #fff;
  border-radius: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow:
    0 25px 50px -12px rgba(59, 130, 246, 0.25),
    0 0 0 1px rgba(59, 130, 246, 0.1);
}

/* 装饰渐变背景 */
.dialog-bg-gradient {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 140px;
  opacity: 0.06;
  pointer-events: none;
}

/* 头部 */
.dialog-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  flex-shrink: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.04) 0%, rgba(99, 102, 241, 0.02) 100%);
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);

  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 120px;
    height: 3px;
    border-radius: 0 3px 3px 0;
  }
}

.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.header-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  color: #fff;
  box-shadow:
    0 4px 14px rgba(59, 130, 246, 0.35),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  animation: pulse-glow 3s ease-in-out infinite;
}

@keyframes pulse-glow {
  0%, 100% {
    box-shadow:
      0 4px 14px rgba(59, 130, 246, 0.35),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
  }
  50% {
    box-shadow:
      0 4px 20px rgba(59, 130, 246, 0.5),
      0 0 30px rgba(59, 130, 246, 0.2),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);
  }
}

.dialog-title {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #1e293b 0%, #3b82f6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 关闭按钮 */
.dialog-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: none;
  background: rgba(59, 130, 246, 0.08);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  .close-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    color: #64748b;
    transition: all 0.25s ease;
  }

  &:hover {
    background: rgba(239, 68, 68, 0.1);
    transform: rotate(90deg) scale(1.05);

    .close-icon {
      color: #ef4444;
    }
  }

  &:active {
    transform: rotate(90deg) scale(0.95);
  }
}

/* 内容区 */
.dialog-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  min-height: 0;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.02) 0%, transparent 100%);

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #3b82f6, #6366f1);
    border-radius: 3px;
    opacity: 0.5;

    &:hover {
      opacity: 0.8;
    }
  }
}

/* 底部 */
.dialog-footer {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 18px 24px;
  flex-shrink: 0;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.03) 0%, rgba(99, 102, 241, 0.01) 100%);
  border-top: 1px solid rgba(59, 130, 246, 0.08);

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 24px;
    right: 24px;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.15), transparent);
  }
}

/* 按钮 */
.dialog-btn {
  position: relative;
  min-width: 100px;
  padding: 12px 24px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  &.secondary {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(99, 102, 241, 0.06));
    color: #64748b;
    border: 1px solid rgba(59, 130, 246, 0.15);

    &:hover {
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(99, 102, 241, 0.1));
      color: #3b82f6;
      border-color: rgba(59, 130, 246, 0.3);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
    }

    &:active {
      transform: translateY(0) scale(0.98);
    }
  }

  &.primary {
    background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
    color: #fff;
    box-shadow:
      0 4px 14px rgba(59, 130, 246, 0.4),
      inset 0 1px 0 rgba(255, 255, 255, 0.2);

    .btn-text {
      position: relative;
      z-index: 1;
    }

    .btn-shine {
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 255, 255, 0.4),
        transparent
      );
      transition: left 0.5s ease;
    }

    &:hover {
      transform: translateY(-3px);
      box-shadow:
        0 8px 25px rgba(59, 130, 246, 0.5),
        0 0 40px rgba(59, 130, 246, 0.2),
        inset 0 1px 0 rgba(255, 255, 255, 0.3);

      .btn-shine {
        left: 100%;
      }
    }

    &:active {
      transform: translateY(0) scale(0.98);
    }
  }
}

/* 弹窗动画 */
.dialog-pop-enter-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);

  .dialog-container {
    transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
  }
}

.dialog-pop-leave-active {
  transition: all 0.25s ease-out;

  .dialog-container {
    transition: all 0.25s ease-out;
  }
}

.dialog-pop-enter-from {
  opacity: 0;

  .dialog-container {
    transform: scale(0.8) translateY(30px) rotateX(10deg);
    opacity: 0;
    filter: blur(10px);
  }
}

.dialog-pop-leave-to {
  opacity: 0;

  .dialog-container {
    transform: scale(0.9) translateY(15px);
    opacity: 0;
  }
}
</style>
