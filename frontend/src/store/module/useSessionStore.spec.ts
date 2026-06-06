import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const {
  getStreamingMessages,
  clearSession,
  clearSessionPendingChanges,
  clearInFlightStreams,
  restorePendingChanges,
  fetchPendingChanges,
  setStreamCurrentSessionId,
  restoreTaskStreams,
} = vi.hoisted(() => ({
  getStreamingMessages: vi.fn(),
  clearSession: vi.fn(),
  clearSessionPendingChanges: vi.fn(),
  clearInFlightStreams: vi.fn(),
  restorePendingChanges: vi.fn(),
  fetchPendingChanges: vi.fn(),
  setStreamCurrentSessionId: vi.fn(),
  restoreTaskStreams: vi.fn(),
}))

const {
  fetchConversationList,
  fetchConversationDetail,
  createConversation,
  updateConversation,
  fetchConversationMessages,
  deleteConversation,
  fetchLatestRun,
  fetchRun,
} = vi.hoisted(() => ({
  fetchConversationList: vi.fn(),
  fetchConversationDetail: vi.fn(),
  createConversation: vi.fn(),
  updateConversation: vi.fn(),
  fetchConversationMessages: vi.fn(),
  deleteConversation: vi.fn(),
  fetchLatestRun: vi.fn(),
  fetchRun: vi.fn(),
}))

vi.mock('@/api/modules/session', () => ({
  fetchConversationList,
  fetchConversationDetail,
  createConversation,
  updateConversation,
  fetchConversationMessages,
  deleteConversation,
  fetchLatestRun,
  fetchRun,
}))

vi.mock('@/api/modules/pendingChanges', () => ({
  fetchPendingChanges,
}))

vi.mock('@/utils/useChatStreamState', () => ({
  useChatStreamState: () => ({
    getStreamingMessages,
    handleMessageStart: vi.fn(),
    handleMessageDelta: vi.fn(),
    handleMessageEnd: vi.fn(),
    handleMessageError: vi.fn(),
    finalizeStream: vi.fn(),
    clearSession,
    setCurrentSessionId: setStreamCurrentSessionId,
    clearSessionPendingChanges,
    clearInFlightStreams,
    restorePendingChanges,
    restoreTaskStreams,
    hasInFlightStream: vi.fn(),
    checkStreamComplete: vi.fn(),
  }),
}))

import { useSessionStore } from './useSessionStore'

