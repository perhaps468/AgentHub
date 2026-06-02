import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Zhu from './zhu.vue'

const {
  fetchSessionList,
  fetchSessionDetail,
  fetchMessages,
  setConnectionState,
  appendHumanMessage,
  clearMessages,
  setCurrentSessionId,
  restorePendingChangesForSession,
  connect,
  disconnect,
  onStateChange,
  onReceiveMessage,
  sendMessage,
  fetchAgentConfig,
  fetchDefaultAgent,
  fetchAgents,
  showToast,
  push,
} = vi.hoisted(() => ({
  fetchSessionList: vi.fn(),
  fetchSessionDetail: vi.fn(),
  fetchMessages: vi.fn(),
  setConnectionState: vi.fn(),
  appendHumanMessage: vi.fn(),
  clearMessages: vi.fn(),
  setCurrentSessionId: vi.fn(),
  restorePendingChangesForSession: vi.fn(),
  connect: vi.fn(),
  disconnect: vi.fn(),
  onStateChange: vi.fn(),
  onReceiveMessage: vi.fn(),
  sendMessage: vi.fn(),
  fetchAgentConfig: vi.fn(),
  fetchDefaultAgent: vi.fn(),
  fetchAgents: vi.fn(),
  showToast: vi.fn(),
  push: vi.fn(),
}))

const agentStore = reactive({
  agent: null,
  agents: [],
  availableModels: ['qwen3-coder-plus'],
  availableCapabilityTags: ['代码生成', '测试验证'],
  fetchAgentConfig,
  fetchDefaultAgent,
  fetchAgents,
  createAgent: vi.fn(),
})

const sessionStore = reactive({
  sessionList: [],
  currentSessionId: 'session-1' as string | null,
  currentSession: null,
  connectionState: 'disconnected',
  isLoadingList: false,
  isLoadingMessages: false,
  fetchSessionList,
  fetchSessionDetail,
  fetchMessages,
  setConnectionState,
  appendHumanMessage,
  clearMessages,
  setCurrentSessionId,
  restorePendingChangesForSession,
  streamState: {
    handleMessageStart: vi.fn(),
    handleMessageDelta: vi.fn(),
    handleMessageEnd: vi.fn(),
    handleMessageError: vi.fn(),
    handleToolEvent: vi.fn(),
    handleRuntimeState: vi.fn(),
    handleChangePreview: vi.fn(),
    handleApplyResult: vi.fn(),
    handleRepairState: vi.fn(),
    getSessionIdForStream: vi.fn(),
  },
})

const userInfoStore = reactive({
  userId: '',
  userName: '',
  avatar: '',
  clearUserInfo: vi.fn(),
})

vi.mock('../store/module/useSessionStore', () => ({
  useSessionStore: () => sessionStore,
}))

vi.mock('../store/module/useUserStore', () => ({
  useUserInfoStore: () => userInfoStore,
}))

vi.mock('../utils/ws-client', () => ({
  wsClient: {
    connect,
    disconnect,
    onStateChange,
    onReceiveMessage,
    manualRetry: vi.fn(),
    sendMessage,
  },
  getWsClientReconnectAttempt: () => 0,
}))

vi.mock('../store/index', () => ({
  useAgentStore: () => agentStore,
}))

vi.mock('../veiws/useToast', () => ({
  useToast: () => showToast,
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}))

describe('zhu', () => {
  beforeEach(() => {
    fetchSessionList.mockReset().mockResolvedValue({ items: [] })
    fetchSessionDetail.mockReset().mockResolvedValue({
      id: 'session-1',
      title: 'Recovered Session',
      mode: 'single',
      created_at: '2026-05-22T00:00:00Z',
    })
    fetchMessages.mockReset().mockResolvedValue({
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
      has_more: false,
    })
    setConnectionState.mockReset()
    appendHumanMessage.mockReset()
    clearMessages.mockReset()
    setCurrentSessionId.mockReset()
    restorePendingChangesForSession.mockReset().mockResolvedValue({
      items: [],
      total: 0,
      session_id: 'session-1',
    })
    connect.mockReset()
    disconnect.mockReset()
    onStateChange.mockReset()
    onReceiveMessage.mockReset()
    sendMessage.mockReset().mockReturnValue(true)
    fetchAgentConfig.mockReset().mockResolvedValue({
      available_models: ['qwen3-coder-plus'],
      available_capability_tags: ['代码生成', '测试验证'],
    })
    fetchDefaultAgent.mockReset().mockResolvedValue({
      id: 'pm_agent',
      name: 'PM Agent',
      capability_tags: ['规划'],
    })
    fetchAgents.mockReset().mockResolvedValue([])
    showToast.mockReset()
    push.mockReset()
    sessionStore.currentSessionId = 'session-1'
    sessionStore.currentSession = null
    sessionStore.connectionState = 'disconnected'
    agentStore.agents = []
  })

  it('restores the persisted session detail and messages before reconnecting websocket on mount', async () => {
    shallowMount(Zhu)
    await flushPromises()

    expect(fetchSessionList).toHaveBeenCalledWith({
      owner_id: 'dev_user',
      page: 1,
      page_size: 50,
    })
    expect(fetchAgentConfig).toHaveBeenCalled()
    expect(fetchDefaultAgent).toHaveBeenCalled()
    expect(fetchAgents).toHaveBeenCalled()
    expect(fetchSessionDetail).toHaveBeenCalledWith('session-1')
    expect(fetchMessages).toHaveBeenCalledWith('session-1', {
      page: 1,
      page_size: 20,
    })
    expect(restorePendingChangesForSession).toHaveBeenCalledWith('session-1', {
      clearExisting: true,
      clearInFlight: false,
    })
    expect(connect).toHaveBeenCalledWith('session-1')
  })

  it('re-syncs pending changes after websocket reconnect succeeds', async () => {
    let stateChangeHandler: ((state: string) => void) | undefined
    onStateChange.mockImplementation((cb) => {
      stateChangeHandler = cb
      return vi.fn()
    })

    shallowMount(Zhu)
    await flushPromises()

    restorePendingChangesForSession.mockClear()

    stateChangeHandler?.('connected')
    await flushPromises()

    expect(restorePendingChangesForSession).toHaveBeenCalledWith('session-1', {
      clearExisting: true,
      clearInFlight: true,
    })
  })

  it('shows an error toast when websocket send fails', async () => {
    const wrapper = shallowMount(Zhu, {
      global: {
        stubs: {
          ChatWorkspace: {
            emits: ['send'],
            template: '<button data-testid="send" @click="$emit(\'send\', \'hello\')">send</button>',
          },
          Search: true,
          avatar: true,
          dot_hint: true,
          ConnectionStatus: true,
          ChatDotRound: true,
          User: true,
          RouterLink: true,
          RouterView: true,
          Transition: false,
        },
      },
    })
    await flushPromises()

    sendMessage.mockReturnValue(false)

    await wrapper.get('[data-testid="send"]').trigger('click')

    expect(appendHumanMessage).toHaveBeenCalledTimes(1)
    expect(showToast).toHaveBeenCalledWith('发送失败，请检查网络', true)
  })
})
