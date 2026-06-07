import { reactive } from 'vue'
import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import Zhu from './zhu.vue'

const {
  fetchSessionList,
  fetchSessionDetail,
  fetchMessages,
  createSession,
  setConnectionState,
  updateTaskStatus,
  appendHumanMessage,
  mergeOrUpdateMessage,
  clearMessages,
  setCurrentSessionId,
  restorePendingChangesForSession,
  fetchLatestRun,
  connect,
  disconnect,
  onStateChange,
  onReceiveMessage,
  sendMessage,
  fetchAgentConfig,
  fetchDefaultAgent,
  fetchAgents,
  updateAgent,
  syncSessionTitlesForAgentRename,
  showToast,
  push,
} = vi.hoisted(() => ({
  fetchSessionList: vi.fn(),
  fetchSessionDetail: vi.fn(),
  fetchMessages: vi.fn(),
  createSession: vi.fn(),
  setConnectionState: vi.fn(),
  updateTaskStatus: vi.fn(),
  appendHumanMessage: vi.fn(),
  mergeOrUpdateMessage: vi.fn(),
  clearMessages: vi.fn(),
  setCurrentSessionId: vi.fn(),
  restorePendingChangesForSession: vi.fn(),
  fetchLatestRun: vi.fn(),
  connect: vi.fn(),
  disconnect: vi.fn(),
  onStateChange: vi.fn(),
  onReceiveMessage: vi.fn(),
  sendMessage: vi.fn(),
  fetchAgentConfig: vi.fn(),
  fetchDefaultAgent: vi.fn(),
  fetchAgents: vi.fn(),
  updateAgent: vi.fn(),
  syncSessionTitlesForAgentRename: vi.fn(),
  showToast: vi.fn(),
  push: vi.fn(),
}))

const agentStore = reactive({
  agent: null as any,
  agents: [] as any[],
  availableModels: ['qwen3-coder-plus'],
  availableCapabilityTags: ['浠ｇ爜鐢熸垚', '娴嬭瘯楠岃瘉'],
  fetchAgentConfig,
  fetchDefaultAgent,
  fetchAgents,
  updateAgent,
  syncSessionTitlesForAgentRename,
  createAgent: vi.fn(),
})

