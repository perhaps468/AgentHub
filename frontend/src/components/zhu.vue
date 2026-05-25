<template>
  <!-- 三栏布局容器：左侧列表区 | 中间聊天区 | 右侧预览区 -->
  <div class="workspace">
    <!-- 左侧列表区 -->
    <LeftSidebarArea
      :show-left="showLeft"
      :current-user="currentUser"
      :active-panel="activeSidebarPanel"
      :show-user-popover="showUserPopover"
      :search-value="searchValue"
      :agent-search-value="agentSearchValue"
      :filtered-sessions="sessionStore.sessionList ?? []"
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
      @open-left="showLeft = true"
      @retry="handleRetry"
      @send="handleSend"
    />

    <!-- 右侧预览区 -->
    <PreviewPanel
      :preview-state="previewState"
      @close="closePreview"
    />
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
    @confirm="handleAddAgent"
  />

  <!-- 新建对话弹窗 -->
  <NewConversationDialog
    v-model="showNewConversationDialog"
    :agents="sidebarAgents"
    @confirm="handleCreateConversation"
    @go-agent-panel="activeSidebarPanel = 'agents'; showNewConversationDialog = false"
  />
</template>

<script lang="ts" setup>
/**
 * zhu.vue - 页面容器
 *
 * 职责：
 * - 三栏布局编排（左侧列表区 / 中间聊天区 / 右侧预览区）
 * - 跨区域状态协调（当前会话、连接状态、预览状态）
 * - 与全局 Store / WebSocket 的 orchestration
 * - 不承载大段列表 DOM、弹窗 DOM 或聊天区 DOM
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { useSessionStore } from '../store/module/useSessionStore'
import { useUserInfoStore } from '../store/module/useUserStore'
import { useAgentStore } from '../store/index'
import type { ConversationItem, ConversationMode, PreviewState, SidebarAgent, SidebarPanel, SidebarUser } from '../types/agenthub'
import { wsClient, getWsClientReconnectAttempt } from '../utils/ws-client'
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
const showToast = useToast()

// ==================== 布局状态 ====================
/** 左侧栏显示开关（移动端控制） */
const showLeft = ref(true)

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

// ==================== 发送状态 ====================
/** 正在发送消息（显示 AI 回复 loading） */
const isSendLoading = ref(false)

// ==================== 预览状态 ====================
/** 右侧预览区状态，一期先使用空状态 */
const previewState = ref<PreviewState>({ type: 'empty', title: '' })

// ==================== Agent 列表选中 ====================
/** 当前选中的 Agent ID（用于高亮） */
const selectedAgentId = ref('')

// ==================== Mock Agent 数据（由 Store 注入后可替换） ====================
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

// ==================== 计算属性 ====================

/** 当前用户信息（由 Store 映射） */
const currentUser = computed<SidebarUser>(() => ({
  id: userInfoStore.userId || 'user-1',
  name: userInfoStore.userName || '管理员',
  avatar: userInfoStore.avatar || '',
  email: (userInfoStore as unknown as { email?: string }).email || 'admin@example.com',
  bio: (userInfoStore as unknown as { bio?: string }).bio || 'AgentHub 用户',
}))

/** WebSocket 重连次数（由 wsClient 提供） */
const reconnectAttempt = computed(() => getWsClientReconnectAttempt())

/** Agent 列表过滤（按搜索关键字过滤） */
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

// ==================== 工具函数 ====================

/**
 * 格式化 ISO 时间字符串为"月日 时:分"格式
 * @param iso ISO 8601 时间字符串
 */
