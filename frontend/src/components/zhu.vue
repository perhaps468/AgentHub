<template>
  <div class="workspace">

    <!-- 左侧边栏 -->
    <aside class="sidebar" :class="{ 'is-open': showLeft }">
      <div class="sidebar-rail">
        <div class="rail-avatar-wrapper">
          <button class="rail-avatar" type="button" @click="showUserPopover = !showUserPopover">
            <avatar :info="{ name: userInfoStore.userName || 'Guest', avatar: userInfoStore.avatar }" size="44px" />
          </button>
          <Transition name="popover-fade">
            <div v-if="showUserPopover" class="user-popover">
              <div class="user-popover-header">
                <avatar :info="{ name: currentUser.name, avatar: currentUser.avatar }" size="56px" />
                <div class="user-popover-info">
                  <span class="user-popover-name">{{ currentUser.name }}</span>
                  <span class="user-popover-email">{{ currentUser.email || 'AgentHub 用户' }}</span>
                </div>
              </div>
              <div class="user-popover-actions">
                <button class="user-popover-btn" type="button" @click="handleEditProfile">编辑资料</button>
                <button class="user-popover-btn logout" type="button" @click="handlerLogout">退出登录</button>
              </div>
            </div>
          </Transition>
        </div>
        <button
          class="rail-button"
          :class="{ active: activeSidebarPanel === 'messages' }"
          type="button"
          @click="activeSidebarPanel = 'messages'"
          title="消息列表"
        >
          <ChatDotRound />
        </button>
        <button
          class="rail-button"
          :class="{ active: activeSidebarPanel === 'agents' }"
          type="button"
          @click="activeSidebarPanel = 'agents'"
          title="Agent 列表"
        >
          <User />
        </button>
      </div>

      <div class="sidebar-panel">
        <!-- 消息列表面板 -->
        <template v-if="activeSidebarPanel === 'messages'">
          <div class="sidebar-header">
            <div>
              <h1>消息列表</h1>
            </div>
            <span class="version-tag">v1.1.3</span>
            <button class="mobile-close" type="button" @click="closeMask">×</button>
          </div>

          <Search
            v-model:value="searchValue"
            placeholder="搜索用户/会话"
            height="38px"
            width="100%"
            radius="12px"
            font-size="14px"
            background-color="rgb(var(--surface-muted))"
          />

          <div class="toolbar-row">
            <button class="new-session-btn" type="button" @click="newDialog">
              新建对话
            </button>
            <button class="toolbar-btn" type="button" @click="showArchived = !showArchived">
              {{ showArchived ? '隐藏归档' : '显示归档' }}
            </button>
          </div>

          <div class="conversation-list">
            <div v-if="sessionStore.isLoadingList" class="loading-hint">加载中...</div>

            <!-- Agent 单聊区 -->
            <div v-if="filteredAgentConversations.length > 0" class="list-section">
              <div class="section-title">Agent 单聊</div>
              <button
                v-for="item in filteredAgentConversations"
                :key="item.id"
                class="conversation-item"
                :class="{ 'is-active': sessionStore.currentSessionId === item.id }"
                type="button"
                @click="selectSession(item)"
              >
                <avatar :info="{ name: item.title || '会话', avatar: getAgentAvatar(item) }" size="38px" />
                <div class="conversation-copy">
                  <div class="conversation-title-row">
                    <span class="conversation-title">{{ item.title || '未命名会话' }}</span>
                    <span v-if="item.mode === 'single'" class="mode-tag single">单聊</span>
                    <dot_hint v-if="item.is_pinned" text="置顶" />
                  </div>
                  <div class="capability-tags" v-if="getAgentTags(item).length > 0">
                    <span v-for="tag in getAgentTags(item).slice(0, 3)" :key="tag" class="capability-tag">{{ tag }}</span>
                    <span v-if="getAgentTags(item).length > 3" class="capability-tag more">+{{ getAgentTags(item).length - 3 }}</span>
                  </div>
                  <div class="conversation-snippet">{{ formatTime(item.updated_at) }}</div>
                </div>
                <div class="conversation-actions">
                  <button class="action-btn" type="button" @click.stop="togglePin(item)">{{ item.is_pinned ? '取消置顶' : '置顶' }}</button>
                  <button class="action-btn" type="button" @click.stop="toggleArchive(item)">归档</button>
                </div>
              </button>
            </div>

            <!-- 群聊区 -->
            <div v-if="filteredGroupConversations.length > 0" class="list-section">
              <div class="section-title">群聊</div>
              <button
                v-for="item in filteredGroupConversations"
                :key="item.id"
                class="conversation-item"
                :class="{ 'is-active': sessionStore.currentSessionId === item.id }"
                type="button"
                @click="selectSession(item)"
              >
                <avatar :info="{ name: '群', avatar: '' }" size="38px" :style="{ background: '#ff7043', color: '#fff' }" />
                <div class="conversation-copy">
                  <div class="conversation-title-row">
                    <span class="conversation-title">{{ item.title || '群聊' }}</span>
                    <span class="mode-tag group">默认</span>
                  </div>
                  <div class="conversation-snippet">{{ formatTime(item.updated_at) }}</div>
                </div>
              </button>
            </div>

            <div v-if="!sessionStore.isLoadingList && filteredSessionList.length === 0" class="empty-hint">
              暂无会话
            </div>
          </div>
        </template>

        <!-- Agent 列表面板 -->
        <template v-else-if="activeSidebarPanel === 'agents'">
          <div class="sidebar-header">
            <div>
              <h1>Agent 列表</h1>
            </div>
            <span class="version-tag">v1.1.3</span>
            <button class="mobile-close" type="button" @click="closeMask">×</button>
          </div>

          <Search
            v-model:value="agentSearchValue"
            placeholder="搜索 Agent"
            height="38px"
            width="100%"
            radius="12px"
            font-size="14px"
            background-color="rgb(var(--surface-muted))"
          />

          <button class="new-Agent-session-btn" type="button" @click="showAddAgentDialog = true">
            + 添加自建 Agent
          </button>

          <div class="agent-list">
            <button
              v-for="agent in filteredAgentList"
              :key="agent.id"
              class="agent-item"
              :class="{ 'is-selected': selectedAgentId === agent.id }"
              type="button"
              @click="handleSelectAgent(agent)"
            >
              <avatar :info="{ name: agent.name, avatar: agent.avatar }" size="42px" :style="getAgentAvatarStyle(agent)" />
              <div class="agent-info">
                <span class="agent-name">{{ agent.name }}</span>
                <span class="agent-desc">{{ agent.description || getAgentPlatformLabel(agent) }}</span>
                <div class="capability-tags">
                  <span v-for="tag in getVisibleCapabilityTags(agent.capabilityTags)" :key="tag" class="capability-tag">{{ tag }}</span>
                  <span v-if="agent.capabilityTags.length > 3" class="capability-tag more">+{{ agent.capabilityTags.length - 3 }}</span>
                </div>
              </div>
            </button>
            <div v-if="filteredAgentList.length === 0" class="empty-hint">
              暂无 Agent
            </div>
          </div>
        </template>
      </div>
    </aside>

    <!-- 中间聊天区 -->
    <main class="chat-shell">
      <header class="chat-header">
        <div class="chat-header-main">
          <button class="header-icon mobile-only" type="button" @click="showLeft = true">☰</button>
          <div>
            <p class="chat-header-kicker">
              {{ sessionStore.currentSession?.mode === 'group' ? '群聊协作' : '单聊会话' }}
            </p>
            <h2>{{ sessionStore.currentSession?.title || '选择或新建会话' }}</h2>
            <p class="chat-header-subtitle">
              {{ sessionStore.currentSession ? `创建于 ${formatTime(sessionStore.currentSession.created_at)}` : '点击左侧新建会话开始聊天' }}
            </p>
          </div>
        </div>
        <ConnectionStatus
          v-if="sessionStore.currentSessionId"
          :state="sessionStore.connectionState"
          :reconnectAttempt="reconnectAttempt"
          @retry="handleRetry"
        />
      </header>

      <section class="chat-stream-panel">
        <ChatShowArea
          ref="chatShow"
          :targetId="sessionStore.currentSessionId || ''"
          :isChatRecordLoading="sessionStore.isLoadingMessages"
          :isSendLoading="isSendLoading"
          :isComplete="false"
        />
      </section>

      <section class="chat-composer-panel">
        <ChatInputArea
          ref="chatRef"
          :sessionId="sessionStore.currentSessionId || ''"
          :disabled="!sessionStore.currentSessionId"
          @send="handleSend"
        />
      </section>
    </main>

    <aside class="blank-panel" aria-hidden="true" />
  </div>
  <!-- 编辑资料弹窗 -->
  <UserProfileDialog
    v-model="showEditProfileDialog"
    :user="currentUser"
    @confirm="handleProfileUpdate"
  />
  <AddAgentDialog
    v-model="showAddAgentDialog"
    :agent="newAgent"
    @confirm="handleAddAgent"
    />
  <NewConversationDialog 
    v-model="showNewConversationDialog" 
    :agents="sidebarAgents" 
    @confirm="handleCreateConversation" 
  />
