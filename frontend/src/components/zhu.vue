<template>
  <!-- ==================== 三栏布局容器：左侧列表区 | 中间聊天区 | 右侧预览区 ==================== -->
  <div class="workspace">
    <!-- 动态背景光晕效果 -->
    <div class="glow-orb glow-orb-1"></div>
    <div class="glow-orb glow-orb-2"></div>
    <div class="glow-orb glow-orb-3"></div>

    <!-- 装饰性网格点阵 -->
    <div class="grid-pattern"></div>

    <!-- 玻璃态主容器 -->
    <div class="glass-container">
      <!-- 左侧列表区 -->
      <LeftSidebarArea
        :show-left="showLeft"
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
 * 高级玻璃态设计，白色为主，带动态效果
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

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
const router = useRouter()
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

/* 右上角蓝色光晕 */
.glow-orb-1 {
  width: 600px;
  height: 600px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
  top: -200px;
  right: -100px;
  animation-delay: 0s;
}

/* 左下角紫色光晕 */
.glow-orb-2 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.12) 0%, transparent 70%);
  bottom: -150px;
  left: -100px;
  animation-delay: -4s;
}

/* 中心青色光晕 */
.glow-orb-3 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(6, 182, 212, 0.1) 0%, transparent 70%);
  top: 40%;
  left: 30%;
  transform: translate(-50%, -50%);
  animation-delay: -7s;
}

/* 光晕浮动动画 */
@keyframes float {
  0%, 100% {
    transform: translate(0, 0) scale(1);
  }
  33% {
    transform: translate(40px, -40px) scale(1.08);
  }
  66% {
    transform: translate(-30px, 30px) scale(0.95);
  }
}

/* ==================== 装饰性网格点阵 ==================== */
.grid-pattern {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 1px 1px, rgba(59, 130, 246, 0.06) 1px, transparent 0);
  background-size: 50px 50px;
  pointer-events: none;
}

/* ==================== 玻璃态主容器 ==================== */
.glass-container {
  position: relative;
  z-index: 10;
  height: 100%;
  display: grid;
  grid-template-columns: 400px minmax(0, 1fr) 340px;
  gap: 0;
  padding: 16px;
  box-sizing: border-box;
}

/* 玻璃态效果：毛玻璃 + 半透明背景 */
.glass-container > :deep(*) {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  box-shadow:
    0 8px 32px rgba(59, 130, 246, 0.08),
    0 2px 8px rgba(0, 0, 0, 0.04),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.6);
  transition: box-shadow 0.3s ease, transform 0.3s ease;
}

/* 悬停时轻微上浮 */
.glass-container > :deep(*):hover {
  box-shadow:
    0 12px 40px rgba(59, 130, 246, 0.12),
    0 4px 12px rgba(0, 0, 0, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

/* ==================== 响应式断点 ==================== */
@media (max-width: 1400px) {
  .glass-container {
    grid-template-columns: 72px 300px minmax(0, 1fr) 300px;
    padding: 12px;
  }
}

@media (max-width: 1200px) {
  .glass-container {
    grid-template-columns: 72px 300px minmax(0, 1fr);
    padding: 12px;
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
