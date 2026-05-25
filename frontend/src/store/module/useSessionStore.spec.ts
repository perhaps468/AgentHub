import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const getStreamingMessages = vi.fn()
const clearSession = vi.fn()

vi.mock('@/utils/useChatStreamState', () => ({
  useChatStreamState: () => ({
    getStreamingMessages,
    handleMessageStart: vi.fn(),
    handleMessageDelta: vi.fn(),
    handleMessageEnd: vi.fn(),
    handleMessageError: vi.fn(),
    finalizeStream: vi.fn(),
    clearSession,
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
})
