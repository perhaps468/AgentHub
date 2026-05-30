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

      <el-form-item label="工作空间（开发型会话必选）">
        <div class="workspace-picker">
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
          <p v-if="workspaceCreateError" class="workspace-error-tip">{{ workspaceCreateError }}</p>
        </div>
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
import { createWorkspace } from '@/api/modules/workspace'
import type { AgentPlatform, ConversationMode, SidebarAgent } from '@/types/agenthub'

// Detect if running in Electron
const isElectron = typeof window !== 'undefined' && window.navigator.userAgent.includes('Electron')

const props = defineProps<{
  modelValue: boolean
  agents: SidebarAgent[]
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
</style>
