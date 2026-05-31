<template>
  <div class="workspace">
    <div class="glow-orb glow-orb-1"></div>
    <div class="glow-orb glow-orb-2"></div>
    <div class="glow-orb glow-orb-3"></div>
    <div class="grid-pattern"></div>

    <div class="glass-container" :class="{ 'sidebar-collapsed': isCollapsed }">
      <LeftSidebarArea
        :show-left="showLeft"
        :is-collapsed="isCollapsed"
        :current-user="currentUser"
        :active-panel="activeSidebarPanel"
        :show-user-popover="showUserPopover"
        :search-value="searchValue"
        :agent-search-value="agentSearchValue"
        :filtered-sessions="filteredSessions"
        :current-session-id="sessionStore.currentSessionId || ''"
        :is-loading-list="sessionStore.isLoadingList"
        :agents="sidebarAgents"
        :filtered-agents="filteredAgentList"
        :selected-agent-id="selectedAgentId"
        :format-time="formatTime"
        @update:activePanel="activeSidebarPanel = $event"
        @update:showUserPopover="showUserPopover = $event"
        @update:searchValue="searchValue = $event"
        @update:agentSearchValue="agentSearchValue = $event"
        @new-session="showNewConversationDialog = true"
        @select-session="selectSession"
        @toggle-pin="togglePin"
        @toggle-archive="toggleArchive"
        @add-agent="showAddAgentDialog = true"
        @select-agent="handleSelectAgent"
        @delete-session="handleDeleteSession"
        @edit-profile="handleEditProfile"
        @logout="handlerLogout"
        @toggle-collapse="isCollapsed = !isCollapsed"
      />

      <ChatWorkspace
        :current-session="sessionStore.currentSession"
        :current-session-id="sessionStore.currentSessionId || ''"
        :connection-state="sessionStore.connectionState"
        :reconnect-attempt="reconnectAttempt"
        :is-loading-messages="sessionStore.isLoadingMessages"
        :is-send-loading="isSendLoading"
        :format-time="formatTime"
        :workspace="currentWorkspace"
        :pending-changes="pendingChanges"
        @open-left="showLeft = true"
        @retry="handleRetry"
        @send="handleSend"
        @confirm-change="handleConfirmChange"
        @cancel-change="handleCancelChange"
      />

      <PreviewPanel :preview-state="previewState" @close="closePreview" />
    </div>
  </div>

  <UserProfileDialog
    v-model="showEditProfileDialog"
    :user="currentUser"
    @confirm="handleProfileUpdate"
  />

  <AddAgentDialog v-model="showAddAgentDialog" @confirm="handleAddAgent" />

  <NewConversationDialog
    v-model="showNewConversationDialog"
    :agents="sidebarAgents"
    @confirm="handleCreateConversation"
    @go-agent-panel="activeSidebarPanel = 'agents'; showNewConversationDialog = false"
  />
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { applyPendingChange } from '../api/modules/pendingChanges'
import { fetchWorkspace } from '../api/modules/workspace'
import { useAgentStore } from '../store/index'
import { useSessionStore } from '../store/module/useSessionStore'
import { useUserInfoStore } from '../store/module/useUserStore'
import type {
  ConversationItem,
  ConversationMode,
  PendingChange,
  PreviewState,
  SidebarAgent,
  SidebarPanel,
  SidebarUser,
  Workspace,
} from '../types/agenthub'
import { getWsClientReconnectAttempt, wsClient } from '../utils/ws-client'
import { useToast } from '../veiws/useToast'
import AddAgentDialog from './zhu/AddAgentDialog.vue'
import ChatWorkspace from './zhu/ChatWorkspace.vue'
import LeftSidebarArea from './zhu/LeftSidebarArea.vue'
import NewConversationDialog from './zhu/NewConversationDialog.vue'
import PreviewPanel from './zhu/PreviewPanel.vue'
import UserProfileDialog from './zhu/UserProfileDialog.vue'

