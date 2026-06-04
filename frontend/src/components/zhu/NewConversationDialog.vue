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

      <el-form-item :label="newConvType === 'single' ? '选择 Agent（单选）' : '选择协作 Agent（可选，默认为主 Agent）'">
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
          <!-- P6-7: Fixed primary agent card (always selected, disabled) -->
          <div v-if="primaryAgent" class="agent-picker-item primary-agent-card selected">
            <input type="checkbox" checked disabled />
            <avatar :info="{ name: primaryAgent.name, avatar: primaryAgent.avatar }" size="32px" />
            <div class="agent-picker-meta">
              <span class="agent-picker-name">{{ primaryAgent.name }}</span>
              <span class="primary-agent-badge">主 Agent</span>
            </div>
          </div>
          <div v-if="!primaryAgent" class="agent-picker-item primary-agent-card selected">
            <input type="checkbox" checked disabled />
            <avatar :info="{ name: '主 PM Agent', avatar: '' }" size="32px" />
            <div class="agent-picker-meta">
              <span class="agent-picker-name">主 PM Agent</span>
              <span class="primary-agent-badge">主 Agent</span>
            </div>
          </div>
          <label
            v-for="agent in agentsWithoutPrimary"
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

      <el-form-item label="工作空间（开发型会话必选）">
        <div class="workspace-picker">
          <!-- Mode toggle -->
          <div class="workspace-mode-toggle">
            <button
              type="button"
              :class="['mode-btn', workspaceMode === 'create' ? 'active' : '']"
              @click="onWorkspaceModeChange('create')"
            >
              创建新工作空间
            </button>
            <button
              type="button"
              :class="['mode-btn', workspaceMode === 'select' ? 'active' : '']"
              @click="onWorkspaceModeChange('select')"
            >
              选择已有工作空间
            </button>
          </div>

          <!-- Create mode -->
          <template v-if="workspaceMode === 'create'">
            <!-- Electron: use native folder picker -->
            <template v-if="isElectron">
              <input
                ref="folderInputRef"
                type="file"
                webkitdirectory
                class="hidden-folder-input"
                @change="onFolderSelected"
              />
              <div v-if="selectedWorkspacePath" class="workspace-selected">
                <span class="workspace-path-display">{{ formatShortPath(selectedWorkspacePath) }}</span>
                <button type="button" class="workspace-change-btn" @click="openFolderPicker">更换</button>
              </div>
              <button
                v-else
                type="button"
                class="workspace-select-btn"
                :disabled="workspaceCreating"
                @click="openFolderPicker"
              >
                <span v-if="workspaceCreating" class="loading-dots">创建中</span>
                <span v-else>选择工作空间文件夹</span>
              </button>
            </template>
            <!-- Browser: manual path input -->
            <template v-else>
              <el-input
                v-model="manualPathInput"
                placeholder="输入工作空间路径，如 D:\code\myproject"
                @keyup.enter="onManualPathSubmit"
              />
              <div v-if="selectedWorkspacePath" class="workspace-selected">
                <span class="workspace-path-display">{{ formatShortPath(selectedWorkspacePath) }}</span>
                <button type="button" class="workspace-change-btn" @click="selectedWorkspacePath = null; selectedWorkspaceId = null">清除</button>
              </div>
              <button
                v-else
                type="button"
                class="workspace-select-btn"
                :disabled="workspaceCreating || !manualPathInput.trim()"
                @click="onManualPathSubmit"
              >
                <span v-if="workspaceCreating" class="loading-dots">创建中</span>
                <span v-else>创建工作空间</span>
              </button>
              <p class="workspace-hint-tip">提示：在 Electron 桌面应用中可直接选择文件夹</p>
            </template>
          </template>

          <!-- Select existing mode -->
          <template v-else>
            <div v-if="workspacesLoading" class="workspace-loading">
              <span class="loading-dots">加载中</span>
            </div>
            <div v-else-if="existingWorkspaces.length === 0" class="workspace-empty-tip">
              暂无已创建的工作空间
            </div>
            <div v-else class="workspace-list">
              <label
                v-for="ws in existingWorkspaces"
                :key="ws.id"
                :class="['workspace-item', selectedWorkspaceId === ws.id ? 'selected' : '']"
              >
                <input
                  type="radio"
                  name="existing-workspace"
                  :value="ws.id"
                  :checked="selectedWorkspaceId === ws.id"
                  @change="onExistingWorkspaceSelect(ws)"
                />
                <div class="workspace-item-info">
                  <span class="workspace-item-name">{{ ws.name }}</span>
                  <span class="workspace-item-path">{{ ws.root_path }}</span>
                </div>
              </label>
            </div>
          </template>

          <p v-if="workspaceCreateError" class="workspace-error-tip">{{ workspaceCreateError }}</p>
        </div>
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
import { createWorkspace, fetchWorkspaceList } from '@/api/modules/workspace'
import type { AgentPlatform, ConversationMode, SidebarAgent, Workspace } from '@/types/agenthub'

