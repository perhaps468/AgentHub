<template>
  <div>
  <el-dialog
    v-model="visible"
    title="编辑资料"
    width="200px"
    :fullscreen="false"
    :modal="true" 
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="dialog-content">
      <div class="avatar-section">
        <avatar :info="{ name: formData.name, avatar: formData.avatar }" size="80px" />
        <span>{{formData.name}}</span>
        <el-button size="small" text>更换头像</el-button>
      </div>

      <div class="form-section">
        <label class="form-label">用户名</label>
        <el-input
          v-model="formData.name"
          placeholder="请输入用户名"
          clearable
          class="el-input__wrapper"
        />
      </div>

      <div class="form-section">
        <label class="form-label">邮箱</label>
        <el-input v-model="formData.email" placeholder="请输入邮箱" clearable class="el-input__wrapper"/>
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
          class="el-input__wrapper"
        />
      </div>
      <div class="dialog-footer">
        <el-button @click="handleClose" class="el-button">取消</el-button>
        <el-button type="primary" @click="handleConfirm">保存</el-button>
      </div>
    </div>
  </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch ,watchEffect} from 'vue'

import type { SidebarUser } from '@/types/agenthub'
import avatar from '@/veiws/img/avatar.vue'

const props = defineProps<{
  modelValue: boolean
  user: SidebarUser
  // showMask:boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:showMask': [value: boolean] 
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
watchEffect(() => {
  console.log('visible 实时变化:', visible.value)
  console.log('formDat',formData.value);
  console.log('showMask',props.showMask);
})

const handleClose = () => {
  visible.value = false
  // emit('update:showMask', false)
}

const handleConfirm = () => {
  emit('confirm', {
    name: formData.value.name,
    email: formData.value.email,
    bio: formData.value.bio,
  })
  visible.value = false
  // emit('update:showMask', false)
}
</script>

<style scoped>
.dialog-content {
  display: flex;
  flex-direction: column;
  background-color: white;
  gap: 30px;
  margin-top: 300px;
  width: 400px;
  height: 400px;
  margin-left: 400px;
  font-size: 20px;
  border-radius: 10px;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 12px 0 4px;
}

.form-section {
  display: flex;
  gap: 8px;
  margin-left: 10px;
  flex-direction: row;
  align-items: center;
  justify-content: center;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
}

.dialog-footer {
  display: flex;
  justify-content:flex-end;
  gap: 20px;
  padding-right: 10px;
}

:deep(.el-dialog) {
  border-radius: 12px;
  margin: 0;
}

:deep(.el-dialog__header) {
  padding: 20px 20px 16px;
  border-bottom: 1px solid #f0f0f0;
}

:deep(.el-dialog__title) {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

:deep(.el-dialog__body) {
  padding: 20px;
}

:deep(.el-dialog__footer) {
  padding: 16px 20px;
  border-top: 1px solid #f0f0f0;
}

:deep(.el-input__wrapper) {
  border-radius: 6px;
  box-shadow: 0 0 0 1px #dcdfe6 inset;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c0c4cc inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
}

:deep(.el-textarea__inner) {
  border-radius: 6px;
  border: 1px solid #dcdfe6;
}

:deep(.el-textarea__inner:hover) {
  border-color: #c0c4cc;
}

:deep(.el-textarea__inner:focus) {
  border-color: #409eff;
}

:deep(el-button) {
  border-radius: 6px;
  padding: 3px 8px;
  font-size: 14px;
  font-weight: 400;
  cursor: pointer;
}


:deep(.el-input__wrapper) {
  min-height: 30px;
  width: 300px;
}




:deep(el-button:hover) {
  color: #409eff;
  border-color: #c6e2ff;
  background-color: #ecf5ff;
}



:deep(.el-buttont:hover) {
  color: #409eff;
  background-color: #ecf5ff;
}
</style>
