<template>
  <!-- 三栏布局：左侧列表区 | 中间聊天区 | 右侧预览区 -->
  <div class="workspace">
    <!-- 动态背景光晕效果 -->
    <div class="glow-orb glow-orb-1"></div>
    <div class="glow-orb glow-orb-2"></div>
    <div class="glow-orb glow-orb-3"></div>

    <!-- 装饰性网格点阵 -->
    <div class="grid-pattern"></div>

    <!-- 玻璃态主容器 -->
    <div
      class="glass-container"
      :class="{ 'sidebar-collapsed': isCollapsed, 'is-preview-resizing': isResizingPreview }"
      :style="glassContainerStyle"
    >
      <!-- 左侧列表区 -->
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
        :agents="filteredAgentList"
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
        @edit-agent="handleEditAgent"
        @delete-agent="handleDeleteAgent"
        @delete-session="handleDeleteSession"
        @edit-profile="handleEditProfile"
        @logout="handlerLogout"
        @toggle-collapse="isCollapsed = !isCollapsed"
      />

      <!-- 中间聊天区 -->
      <ChatWorkspace
        :current-session="sessionStore.currentSession"
        :current-session-id="sessionStore.currentSessionId || ''"
        :connection-state="sessionStore.connectionState"
        :reconnect-attempt="reconnectAttempt"
        :is-loading-messages="sessionStore.isLoadingMessages"
        :is-send-loading="isSendLoading"
        :format-time="formatTime"
        :workspace="currentWorkspace"
        @open-left="showLeft = true"
        @retry="handleRetry"
        @send="handleSend"
      />

      <div
        class="preview-resize-handle"
        :class="{ 'is-dragging': isResizingPreview }"
        role="separator"
        aria-orientation="vertical"
        aria-label="调整预览区宽度"
        @mousedown="startPreviewResize"
      >
        <span class="preview-resize-grip"></span>
      </div>

      <!-- 右侧预览区 -->
      <PreviewPanel
        :preview-state="previewState"
        @close="closePreview"
      />
    </div>
  </div>

  <!-- 用户资料编辑弹窗 -->
  <UserProfileDialog
    v-model="showEditProfileDialog"
    :user="currentUser"
    @confirm="handleProfileUpdate"
  />

  <!-- 添加自建 Agent 弹窗 -->
  <AddAgentDialog
    v-model="showAddAgentDialog"
    :available-models="agentStore.availableModels"
    :available-capability-tags="agentStore.availableCapabilityTags"
    @confirm="handleAddAgent"
  />

  <!-- 编辑 Agent 弹窗 -->
  <AddAgentDialog
    v-model="showEditAgentDialog"
    :available-models="agentStore.availableModels"
    :available-capability-tags="agentStore.availableCapabilityTags"
    :is-edit="true"
    :editing-agent="editingAgent"
    @confirm-edit="handleUpdateAgent"
  />

  <!-- 新建对话弹窗 -->
  <NewConversationDialog
    v-model="showNewConversationDialog"
    :agents="groupSelectableAgents"
    :primary-agent="primaryGroupAgent"
    @confirm="handleCreateConversation"
    @go-agent-panel="activeSidebarPanel = 'agents'; showNewConversationDialog = false"
  />
</template>

<script lang="ts" setup>
/**
 * zhu.vue - 页面容器
 * 高级玻璃态设计，白色为主，带动态效果
 * 结合 V1 完整功能 + V3 清晰结构
 */
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