const userInfoStore = useUserInfoStore()
const sessionStore = useSessionStore()
const agentStore = useAgentStore()
const router = useRouter()
const showToast = useToast()

const showLeft = ref(true)
const isCollapsed = ref(false)
const activeSidebarPanel = ref<SidebarPanel>('messages')
const searchValue = ref('')
const agentSearchValue = ref('')
const showUserPopover = ref(false)
const showEditProfileDialog = ref(false)
const showNewConversationDialog = ref(false)
const showAddAgentDialog = ref(false)
const currentWorkspace = ref<Workspace | null>(null)
const isSendLoading = ref(false)
const previewState = ref<PreviewState>({ type: 'empty', title: '' })
const selectedAgentId = ref('')

const filteredSessions = computed(() => {
  const list = sessionStore.sessionList ?? []
  if (!searchValue.value) return list
  const q = searchValue.value.toLowerCase()
  return list.filter(
    (session) =>
      session.title?.toLowerCase().includes(q) ||
      session.description?.toLowerCase().includes(q),
  )
})

const pendingChanges = computed<PendingChange[]>(() => {
  return sessionStore.streamState.sessionPendingChanges.value
})

const sidebarAgents = ref<SidebarAgent[]>([
  {
    id: 'claude-code',
    name: 'Claude Code',
    avatar: '',
    capabilityTags: ['代码生成', '重构', '文档'],
    description: '专注代码与组件任务',
    platform: 'claude-code',
  },
  {
    id: 'codex',
    name: 'Codex',
    avatar: '',
    capabilityTags: ['代码生成', '调试', '测试'],
    description: 'OpenAI 代码助手',
    platform: 'codex',
  },
  {
    id: 'opencode',
    name: 'OpenCode',
    avatar: '',
    capabilityTags: ['需求分析', '架构', '文档'],
    description: '开源多模态开发 Agent',
    platform: 'opencode',
  },
  {
    id: 'agent-default',
    name: 'agent',
    avatar: '',
    capabilityTags: ['代码生成', '需求分析', '测试'],
    description: '通用开发助手',
    platform: 'custom',
  },
  {
    id: 'my-agent',
    name: '我的助手',
    avatar: '',
    capabilityTags: ['自定义', '脚本'],
    description: '用户自建 Agent 示例',
    platform: 'custom',
    isCustom: true,
  },
])

const currentUser = computed<SidebarUser>(() => ({
  id: userInfoStore.userId || 'user-1',
  name: userInfoStore.userName || '管理员',
  avatar: userInfoStore.avatar || '',
  email:
    (userInfoStore as unknown as { email?: string }).email || 'admin@example.com',
  bio:
    (userInfoStore as unknown as { bio?: string }).bio || 'AgentHub 用户',
}))

const reconnectAttempt = computed(() => getWsClientReconnectAttempt())

const filteredAgentList = computed(() => {
  if (!agentSearchValue.value) return sidebarAgents.value
  const q = agentSearchValue.value.toLowerCase()
  return sidebarAgents.value.filter(
    (agent) =>
      agent.name.toLowerCase().includes(q) ||
      agent.description?.toLowerCase().includes(q) ||
      agent.capabilityTags.some((tag) => tag.toLowerCase().includes(q)),
  )
})