// Detect if running in Electron
const isElectron = typeof window !== 'undefined' && window.navigator.userAgent.includes('Electron')

const props = defineProps<{
  modelValue: boolean
  agents: SidebarAgent[]
  primaryAgent?: SidebarAgent | null
  initialAgentId?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: [payload: { mode: ConversationMode; title: string; agentId?: string; participantAgentIds?: string[]; workspace_id?: string | null }]
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

// Task B: workspace selection via native folder picker
const folderInputRef = ref<HTMLInputElement | null>(null)
const selectedWorkspacePath = ref<string | null>(null)
const selectedWorkspaceId = ref<string | null>(null)
const workspaceCreating = ref(false)
const workspaceCreateError = ref('')

// For non-Electron browsers: manual path input
const manualPathInput = ref('')

// Task B+C-1: Workspace mode toggle (create new vs select existing)
const workspaceMode = ref<'create' | 'select'>('create')
const existingWorkspaces = ref<Workspace[]>([])
const workspacesLoading = ref(false)

// P6-7: Primary agent for group mode
const PRIMARY_AGENT_ID = 'primary_pm_agent'

const primaryAgent = computed(() => {
  return props.primaryAgent || null
})

const agentsWithoutPrimary = computed(() => {
  const primaryAgentId = primaryAgent.value?.id
  if (!primaryAgentId) return props.agents
  return props.agents.filter((a) => a.id !== primaryAgentId)
})

function openFolderPicker() {
  workspaceCreateError.value = ''
  folderInputRef.value?.click()
}

async function onFolderSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const files = input.files
  if (!files || files.length === 0) return

  const dirPath = (files[0] as File & { path?: string }).path
  if (!dirPath) {
    workspaceCreateError.value = '无法获取文件夹路径，请使用 Chrome/Edge 或升级 Electron 版本'
    return
  }

  await createWorkspaceFromPath(dirPath)
}

async function createWorkspaceFromPath(path: string) {
  workspaceCreating.value = true
  workspaceCreateError.value = ''
  selectedWorkspacePath.value = path

  try {
    const ws = await createWorkspace({ root_path: path })
    selectedWorkspaceId.value = ws.id
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err)
    workspaceCreateError.value = `创建工作空间失败：${msg}`
    selectedWorkspacePath.value = null
  } finally {
    workspaceCreating.value = false
  }
}

function onManualPathSubmit() {
  if (!manualPathInput.value.trim()) {
    workspaceCreateError.value = '请输入工作空间路径'
    return
  }
  createWorkspaceFromPath(manualPathInput.value.trim())
  manualPathInput.value = ''
}

function formatShortPath(path: string): string {
  // Always show the absolute path in full
  return path
}

// Task B+C-1: Load existing workspaces for selection
async function loadExistingWorkspaces() {
  if (workspacesLoading.value || existingWorkspaces.value.length > 0) return
  workspacesLoading.value = true
  try {
    existingWorkspaces.value = await fetchWorkspaceList()
  } catch (err) {
    console.error('Failed to load workspaces:', err)
  } finally {
    workspacesLoading.value = false
  }
}

function onWorkspaceModeChange(mode: 'create' | 'select') {
  workspaceMode.value = mode
  if (mode === 'select') {
    loadExistingWorkspaces()
  } else {
    // Clear selection when switching back to create mode
    selectedWorkspaceId.value = null
    selectedWorkspacePath.value = null
  }
}

