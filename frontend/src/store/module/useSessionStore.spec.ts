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
} = vi.hoisted(() => ({
  getStreamingMessages: vi.fn(),
  clearSession: vi.fn(),
  clearSessionPendingChanges: vi.fn(),
  clearInFlightStreams: vi.fn(),
  restorePendingChanges: vi.fn(),
  fetchPendingChanges: vi.fn(),
  setStreamCurrentSessionId: vi.fn(),
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
    fetchPendingChanges.mockReset()
    setStreamCurrentSessionId.mockReset()
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
})
