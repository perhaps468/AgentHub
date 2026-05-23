<template>
  <el-dialog
    v-model="visible"
    title="添加自建 Agent"
    width="480px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="dialog-content">
      <div class="form-section">
        <label class="form-label">Agent 名称 <span class="required">*</span></label>
        <el-input
          v-model="formData.name"
          placeholder="请输入 Agent 名称"
          clearable
        />
      </div>

      <div class="form-section">
        <label class="form-label">头像 URL</label>
        <el-input
          v-model="formData.avatar"
          placeholder="https://example.com/avatar.png"
          clearable
        />
      </div>

      <div class="form-section">
        <label class="form-label">能力标签 <span class="required">*</span></label>
        <div class="tags-input-wrapper">
          <div v-if="formData.capabilityTags.length > 0" class="tags-display">
            <span
              v-for="(tag, idx) in formData.capabilityTags"
              :key="idx"
              class="tag-item"
            >
              {{ tag }}
              <button type="button" class="tag-remove" @click="removeTag(idx)">×</button>
            </span>
          </div>
          <div class="tag-input-row">
            <el-input
              v-model="currentTag"
              placeholder="输入标签后按回车添加"
              size="small"
              @keyup.enter="addTag"
            />
            <el-button size="small" @click="addTag">添加</el-button>
          </div>
        </div>
        <p class="form-hint">例如：代码生成、需求分析、测试、文档</p>
      </div>

      <div class="form-section">
        <label class="form-label">描述</label>
        <el-input
          v-model="formData.description"
          type="textarea"
          :rows="3"
          placeholder="简要描述 Agent 的功能和特点"
          maxlength="200"
          show-word-limit
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :disabled="!canConfirm" @click="handleConfirm">
          添加
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { SidebarAgent } from '@/types/agenthub'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [data: Omit<SidebarAgent, 'id'>]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const formData = ref<{
  name: string
  avatar: string
  capabilityTags: string[]
  description: string
}>({
  name: '',
  avatar: '',
  capabilityTags: [],
  description: '',
})

const currentTag = ref('')

const canConfirm = computed(() => {
  return formData.value.name.trim() !== '' && formData.value.capabilityTags.length > 0
})

const addTag = () => {
  const tag = currentTag.value.trim()
  if (tag && !formData.value.capabilityTags.includes(tag)) {
    formData.value.capabilityTags.push(tag)
    currentTag.value = ''
  }
}

const removeTag = (index: number) => {
  formData.value.capabilityTags.splice(index, 1)
}

const handleClose = () => {
  visible.value = false
  resetForm()
}

const handleConfirm = () => {
  if (!canConfirm.value) return

  emit('confirm', {
    name: formData.value.name.trim(),
    avatar: formData.value.avatar.trim() || '',
    capabilityTags: formData.value.capabilityTags,
    description: formData.value.description.trim(),
    platform: 'custom',
    isCustom: true,
  })
  visible.value = false
  resetForm()
}

const resetForm = () => {
  formData.value = {
    name: '',
    avatar: '',
    capabilityTags: [],
    description: '',
  }
  currentTag.value = ''
}
</script>

<style scoped>
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 4px 0;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: rgb(var(--text-color));
}

.required {
  color: #f56c6c;
}

.form-hint {
  margin: 0;
  font-size: 12px;
  color: rgb(var(--text-muted));
}

.tags-input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tags-display {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgb(var(--primary-soft));
  color: rgb(var(--primary-strong));
  font-size: 13px;
}

.tag-remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.1);
  color: inherit;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.tag-remove:hover {
  background: rgba(0, 0, 0, 0.2);
}

.tag-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.tag-input-row :deep(.el-input) {
  flex: 1;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}
</style>
