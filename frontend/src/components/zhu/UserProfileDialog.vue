<template>
  <BaseDialog
    v-model="visible"
    title="编辑资料"
    @confirm="handleConfirm"
  >
    <div class="dialog-content">
      <div class="avatar-section">
        <div class="avatar-wrapper">
          <avatar :info="{ name: formData.name, avatar: formData.avatar }" size="80px" />
          <label class="avatar-upload-btn">
            <input type="file" accept="image/*" @change="handleAvatarChange" />
            <span>更换</span>
          </label>
        </div>
        <span class="avatar-name">{{ formData.name }}</span>
      </div>

      <div class="form-section">
        <label class="form-label">用户名</label>
        <el-input
          v-model="formData.name"
          placeholder="请输入用户名"
          clearable
        />
      </div>

      <div class="form-section">
        <label class="form-label">邮箱</label>
        <el-input v-model="formData.email" placeholder="请输入邮箱" clearable />
      </div>

      <div class="form-section">
        <label class="form-label">个人简介</label>
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

<style scoped>
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}

.avatar-wrapper {
  position: relative;
  display: inline-block;
}

.avatar-upload-btn {
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.6);
  color: #fff;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  cursor: pointer;
  white-space: nowrap;
}

.avatar-upload-btn input {
  display: none;
}

.avatar-upload-btn:hover {
  background: rgba(0, 0, 0, 0.8);
}

.avatar-name {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-size: 12px;
  font-weight: 500;
  color: #606266;
}
</style>
