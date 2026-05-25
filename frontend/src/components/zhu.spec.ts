import { reactive } from 'vue'
import { shallowMount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Zhu from './zhu.vue'

const {
  fetchSessionList,
  fetchSessionDetail,
  fetchMessages,
  setConnectionState,
  appendMessage,
  appendHumanMessage,
  clearMessages,
  setCurrentSessionId,
  connect,
  disconnect,
  onStateChange,
  onReceiveMessage,
  sendMessage,
  fetchDefaultAgent,
  showToast,
} = vi.hoisted(() => ({
  fetchSessionList: vi.fn(),
  fetchSessionDetail: vi.fn(),
  fetchMessages: vi.fn(),
  setConnectionState: vi.fn(),
  appendMessage: vi.fn(),
  appendHumanMessage: vi.fn(),
  clearMessages: vi.fn(),
  setCurrentSessionId: vi.fn(),
  connect: vi.fn(),
  disconnect: vi.fn(),
  onStateChange: vi.fn(),
  onReceiveMessage: vi.fn(),
  sendMessage: vi.fn(),
  fetchDefaultAgent: vi.fn(),
  showToast: vi.fn(),
}))

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
  appendMessage,
  appendHumanMessage,
  clearMessages,
  setCurrentSessionId,
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
  useAgentStore: () => ({
    fetchDefaultAgent,
    agent: null,
  }),
}))

vi.mock('../veiws/useToast', () => ({
  useToast: () => showToast,
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
    appendMessage.mockReset()
    appendHumanMessage.mockReset()
    clearMessages.mockReset()
    setCurrentSessionId.mockReset()
    connect.mockReset()
    disconnect.mockReset()
    onStateChange.mockReset()
    onReceiveMessage.mockReset()
    sendMessage.mockReset().mockReturnValue(true)
    fetchDefaultAgent.mockReset()
    showToast.mockReset()
    sessionStore.currentSessionId = 'session-1'
    sessionStore.currentSession = null
    sessionStore.connectionState = 'disconnected'
  })

  it('restores the persisted session detail and messages before reconnecting websocket on mount', async () => {
    shallowMount(Zhu)
    await flushPromises()

    expect(fetchSessionList).toHaveBeenCalledWith({
      owner_id: 'dev_user',
      page: 1,
      page_size: 50,
    })
    expect(fetchSessionDetail).toHaveBeenCalledWith('session-1')
    expect(fetchMessages).toHaveBeenCalledWith('session-1', {
      page: 1,
      page_size: 20,
    })
    expect(connect).toHaveBeenCalledWith('session-1')

    expect(fetchSessionList.mock.invocationCallOrder[0]).toBeLessThan(
      fetchSessionDetail.mock.invocationCallOrder[0],
    )
    expect(fetchSessionDetail.mock.invocationCallOrder[0]).toBeLessThan(
      fetchMessages.mock.invocationCallOrder[0],
    )
    expect(fetchMessages.mock.invocationCallOrder[0]).toBeLessThan(
      connect.mock.invocationCallOrder[0],
    )
  })

  it('queues sending until websocket becomes connected', async () => {
    let stateChangeHandler: ((state: string) => void) | undefined
    onStateChange.mockImplementation((cb) => {
      stateChangeHandler = cb
      return vi.fn()
    })

    const wrapper = shallowMount(Zhu, {
      global: {
        stubs: {
          ChatInputArea: {
            emits: ['send'],
            template: '<button data-testid="send" @click="$emit(\'send\', \'hello\')">send</button>',
          },
          ChatShowArea: true,
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

    sessionStore.connectionState = 'connecting'
    sendMessage.mockReturnValue(false)

    await wrapper.get('[data-testid="send"]').trigger('click')

    // P1-3-4: Optimistic human message is appended locally.
    expect(appendHumanMessage).toHaveBeenCalledTimes(1)
    // During the queued phase, sendMessage returns false (WS not connected yet),
    // but the new protocol does NOT show a toast for this transient queued state.
    // The toast-only-once logic handles it differently in the new protocol.
    // showToast should NOT be called during the queued phase.
    expect(showToast).not.toHaveBeenCalled()

    sendMessage.mockReturnValue(true)
    stateChangeHandler?.('connected')

    expect(sendMessage).toHaveBeenCalledWith('hello')
  })
})
