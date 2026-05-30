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
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span>去 Agent 列表添加或浏览更多</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
          <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
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

<style scoped lang="less">
.create-conversation-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-top: 4px;

  :deep(.el-form-item) {
    margin-bottom: 0;

    .el-form-item__label {
      font-size: 13px;
      font-weight: 700;
      color: #3b82f6;
      padding-bottom: 12px;
      letter-spacing: 0.02em;

      &::before {
        display: none;
      }
    }

    .el-radio-group {
      display: flex;
      gap: 8px;
    }

    .el-radio {
      margin-right: 0;
      padding: 12px 20px;
      border-radius: 12px;
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.04), rgba(99, 102, 241, 0.02));
      border: 1px solid rgba(59, 130, 246, 0.12);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);

      .el-radio__input {
        .el-radio__inner {
          border-radius: 50%;
          border-color: #93c5fd;
          width: 18px;
          height: 18px;
          transition: all 0.25s ease;

          &::after {
            width: 8px;
            height: 8px;
            background-color: #fff;
            transition: all 0.25s ease;
          }
        }

        &.is-checked .el-radio__inner {
          background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
          border-color: #3b82f6;
          box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
        }
      }

      .el-radio__label {
        font-size: 14px;
        font-weight: 600;
        color: #64748b;
        transition: color 0.2s ease;
        padding-left: 8px;
      }

      &.is-checked {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.08));
        border-color: #3b82f6;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.12);

        .el-radio__label {
          color: #3b82f6;
          font-weight: 700;
        }
      }

      &:hover:not(.is-checked) {
        border-color: rgba(59, 130, 246, 0.3);
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(99, 102, 241, 0.04));
      }
    }

    .el-input__wrapper {
      border-radius: 14px;
      box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.12), inset 0 1px 2px rgba(0, 0, 0, 0.02);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      padding: 14px 18px;
      background: linear-gradient(135deg, rgba(59, 130, 246, 0.02), rgba(99, 102, 241, 0.01));

      .el-input__inner {
        font-size: 14px;
        color: #1e293b;
      }

      &:hover {
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2), inset 0 1px 2px rgba(0, 0, 0, 0.02);
      }

      &:focus-within {
        box-shadow:
          0 0 0 3px rgba(59, 130, 246, 0.25),
          0 8px 24px rgba(59, 130, 246, 0.15),
          inset 0 1px 2px rgba(0, 0, 0, 0.02);
        background: #fff;
      }
    }
  }
}

.agent-picker-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  max-height: 220px;
  width: 100%;
  overflow-y: auto;
  padding: 4px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(59, 130, 246, 0.12);
    border-radius: 3px;
    opacity: 0.5;

    &:hover {
      opacity: 0.8;
    }
  }
}

.agent-picker-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.02), rgba(99, 102, 241, 0.01));
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, #3b82f6, #6366f1);
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  &:hover {
    border-color: rgba(59, 130, 246, 0.35);
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(99, 102, 241, 0.04));
    transform: translateY(-3px) scale(1.02);
    box-shadow:
      0 8px 20px rgba(59, 130, 246, 0.15),
      0 2px 8px rgba(59, 130, 246, 0.1);

    &::before {
      opacity: 1;
    }
  }

  &.selected {
    border-color: #3b82f6;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(99, 102, 241, 0.08));
    box-shadow:
      0 0 0 2px rgba(59, 130, 246, 0.2),
      0 8px 24px rgba(59, 130, 246, 0.2);
    transform: translateY(-3px) scale(1.02);

    &::before {
      opacity: 1;
    }

    .agent-picker-name {
      color: #3b82f6;
      font-weight: 700;
    }
  }

  input[type="radio"],
  input[type="checkbox"] {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
    accent-color: #3b82f6;
    cursor: pointer;
    filter: drop-shadow(0 2px 4px rgba(59, 130, 246, 0.25));
    transition: transform 0.2s ease;

    &:hover {
      transform: scale(1.1);
    }
  }
}

.agent-picker-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.agent-picker-name {
  color: #1e293b;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: all 0.2s ease;
}

.link-to-agent-panel {
  display: flex;
  align-items: center;
  gap: 8px;
  align-self: flex-start;
  padding: 12px 20px;
  margin-top: 8px;
  border: 1px dashed rgba(59, 130, 246, 0.3);
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.04), rgba(99, 102, 241, 0.02));
  color: #64748b;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.2), transparent);
    border-radius: 50%;
    transform: translate(-50%, -50%);
    transition: all 0.4s ease;
  }

  svg {
    transition: transform 0.3s ease;
  }

  &:hover {
    color: #3b82f6;
    border-color: #3b82f6;
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.06));
    transform: translateX(6px);
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);

    &::before {
      width: 200px;
      height: 200px;
    }

    svg {
      transform: translateX(4px);
    }
  }

  &:active {
    transform: translateX(6px) scale(0.98);
  }
}
</style>