function onExistingWorkspaceSelect(workspace: Workspace) {
  selectedWorkspaceId.value = workspace.id
  selectedWorkspacePath.value = workspace.root_path
  workspaceCreateError.value = ''
}

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      if (props.initialAgentId) {
        newConvType.value = 'single'
        selectedAgentForConv.value = props.initialAgentId
      } else {
        selectedAgentForConv.value = ''
        selectedAgentsForGroup.value = []
        newConvTitle.value = ''
        newConvType.value = 'single'
      }
      selectedWorkspaceId.value = null
      selectedWorkspacePath.value = null
      workspaceCreateError.value = ''
      // Reset workspace mode and clear cached list
      workspaceMode.value = 'create'
      existingWorkspaces.value = []
    }
  },
)

const canCreateConversation = computed(() => {
  // Task B+C-1: Workspace selection is now mandatory
  if (!selectedWorkspaceId.value) {
    return false
  }
  if (newConvType.value === 'single') {
    return !!selectedAgentForConv.value
  }
  // P6-7: Group mode always has the primary agent, so zero additional agents is allowed
  return true
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
  // Task B+C-1: Ensure workspace is selected before allowing creation
  if (!selectedWorkspaceId.value) {
    workspaceCreateError.value = '请先选择工作空间文件夹'
    return
  }
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
    workspace_id: selectedWorkspaceId.value,
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

.workspace-select {
  width: 100%;
}

.workspace-empty-tip {
  margin: 4px 0 0;
  color: #737373;
  font-size: 12px;
}

.hidden-folder-input {
  display: none;
}

.workspace-picker {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.workspace-mode-toggle {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.mode-btn {
  padding: 8px 16px;
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-btn:hover {
  border-color: rgba(59, 130, 246, 0.4);
  color: #3b82f6;
}

.mode-btn.active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.08));
  border-color: #3b82f6;
  color: #3b82f6;
  font-weight: 600;
}

.workspace-loading {
  padding: 20px;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.workspace-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 200px;
  overflow-y: auto;
  padding: 4px;
}

.workspace-list::-webkit-scrollbar {
  width: 6px;
}

.workspace-list::-webkit-scrollbar-track {
  background: transparent;
}

.workspace-list::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.12);
  border-radius: 3px;
}

.workspace-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid rgba(59, 130, 246, 0.12);
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.02), rgba(99, 102, 241, 0.01));
  cursor: pointer;
  transition: all 0.25s ease;
}

.workspace-item:hover {
  border-color: rgba(59, 130, 246, 0.3);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.06), rgba(99, 102, 241, 0.03));
}

.workspace-item.selected {
  border-color: #3b82f6;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.08));
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
}

.workspace-item input[type="radio"] {
  width: 18px;
  height: 18px;
  accent-color: #3b82f6;
  cursor: pointer;
  flex-shrink: 0;
}

.workspace-item-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.workspace-item-name {
  color: #1e293b;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspace-item-path {
  color: #94a3b8;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspace-select-btn {
  align-self: flex-start;
  padding: 8px 16px;
  border: 1px dashed #d1d5db;
  border-radius: 8px;
  background: #fafafa;
  color: #262626;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s;
}

.workspace-select-btn:hover:not(:disabled) {
  border-color: #1a1a1a;
  background: #f0f0f0;
}

.workspace-select-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.workspace-selected {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #f9f9f9;
}

.workspace-path-display {
  flex: 1;
  color: #262626;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.workspace-change-btn {
  flex: 0 0 auto;
  padding: 4px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  color: #737373;
  font-size: 12px;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s;
}

.workspace-change-btn:hover {
  border-color: #1a1a1a;
  color: #262626;
}

.workspace-error-tip {
  margin: 0;
  color: #ef4444;
  font-size: 12px;
}

.workspace-hint-tip {
  margin: 4px 0 0;
  color: #737373;
  font-size: 12px;
}

.loading-dots {
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

/* P6-7: Primary agent card in group mode */
.primary-agent-card {
  border-color: #3b82f6 !important;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(99, 102, 241, 0.08)) !important;
  box-shadow:
    0 0 0 2px rgba(59, 130, 246, 0.2),
    0 8px 24px rgba(59, 130, 246, 0.2) !important;
  transform: none !important;

  input[type="checkbox"] {
    opacity: 0.6;
  }

  &::before {
    opacity: 1 !important;
  }
}

.primary-agent-badge {
  display: inline-block;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #3b82f6, #6366f1);
  border-radius: 6px;
  letter-spacing: 0.03em;
  white-space: nowrap;
}
</style>