const formatTime = (iso: string) => {
  if (!iso) return ''
  try {
    const date = new Date(iso)
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

const handleConfirmChange = async (changeId: string) => {
  try {
    const sessionId = sessionStore.currentSessionId || undefined
    const result = await applyPendingChange(changeId, sessionId)
    if (!result.success && result.status !== 'applied') {
      showToast(`应用失败: ${result.message}`, true)
    }
  } catch (error) {
    console.error('确认变更失败', error)
    showToast('确认变更失败', true)
  }
}

const handleCancelChange = (changeId: string) => {
  sessionStore.streamState.removePendingChange(changeId)
  showToast('已取消写入')
}

async function loadSessionWorkspace(session: ConversationItem | null) {
  if (!session?.workspace_id) {
    currentWorkspace.value = null
    return
  }

  try {
    currentWorkspace.value = await fetchWorkspace(session.workspace_id)
  } catch {
    currentWorkspace.value = null
  }
}

async function restorePendingChangesForCurrentSession(
  sessionId: string,
  opts: { clearInFlight?: boolean } = {},
) {
  try {
    await sessionStore.restorePendingChangesForSession(sessionId, {
      clearExisting: true,
      clearInFlight: opts.clearInFlight ?? false,
    })
  } catch (error) {
    console.error('恢复待确认变更失败', error)
  }
}

watch(
  () => sessionStore.currentSession,
  (session) => {
    void loadSessionWorkspace(session)
  },
  { immediate: true },
)

const selectSession = async (item: ConversationItem) => {
  if (sessionStore.currentSessionId === item.id) {
    showLeft.value = false
    return
  }

  wsClient.disconnect()
  sessionStore.clearMessages(item.id)
  sessionStore.setCurrentSessionId(item.id)
  await sessionStore.fetchSessionDetail(item.id)
  await sessionStore.fetchMessages(item.id, { page: 1, page_size: 20 })
  await restorePendingChangesForCurrentSession(item.id)
  wsClient.connect(item.id)
  showLeft.value = false
}

const togglePin = async (item: ConversationItem) => {
  try {
    await sessionStore.updateSession(item.id, { is_pinned: !item.is_pinned })
  } catch {
    showToast('操作失败', true)
  }
}

const toggleArchive = async (item: ConversationItem) => {
  try {
    await sessionStore.updateSession(item.id, { is_archived: !item.is_archived })
  } catch {
    showToast('操作失败', true)
  }
}

const handleDeleteSession = async (item: ConversationItem) => {
  try {
    await sessionStore.deleteSession(item.id)
    showToast('会话已删除')
  } catch {
    showToast('删除失败', true)
  }
}

const handleCreateConversation = async (payload: {
  mode: ConversationMode
  title: string
  agentId?: string
  participantAgentIds?: string[]
  workspace_id?: string | null
}) => {
  if (payload.mode === 'single' && !payload.agentId) {
    showToast('请先选择一个 Agent', true)
    return
  }
  if (
    payload.mode === 'group' &&
    (!payload.participantAgentIds || payload.participantAgentIds.length === 0)
  ) {
    showToast('请至少选择一个 Agent', true)
    return
  }
  if (!payload.workspace_id) {
    showToast('请先选择工作空间', true)
    return
  }

  try {
    const session = await sessionStore.createSession({
      owner_id: userInfoStore.userId || 'dev_user',
      title: payload.title,
      mode: payload.mode,
      workspace_id: payload.workspace_id,
    })
    if (session.workspace) {
      currentWorkspace.value = session.workspace as Workspace
    }
    sessionStore.setCurrentSessionId(session.id)
    await sessionStore.fetchMessages(session.id, { page: 1, page_size: 20 })
    await restorePendingChangesForCurrentSession(session.id)
    wsClient.connect(session.id)
    showNewConversationDialog.value = false
  } catch (error) {
    console.error('创建会话失败', error)
    showToast('创建会话失败', true)
  }
}

const handleSelectAgent = (agent: SidebarAgent) => {
  selectedAgentId.value = agent.id
  const existing = sessionStore.sessionList.find(
    (session) => session.title?.includes(agent.name) && session.mode === 'single',
  )
  if (existing) {
    void selectSession(existing)
    return
  }
  showNewConversationDialog.value = true
}

const handleSend = async (content: string) => {
  const sessionId = sessionStore.currentSessionId
  if (!sessionId) {
    showToast('请先选择或新建会话', true)
    return
  }

  isSendLoading.value = true
  const tempId = `temp_${Date.now()}`
  sessionStore.appendHumanMessage(sessionId, {
    id: tempId,
    session_id: sessionId,
    sender_type: 'human',
    sender_role: null,
    content,
    type: 'text',
    payload: { text: content },
    metadata: {},
    status: 'pending',
    created_at: new Date().toISOString(),
  })

  const ok = wsClient.sendMessage(content)
  if (!ok) {
    showToast('发送失败，请检查网络', true)
    isSendLoading.value = false
  }
}

const handleRetry = () => {
  wsClient.manualRetry()
}

const handleEditProfile = () => {
  showUserPopover.value = false
  showEditProfileDialog.value = true
}

const handleProfileUpdate = (data: Partial<SidebarUser>) => {
  if (data.name) userInfoStore.setUserName(data.name)
  if (data.email) {
    ;(userInfoStore as unknown as { setEmail: (value: string) => void }).setEmail(
      data.email,
    )
  }
  if (data.avatar !== undefined) userInfoStore.setUserAvatar(data.avatar)
  showToast('资料已更新')
}

const handleAddAgent = (newAgent: SidebarAgent) => {
  sidebarAgents.value.push(newAgent)
  showAddAgentDialog.value = false
}

const handlerLogout = () => {
  showUserPopover.value = false
  wsClient.disconnect()
  localStorage.removeItem('x-token')
  localStorage.removeItem('user')
  localStorage.removeItem('session-store')
  sessionStore.setCurrentSessionId(null)
  sessionStore.clearMessages('')
  userInfoStore.clearUserInfo()
  router.push('/login')
}

const restoreCurrentSession = async () => {
  const sessionId = sessionStore.currentSessionId
  if (!sessionId) return
  await sessionStore.fetchSessionDetail(sessionId)
  await sessionStore.fetchMessages(sessionId, { page: 1, page_size: 20 })
  await restorePendingChangesForCurrentSession(sessionId)
  wsClient.connect(sessionId)
}

const closePreview = () => {
  previewState.value = { type: 'empty', title: '' }
}

onMounted(async () => {
  await sessionStore.fetchSessionList({
    owner_id: userInfoStore.userId || 'dev_user',
    page: 1,
    page_size: 50,
  })

  agentStore.fetchDefaultAgent()

  wsClient.onStateChange((state) => {
    sessionStore.setConnectionState(state)
    if (state === 'connected') {
      isSendLoading.value = false
      const sessionId = sessionStore.currentSessionId
      if (sessionId) {
        void restorePendingChangesForCurrentSession(sessionId, { clearInFlight: true })
      }
    }
  })

  wsClient.onReceiveMessage((msg) => {
    const currentSessionId = sessionStore.currentSessionId
    if (!currentSessionId) return

    if (msg.type === 'message_start') {
      sessionStore.streamState.handleMessageStart(msg, currentSessionId)
      return
    }
    if (msg.type === 'message_delta') {
      sessionStore.streamState.handleMessageDelta(msg, currentSessionId)
      return
    }
    if (msg.type === 'message_end') {
      const stream = sessionStore.streamState.handleMessageEnd(msg, currentSessionId)
      if (stream) {
        sessionStore.mergeOrUpdateMessage(currentSessionId, {
          id: stream.message_id || msg.message_id || '',
          session_id: currentSessionId,
          sender_type: 'agent',
          sender_role: stream.sender_role,
          content: stream.accumulated_content,
          type: stream.type || 'text',
          payload: stream.payload || { text: stream.accumulated_content },
          metadata: stream.metadata || {},
          status: msg.status === 'completed' ? 'completed' : 'failed',
          created_at: stream.created_at,
        })
      }
      isSendLoading.value = false
      return
    }
    if (msg.type === 'message_error') {
      sessionStore.streamState.handleMessageError(msg, currentSessionId)
      isSendLoading.value = false
      return
    }
    if (msg.type === 'tool_event') {
      sessionStore.streamState.handleToolEvent(msg, currentSessionId)
      return
    }
    if (msg.type === 'runtime_state') {
      sessionStore.streamState.handleRuntimeState(msg, currentSessionId)
      return
    }
    if (msg.type === 'change_preview') {
      sessionStore.streamState.handleChangePreview(msg, currentSessionId)
      return
    }
    if (msg.type === 'apply_result') {
      sessionStore.streamState.handleApplyResult(msg)
      return
    }
    if (msg.type === 'preview_result') {
      previewState.value = {
        type: 'web',
        title: 'Runtime Preview',
        url: msg.preview_url || '',
        description: msg.status || 'ready',
      }
      return
    }
    if (msg.type === 'repair_state') {
      sessionStore.streamState.handleRepairState(msg)
      return
    }
    if (msg.type === 'error') {
      console.error('[WsClient] Server error:', msg.error_code, msg.error_message)
      isSendLoading.value = false
    }
  })

  await restoreCurrentSession()
})

onUnmounted(() => {
  wsClient.disconnect()
})
</script>

<style scoped>
.workspace {
  position: relative;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #ffffff 0%, #f0f4ff 50%, #e8f0fe 100%);
}

.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  animation: float 10s ease-in-out infinite;
  pointer-events: none;
}

.glow-orb-1 {
  top: -200px;
  right: -100px;
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
  animation-delay: 0s;
}

.glow-orb-2 {
  bottom: -150px;
  left: -100px;
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.12) 0%, transparent 70%);
  animation-delay: -4s;
}