</template>
<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { ChatDotRound, User } from '@element-plus/icons-vue'
import { logout } from '../api/login'
import router from '../router/index'
import { useSessionStore } from '../store/module/useSessionStore'
import { useUserInfoStore } from '../store/module/useUserStore'
import { useAgentStore } from '../store/index'
import type { ConversationItem, ConversationMode, SidebarAgent, SidebarPanel, SidebarUser } from '../types/agenthub'
import { wsClient, getWsClientReconnectAttempt } from '../utils/ws-client'
import Search from '../veiws/Serach.vue'
import { useToast } from '../veiws/useToast'
import ChatInputArea from '../veiws/Chat-input-area.vue'
import ChatShowArea from '../veiws/Chat-show-area.vue'
import avatar from '../veiws/img/avatar.vue'
import dot_hint from '../veiws/left/dot-hint.vue'
import UserProfileDialog from './zhu/UserProfileDialog.vue'
import ConnectionStatus from './ConnectionStatus.vue'
import AddAgentDialog from './zhu/AddAgentDialog.vue'
import NewConversationDialog from './zhu/NewConversationDialog.vue'
const userInfoStore = useUserInfoStore()
const sessionStore = useSessionStore()
const agentStore = useAgentStore()
const showToast = useToast()

const showLeft = ref(false)
const activeSidebarPanel = ref<SidebarPanel>('messages')
const searchValue = ref('')
const agentSearchValue = ref('')
const isSendLoading = ref(false)
const showArchived = ref(false)

