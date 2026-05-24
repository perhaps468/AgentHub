<template>
  <el-dialog
    v-model="visible"
    title="新建对话"
    width="520px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div class="dialog-content">
      <div class="form-section">
        <label class="form-label">会话类型</label>
        <el-radio-group v-model="formData.conversationType" class="type-radio-group">
          <el-radio value="single-agent" size="large">
            <div class="radio-content">
              <span class="radio-icon">💬</span>
              <div>
                <div class="radio-title">单聊</div>
                <div class="radio-desc">与一个 Agent 对话</div>
              </div>
            </div>
          </el-radio>
          <el-radio value="group" size="large">
            <div class="radio-content">
              <span class="radio-icon">👥</span>
              <div>
                <div class="radio-title">群聊</div>
                <div class="radio-desc">多个 Agent 协作</div>
              </div>
            </div>
          </el-radio>
        </el-radio-group>
      </div>

      <div class="form-section">
        <label class="form-label">
          选择 Agent
          <span v-if="formData.conversationType === 'single-agent'" class="label-hint">（单选）</span>
          <span v-else class="label-hint">（多选）</span>
        </label>
        <div class="agent-list">
          <button
            v-for="agent in agents"
            :key="agent.id"
            class="agent-item"
            :class="{ selected: isAgentSelected(agent.id) }"
            type="button"
            @click="toggleAgent(agent.id)"
          >
            <avatar :info="{ name: agent.name, avatar: agent.avatar }" size="40px" />
            <div class="agent-info">
              <div class="agent-name">{{ agent.name }}</div>
              <div class="agent-tags">
                <span
                  v-for="(tag, idx) in agent.capabilityTags.slice(0, 2)"
                  :key="idx"
                  class="agent-tag"
                >
                  {{ tag }}
                </span>
                <span v-if="agent.capabilityTags.length > 2" class="agent-tag-more">
                  +{{ agent.capabilityTags.length - 2 }}
                </span>
              </div>
            </div>
            <span v-if="isAgentSelected(agent.id)" class="check-icon">✓</span>
          </button>
        </div>
        <button class="add-custom-agent-btn" type="button" @click="handleAddCustomAgent">
          + 添加自建 Agent
        </button>
      </div>

      <div class="form-section">
        <label class="form-label">会话标题（可选）</label>
        <el-input
          v-model="formData.title"
          :placeholder="titlePlaceholder"
          clearable
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :disabled="!canConfirm" @click="handleConfirm">
          创建
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { SidebarAgent } from '@/types/agenthub'
import avatar from '@/veiws/img/avatar.vue'

const props = defineProps<{
  modelValue: boolean
  agents: SidebarAgent[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [data: {
    conversationType: 'single-agent' | 'group'
    agentIds: string[]
    title?: string
  }]
  'add-custom-agent': []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const formData = ref<{
  conversationType: 'single-agent' | 'group'
  selectedAgentIds: string[]
  title: string
}>({
  conversationType: 'single-agent',
  selectedAgentIds: [],
  title: '',
})

const titlePlaceholder = computed(() => {
  if (formData.value.conversationType === 'single-agent') {
    const agent = props.agents.find(a => a.id === formData.value.selectedAgentIds[0])
    return agent ? `${agent.name} 对话` : 'Agent 对话'
  }
  return '多 Agent 协作'
})

const canConfirm = computed(() => {
  return formData.value.selectedAgentIds.length > 0
})

const isAgentSelected = (agentId: string) => {
  return formData.value.selectedAgentIds.includes(agentId)
}

const toggleAgent = (agentId: string) => {
  if (formData.value.conversationType === 'single-agent') {
    formData.value.selectedAgentIds = [agentId]
  } else {
    const index = formData.value.selectedAgentIds.indexOf(agentId)
    if (index > -1) {
      formData.value.selectedAgentIds.splice(index, 1)
    } else {
      formData.value.selectedAgentIds.push(agentId)
    }
  }
}


const handleClose = () => {
  visible.value = false
  resetForm()
}

const handleConfirm = () => {
  if (!canConfirm.value) return

  emit('confirm', {
    conversationType: formData.value.conversationType,
    agentIds: formData.value.selectedAgentIds,
    title: formData.value.title || undefined,
  })
  visible.value = false
  resetForm()
}

const resetForm = () => {
  formData.value = {
    conversationType: 'single-agent',
    selectedAgentIds: [],
    title: '',
  }
}

watch(() => formData.value.conversationType, () => {
  formData.value.selectedAgentIds = []
})
</script>

<style scoped>
.dialog-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding: 4px 0;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: rgb(var(--text-color));
}

.label-hint {
  font-size: 13px;
  font-weight: 400;
  color: rgb(var(--text-secondary));
}

.type-radio-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.type-radio-group :deep(.el-radio) {
  margin-right: 0;
  padding: 14px 16px;
  border: 1px solid rgb(var(--border-color));
  border-radius: 10px;
  background: transparent;
  transition: all 0.2s;
}

.type-radio-group :deep(.el-radio:hover) {
  border-color: rgb(var(--primary-color));
  background: rgb(var(--primary-soft));
}

.type-radio-group :deep(.el-radio.is-checked) {
  border-color: rgb(var(--primary-color));
  background: rgb(var(--primary-soft));
}

.radio-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.radio-icon {
  font-size: 24px;
  line-height: 1;
}

.radio-title {
  font-size: 15px;
  font-weight: 600;
  color: rgb(var(--text-color));
  margin-bottom: 2px;
}

.radio-desc {
  font-size: 13px;
  color: rgb(var(--text-secondary));
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
  padding: 2px;
}

.agent-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border: 1px solid rgb(var(--border-color));
  border-radius: 10px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.agent-item:hover {
  border-color: rgb(var(--primary-color));
  background: rgb(var(--surface-muted));
}

.agent-item.selected {
  border-color: rgb(var(--primary-color));
  background: rgb(var(--primary-soft));
}

.agent-info {
  flex: 1;
  min-width: 0;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--text-color));
  margin-bottom: 6px;
}

.agent-tags {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.agent-tag {
  padding: 2px 8px;
  border-radius: 4px;
  background: rgb(var(--surface-muted));
  color: rgb(var(--text-secondary));
  font-size: 12px;
  white-space: nowrap;
}

.agent-tag-more {
  font-size: 12px;
  color: rgb(var(--text-muted));
}

.check-icon {
  font-size: 18px;
  color: rgb(var(--primary-strong));
  font-weight: bold;
}

.add-custom-agent-btn {
  width: 100%;
  padding: 10px;
  border: 1px dashed rgb(var(--border-color));
  border-radius: 8px;
  background: transparent;
  color: rgb(var(--primary-strong));
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.add-custom-agent-btn:hover {
  border-color: rgb(var(--primary-color));
  background: rgb(var(--primary-soft));
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 8px;
}

:deep(.el-input__wrapper) {
  border-radius: 8px;
}
</style>
