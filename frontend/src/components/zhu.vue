<template>
  <div class="workspace">
    <div v-if="showLeft" class="workspace-backdrop" @click="closeMask" />

    <!-- 左侧边栏 -->
    <aside class="sidebar" :class="{ 'is-open': showLeft }">
      <div class="sidebar-rail">
        <button class="rail-avatar" type="button">
          <avatar :info="{ name: userInfoStore.userName || 'Guest', avatar: userInfoStore.avatar }" size="44px" />
        </button>
        <button class="rail-button" :class="{ active: true }" type="button" @click="showLeft = !showLeft">
          <ChatDotRound />
        </button>
        <button class="rail-button" type="button" @click="activePanel = 'contacts'">
          <User />
        </button>
        <button class="rail-logout" type="button" @click="handlerLogout">退出</button>
      </div>

      <div class="sidebar-panel">
        <div class="sidebar-header">
          <div>
            <p class="sidebar-kicker">会话</p>
            <h1>最近聊天</h1>
          </div>
          <button class="mobile-close" type="button" @click="closeMask">×</button>
        </div>

        <button class="new-session-btn" type="button" @click="handleNewSession">
          + 新建会话
        </button>

        <Search v-model:value="searchValue" placeholder="搜索会话" height="38px" width="100%" radius="12px" font-size="14px" background-color="rgb(var(--surface-muted))" />

        <div class="conversation-list">
          <div v-if="sessionStore.isLoadingList" class="loading-hint">加载中...</div>
          <button
            v-for="item in filteredSessionList"
            :key="item.id"
            class="conversation-item"
            :class="{ 'is-active': sessionStore.currentSessionId === item.id }"
            type="button"
            @click="selectSession(item)"
          >
            <avatar :info="{ name: item.title || '会话' }" size="38px" />
            <div class="conversation-copy">
              <div class="conversation-title-row">
                <span class="conversation-title">{{ item.title || '未命名会话' }}</span>
                <dot_hint v-if="item.is_pinned" text="📌" />
              </div>
              <div class="conversation-snippet">
                {{ formatTime(item.updated_at) }}
              </div>
            </div>
          </button>
          <div v-if="!sessionStore.isLoadingList && filteredSessionList.length === 0" class="empty-hint">
            暂无会话
          </div>
        </div>
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
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

import { ChatDotRound, User } from '@element-plus/icons-vue'
import { logout } from '../api/login'
import router from '../router/index'
import { useSessionStore } from '../store/module/useSessionStore'
import { useUserInfoStore } from '../store/module/useUserStore'
import type { ConversationItem } from '../types/agenthub'
import { wsClient, getWsClientReconnectAttempt } from '../utils/ws-client'
import Search from '../veiws/Serach.vue'
import { useToast } from '../veiws/useToast'
import ChatInputArea from '../veiws/Chat-input-area.vue'
import ChatShowArea from '../veiws/Chat-show-area.vue'
import avatar from '../veiws/img/avatar.vue'
import dot_hint from '../veiws/left/dot-hint.vue'

const userInfoStore = useUserInfoStore()
const sessionStore = useSessionStore()
const showToast = useToast()

const showLeft = ref(false)
const activePanel = ref<'chats' | 'contacts'>('chats')
const searchValue = ref('')
const isSendLoading = ref(false)

const reconnectAttempt = computed(() => getWsClientReconnectAttempt())

const chatShow = ref<InstanceType<typeof ChatShowArea>>()
const chatRef = ref<InstanceType<typeof ChatInputArea>>()

const filteredSessionList = computed(() => {
  if (!searchValue.value) return sessionStore.sessionList
  const q = searchValue.value.toLowerCase()
  return sessionStore.sessionList.filter(
    (s) => s.title?.toLowerCase().includes(q),
  )
})

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

const handleNewSession = async () => {
  try {
    const session = await sessionStore.createSession({
      owner_id: userInfoStore.userId || 'dev_user',
      title: `会话 ${new Date().toLocaleString('zh-CN')}`,
      mode: 'single',
    })
    sessionStore.setCurrentSessionId(session.id)
    await sessionStore.fetchMessages(session.id, { page: 1, page_size: 20 })
    wsClient.connect(session.id)
  } catch (e) {
    console.error('创建会话失败', e)
    showToast('创建会话失败', true)
  }
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
}

const handlerLogout = async () => {
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

  wsClient.onStateChange((state) => {
    sessionStore.setConnectionState(state)
    if (state === 'connected') {
      isSendLoading.value = false
    }
  })

  wsClient.onReceiveMessage((msg) => {
    if (msg.type === 'chat_stream' && sessionStore.currentSessionId) {
      sessionStore.appendMessage(sessionStore.currentSessionId, {
        id: msg.message_id || `agent_${Date.now()}`,
        session_id: sessionStore.currentSessionId,
        sender_type: (msg.sender_type as 'human' | 'agent' | 'system') ?? 'agent',
        sender_role: msg.sender_role ?? null,
        content: msg.content ?? '',
        content_type: (msg.content_type as 'text') ?? 'text',
        created_at: msg.created_at ?? new Date().toISOString(),
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
  height: 100vh;
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

.rail-avatar,
.rail-button {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  color: rgb(var(--text-secondary));
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

.rail-logout {
  margin-top: auto;
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  color: rgb(var(--text-secondary));
  font-size: 13px;
  font-weight: 700;
  background: transparent;
  border: none;
  cursor: pointer;
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.sidebar-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  color: rgb(var(--text-muted));
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.sidebar-header h1 {
  margin: 0;
  font-size: 24px;
  line-height: 1.15;
}

.new-session-btn {
  width: 100%;
  padding: 10px;
  border-radius: 12px;
  border: 1px dashed rgb(var(--border-color));
  background: transparent;
  color: rgb(var(--primary-strong));
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.new-session-btn:hover {
  background: rgb(var(--primary-soft));
  border-color: rgb(var(--primary-color));
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
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
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid transparent;
  text-align: left;
  background: transparent;
  cursor: pointer;
}

.conversation-item:hover {
  background: rgb(var(--surface-muted));
}

.conversation-item.is-active {
  background: rgb(var(--primary-soft));
  border-color: rgba(var(--primary-color), 0.35);
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
}

.conversation-title {
  color: rgb(var(--text-color));
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-snippet {
  color: rgb(var(--text-secondary));
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-shell {
  display: flex;
  flex-direction: column;
  height: 100vh;
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
</style>