// 用户弹框与编辑资料
const showUserPopover = ref(false)
const showEditProfileDialog = ref(false)

// 新建对话弹窗
const showNewConversationDialog = ref(false)
const newConvType = ref<'single' | 'group'>('single')
const selectedAgentForConv = ref('')
const selectedAgentsForGroup = ref<string[]>([])
const newConvTitle = ref('')
const showMask=ref(false)
// 添加自建 Agent 弹窗
const showAddAgentDialog = ref(false)
const newAgentName = ref('')
const newAgentTags = ref('')
const newAgentDesc = ref('')

// Agent 列表选中
const selectedAgentId = ref('')

// Mock Agent 数据
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
  email: (userInfoStore as any).email || 'admin@example.com',
  bio: (userInfoStore as any).bio || 'AgentHub 用户',
}))

const reconnectAttempt = computed(() => getWsClientReconnectAttempt())

const chatShow = ref<InstanceType<typeof ChatShowArea>>()
const chatRef = ref<InstanceType<typeof ChatInputArea>>()

const filteredSessionList = computed(() => {
  let list = sessionStore.sessionList ?? []
  if (!showArchived.value) {
    list = list.filter((s) => !s.is_archived)
  }
  if (!searchValue.value) return list
  const q = searchValue.value.toLowerCase()
  return list.filter((s) => s.title?.toLowerCase().includes(q))
})

