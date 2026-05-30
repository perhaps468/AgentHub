<template>
  <BaseDialog
    v-model="visible"
    title="编辑资料"
    @confirm="handleConfirm"
  >
    <div class="dialog-content">
      <div class="avatar-section">
        <div class="avatar-wrapper">
          <div class="avatar-container">
            <avatar :info="{ name: formData.name, avatar: formData.avatar }" size="80px" />
            <label class="avatar-upload-overlay">
              <input type="file" accept="image/*" @change="handleAvatarChange" />
              <div class="upload-content">
                <el-icon :size="32" class="upload-icon">
                  <PictureRounded />
                </el-icon>
                <span class="upload-text">更换头像</span>
              </div>
            </label>
          </div>
        </div>
        <span class="avatar-name">{{ formData.name }}</span>
      </div>

      <div class="form-section">
        <label class="form-label">
          <svg class="label-icon" width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <circle cx="12" cy="7" r="4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          用户名
        </label>
        <el-input
          v-model="formData.name"
          placeholder="请输入用户名"
          clearable
        />
      </div>

      <div class="form-section">
        <label class="form-label">
          <svg class="label-icon" width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <polyline points="22,6 12,13 2,6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          邮箱
        </label>
        <el-input v-model="formData.email" placeholder="请输入邮箱" clearable />
      </div>

      <div class="form-section">
        <label class="form-label">
          <svg class="label-icon" width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <polyline points="14,2 14,8 20,8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <line x1="16" y1="13" x2="8" y2="13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <line x1="16" y1="17" x2="8" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
          个人简介
        </label>
        <el-input
          v-model="formData.bio"
          type="textarea"
          :rows="3"
          placeholder="AgentHub 用户"
          maxlength="200"
          show-word-limit
        />
      </div>
    </div>
  </BaseDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BaseDialog from './BaseDialog.vue'
import avatar from '@/veiws/img/avatar.vue'
import type { SidebarUser } from '@/types/agenthub'
import { PictureRounded } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: boolean
  user: SidebarUser
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [data: Partial<SidebarUser>]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const formData = ref<SidebarUser>({
  id: '',
  name: '',
  avatar: '',
  email: '',
  bio: '',
})

watch(
  () => props.user,
  (newUser) => {
    if (newUser) {
      formData.value = { ...newUser }
    }
  },
  { immediate: true },
)

const handleAvatarChange = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) {
    const reader = new FileReader()
    reader.onload = (e) => {
      const result = e.target?.result as string
      formData.value.avatar = result
    }
    reader.readAsDataURL(file)
  }
}

const handleConfirm = () => {
  emit('confirm', {
    name: formData.value.name,
    avatar: formData.value.avatar,
    email: formData.value.email,
    bio: formData.value.bio,
  })
  visible.value = false
}
</script>

<style scoped lang="less">
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 头像区域 */
.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 20px 0;
  position: relative;
}

.avatar-wrapper {
  position: relative;
  display: inline-block;
}

.avatar-container {
  position: relative;
  border-radius: 50%;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: -3px;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #6366f1, #8b5cf6);
    opacity: 0.4;
    z-index: -1;
    animation: avatar-glow 3s ease-in-out infinite;
  }

  @keyframes avatar-glow {
    0%, 100% {
      opacity: 0.4;
      transform: scale(1);
    }
    50% {
      opacity: 0.6;
      transform: scale(1.03);
    }
  }
}

.avatar-upload-overlay {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: linear-gradient(
    135deg,
    rgba(59, 130, 246, 0.9) 0%,
    rgba(99, 102, 241, 0.95) 100%
  );
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transform: scale(0.8);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);

  input {
    display: none;
  }
}

.avatar-container:hover .avatar-upload-overlay {
  opacity: 1;
  transform: scale(1);
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-align: center;
}

.upload-icon {
  color: #fff;
  animation: icon-bounce 2s ease-in-out infinite;
}

@keyframes icon-bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

.upload-text {
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.avatar-name {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.01em;
  background: linear-gradient(135deg, #1e293b, #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* 表单区域 */
.form-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  font-weight: 700;
  color: #3b82f6;
  padding-left: 4px;
  letter-spacing: 0.02em;
  display: flex;
  align-items: center;
  gap: 8px;
}

.label-icon {
  flex-shrink: 0;
}

/* Element Plus 输入框样式覆盖 */
:deep(.el-input) {
  .el-input__wrapper {
    border-radius: 14px;
    box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.12), inset 0 1px 2px rgba(0, 0, 0, 0.02);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    padding: 14px 18px;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.02), rgba(99, 102, 241, 0.01));

    &:hover {
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2), inset 0 1px 2px rgba(0, 0, 0, 0.02);
    }

    &.is-focus {
      box-shadow:
        0 0 0 3px rgba(59, 130, 246, 0.25),
        0 8px 24px rgba(59, 130, 246, 0.15),
        inset 0 1px 2px rgba(0, 0, 0, 0.02);
      background: #fff;
    }
  }

  .el-input__inner {
    font-size: 14px;
    color: #1e293b;

    &::placeholder {
      color: #94a3b8;
    }
  }

  .el-input__clear {
    color: #64748b;
    transition: all 0.2s ease;

    &:hover {
      color: #3b82f6;
    }
  }
}

:deep(.el-textarea) {
  .el-textarea__inner {
    border-radius: 14px;
    box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.12), inset 0 1px 2px rgba(0, 0, 0, 0.02);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    padding: 14px 18px;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.02), rgba(99, 102, 241, 0.01));
    font-size: 14px;
    color: #1e293b;

    &::placeholder {
      color: #94a3b8;
    }

    &:hover {
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2), inset 0 1px 2px rgba(0, 0, 0, 0.02);
    }

    &:focus {
      box-shadow:
        0 0 0 3px rgba(59, 130, 246, 0.25),
        0 8px 24px rgba(59, 130, 246, 0.15),
        inset 0 1px 2px rgba(0, 0, 0, 0.02);
      background: #fff;
    }
  }

  .el-input__count {
    background: transparent;
    color: #94a3b8;
    font-size: 11px;

    .el-input__count-inner {
      background: transparent;
    }
  }
}
</style>