import { fetchWorkspace } from '../api/modules/workspace'
import userApi from '../api/user'
import { useAgentStore } from '../store/index'
import { useSessionStore } from '../store/module/useSessionStore'
import { useUserInfoStore } from '../store/module/useUserStore'
import type {
  AgentDraft,
  ConversationItem,
  ConversationMode,
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

// ==================== Store ====================
const userInfoStore = useUserInfoStore()
const sessionStore = useSessionStore()
const agentStore = useAgentStore()
const router = useRouter()
const showToast = useToast()

// ==================== 布局状态 ====================
/** 左侧栏显示开关（移动端控制） */
const showLeft = ref(true)

const DEFAULT_PREVIEW_WIDTH = 340
const MIN_PREVIEW_WIDTH = 280
const MAX_PREVIEW_WIDTH = 1400
const PREVIEW_RESIZE_HANDLE_WIDTH = 8

/** 左侧栏收起状态 */
const isCollapsed = ref(false)

/** 右侧预览区宽度 */
const previewWidth = ref(DEFAULT_PREVIEW_WIDTH)

/** 是否正在拖拽调整预览区 */
const isResizingPreview = ref(false)

/** 左侧栏当前面板：消息列表 / Agent 列表 */
const activeSidebarPanel = ref<SidebarPanel>('messages')

// ==================== 搜索状态 ====================
/** 消息列表搜索关键字 */
const searchValue = ref('')
/** Agent 列表搜索关键字 */
const agentSearchValue = ref('')

// ==================== 用户弹框 & 编辑资料 ====================
/** 用户信息弹框显隐 */
const showUserPopover = ref(false)
/** 编辑资料弹框显隐 */
const showEditProfileDialog = ref(false)

// ==================== 新建对话 ====================
/** 新建对话弹框显隐 */
const showNewConversationDialog = ref(false)

// ==================== 添加自建 Agent ====================
/** 添加 Agent 弹框显隐 */
const showAddAgentDialog = ref(false)

// ==================== 编辑自建 Agent ====================
/** 编辑 Agent 弹框显隐 */
const showEditAgentDialog = ref(false)
/** 当前编辑的 Agent */
const editingAgent = ref<SidebarAgent | null>(null)

// ==================== 发送状态 ====================
/** 正在发送消息（显示 AI 回复 loading） */
const isSendLoading = ref(false)

// ==================== 预览状态 ====================
/** 右侧预览区状态 */
const previewState = ref<PreviewState>({ type: 'empty', title: '' })

// ==================== Agent 列表选中 ====================
/** 当前选中的 Agent ID（用于高亮） */
const selectedAgentId = ref('')

// ==================== 工作空间 ====================
/** 当前会话的工作空间 */
const currentWorkspace = ref<Workspace | null>(null)

const sidebarAgents = computed(() => agentStore.agents)
const primaryGroupAgent = computed(() => {
  const groupHost = sidebarAgents.value.find((item) => item.id.startsWith('group_host_'))
  if (groupHost) return groupHost

  const current = agentStore.agent
  if (!current) return null
  return sidebarAgents.value.find((item) => item.id === current.id) || {
    id: current.id,
    name: current.name,
    avatar: current.avatar_url || current.avatar || '',
    capabilityTags: current.capabilityTags || current.capability_tags || [],
    description: current.description,
    platform: current.platform || 'custom',
    isCustom: !current.is_builtin,
    role: current.role,
    model: current.model,
    system_prompt: current.system_prompt,
  }
})

// ==================== 计算属性 ====================

/** 会话列表过滤（按搜索关键字过滤标题和摘要） */
const filteredSessions = computed(() => {
  const list = sessionStore.sessionList ?? []
  if (!searchValue.value) return list
  const q = searchValue.value.toLowerCase()
  return list.filter(
    (s) =>
      s.title?.toLowerCase().includes(q) ||
      s.description?.toLowerCase().includes(q),
  )
})

/** 当前用户信息 */
const currentUser = computed<SidebarUser>(() => ({
  id: userInfoStore.userId || 'user-1',
  name: userInfoStore.userName || '管理员',
  avatar: userInfoStore.avatar || '/msg10.jpg',
  email: (userInfoStore as unknown as { email?: string }).email || 'admin@example.com',
  bio: (userInfoStore as unknown as { bio?: string }).bio || 'AgentHub 用户',
}))

/** WebSocket 重连次数 */
const reconnectAttempt = computed(() => getWsClientReconnectAttempt())

/** Agent 列表过滤 */
const filteredAgentList = computed(() => {
  if (!agentSearchValue.value) return sidebarAgents.value
  const q = agentSearchValue.value.toLowerCase()
  return sidebarAgents.value.filter(
    (a) =>
      a.name.toLowerCase().includes(q) ||
      a.description?.toLowerCase().includes(q) ||
      a.capabilityTags.some((t) => t.toLowerCase().includes(q)),
  )
})

const groupSelectableAgents = computed(() => {
  const primaryId = primaryGroupAgent.value?.id
  if (!primaryId) return filteredAgentList.value
  return filteredAgentList.value.filter((agent) => agent.id !== primaryId)
})

const glassContainerStyle = computed(() => {
  const sidebarWidth = isCollapsed.value ? 72 : 400
  const previewTrackWidth = PREVIEW_RESIZE_HANDLE_WIDTH + previewWidth.value
  return {
    gridTemplateColumns: `${sidebarWidth}px minmax(0, 1fr) ${previewTrackWidth}px`,
    '--preview-width': `${previewWidth.value}px`,
    '--preview-track-width': `${previewTrackWidth}px`,
    '--preview-handle-width': `${PREVIEW_RESIZE_HANDLE_WIDTH}px`,
  }
})

// ==================== 工具函数 ====================

function clampPreviewWidth(nextWidth: number) {
  return Math.min(MAX_PREVIEW_WIDTH, Math.max(MIN_PREVIEW_WIDTH, nextWidth))
}

function stopPreviewResize() {
  isResizingPreview.value = false
  document.body.classList.remove('preview-resizing')
  document.removeEventListener('mousemove', handlePreviewResize)
  document.removeEventListener('mouseup', stopPreviewResize)
}

function handlePreviewResize(event: MouseEvent) {
  const viewportWidth = window.innerWidth
  if (viewportWidth <= 1200) return

  const nextWidth = clampPreviewWidth(viewportWidth - event.clientX - 16)
  previewWidth.value = nextWidth
}

function startPreviewResize(event: MouseEvent) {
  if (window.innerWidth <= 1200) return

  event.preventDefault()
  isResizingPreview.value = true
  document.body.classList.add('preview-resizing')
  document.addEventListener('mousemove', handlePreviewResize)
  document.addEventListener('mouseup', stopPreviewResize)
}

// ==================== 工具函数 ====================

/**
 * 格式化 ISO 时间字符串为"月日 时:分"格式
 */
const formatTime = (iso: string) => {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

// ==================== 加载工作空间 ====================

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

// ==================== 恢复待确认变更 ====================

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

// ==================== 会话操作 ====================

/** 选中会话 */
const selectSession = async (item: ConversationItem) => {
  if (sessionStore.currentSessionId === item.id) {
    showLeft.value = false
    return
  }
  const previousSessionId = sessionStore.currentSessionId
  wsClient.disconnect()
  if (previousSessionId) {
    sessionStore.clearMessages(previousSessionId)
  }
  sessionStore.setCurrentSessionId(item.id)
  await sessionStore.fetchSessionDetail(item.id)
  await sessionStore.fetchMessages(item.id, { page: 1, page_size: 20 })
  await sessionStore.fetchLatestRun(item.id)
  await restorePendingChangesForCurrentSession(item.id)
  wsClient.connect(item.id)
  showLeft.value = false
}

/** 置顶 / 取消置顶会话 */
const togglePin = async (item: ConversationItem) => {
  try {
    await sessionStore.updateSession(item.id, { is_pinned: !item.is_pinned })
  } catch {
    showToast('操作失败', true)
  }
}

/** 归档 / 取消归档会话 */
const toggleArchive = async (item: ConversationItem) => {
  try {
    await sessionStore.updateSession(item.id, { is_archived: !item.is_archived })
  } catch {
    showToast('操作失败', true)
  }
}

/** 删除会话 */
const handleDeleteSession = async (item: ConversationItem) => {
  try {
    await sessionStore.deleteSession(item.id)
    showToast('会话已删除')
  } catch {
    showToast('删除失败', true)
  }
}

/** 创建新会话 */
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
      agent_id: payload.agentId,
      participant_agent_ids: payload.participantAgentIds || [],
    })
    if (session.workspace) {
      currentWorkspace.value = session.workspace as Workspace
    }
    sessionStore.setCurrentSessionId(session.id)
  await sessionStore.fetchSessionDetail(session.id)
    await sessionStore.fetchMessages(session.id, { page: 1, page_size: 20 })
    await sessionStore.fetchLatestRun(session.id)
    await restorePendingChangesForCurrentSession(session.id)
    wsClient.connect(session.id)
    showNewConversationDialog.value = false
  } catch (error) {
    console.error('创建会话失败', error)
    showToast('创建会话失败', true)
  }
}