const filteredAgentConversations = computed(() => {
  return filteredSessionList.value.filter((s) => s.mode === 'single')
})

const filteredGroupConversations = computed(() => {
  return filteredSessionList.value.filter((s) => s.mode === 'group')
})

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

const canCreateConversation = computed(() => {
  if (newConvType.value === 'single') return !!selectedAgentForConv.value
  return selectedAgentsForGroup.value.length >= 1
})

const getVisibleCapabilityTags = (tags: string[]) => tags.slice(0, 3)

const getAgentAvatarStyle = (agent: SidebarAgent) => {
  const colors: Record<string, string> = {
    'claude-code': '#e65100',
    codex: '#e65100',
    opencode: '#7b1fa2',
    custom: '#ff7043',
  }
  const bg = colors[agent.platform || 'custom'] || '#9e9e9e'
  return { '--avatar-bg': bg }
}
const newDialog =()=>{
  showNewConversationDialog.value = true
}
// const handleNewSession = async () => {
//   try {
//     const session = await sessionStore.createSession({
//       owner_id: userInfoStore.userId || 'dev_user',
//       title: `会话 ${new Date().toLocaleString('zh-CN')}`,
//       mode: 'single',
//     })
//     sessionStore.setCurrentSessionId(session.id)
//     await sessionStore.fetchMessages(session.id, { page: 1, page_size: 20 })
//     wsClient.connect(session.id)
//   } catch (e) {
//     console.error('创建会话失败', e)
//     showToast('创建会话失败', true)
//   }
// }
const handleAddAgent = (newAgent: SidebarAgent) => {
  sidebarAgents.value.push(newAgent)
  showAddAgentDialog.value = false
}


const getAgentPlatformLabel = (agent: SidebarAgent) => {
  const labels: Record<string, string> = {
    'claude-code': 'Claude',
    codex: 'Codex',
    opencode: 'OpenCode',
    custom: '自建',
  }
  return labels[agent.platform || 'custom'] || agent.platform || ''
}

const formatPlatformLabel = (platform?: string) => {
  const labels: Record<string, string> = {
    'claude-code': 'Claude',
    codex: 'Codex',
    opencode: 'OpenCode',
    custom: '自建',
  }
  return platform ? labels[platform] || platform : ''
}

const goToAgentPanelFromCreateDialog = () => {
  activeSidebarPanel.value = 'agents'
  showNewConversationDialog.value = false
}

const resetCustomAgentForm = () => {
  newAgentName.value = ''
  newAgentTags.value = ''
  newAgentDesc.value = ''
}



const getAgentAvatar = (item: ConversationItem) => {
  const agent = sidebarAgents.value.find((a) => item.title?.includes(a.name))
  return agent?.avatar || ''
}

const getAgentTags = (item: ConversationItem) => {
  const agent = sidebarAgents.value.find((a) => item.title?.includes(a.name))
  return agent?.capabilityTags || []
}


const formatTime = (iso: string) => {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return d.toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
  } catch {
    return iso
  }
}

const selectSession = async (item: ConversationItem) => {
  if (sessionStore.currentSessionId === item.id) {
    closeMask()
    return
  }

  wsClient.disconnect()
  sessionStore.clearMessages(item.id)
  sessionStore.setCurrentSessionId(item.id)
  await sessionStore.fetchSessionDetail(item.id)
  await sessionStore.fetchMessages(item.id, { page: 1, page_size: 20 })
  wsClient.connect(item.id)
  closeMask()
}