.glow-orb-3 {
  top: 40%;
  left: 30%;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.1) 0%, transparent 70%);
  transform: translate(-50%, -50%);
  animation-delay: -7s;
}

@keyframes float {
  0%,
  100% {
    transform: translate(0, 0) scale(1);
  }

  33% {
    transform: translate(40px, -40px) scale(1.08);
  }

  66% {
    transform: translate(-30px, 30px) scale(0.95);
  }
}

.grid-pattern {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(
    circle at 1px 1px,
    rgba(59, 130, 246, 0.06) 1px,
    transparent 0
  );
  background-size: 50px 50px;
  pointer-events: none;
}

.glass-container {
  position: relative;
  z-index: 10;
  display: grid;
  height: 100%;
  gap: 0;
  padding: 16px;
  box-sizing: border-box;
  grid-template-columns: 400px minmax(0, 1fr) 340px;
}

.glass-container > :deep(*) {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.6);
  border-radius: 20px;
  box-shadow:
    0 8px 32px rgba(59, 130, 246, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}

.glass-container > :deep(*):hover {
  box-shadow:
    0 12px 40px rgba(59, 130, 246, 0.12),
    0 4px 12px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

@media (max-width: 1400px) {
  .glass-container {
    padding: 12px;
    grid-template-columns: 72px 300px minmax(0, 1fr) 300px;
  }
}

@media (max-width: 1200px) {
  .glass-container {
    padding: 12px;
    grid-template-columns: 72px 300px minmax(0, 1fr);
  }
}

.glass-container.sidebar-collapsed {
  grid-template-columns: 72px minmax(0, 1fr) 340px;
}

@media (max-width: 1400px) {
  .glass-container.sidebar-collapsed {
    grid-template-columns: 72px minmax(0, 1fr) 300px;
  }
}

@media (max-width: 1200px) {
  .glass-container.sidebar-collapsed {
    grid-template-columns: 72px minmax(0, 1fr);
  }
}

@media (max-width: 900px) {
  .glass-container {
    padding: 8px;
    grid-template-columns: 1fr;
  }

  .glass-container > :deep(*) {
    border-radius: 16px;
  }
}

:deep(.el-dialog) {
  backdrop-filter: blur(20px);
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 20px;
  box-shadow:
    0 25px 50px rgba(59, 130, 246, 0.15),
    0 10px 20px rgba(0, 0, 0, 0.08);
}

:deep(.el-dialog__header) {
  padding: 20px 24px 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
}

:deep(.el-dialog__title) {
  color: #1e40af;
  font-size: 18px;
  font-weight: 600;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid rgba(59, 130, 246, 0.08);
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  border-color: transparent;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
  transition: all 0.3s ease;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
  transform: translateY(-1px);
}
</style>