/** 选择 Agent（高亮选中状态） */
const handleSelectAgent = (agent: SidebarAgent) => {
  selectedAgentId.value = agent.id
}

/** 编辑 Agent */
const handleEditAgent = (agent: SidebarAgent) => {
  editingAgent.value = agent
  showEditAgentDialog.value = true
}

/** 删除 Agent */
const handleDeleteAgent = async (agent: SidebarAgent) => {
  try {
    await agentStore.deleteAgent(agent.id)
    showToast('Agent 已删除')
    if (selectedAgentId.value === agent.id) {
      selectedAgentId.value = ''
    }
  } catch {
    showToast('删除失败', true)
  }
}

// ==================== 发送消息 ====================

/** 发送消息 */
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

/** 重试连接 */
const handleRetry = () => {
  wsClient.manualRetry()
}

// ==================== 用户资料 ====================

/** 打开编辑资料弹框 */
const handleEditProfile = () => {
  showUserPopover.value = false
  showEditProfileDialog.value = true
}

/** 提交资料更新 */
const handleProfileUpdate = async (data: Partial<SidebarUser>) => {
  if (data.name) userInfoStore.setUserName(data.name)
  if (data.email) {
    ;(userInfoStore as unknown as { setEmail: (value: string) => void }).setEmail(data.email)
  }
  if (data.avatar !== undefined) userInfoStore.setUserAvatar(data.avatar)

  const saved = localStorage.getItem('user')
  const userData = saved ? JSON.parse(saved) : {}
  if (data.name) userData.userName = data.name
  if (data.email) userData.email = data.email
  if (data.avatar !== undefined) userData.avatar = data.avatar
  localStorage.setItem('user', JSON.stringify(userData))

  try {
    await userApi.update({ userName: data.name, avatar: data.avatar, email: data.email })
  } catch (e) {
    // silent fail
  }

  showToast('资料已更新')
}