const handleCreateConversation = async (payload: { mode: ConversationMode; title: string; agentId?: string; participantAgentIds?: string[] }) => {
  if (payload.mode === 'single' && !payload.agentId) {
    showToast('请先选择一个 Agent', true)
    return
  }
  if (payload.mode === 'group' && (!payload.participantAgentIds || payload.participantAgentIds.length === 0)) {
    showToast('请至少选择一个 Agent', true)
    return
  }

  const mode = newConvType.value === 'single' ? 'single' : 'group'
  let title = newConvTitle.value.trim()

  if (!title) {
    if (mode === 'single') {
      const agent = sidebarAgents.value.find((a) => a.id === selectedAgentForConv.value)
      title = agent ? `${agent.name} 对话` : `会话 ${new Date().toLocaleString('zh-CN')}`
    } else {
      title = '多 Agent 协作'
    }
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
    resetNewConvForm()
  } catch (e) {
    console.error('创建会话失败', e)
    showToast('创建会话失败', true)
  }
}

const resetNewConvForm = () => {
  newConvType.value = 'single'
  selectedAgentForConv.value = ''
  selectedAgentsForGroup.value = []
  newConvTitle.value = ''
}

const handleSelectAgent = (agent: SidebarAgent) => {
  selectedAgentId.value = agent.id
  const existing = sessionStore.sessionList.find((s) => s.title?.includes(agent.name) && s.mode === 'single')
  if (existing) {
    selectSession(existing)
  } else {
    showNewConversationDialog.value = true
    newConvType.value = 'single'
    selectedAgentForConv.value = agent.id
  }
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

const handleEditProfile = () => {
  showUserPopover.value = false
  showEditProfileDialog.value = true
  showMask.value=true
}

const handleProfileUpdate = (data: Partial<SidebarUser>) => {
  if (data.name) userInfoStore.setUserName(data.name)
  if (data.email) userInfoStore.setEmail(data.email)
  if (data.avatar !== undefined) userInfoStore.setUserAvatar(data.avatar)
  showToast('资料已更新')
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
    content_type: 'text',
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

const restoreCurrentSession = async () => {
  const sessionId = sessionStore.currentSessionId
  if (!sessionId) return

  await sessionStore.fetchSessionDetail(sessionId)
  await sessionStore.fetchMessages(sessionId, { page: 1, page_size: 20 })
  wsClient.connect(sessionId)
}

const closeMask = () => {
  showLeft.value = false
  showUserPopover.value = false
}

const handlerLogout = async () => {
  showUserPopover.value = false
  wsClient.disconnect()
  const rawRes = await logout()
  const res = 'status' in rawRes ? rawRes.data : rawRes

  if (res.code === 0) {
    localStorage.removeItem('x-token')
    userInfoStore.clearUserInfo()
    router.push('/login')
  } else {
    showToast(res.msg, true)
  }
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
    }
  })

  wsClient.onReceiveMessage((msg) => {
    const currentSessionId = sessionStore.currentSessionId
    if (!currentSessionId) return

    if (msg.type === 'agent_typing') {
      sessionStore.streamState.handleAgentTyping(msg as any, currentSessionId)
    } else if (msg.type === 'chat_stream') {
      const result = sessionStore.streamState.handleChatStream(msg as any, currentSessionId)
      
      if (result?.stream.message_id) {
        const checkInterval = setInterval(() => {
          const checkResult = sessionStore.streamState.checkStreamComplete(result.stream.stream_id)
          if (checkResult.isComplete && checkResult.stream) {
            sessionStore.mergeOrUpdateMessage(currentSessionId, {
              id: checkResult.stream.message_id!,
              session_id: currentSessionId,
              sender_type: 'agent',
              sender_role: checkResult.stream.sender_role,
              content: checkResult.stream.accumulated_content,
              content_type: 'text',
              created_at: checkResult.stream.created_at,
              delivery_status: 'completed',
            })
            sessionStore.streamState.finalizeStream(result.stream.stream_id)
            clearInterval(checkInterval)
          }
        }, 100)

        setTimeout(() => clearInterval(checkInterval), 30000)
      }
      
      if (result?.shouldFinalize && result.stream.message_id) {
        sessionStore.mergeOrUpdateMessage(currentSessionId, {
          id: result.stream.message_id,
          session_id: currentSessionId,
          sender_type: 'agent',
          sender_role: result.stream.sender_role,
          content: result.stream.accumulated_content,
          content_type: 'text',
          created_at: result.stream.created_at,
          delivery_status: 'completed',
        })
        sessionStore.streamState.finalizeStream(result.stream.stream_id)
      }
      isSendLoading.value = false
    } else if (msg.type === 'error') {
      sessionStore.streamState.handleError(msg as any, currentSessionId, async () => {
        await sessionStore.fetchMessages(currentSessionId, { page: 1, page_size: 20 })
      })
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
  display: grid;
  grid-template-columns: 304px minmax(0, 1fr) 280px;
  gap: 0;
  padding: 0;
  background: rgb(var(--surface-color));
}

.workspace-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  background: rgba(18, 23, 20, 0.18);
}

.sidebar,
.chat-shell,
.blank-panel {
  height: 100%;
  overflow: hidden;
  background: rgb(var(--surface-color));
}

.sidebar {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  border-right: 1px solid rgb(var(--border-color));
}

.sidebar-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 12px;
  background: rgb(var(--surface-muted));
  border-right: 1px solid rgb(var(--border-color));
}