const formatTime = (iso: string) => {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

// ==================== 会话操作 ====================

/**
 * 选中会话：断开旧连接、加载会话详情与消息、建立新 WebSocket 连接
 */
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

/**
 * 创建新会话并连接 WebSocket
 */
const handleCreateConversation = async (payload: {
  mode: ConversationMode
  title: string
  agentId?: string
  participantAgentIds?: string[]
}) => {
  if (payload.mode === 'single' && !payload.agentId) {
    showToast('请先选择一个 Agent', true)
    return
  }
  if (payload.mode === 'group' && (!payload.participantAgentIds || payload.participantAgentIds.length === 0)) {
    showToast('请至少选择一个 Agent', true)
    return
  }

  try {
    const session = await sessionStore.createSession({
      owner_id: userInfoStore.userId || 'dev_user',
      title: payload.title,
      mode: payload.mode,
    })
    sessionStore.setCurrentSessionId(session.id)
    await sessionStore.fetchMessages(session.id, { page: 1, page_size: 20 })
    wsClient.connect(session.id)
    showNewConversationDialog.value = false
  } catch (e) {
    console.error('创建会话失败', e)
    showToast('创建会话失败', true)
  }
}

/**
 * 选择 Agent：若已有该 Agent 的单聊会话则进入，否则打开新建流程并预填 Agent
 */
const handleSelectAgent = (agent: SidebarAgent) => {
  selectedAgentId.value = agent.id
  const existing = sessionStore.sessionList.find(
    (s) => s.title?.includes(agent.name) && s.mode === 'single',
  )
  if (existing) {
    selectSession(existing)
  } else {
    showNewConversationDialog.value = true
  }
}

// ==================== 发送消息 ====================

/**
 * 发送消息：追加用户消息到 Store，通过 WebSocket 发送
 */
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

// ==================== 重试连接 ====================
const handleRetry = () => {
  wsClient.manualRetry()
}

// ==================== 用户资料 ====================

/** 打开编辑资料弹框 */
const handleEditProfile = () => {
  showUserPopover.value = false
  showEditProfileDialog.value = true
}

/** 提交资料更新到 Store */
const handleProfileUpdate = (data: Partial<SidebarUser>) => {
  if (data.name) userInfoStore.setUserName(data.name)
  if (data.email) (userInfoStore as unknown as { setEmail: (e: string) => void }).setEmail(data.email)
  if (data.avatar !== undefined) userInfoStore.setUserAvatar(data.avatar)
  showToast('资料已更新')
}

// ==================== 添加自建 Agent ====================

/** 添加新 Agent 到列表 */
const handleAddAgent = (newAgent: SidebarAgent) => {
  sidebarAgents.value.push(newAgent)
  showAddAgentDialog.value = false
}

// ==================== 登出 ====================

/** 退出登录：断开 WebSocket、清除本地信息、跳转登录页 */
const handlerLogout = async () => {
  showUserPopover.value = false
  wsClient.disconnect()
  const rawRes = await import('../api/login').then((m) => m.logout())
  const res = 'status' in rawRes ? rawRes.data : rawRes

  if (res.code === 0) {
    localStorage.removeItem('x-token')
    userInfoStore.clearUserInfo()
    import('../router/index').then((m) => m.default.push('/login'))
  } else {
    showToast(res.msg, true)
  }
}

// ==================== 恢复当前会话 ====================

/** 页面加载时恢复上一次会话（若有） */
const restoreCurrentSession = async () => {
  const sessionId = sessionStore.currentSessionId
  if (!sessionId) return
  await sessionStore.fetchSessionDetail(sessionId)
  await sessionStore.fetchMessages(sessionId, { page: 1, page_size: 20 })
  wsClient.connect(sessionId)
}

// ==================== 预览区 ====================

/** 关闭预览区，恢复空状态 */
const closePreview = () => {
  previewState.value = { type: 'empty', title: '' }
}

// ==================== 生命周期 ====================

onMounted(async () => {
  // 加载会话列表
  await sessionStore.fetchSessionList({
    owner_id: userInfoStore.userId || 'dev_user',
    page: 1,
    page_size: 50,
  })

  // 加载默认 Agent
  agentStore.fetchDefaultAgent()

  // 监听 WebSocket 连接状态变化
  wsClient.onStateChange((state) => {
    sessionStore.setConnectionState(state)
    if (state === 'connected') {
      isSendLoading.value = false
    }
  })

  // 监听 WebSocket 消息，处理流式消息协议
  wsClient.onReceiveMessage((msg) => {
    const currentSessionId = sessionStore.currentSessionId
    if (!currentSessionId) return

    if (msg.type === 'message_start') {
      sessionStore.streamState.handleMessageStart(msg, currentSessionId)
    } else if (msg.type === 'message_delta') {
      sessionStore.streamState.handleMessageDelta(msg, currentSessionId)
    } else if (msg.type === 'message_end') {
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
    } else if (msg.type === 'message_error') {
      sessionStore.streamState.handleMessageError(msg, currentSessionId)
      isSendLoading.value = false
    } else if (msg.type === 'error') {
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
/* ==================== 三栏基础布局 ==================== */
.workspace {
  position: relative;
  height: 100vh;
  overflow: hidden;
  display: grid;
  grid-template-columns: 400px minmax(0, 1fr) 280px;
  gap: 0;
  padding: 0;
  background: rgb(var(--surface-color));
}

/* ==================== 响应式断点 ==================== */
@media (max-width: 1200px) {
  .workspace {
    grid-template-columns: 304px minmax(0, 1fr);
  }
}

@media (max-width: 900px) {
  .workspace {
    grid-template-columns: 1fr;
  }
}

/* ==================== Element Plus 弹窗样式覆盖 ==================== */
:deep(.el-dialog) {
  border-radius: 12px;
}

:deep(.el-dialog__header) {
  padding: 20px 24px 16px;
  border-bottom: 1px solid #f0f0f0;
}

:deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
}

:deep(.el-button--primary) {
  background: #1a1a1a;
  border-color: #1a1a1a;
}

:deep(.el-button--primary:hover) {
  background: #333;
  border-color: #333;
}
</style>