// ==================== 添加自建 Agent ====================

const handleAddAgent = async (newAgent: AgentDraft) => {
  try {
    const created = await agentStore.createAgent({
      name: newAgent.name,
      model: newAgent.model,
      platform: newAgent.platform || 'custom',
      description: newAgent.description || null,
      avatar_url: newAgent.avatar || null,
      capability_tags: newAgent.capabilityTags,
    })
    selectedAgentId.value = created.id
    showAddAgentDialog.value = false
    await agentStore.fetchAgents()
  } catch (error) {
    console.error('添加 Agent 失败', error)
    showToast('添加 Agent 失败', true)
  }
}

/** 更新 Agent */
const handleUpdateAgent = async (agentData: AgentDraft & { id: string }) => {
  try {
    await agentStore.updateAgent(agentData.id, {
      name: agentData.name,
      model: agentData.model,
      platform: agentData.platform || 'custom',
      description: agentData.description || null,
      avatar_url: agentData.avatar || null,
      capability_tags: agentData.capabilityTags,
    })
    showEditAgentDialog.value = false
    showToast('Agent 已更新')
    await agentStore.fetchAgents()
  } catch (error) {
    console.error('更新 Agent 失败', error)
    showToast('更新 Agent 失败', true)
  }
}

// ==================== 登出 ====================

/** 退出登录 */
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

// ==================== 恢复当前会话 ====================

async function restoreCurrentSession() {
  const sessionId = sessionStore.currentSessionId
  if (!sessionId) return
  await sessionStore.fetchSessionDetail(sessionId)
  await sessionStore.fetchMessages(sessionId, { page: 1, page_size: 20 })
  await sessionStore.fetchLatestRun(sessionId)
  await restorePendingChangesForCurrentSession(sessionId)
  wsClient.connect(sessionId)
}

// ==================== 预览区 ====================

/** 关闭预览区 */
const closePreview = () => {
  previewState.value = { type: 'empty', title: '' }
  sessionStore.streamState?.clearPreviewDiff()
}

// M6: 监听预览 diff 状态变化，更新右侧预览面板
watch(
  () => sessionStore.streamState?.previewDiff,
  (previewDiff) => {
    if (previewDiff) {
      previewState.value = {
        type: 'diff',
        title: previewDiff.path.split(/[/\\]/).pop() || '文件预览',
        change_id: previewDiff.change_id,
        operation: previewDiff.operation,
        path: previewDiff.path,
        unified_diff: previewDiff.unified_diff,
      }
    } else {
      previewState.value = { type: 'empty', title: '' }
    }
  },
  { immediate: true, deep: true },
)

// ==================== 生命周期 ====================