.rail-avatar-wrapper {
  position: relative;
}

.rail-avatar,
.rail-button {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  color: rgb(var(--text-secondary));
  background: transparent;
  border: none;
  cursor: pointer;
}

.rail-button :deep(svg) {
  width: 22px;
  height: 22px;
}

.rail-button.active,
.rail-button:hover,
.rail-avatar:hover {
  background: rgb(var(--primary-soft));
  color: rgb(var(--primary-strong));
}

/* 用户弹框 */
.user-popover {
  position: absolute;
  top: 0;
  left: 56px;
  z-index: 100;
  width: 240px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  padding: 16px;
}

.user-popover-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.user-popover-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.user-popover-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
}

.user-popover-email {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-popover-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-popover-btn {
  width: 100%;
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #333;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.user-popover-btn:hover {
  background: #f5f5f5;
}

.user-popover-btn.logout {
  color: #e53935;
  border-color: #ffcdd2;
}

.user-popover-btn.logout:hover {
  background: #ffebee;
}

.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

.sidebar-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px 18px 18px;
  min-width: 0;
  overflow-y: auto;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sidebar-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.2;
}

.version-tag {
  font-size: 12px;
  color: #9c27b0;
  font-weight: 500;
}

.toolbar-row {
  display: flex;
  gap: 8px;
}

.new-session-btn {
  flex: 1;
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid #1a1a1a;
  background: #1a1a1a;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}
.new-Agent-session-btn{
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid #1a1a1a;
  background: #1a1a1a;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s
}

.new-session-btn:hover {
  background: #333;
}

.toolbar-btn {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #666;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.toolbar-btn:hover {
  background: #f5f5f5;
}

/* 列表分区 */
.list-section {
  margin-bottom: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
  padding-left: 4px;
}

.conversation-list,
.agent-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  overflow-y: auto;
}

.loading-hint,
.empty-hint {
  text-align: center;
  color: rgb(var(--text-muted));
  font-size: 13px;
  padding: 20px 0;
}

.conversation-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid transparent;
  text-align: left;
  background: transparent;
  cursor: pointer;
  position: relative;
}

.conversation-item:hover {
  background: #f9f9f9;
}

.conversation-item.is-active {
  background: #e3f2fd;
  border-color: #1976d2;
}

.conversation-copy {
  min-width: 0;
  flex: 1;
}

.conversation-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.conversation-title {
  color: #1a1a1a;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mode-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.mode-tag.single {
  background: #e3f2fd;
  color: #1976d2;
}