const sessionStore = reactive({
  sessionList: [] as any[],
  currentSessionId: 'session-1' as string | null,
  currentSession: null as any,
  connectionState: 'disconnected',
  isLoadingList: false,
  isLoadingMessages: false,
  fetchSessionList,
  fetchSessionDetail,
  fetchMessages,
  createSession,
  setConnectionState,
  updateTaskStatus,
  appendHumanMessage,
  mergeOrUpdateMessage,
  clearMessages,
  setCurrentSessionId,
  restorePendingChangesForSession,
  fetchLatestRun,
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
    setOnTaskStatusUpdate: vi.fn(),
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
  ws: {
    connect,
    disconnect,
    onStateChange,
    onReceiveMessage,
    getConnectedSessions: vi.fn(() => []),
    manualRetry: vi.fn(),
    send: sendMessage,
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
    createSession.mockReset().mockResolvedValue({
      id: 'session-created',
      title: 'Created Session',
      mode: 'group',
      workspace: null,
    })
    setConnectionState.mockReset()
    updateTaskStatus.mockReset()
    appendHumanMessage.mockReset()
    mergeOrUpdateMessage.mockReset()
    clearMessages.mockReset()
    setCurrentSessionId.mockReset()
    restorePendingChangesForSession.mockReset().mockResolvedValue({
      items: [],
      total: 0,
      session_id: 'session-1',
    })
    fetchLatestRun.mockReset().mockResolvedValue(null)
    connect.mockReset()
    disconnect.mockReset()
    onStateChange.mockReset()
    onReceiveMessage.mockReset()
    sendMessage.mockReset().mockReturnValue(true)
    fetchAgentConfig.mockReset().mockResolvedValue({
      available_models: ['qwen3-coder-plus'],
      available_capability_tags: ['浠ｇ爜鐢熸垚', '娴嬭瘯楠岃瘉'],
    })
    fetchDefaultAgent.mockReset().mockResolvedValue({
      id: 'pm_agent',
      name: 'PM Agent',
      capability_tags: ['瑙勫垝'],
    })
    fetchAgents.mockReset().mockResolvedValue([])
    updateAgent.mockReset().mockResolvedValue({
      previousAgentName: 'Old Agent',
      updatedAgentName: 'New Agent',
    })
    syncSessionTitlesForAgentRename.mockReset().mockResolvedValue([])
    showToast.mockReset()
    push.mockReset()
    sessionStore.currentSessionId = 'session-1'
    sessionStore.currentSession = null
    sessionStore.connectionState = 'disconnected'
    agentStore.agent = null
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
    expect(fetchLatestRun).toHaveBeenCalledWith('session-1')
    expect(restorePendingChangesForSession).toHaveBeenCalledWith('session-1', {
      clearExisting: true,
      clearInFlight: false,
    })
    expect(connect).toHaveBeenCalledWith('session-1')
  })

  it('re-syncs pending changes after websocket reconnect succeeds', async () => {
    let stateChangeHandler: ((state: string) => void) | undefined
    onStateChange.mockImplementation((_sessionId, cb) => {
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
            template: '<button data-testid="send" @click="$emit(\'send\', { text: \'hello\', targetAgentIds: [], selectedAgents: [], mentions: [], nodes: [{ type: \'text\', content: \'hello\' }] })">send</button>',
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
    expect(showToast).toHaveBeenCalledTimes(1)
    expect(showToast).toHaveBeenLastCalledWith(expect.any(String), true)
  })

  it('uses the group host agent as the primary agent for group conversations', async () => {
    agentStore.agent = {
      id: 'test',
      name: 'test',
      capability_tags: ['test'],
    }
    agentStore.agents = [
      {
        id: 'group_host_user_1',
        name: '缇よ亰涓籄gent',
        avatar: '',
        capabilityTags: ['璋冨害'],
        description: 'group host',
        platform: 'custom',
        isCustom: true,
        role: 'PM',
        model: 'qwen',
        system_prompt: 'host',
      },
      {
        id: 'test',
        name: 'test',
        avatar: '',
        capabilityTags: ['test'],
        description: 'test',
        platform: 'custom',
        isCustom: true,
        role: 'Engineer',
        model: 'qwen',
        system_prompt: 'test',
      },
    ]

    const wrapper = shallowMount(Zhu, {
      global: {
        stubs: {
          LeftSidebarArea: true,
          ChatWorkspace: true,
          PreviewPanel: true,
          UserProfileDialog: true,
          AddAgentDialog: true,
          NewConversationDialog: {
            name: 'NewConversationDialog',
            props: ['primaryAgent', 'agents'],
            template: '<div />',
          },
        },
      },
    })
    await flushPromises()

    const dialog = wrapper.findComponent({ name: 'NewConversationDialog' })
    expect(dialog.props('primaryAgent')).toMatchObject({
      id: 'group_host_user_1',
      name: '缇よ亰涓籄gent',
    })
    expect(dialog.props('agents')).toEqual([
      expect.objectContaining({ id: 'test' }),
    ])
  })

  it('does not fall back to the default builtin pm as a group primary agent', async () => {
    agentStore.agent = {
      id: 'pm_agent',
      name: 'PM Agent',
      capability_tags: ['pm'],
      is_builtin: true,
    }
    agentStore.agents = [
      {
        id: 'coder-1',
        name: 'Coder',
        avatar: '',
        capabilityTags: ['code'],
        description: 'coder',
        platform: 'custom',
        isCustom: true,
        role: 'Engineer',
        model: 'qwen',
        system_prompt: 'coder',
      },
    ]

    const wrapper = shallowMount(Zhu, {
      global: {
        stubs: {
          LeftSidebarArea: true,
          ChatWorkspace: true,
          PreviewPanel: true,
          UserProfileDialog: true,
          AddAgentDialog: true,
          NewConversationDialog: {
            name: 'NewConversationDialog',
            props: ['primaryAgent', 'agents'],
            template: '<div />',
          },
        },
      },
    })
    await flushPromises()

    const dialog = wrapper.findComponent({ name: 'NewConversationDialog' })
    expect(dialog.props('primaryAgent')).toBeNull()
    expect(dialog.props('agents')).toEqual([
      expect.objectContaining({ id: 'coder-1' }),
    ])
  })

  it('filters builtin and legacy pm agents from the visible agent list', async () => {
    agentStore.agents = [
      {
        id: 'pm_agent',
        name: 'PM Agent',
        avatar: '',
        capabilityTags: ['pm'],
        description: 'builtin pm',
        platform: 'custom',
        isCustom: false,
        role: 'PM',
        model: 'qwen',
        system_prompt: 'pm',
      },
      {
        id: 'primary_pm_agent',
        name: 'Primary PM Agent',
        avatar: '',
        capabilityTags: ['pm'],
        description: 'builtin primary pm',
        platform: 'custom',
        isCustom: false,
        role: 'PM',
        model: 'qwen',
        system_prompt: 'primary',
      },
      {
        id: 'group_host_user_1',
        name: '群聊主Agent',
        avatar: '',
        capabilityTags: ['pm'],
        description: 'group host',
        platform: 'custom',
        isCustom: true,
        role: 'PM',
        model: 'qwen',
        system_prompt: 'host',
      },
      {
        id: 'user_pm_agent',
        name: 'PM Agent',
        avatar: '',
        capabilityTags: ['pm'],
        description: 'legacy custom pm',
        platform: 'custom',
        isCustom: true,
        role: 'PM',
        model: 'qwen',
        system_prompt: 'legacy',
      },
    ]

    const wrapper = shallowMount(Zhu, {
      global: {
        stubs: {
          LeftSidebarArea: {
            name: 'LeftSidebarArea',
            props: ['filteredAgents'],
            template: '<div />',
          },
          ChatWorkspace: true,
          PreviewPanel: true,
          UserProfileDialog: true,
          AddAgentDialog: true,
          NewConversationDialog: true,
        },
      },
    })
    await flushPromises()

    const sidebar = wrapper.findComponent({ name: 'LeftSidebarArea' })
    expect(sidebar.props('filteredAgents')).toEqual([
      expect.objectContaining({ id: 'group_host_user_1' }),
    ])
  })

  it('includes the group host agent in group creation payloads', async () => {
    agentStore.agent = {
      id: 'group_host_user_1',
      name: 'Group Host',
      capability_tags: ['pm'],
    }
    agentStore.agents = [
      {
        id: 'group_host_user_1',
        name: 'Group Host',
        avatar: '',
        capabilityTags: ['pm'],
        description: 'group host',
        platform: 'custom',
        isCustom: true,
        role: 'PM',
        model: 'qwen',
        system_prompt: 'host',
      },
      {
        id: 'coder-1',
        name: 'Coder',
        avatar: '',
        capabilityTags: ['code'],
        description: 'coder',
        platform: 'custom',
        isCustom: true,
        role: 'Engineer',
        model: 'qwen',
        system_prompt: 'coder',
      },
    ]

    const wrapper = shallowMount(Zhu, {
      global: {
        stubs: {
          LeftSidebarArea: true,
          ChatWorkspace: true,
          PreviewPanel: true,
          UserProfileDialog: true,
          AddAgentDialog: true,
          NewConversationDialog: {
            name: 'NewConversationDialog',
            emits: ['confirm'],
            template: '<button data-testid="confirm-group" @click="$emit(\'confirm\', { mode: \'group\', title: \'Group\', participantAgentIds: [\'coder-1\'], workspace_id: \'ws-1\' })">create</button>',
          },
        },
      },
    })
    await flushPromises()

    await wrapper.get('[data-testid="confirm-group"]').trigger('click')
    await flushPromises()

    expect(createSession).toHaveBeenCalledWith({
      owner_id: 'dev_user',
      title: 'Group',
      mode: 'group',
      workspace_id: 'ws-1',
      agent_id: undefined,
      participant_agent_ids: ['group_host_user_1', 'coder-1'],
    })
  })

  it('keeps parallel task completions as separate messages when message_id is missing', async () => {
    let receiveHandler: ((msg: any) => void) | undefined
    onReceiveMessage.mockImplementation((cb) => {
      receiveHandler = cb
      return vi.fn()
    })

    sessionStore.streamState.handleMessageEnd = vi.fn()
      .mockReturnValueOnce({
        stream_id: 'stream-java',
        message_id: '',
        sender_role: 'coder',
        accumulated_content: 'java done',
        type: 'text',
        payload: { text: 'java done' },
        metadata: { task_id: 'task-java' },
        created_at: '2026-06-04T10:00:00Z',
      })
      .mockReturnValueOnce({
        stream_id: 'stream-python',
        message_id: '',
        sender_role: 'coder',
        accumulated_content: 'python done',
        type: 'text',
        payload: { text: 'python done' },
        metadata: { task_id: 'task-python' },
        created_at: '2026-06-04T10:00:01Z',
      })

    shallowMount(Zhu)
    await flushPromises()

    receiveHandler?.({
      type: 'message_end',
      stream_id: 'stream-java',
      status: 'completed',
    })
    receiveHandler?.({
      type: 'message_end',
      stream_id: 'stream-python',
      status: 'completed',
    })

    expect(mergeOrUpdateMessage).toHaveBeenCalledTimes(2)
    expect(mergeOrUpdateMessage).toHaveBeenNthCalledWith(
      1,
      'session-1',
      expect.objectContaining({ id: 'stream-java', content: 'java done' }),
    )
    expect(mergeOrUpdateMessage).toHaveBeenNthCalledWith(
      2,
      'session-1',
      expect.objectContaining({ id: 'stream-python', content: 'python done' }),
    )
  })

  it('does not refetch messages when the group host final summary stream ends', async () => {
    let receiveHandler: ((msg: any) => void) | undefined
    onReceiveMessage.mockImplementation((cb) => {
      receiveHandler = cb
      return vi.fn()
    })

    sessionStore.currentSession = {
      id: 'session-1',
      mode: 'group',
    }
    sessionStore.streamState.handleMessageEnd = vi.fn().mockReturnValue({
      stream_id: 'stream-summary',
      message_id: 'msg-summary',
      sender_role: 'PM',
      accumulated_content:
        '全部任务完成。请查看以下执行结果：\n创建heleo.java文件: 已完成\n\n如需继续修改，或还有其他问题，请继续告诉我。',
      type: 'text',
      payload: {
        text: '全部任务完成。请查看以下执行结果：\n创建heleo.java文件: 已完成\n\n如需继续修改，或还有其他问题，请继续告诉我。',
      },
      metadata: { is_orchestration_summary: true },
      created_at: '2026-06-04T10:00:02Z',
    })

    shallowMount(Zhu)
    await flushPromises()
    fetchMessages.mockClear()

    receiveHandler?.({
      type: 'message_end',
      stream_id: 'stream-summary',
      status: 'completed',
    })
    await flushPromises()

    expect(mergeOrUpdateMessage).toHaveBeenCalledWith(
      'session-1',
      expect.objectContaining({
        id: 'msg-summary',
        content:
          '全部任务完成。请查看以下执行结果：\n创建heleo.java文件: 已完成\n\n如需继续修改，或还有其他问题，请继续告诉我。',
      }),
    )
    expect(fetchMessages).not.toHaveBeenCalled()
  })

  it('preserves current session members when syncing renamed agent session titles', async () => {
    sessionStore.sessionList = [
      {
        id: 'session-1',
        title: 'Old Agent',
        mode: 'group',
      },
    ]
    sessionStore.currentSession = {
      id: 'session-1',
      title: 'Old Agent',
      mode: 'group',
      members: [
        {
          id: 'member-1',
          session_id: 'session-1',
          member_type: 'agent',
          member_id: 'agent-1',
          is_primary: true,
          status: 'online',
          agent_name: 'Old Agent',
          agent_avatar: null,
          agent_role: 'PM',
          created_at: '2026-06-06T00:00:00Z',
        },
      ],
    }
    syncSessionTitlesForAgentRename.mockResolvedValue([
      {
        id: 'session-1',
        title: 'New Agent',
        mode: 'group',
      },
    ])

    const wrapper = shallowMount(Zhu, {
      global: {
        stubs: {
          LeftSidebarArea: true,
          ChatWorkspace: true,
          PreviewPanel: true,
          UserProfileDialog: true,
          AddAgentDialog: {
            emits: ['confirm-edit', 'update:modelValue'],
            template: '<button data-testid="confirm-edit" @click="$emit(\'confirm-edit\', { id: \'agent-1\', name: \'New Agent\', model: \'qwen\', platform: \'custom\', description: \'\', avatar: \'\', capabilityTags: [] })">edit</button>',
          },
          NewConversationDialog: true,
        },
      },
    })
    await flushPromises()

    await wrapper.findAll('[data-testid="confirm-edit"]')[1].trigger('click')
    await flushPromises()

    expect(sessionStore.currentSession).toMatchObject({
      id: 'session-1',
      title: 'New Agent',
    })
    expect(sessionStore.currentSession.members).toEqual([
      expect.objectContaining({
        member_id: 'agent-1',
        agent_name: 'Old Agent',
      }),
    ])
  })
})