onMounted(async () => {
  await Promise.all([
    sessionStore.fetchSessionList({
      owner_id: userInfoStore.userId || 'dev_user',
      page: 1,
      page_size: 50,
    }),
    agentStore.fetchAgentConfig(),
    agentStore.fetchDefaultAgent(),
    agentStore.fetchAgents(),
  ])

  // 监听 WebSocket 状态变化
  wsClient.onStateChange((state) => {
    sessionStore.setConnectionState(state)
    if (state === 'connected') {
      const sessionId = sessionStore.currentSessionId
      if (sessionId) {
        void restorePendingChangesForCurrentSession(sessionId, { clearInFlight: true })
      }
    }
  })

  // 监听 WebSocket 消息
  wsClient.onReceiveMessage((msg) => {
    const currentSessionId = sessionStore.currentSessionId
    const resolvedSessionId =
      msg.message?.session_id
      || (msg.stream_id ? sessionStore.streamState.getSessionIdForStream(msg.stream_id) : undefined)
      || currentSessionId

    if (!resolvedSessionId) return

    if (msg.type === 'message_start') {
      sessionStore.streamState.handleMessageStart(msg, resolvedSessionId)
    } else if (msg.type === 'message_delta') {
      sessionStore.streamState.handleMessageDelta(msg, resolvedSessionId)
    } else if (msg.type === 'message_end') {
      const stream = sessionStore.streamState.handleMessageEnd(msg, resolvedSessionId)
      if (stream) {
        const persistedMessageId = stream.message_id || msg.message_id || msg.stream_id || stream.stream_id
        sessionStore.mergeOrUpdateMessage(resolvedSessionId, {
          id: persistedMessageId,
          session_id: resolvedSessionId,
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
    } else if (msg.type === 'message_error') {
      sessionStore.streamState.handleMessageError(msg, resolvedSessionId)
      isSendLoading.value = false
    } else if (msg.type === 'tool_event') {
      sessionStore.streamState.handleToolEvent(msg, resolvedSessionId)
    } else if (msg.type === 'runtime_state') {
      sessionStore.streamState.handleRuntimeState(msg, resolvedSessionId)
    } else if (msg.type === 'change_preview') {
      // M6: Use handleChangePreviewAsMessage to render confirmation inline in chat
      // instead of in a separate panel
      sessionStore.streamState.handleChangePreviewAsMessage(msg, resolvedSessionId)
    } else if (msg.type === 'apply_result') {
      // M6: Update change preview status in stream state
      const changeId = msg.change_id
      if (changeId) {
        const newStatus = msg.status === 'applied' ? 'confirmed' : 'rejected'
        sessionStore.streamState.updateChangePreviewStatus(changeId, newStatus)
      }
      sessionStore.streamState.handleApplyResult(msg)
    } else if (msg.type === 'preview_result') {
      previewState.value = {
        type: 'web',
        title: 'Runtime Preview',
        url: msg.preview_url || '',
        description: msg.status || 'ready',
      }
    } else if (msg.type === 'repair_state') {
      sessionStore.streamState.handleRepairState(msg)
    } else if (msg.type === 'error') {
      console.error('[WsClient] Server error:', msg.error_code, msg.error_message)
      isSendLoading.value = false
    } else if (msg.type === 'orchestration_run_started') {
      // M6: Handle orchestration run started event - initialize run and tasks
      const runId = msg.run_id
      const taskCount = msg.task_count
      if (runId && taskCount) {
        sessionStore.updateRun(runId, 'running')
      }
    } else if (msg.type === 'orchestration_run_finished') {
      // M6: Handle orchestration run finished event
      const runId = msg.run_id
      const status = msg.status
      const summary = msg.summary
      if (runId) {
        sessionStore.updateRun(runId, status || 'completed', summary)
      }
    } else if (msg.type === 'orchestration_run_updated') {
      // M6: Handle orchestration run updated event
      const runId = msg.run_id
      const status = msg.status
      if (runId) {
        sessionStore.updateRun(runId, status || 'running')
      }
    } else if (msg.type === 'task_start') {
      // M6: Handle task start event - add task to active tasks
      const { run_id, task_id, agent_id, stream_id, title, goal } = msg
      if (task_id && run_id) {
        sessionStore.addTask({
          id: task_id,
          run_id: run_id,
          assigned_agent_id: agent_id || '',
          kind: 'unknown',
          title: title || '任务',
          goal: goal || '',
          input_payload: {},
          status: 'running',
        })
        // Also ensure the run is set
        sessionStore.updateRun(run_id, 'running')
      }
    } else if (msg.type === 'task_end') {
      // M6: Handle task end event - update task status
      const { task_id, status, run_id } = msg
      if (task_id) {
        sessionStore.updateTaskStatus(task_id, status || 'completed')
      }
    } else if (msg.type === 'task_error') {
      // M6: Handle task error event
      const { task_id, error_code, error_message } = msg
      if (task_id) {
        sessionStore.updateTaskStatus(task_id, 'failed')
        console.error('[WsClient] Task error:', task_id, error_code, error_message)
      }
    }
  })

  await restoreCurrentSession()

  // M6: Register task status update callback - replaces window event as primary sync
  sessionStore.streamState.setOnTaskStatusUpdate((taskId, runId, status) => {
    sessionStore.updateTaskStatus(taskId, status)
    if (runId) {
      sessionStore.fetchRun(runId).catch((error) => {
        console.error('刷新编排状态失败', error)
      })
    }
  })
})

onUnmounted(() => {
  stopPreviewResize()
  sessionStore.streamState.setOnTaskStatusUpdate(() => {})
  wsClient.disconnect()
})
</script>

<style scoped>
/* ==================== 工作区容器 ==================== */
.workspace {
  position: relative;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #ffffff 0%, #f0f4ff 50%, #e8f0fe 100%);
}

/* ==================== 动态光晕效果 ==================== */
.glow-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(100px);
  animation: float 10s ease-in-out infinite;
  pointer-events: none;
}

.glow-orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
  top: -200px;
  right: -100px;
  animation-delay: 0s;
}

.glow-orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.12) 0%, transparent 70%);
  bottom: -150px;
  left: -100px;
  animation-delay: -4s;
}

