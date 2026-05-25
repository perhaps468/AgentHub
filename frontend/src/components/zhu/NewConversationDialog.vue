<template>
  <BaseDialog
    v-model="visible"
    title="新建对话"
    @confirm="confirmCreate"
  >
    <el-form label-position="top" class="create-conversation-form">
      <el-form-item label="会话类型">
        <el-radio-group v-model="newConvType">
          <el-radio value="single">单聊</el-radio>
          <el-radio value="group">群聊</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item :label="newConvType === 'single' ? '选择 Agent（单选）' : '选择 Agent（多选，至少 1 个）'">
        <div v-if="newConvType === 'single'" class="agent-picker-list">
          <label
            v-for="agent in agents"
            :key="agent.id"
            :class="['agent-picker-item', selectedAgentForConv === agent.id ? 'selected' : '']"
          >
            <input
              v-model="selectedAgentForConv"
              type="radio"
              name="single-agent"
              :value="agent.id"
            />
            <avatar :info="{ name: agent.name, avatar: agent.avatar }" size="32px" />
            <div class="agent-picker-meta">
              <span class="agent-picker-name">{{ agent.name }}</span>
              <span v-if="agent.platform" class="agent-platform-tag">{{ formatPlatformLabel(agent.platform) }}</span>
            </div>
          </label>
        </div>

        <div v-else class="agent-picker-list agent-picker-checkboxes">
          <label
            v-for="agent in agents"
            :key="agent.id"
            :class="['agent-picker-item', selectedAgentsForGroup.includes(agent.id) ? 'selected' : '']"
          >
            <input
              v-model="selectedAgentsForGroup"
              type="checkbox"
              :value="agent.id"
            />
            <avatar :info="{ name: agent.name, avatar: agent.avatar }" size="32px" />
            <div class="agent-picker-meta">
              <span class="agent-picker-name">{{ agent.name }}</span>
              <span v-if="agent.platform" class="agent-platform-tag">{{ formatPlatformLabel(agent.platform) }}</span>
            </div>
          </label>
        </div>
      </el-form-item>

      <el-form-item label="会话标题（可选）">
        <el-input
          v-model="newConvTitle"
          maxlength="48"
          :placeholder="getDefaultConvTitle()"
        />
      </el-form-item>

      <button class="link-to-agent-panel" type="button" @click="$emit('go-agent-panel')">
        去 Agent 列表添加或浏览更多 Agent →
      </button>
    </el-form>
  </BaseDialog>
</template>

<script lang="ts" setup>
import { computed, ref, watch } from 'vue'
import BaseDialog from './BaseDialog.vue'
import avatar from '@/veiws/img/avatar.vue'
import type { AgentPlatform, ConversationMode, SidebarAgent } from '@/types/agenthub'

const props = defineProps<{
  modelValue: boolean
  agents: SidebarAgent[]
  initialAgentId?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [payload: { mode: ConversationMode; title: string; agentId?: string; participantAgentIds?: string[] }]
  'go-agent-panel': []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const newConvType = ref<ConversationMode>('single')
const selectedAgentForConv = ref('')
const selectedAgentsForGroup = ref<string[]>([])
const newConvTitle = ref('')

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      if (props.initialAgentId) {
        newConvType.value = 'single'
        selectedAgentForConv.value = props.initialAgentId
      } else {
        // Reset selection when dialog opens
        selectedAgentForConv.value = ''
        selectedAgentsForGroup.value = []
        newConvTitle.value = ''
        newConvType.value = 'single'
      }
    }
  },
)

const canCreateConversation = computed(() => {
  if (newConvType.value === 'single') return !!selectedAgentForConv.value
  return selectedAgentsForGroup.value.length >= 1
})

const formatPlatformLabel = (platform?: AgentPlatform) => {
  const labels: Record<string, string> = {
    'claude-code': 'Claude',
    codex: 'Codex',
    opencode: 'OpenCode',
    custom: '自建',
  }
  return platform ? labels[platform] || platform : ''
}

const getDefaultConvTitle = () => {
  if (newConvType.value === 'single') {
    const agent = props.agents.find((a) => a.id === selectedAgentForConv.value)
    return agent ? `${agent.name} 对话` : '选择 Agent 后自动生成'
  }
  return '多 Agent 协作'
}

const confirmCreate = () => {
  if (!canCreateConversation.value) {
    return
  }
  const mode = newConvType.value
  const title = newConvTitle.value.trim() || getDefaultConvTitle()
  emit('confirm', {
    mode,
    title,
    agentId: mode === 'single' ? selectedAgentForConv.value : undefined,
    participantAgentIds: mode === 'group' ? [...selectedAgentsForGroup.value] : undefined,
  })
  visible.value = false
}
</script>

<style scoped>
.create-conversation-form {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.agent-picker-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 160px;
  overflow-y: auto;
}

.agent-picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border: 1px solid #ececec;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}

.agent-picker-item:hover,
.agent-picker-item.selected {
  border-color: #1a1a1a;
  background: #fafafa;
}

.agent-picker-item input {
  width: 14px;
  height: 14px;
  accent-color: #1677ff;
}

.agent-picker-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.agent-picker-name {
  color: #262626;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-platform-tag {
  flex: 0 0 auto;
  padding: 2px 6px;
  border-radius: 999px;
  background: #f5f5f5;
  color: #737373;
  font-size: 11px;
}

.link-to-agent-panel {
  align-self: flex-start;
  padding: 0;
  border: none;
  background: transparent;
  color: #737373;
  font-size: 12px;
  cursor: pointer;
}

.link-to-agent-panel:hover {
  color: #262626;
  text-decoration: underline;
}
</style>