describe('useSessionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    getStreamingMessages.mockReset()
    clearSession.mockReset()
    clearSessionPendingChanges.mockReset()
    clearInFlightStreams.mockReset()
    restorePendingChanges.mockReset()
    restoreTaskStreams.mockReset()
    fetchPendingChanges.mockReset()
    setStreamCurrentSessionId.mockReset()
    fetchLatestRun.mockReset()
    fetchRun.mockReset()
  })

  it('returns current session streaming messages from stream state', () => {
    getStreamingMessages.mockReturnValue([
      {
        stream_id: 'stream-1',
        message_id: 'message-1',
        session_id: 'session-1',
        sender_type: 'agent',
        sender_role: 'PM',
        type: 'text',
        content: 'streaming reply',
        payload: { text: 'streaming reply' },
        metadata: { source: 'fixed_responder' },
        ui_status: 'streaming',
        is_ephemeral: false,
        created_at: '2026-05-24T10:00:00Z',
      },
    ])

    const store = useSessionStore()
    store.setCurrentSessionId('session-1')

    expect(store.currentStreamingMessages).toEqual([
      {
        stream_id: 'stream-1',
        message_id: 'message-1',
        session_id: 'session-1',
        sender_type: 'agent',
        sender_role: 'PM',
        type: 'text',
        content: 'streaming reply',
        payload: { text: 'streaming reply' },
        metadata: { source: 'fixed_responder' },
        ui_status: 'streaming',
        is_ephemeral: false,
        created_at: '2026-05-24T10:00:00Z',
      },
    ])
    expect(getStreamingMessages).toHaveBeenCalledWith('session-1')
  })

  it('restores pending changes for a session from the API', async () => {
    fetchPendingChanges.mockResolvedValue({
      items: [
        {
          change_id: 'change-1',
          session_id: 'session-1',
          path: '/workspace/hello_world.py',
          operation: 'create',
          unified_diff: '--- /dev/null\n+++ hello_world.py',
          status: 'pending_confirmation',
        },
      ],
      total: 1,
      session_id: 'session-1',
    })

    const store = useSessionStore()
    const res = await store.restorePendingChangesForSession('session-1', {
      clearExisting: true,
      clearInFlight: true,
    })

    expect(clearSessionPendingChanges).toHaveBeenCalledWith('session-1')
    expect(clearInFlightStreams).toHaveBeenCalledWith('session-1')
    expect(fetchPendingChanges).toHaveBeenCalledWith('session-1')
    expect(restorePendingChanges).toHaveBeenCalledWith(res.items, 'session-1')
  })

  it('updates currentMessages immediately when mergeOrUpdateMessage inserts a new message', () => {
    const store = useSessionStore()
    store.setCurrentSessionId('session-1')

    store.mergeOrUpdateMessage('session-1', {
      id: 'message-1',
      session_id: 'session-1',
      sender_type: 'agent',
      sender_role: 'PM',
      type: 'text',
      content: 'final reply',
      payload: { text: 'final reply' },
      metadata: { source: 'runtime' },
      status: 'completed',
      created_at: '2026-06-01T00:00:00Z',
    } as any)

    expect(store.currentMessages).toHaveLength(1)
    expect(store.currentMessages[0].content).toBe('final reply')
  })

  it('prepends older paginated messages so chronological order stays stable', async () => {
    fetchConversationMessages
      .mockResolvedValueOnce({
        items: [
          {
            id: 'msg-3',
            session_id: 'session-1',
            sender_type: 'agent',
            sender_role: 'PM',
            type: 'text',
            content: 'third',
            payload: { text: 'third' },
            metadata: {},
            status: 'completed',
            created_at: '2026-06-03T00:00:00Z',
          },
          {
            id: 'msg-2',
            session_id: 'session-1',
            sender_type: 'agent',
            sender_role: 'PM',
            type: 'text',
            content: 'second',
            payload: { text: 'second' },
            metadata: {},
            status: 'completed',
            created_at: '2026-06-02T00:00:00Z',
          },
        ],
        page: 1,
        page_size: 20,
        total: 4,
        has_more: true,
      })
      .mockResolvedValueOnce({
        items: [
          {
            id: 'msg-1',
            session_id: 'session-1',
            sender_type: 'human',
            sender_role: null,
            type: 'text',
            content: 'first',
            payload: { text: 'first' },
            metadata: {},
            status: 'completed',
            created_at: '2026-06-01T00:00:00Z',
          },
          {
            id: 'msg-0',
            session_id: 'session-1',
            sender_type: 'human',
            sender_role: null,
            type: 'text',
            content: 'zero',
            payload: { text: 'zero' },
            metadata: {},
            status: 'completed',
            created_at: '2026-05-31T00:00:00Z',
          },
        ],
        page: 2,
        page_size: 20,
        total: 4,
        has_more: false,
      })

    const store = useSessionStore()

    await store.fetchMessages('session-1')
    await store.fetchMessages('session-1', { page: 2 })

    expect(store.messageMap['session-1'].map((message) => message.id)).toEqual([
      'msg-0',
      'msg-1',
      'msg-2',
      'msg-3',
    ])
  })

  it('updates currentMessages immediately when mergeOrUpdateMessage replaces an existing message', () => {
    const store = useSessionStore()
    store.setCurrentSessionId('session-1')

    store.mergeOrUpdateMessage('session-1', {
      id: 'message-1',
      session_id: 'session-1',
      sender_type: 'agent',
      sender_role: 'PM',
      type: 'text',
      content: 'old reply',
      payload: { text: 'old reply' },
      metadata: { source: 'runtime' },
      status: 'streaming',
      created_at: '2026-06-01T00:00:00Z',
    } as any)

    store.mergeOrUpdateMessage('session-1', {
      id: 'message-1',
      session_id: 'session-1',
      sender_type: 'agent',
      sender_role: 'PM',
      type: 'text',
      content: 'new reply',
      payload: { text: 'new reply' },
      metadata: { source: 'runtime' },
      status: 'completed',
      created_at: '2026-06-01T00:00:00Z',
    } as any)

    expect(store.currentMessages).toHaveLength(1)
    expect(store.currentMessages[0].content).toBe('new reply')
    expect(store.currentMessages[0].status).toBe('completed')
  })

  it('stores latest orchestration run and tasks for the active session', async () => {
    fetchLatestRun.mockResolvedValue({
      id: 'run-1',
      session_id: 'session-1',
      trigger_message_id: 'msg-1',
      planner_agent_id: 'primary_pm_agent',
      status: 'planned',
      summary: 'planned 2 tasks',
      tasks: [
        {
          id: 'task-1',
          run_id: 'run-1',
          parent_task_id: null,
          sequence: 1,
          assigned_agent_id: 'primary_pm_agent',
          kind: 'file_write',
          title: 'Task 1',
          goal: 'Create alpha.py',
          input_payload: { raw: 'alpha.py' },
          status: 'planned',
        },
      ],
    })

    const store = useSessionStore()
    const run = await store.fetchLatestRun('session-1')

    expect(fetchLatestRun).toHaveBeenCalledWith('session-1')
    expect(run.id).toBe('run-1')
    expect(store.activeRun?.id).toBe('run-1')
    expect(store.activeTasks).toHaveLength(1)
    expect(store.activeTasks[0].title).toBe('Task 1')
    expect(restoreTaskStreams).toHaveBeenCalledWith('session-1', expect.objectContaining({
      run_id: 'run-1',
    }))
  })

  it('clears orchestration state when current session is cleared', async () => {
    fetchLatestRun.mockResolvedValue({
      id: 'run-1',
      session_id: 'session-1',
      trigger_message_id: 'msg-1',
      planner_agent_id: 'primary_pm_agent',
      status: 'planned',
      summary: 'planned 1 task',
      tasks: [],
    })

    const store = useSessionStore()
    await store.fetchLatestRun('session-1')

    store.setCurrentSessionId(null)

    expect(store.activeRun).toBeNull()
    expect(store.activeTasks).toEqual([])
    expect(setStreamCurrentSessionId).toHaveBeenCalledWith(null)
  })

  // M4: Tests for task-aware pending change methods
  it('filters pending changes by task_id', async () => {
    const store = useSessionStore()
    store.setCurrentSessionId('session-1')

    // Setup mock for getPendingChanges
    const mockGetPendingChanges = vi.fn().mockReturnValue([
      { change_id: 'change-1', task_id: 'task-1', run_id: 'run-1', path: 'a.txt' },
      { change_id: 'change-2', task_id: 'task-2', run_id: 'run-1', path: 'b.txt' },
    ])
    ;(store.streamState as any).getPendingChanges = mockGetPendingChanges

    const task1Changes = store.getPendingChangesByTask('task-1')
    expect(task1Changes).toHaveLength(1)
    expect(task1Changes[0].change_id).toBe('change-1')

    const task2Changes = store.getPendingChangesByTask('task-2')
    expect(task2Changes).toHaveLength(1)
    expect(task2Changes[0].change_id).toBe('change-2')
  })

  it('updates task status in activeTasks', () => {
    const store = useSessionStore()
    store.activeTasks = [
      { id: 'task-1', status: 'waiting_confirmation' },
      { id: 'task-2', status: 'waiting_confirmation' },
    ] as any

    store.updateTaskStatus('task-1', 'completed')

    expect(store.activeTasks[0].status).toBe('completed')
    expect(store.activeTasks[1].status).toBe('waiting_confirmation')
  })

  it('checks if all tasks are in terminal state', () => {
    const store = useSessionStore()

    store.activeTasks = [
      { id: 'task-1', status: 'completed' },
      { id: 'task-2', status: 'completed' },
    ] as any
    expect(store.areAllTasksTerminal()).toBe(true)

    store.activeTasks = [
      { id: 'task-1', status: 'completed' },
      { id: 'task-2', status: 'waiting_confirmation' },
    ] as any
    expect(store.areAllTasksTerminal()).toBe(false)
  })
})