.glow-orb-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.1) 0%, transparent 70%);
  top: 40%;
  left: 30%;
  transform: translate(-50%, -50%);
  animation-delay: -7s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(40px, -40px) scale(1.08); }
  66% { transform: translate(-30px, 30px) scale(0.95); }
}

/* ==================== 装饰性网格点阵 ==================== */
.grid-pattern {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(circle at 1px 1px, rgba(59, 130, 246, 0.06) 1px, transparent 0);
  background-size: 50px 50px;
  pointer-events: none;
}

/* ==================== 玻璃态主容器 ==================== */
.glass-container {
  --preview-width: 340px;
  --preview-track-width: 348px;
  --preview-handle-width: 8px;
  position: relative;
  z-index: 10;
  height: 100%;
  display: grid;
  grid-template-columns: 400px minmax(0, 1fr) var(--preview-track-width);
  gap: 0;
  padding: 16px;
  box-sizing: border-box;
}

.glass-container > :deep(*) {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow:
    0 8px 32px rgba(59, 130, 246, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}

.glass-container > .preview-resize-handle {
  background: transparent;
  backdrop-filter: none;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.glass-container > :deep(*):hover {
  box-shadow:
    0 12px 40px rgba(59, 130, 246, 0.12),
    0 4px 12px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.glass-container > .preview-resize-handle:hover {
  box-shadow: none;
}

.preview-resize-handle {
  position: absolute;
  top: 16px;
  right: calc(var(--preview-width) + 16px);
  width: var(--preview-handle-width);
  height: calc(100% - 32px);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: col-resize;
  user-select: none;
  touch-action: none;
  z-index: 20;
}

.preview-resize-grip {
  width: 4px;
  height: 72px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.5);
  transition: background-color 0.2s ease, transform 0.2s ease;
}

.preview-resize-handle:hover .preview-resize-grip,
.glass-container.is-preview-resizing .preview-resize-grip {
  background: rgba(59, 130, 246, 0.75);
  transform: scaleX(1.15);
}

.glass-container.sidebar-collapsed {
  grid-template-columns: 72px minmax(0, 1fr) var(--preview-track-width);
}

/* ==================== 响应式断点 ==================== */
@media (max-width: 1400px) {
  .glass-container {
    padding: 12px;
  }

  .preview-resize-handle {
    top: 12px;
    right: calc(var(--preview-width) + 12px);
    height: calc(100% - 24px);
  }
}

@media (max-width: 1200px) {
  .glass-container {
    grid-template-columns: 72px 300px minmax(0, 1fr);
    padding: 12px;
  }
  .glass-container.sidebar-collapsed {
    grid-template-columns: 72px minmax(0, 1fr);
  }

  .preview-resize-handle {
    display: none;
  }
}

@media (max-width: 900px) {
  .glass-container {
    grid-template-columns: 1fr;
    padding: 8px;
  }
  .glass-container > :deep(*) {
    border-radius: 16px;
  }

  .preview-resize-handle {
    display: none;
  }
}

/* ==================== Element Plus 弹窗样式覆盖 ==================== */
:deep(.el-dialog) {
  border-radius: 20px;
  backdrop-filter: blur(20px);
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(59, 130, 246, 0.1);
  box-shadow:
    0 25px 50px rgba(59, 130, 246, 0.15),
    0 10px 20px rgba(0, 0, 0, 0.08);
}

:deep(.el-dialog__header) {
  padding: 20px 24px 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
}

:deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
  color: #1e40af;
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
