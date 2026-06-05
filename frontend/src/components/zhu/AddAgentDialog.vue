<template>
  <BaseDialog v-model="visible" :title="isEdit ? '编辑 Agent' : '添加自建 Agent'" @confirm="confirmAdd">
    <el-form label-position="top" class="edit-profile-form">
      <el-form-item label="头像">
        <div class="avatar-picker">
          <div class="avatar-grid">
            <div
              v-for="img in availableImages"
              :key="img"
              class="avatar-option"
              :class="{ selected: form.avatar === img }"
              @click="form.avatar = img"
            >
              <img :src="img" :alt="img" />
              <div class="avatar-check">
                <el-icon><Check /></el-icon>
              </div>
            </div>
          </div>
        </div>
      </el-form-item>
      <el-form-item label="名称">
        <el-input v-model="form.name" maxlength="32" placeholder="例如：我的代码助手" />
      </el-form-item>
      <el-form-item label="模型">
        <el-select v-model="form.model" placeholder="请选择模型">
          <el-option
            v-for="model in availableModels"
            :key="model"
            :label="model"
            :value="model"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="能力标签">
        <el-checkbox-group v-model="form.capabilityTags" class="tag-grid">
          <el-checkbox
            v-for="tag in availableCapabilityTags"
            :key="tag"
            :label="tag"
            :value="tag"
          >
            {{ tag }}
          </el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <el-form-item label="简介（可选）">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          maxlength="120"
          placeholder="补充这个 Agent 的工作重点或适用场景"
        />
      </el-form-item>

      <div class="prompt-hint">
        系统提示词会根据名称、标签和简介自动生成，默认可使用全部工具。
      </div>
    </el-form>
  </BaseDialog>
</template>

<script lang="ts" setup>
import { computed, reactive, watch } from 'vue'

import { Check } from '@element-plus/icons-vue'

import type { AgentDraft, SidebarAgent } from '@/types/agenthub'

import BaseDialog from './BaseDialog.vue'

const props = withDefaults(defineProps<{
  modelValue: boolean
  availableModels: string[]
  availableCapabilityTags: string[]
  isEdit?: boolean
  editingAgent?: SidebarAgent | null
}>(), {
  availableModels: () => [],
  availableCapabilityTags: () => [],
  isEdit: false,
  editingAgent: null,
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [agent: AgentDraft]
  'confirm-edit': [agent: AgentDraft & { id: string }]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const availableImages = [
  '/msg1.png',
  '/msg6.png',
  '/msg9.png',
  '/msg7.png',
  '/msg4.png',
  '/msg2.png',
  '/msg8.png',
  '/msg5.png',
]


const form = reactive({
  name: '',
  model: '',
  capabilityTags: [] as string[],
  description: '',
  avatar: '',
})

function resetForm() {
  if (props.isEdit && props.editingAgent) {
    form.name = props.editingAgent.name
    form.model = props.editingAgent.model || ''
    form.capabilityTags = [...props.editingAgent.capabilityTags]
    form.description = props.editingAgent.description || ''
    form.avatar = props.editingAgent.avatar || ''
  } else {
    form.name = ''
    form.model = props.availableModels[0] || ''
    form.capabilityTags = []
    form.description = ''
    form.avatar = ''
  }
}

watch(
  () => visible.value,
  (val) => {
    if (!val) return
    resetForm()
  },
)

watch(
  () => props.availableModels,
  (models) => {
    if (!form.model && models.length > 0) {
      form.model = models[0]
    }
  },
  { immediate: true },
)

watch(
  () => props.editingAgent,
  () => {
    if (visible.value) {
      resetForm()
    }
  },
)

const confirmAdd = () => {
  const name = form.name.trim()
  const description = form.description.trim()

  if (!name || !form.model || form.capabilityTags.length === 0) {
    return
  }

  if (props.isEdit && props.editingAgent) {
    emit('confirm-edit', {
      id: props.editingAgent.id,
      name,
      model: form.model,
      capabilityTags: [...form.capabilityTags],
      description: description || undefined,
      avatar: form.avatar,
      platform: 'custom',
    })
  } else {
    emit('confirm', {
      name,
      model: form.model,
      capabilityTags: [...form.capabilityTags],
      description: description || undefined,
      avatar: form.avatar,
      platform: 'custom',
    })
  }
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

      &::before {
        display: none;
      }
    }

    .el-input__wrapper,
    .el-select__wrapper {
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

.tag-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

:deep(.el-checkbox) {
  margin-right: 0;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.05);
}

.prompt-hint {
  border-radius: 12px;
  padding: 12px 14px;
  background: rgba(59, 130, 246, 0.06);
  color: #475569;
  font-size: 12px;
  line-height: 1.5;
}

.avatar-picker {
  width: 100%;
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.avatar-option {
  position: relative;
  aspect-ratio: 1;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s ease;
  background: rgba(59, 130, 246, 0.05);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  &:hover {
    border-color: rgba(59, 130, 246, 0.4);
    transform: scale(1.05);
  }

  &.selected {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);

    .avatar-check {
      opacity: 1;
    }
  }

  .avatar-check {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #3b82f6;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s ease;

    .el-icon {
      color: white;
      font-size: 12px;
    }
  }
}

.avatar-picker {
  width: 100%;
}

.avatar-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.avatar-option {
  position: relative;
  aspect-ratio: 1;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s ease;
  background: rgba(59, 130, 246, 0.05);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  &:hover {
    border-color: rgba(59, 130, 246, 0.4);
    transform: scale(1.05);
  }

  &.selected {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3);

    .avatar-check {
      opacity: 1;
    }
  }

  .avatar-check {
    position: absolute;
    top: 4px;
    right: 4px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: #3b82f6;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s ease;

    .el-icon {
      color: white;
      font-size: 12px;
    }
  }
}
</style>