.mode-tag.group {
  background: #fff3e0;
  color: #e65100;
}

.conversation-snippet {
  color: #999;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-actions {
  display: none;
  flex-direction: column;
  gap: 4px;
}

.conversation-item:hover .conversation-actions {
  display: flex;
}

.action-btn {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #666;
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
}

.action-btn:hover {
  background: #f5f5f5;
}

/* 能力标签 */
.capability-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.capability-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f5f5f5;
  color: #666;
}

.capability-tag.more {
  background: #e0e0e0;
  color: #999;
}

/* Agent 列表项 */
.agent-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid transparent;
  text-align: left;
  background: transparent;
  cursor: pointer;
}

.agent-item:hover {
  background: #f9f9f9;
}

.agent-item.is-selected {
  background: #e3f2fd;
  border-color: #1976d2;
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

.agent-desc {
  font-size: 12px;
  color: #999;
}

/* 新建对话 / 自建 Agent 弹窗 */
.create-conversation-form,
.edit-profile-form {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.agent-picker-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-height: 240px;
  overflow-y: auto;
  padding-right: 4px;
}

.agent-picker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #ececec;
  border-radius: 10px;
  background: #fff;
  cursor: pointer;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.agent-picker-item:hover,
.agent-picker-item.selected {
  border-color: #1f1f1f;
  background: #fafafa;
}

.agent-picker-item input {
  width: 16px;
  height: 16px;
  accent-color: #1677ff;
}

.agent-picker-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.agent-picker-name {
  color: #262626;
  font-size: 14px;
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
  font-size: 12px;
  line-height: 1.4;
}

.link-to-agent-panel {
  align-self: flex-start;
  padding: 0;
  border: none;
  background: transparent;
  color: #737373;
  font-size: 13px;
  cursor: pointer;
}

.link-to-agent-panel:hover {
  color: #262626;
  text-decoration: underline;
}

.profile-dialog-btn {
  min-width: 72px;
  border: 1px solid #ececec;
  border-radius: 8px;
  background: #fff;
  color: #262626;
  font-size: 14px;
  padding: 8px 14px;
  cursor: pointer;
}

.profile-dialog-btn:hover {
  background: #f8f8f8;
}

.profile-dialog-btn.primary {
  border-color: #1f1f1f;
  background: #1f1f1f;
  color: #fff;
}

.profile-dialog-btn.primary:hover {
  background: #333;
}

.profile-dialog-btn:disabled,
.profile-dialog-btn.primary:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 聊天区域 */
.chat-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  border-right: 1px solid rgb(var(--border-color));
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 76px;
  padding: 16px 24px;
  border-bottom: 1px solid rgb(var(--border-color));
}

.chat-header-main {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.chat-header-kicker {
  margin: 0 0 4px;
  color: rgb(var(--text-muted));
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.chat-header h2 {
  margin: 0 0 4px;
  font-size: 24px;
  line-height: 1.15;
}

.chat-header-subtitle {
  margin: 0;
  color: rgb(var(--text-secondary));
  font-size: 13px;
}

.chat-stream-panel {
  min-height: 0;
  flex: 1;
  overflow: hidden;
}

.chat-composer-panel {
  border-top: 1px solid rgb(var(--border-color));
}

.blank-panel {
  background: rgb(var(--surface-color));
}

.mobile-only,
.mobile-close {
  display: none;
}

.header-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgb(var(--surface-muted));
  color: rgb(var(--text-secondary));
}

@media (max-width: 1200px) {
  .workspace {
    grid-template-columns: 304px minmax(0, 1fr);
  }

  .blank-panel {
    display: none;
  }
}

@media (max-width: 900px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: min(320px, 88vw);
    z-index: 30;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }

  .sidebar.is-open {
    transform: translateX(0);
  }

  .mobile-only {
    display: inline-flex;
  }

  .mobile-close {
    display: inline-flex;
  }
}

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
