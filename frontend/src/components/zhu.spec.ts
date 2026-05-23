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
  clearMessages,
  setCurrentSessionId,
  connect,
  disconnect,
  onStateChange,
  onReceiveMessage,
} = vi.hoisted(() => ({
  fetchSessionList: vi.fn(),
  fetchSessionDetail: vi.fn(),
  fetchMessages: vi.fn(),
  setConnectionState: vi.fn(),
  appendMessage: vi.fn(),
  clearMessages: vi.fn(),
  setCurrentSessionId: vi.fn(),
  connect: vi.fn(),
  disconnect: vi.fn(),
  onStateChange: vi.fn(),
  onReceiveMessage: vi.fn(),
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
    sendMessage: vi.fn(),
  },
  getWsClientReconnectAttempt: () => 0,
}))

vi.mock('../veiws/ToastProvider.vue', () => ({
  useToast: () => vi.fn(),
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
    clearMessages.mockReset()
    setCurrentSessionId.mockReset()
    connect.mockReset()
    disconnect.mockReset()
    onStateChange.mockReset()
    onReceiveMessage.mockReset()
    sessionStore.currentSessionId = 'session-1'
    sessionStore.currentSession = null
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
})
