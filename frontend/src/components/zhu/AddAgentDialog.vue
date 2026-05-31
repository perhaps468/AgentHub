<template>
  <BaseDialog v-model="visible" title="添加自建 Agent" @confirm="confirmAdd">
    <el-form label-position="top" class="edit-profile-form">
      <el-form-item label="名称">
        <el-input
          v-model="newAgentName"
          maxlength="32"
          placeholder="例如：我的代码助手"
        />
      </el-form-item>
      <el-form-item label="能力标签（逗号分隔）">
        <el-input
          v-model="newAgentTags"
          maxlength="80"
          placeholder="代码生成, 测试, 文档"
        />
      </el-form-item>
      <el-form-item label="简介（可选）">
        <el-input
          v-model="newAgentDesc"
          type="textarea"
          :rows="3"
          maxlength="80"
          placeholder="简要描述 Agent 能力"
        />
      </el-form-item>
    </el-form>
  </BaseDialog>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'

import type { SidebarAgent } from '@/types/agenthub'
import BaseDialog from './BaseDialog.vue'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [agent: SidebarAgent]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

const newAgentName = ref('')
const newAgentTags = ref('')
const newAgentDesc = ref('')

const confirmAdd = () => {
  const tags = newAgentTags.value
    .split(/[,\uFF0C]/)
    .map((tag) => tag.trim())
    .filter(Boolean)

  const newAgent: SidebarAgent = {
    id: `custom_${Date.now()}`,
    name: newAgentName.value.trim() || '自定义 Agent',
    avatar: '',
    capabilityTags: tags.length > 0 ? tags : ['自定义'],
    description: newAgentDesc.value.trim() || undefined,
    platform: 'custom',
  }

  emit('confirm', newAgent)
  visible.value = false
}
</script>

<style scoped>
.edit-profile-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.edit-profile-form :deep(.el-form-item) {
  margin-bottom: 0;
}
</style>
