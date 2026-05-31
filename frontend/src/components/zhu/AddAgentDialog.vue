<template>
  <BaseDialog
    v-model="visible"
    title="添加自建 Agent"
    @confirm="confirmAdd"
  >
    <el-form label-position="top" class="edit-profile-form">
      <el-form-item label="名称">
        <el-input v-model="newAgentName" maxlength="32" placeholder="例如：我的代码助手" />
      </el-form-item>
      <el-form-item label="能力标签（逗号分隔）">
        <el-input v-model="newAgentTags" maxlength="80" placeholder="代码生成, 测试, 文档" />
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
import BaseDialog from './BaseDialog.vue'
import type { SidebarAgent } from '@/types/agenthub'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [agent: SidebarAgent]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const newAgentName = ref('')
const newAgentTags = ref('')
const newAgentDesc = ref('')

const confirmAdd = () => {
  const tags = newAgentTags.value
    .split(/[,，]/)
    .map((t) => t.trim())
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

<style scoped lang="less">
.edit-profile-form {
  display: flex;
  flex-direction: column;
  gap: 18px;

  :deep(.el-form-item) {
    margin-bottom: 0;

    .el-form-item__label {
      font-size: 13px;
      font-weight: 600;
      color: #3b82f6;
      padding-bottom: 10px;
      position: relative;

      &::before {
        display: none;
      }
    }

    .el-input__wrapper {
      border-radius: 12px;
      box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.15);
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      padding: 12px 16px;

      &:hover {
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
      }

      &:focus-within {
        box-shadow:
          0 0 0 2px rgba(59, 130, 246, 0.3),
          0 4px 14px rgba(59, 130, 246, 0.15);
      }
    }

    .el-textarea__inner {
      border-radius: 12px;
      box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.15);
      transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
      padding: 14px 16px;

      &:hover {
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
      }

      &:focus {
        box-shadow:
          0 0 0 2px rgba(59, 130, 246, 0.3),
          0 4px 14px rgba(59, 130, 246, 0.15);
      }
    }
  }
}
</style>
