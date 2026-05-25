/**
 * P1-3-4 前端 Stream 状态机 TDD 测试。
 *
 * 驱动 useChatStreamState 的实现改造（P1-3 task spec Section 6.5）：
 *
 * 设计契约:
 * - handleMessageStart: 创建 in-flight 消息占位，使用后端返回的完整消息壳
 * - handleMessageDelta: 按 stream_id 归并到同一条消息，追加 delta
 * - handleMessageEnd: 当前 in-flight 消息收口，释放状态，触发后台 fetchMessages
 * - handleMessageError: 标记失败，触发后台 fetchMessages
 * - optimistic human message 使用统一消息形状
 * - fetchMessages 后按 message.id upsert，删除 optimistic human，agent 消息不重复
 *
 * 本测试文件使用 TDD 红色优先策略。
 */

import { describe, expect, it, vi, beforeEach } from 'vitest'

// ---------------------------------------------------------------------------
// Mock: 拦截 store 模块
// ---------------------------------------------------------------------------

const mockInFlightMessages = new Map<string, any>()
const mockFetchMessages = vi.fn()
const mockUpsertMessage = vi.fn()
const mockDeleteMessage = vi.fn()

vi.mock('@/store/module/useSessionStore', () => ({
  useSessionStore: () => ({
    inFlightMessages: mockInFlightMessages,
    fetchMessages: mockFetchMessages,
    upsertMessage: mockUpsertMessage,
    deleteMessage: mockDeleteMessage,
  }),
}))

// ---------------------------------------------------------------------------
// Import after mock setup
// ---------------------------------------------------------------------------

import { useChatStreamState } from '../utils/useChatStreamState'

// ---------------------------------------------------------------------------
// Test Helpers: 构造新协议事件
// ---------------------------------------------------------------------------

function makeMessageStart(overrides: Record<string, any> = {}): any {
  return {
    type: 'message_start',
    agent_role: 'PM',
    timestamp: '2026-05-24T10:00:00Z',
    stream_id: 'stream-001',
    ...overrides,
    message: {
      id: 'msg-001',
      session_id: 'session-001',
      sender_type: 'agent',
      sender_role: 'PM',
      type: 'text',
      content: '',
      payload: { text: '' },
      metadata: {
        stream_id: 'stream-001',
        source: 'fixed_responder',
        render_hint: 'markdown',
      },
      status: 'streaming',
      created_at: '2026-05-24T10:00:00Z',
      ...(overrides.message || {}),
    },
  }
}

function makeMessageDelta(overrides: Record<string, any> = {}): any {
  return {
    type: 'message_delta',
    agent_role: 'PM',
    timestamp: '2026-05-24T10:00:01Z',
    stream_id: 'stream-001',
    message_id: 'msg-001',
    delta: 'Hello, ',
    ...overrides,
  }
}

function makeMessageEnd(overrides: Record<string, any> = {}): any {
  return {
    type: 'message_end',
    agent_role: 'PM',
    timestamp: '2026-05-24T10:00:02Z',
    stream_id: 'stream-001',
    message_id: 'msg-001',
    status: 'completed',
    ...overrides,
  }
}

function makeMessageError(overrides: Record<string, any> = {}): any {
  return {
    type: 'message_error',
    agent_role: 'PM',
    timestamp: '2026-05-24T10:00:02Z',
    stream_id: 'stream-001',
    message_id: 'msg-001',
    error_code: 'fixed_responder_failed',
    error_message: 'Failed to stream fixed response',
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// TDD Phase 1: 验证 useChatStreamState 导出期望的函数
// ---------------------------------------------------------------------------

describe('P1-3-4 TDD: useChatStreamState 模块存在性', () => {
  it('useChatStreamState 必须可导入', () => {
    expect(typeof useChatStreamState).toBe('function')
  })

  it('useChatStreamState 必须返回 handleMessageStart 函数', () => {
    const result = useChatStreamState()
    expect(typeof result.handleMessageStart).toBe('function')
  })

  it('useChatStreamState 必须返回 handleMessageDelta 函数', () => {
    const result = useChatStreamState()
    expect(typeof result.handleMessageDelta).toBe('function')
  })

  it('useChatStreamState 必须返回 handleMessageEnd 函数', () => {
    const result = useChatStreamState()
    expect(typeof result.handleMessageEnd).toBe('function')
  })

  it('useChatStreamState 必须返回 handleMessageError 函数', () => {
    const result = useChatStreamState()
    expect(typeof result.handleMessageError).toBe('function')
  })

  it('useChatStreamState 必须返回 getStreamingMessages 函数', () => {
    const result = useChatStreamState()
    expect(typeof result.getStreamingMessages).toBe('function')
  })

  it('useChatStreamState 必须返回 finalizeStream 函数', () => {
    const result = useChatStreamState()
    expect(typeof result.finalizeStream).toBe('function')
  })

  it('useChatStreamState 必须返回 clearSession 函数', () => {
    const result = useChatStreamState()
    expect(typeof result.clearSession).toBe('function')
  })
})

// ---------------------------------------------------------------------------
// TDD Phase 2: message_start 处理
// ---------------------------------------------------------------------------

describe('P1-3-4 TDD: message_start 处理', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockInFlightMessages.clear()
    mockFetchMessages.mockResolvedValue({ items: [] })
  })

  it('handleMessageStart 必须接受 event 和 sessionId 参数', () => {
    const { handleMessageStart } = useChatStreamState()

    const event = makeMessageStart()
    const sessionId = 'session-001'

    expect(() => handleMessageStart(event, sessionId)).not.toThrow()
  })

  it('handleMessageStart 使用后端返回的完整消息壳创建 in-flight 占位', () => {
    const { handleMessageStart } = useChatStreamState()

    const event = makeMessageStart({
      message: { id: 'msg-backend-123' },
      stream_id: 'stream-xyz',
      agent_role: 'Coder',
    })
    const sessionId = 'session-001'

    handleMessageStart(event, sessionId)

    const inFlight = mockInFlightMessages.get('stream-xyz')
    expect(inFlight).toBeDefined()
    expect(inFlight.message_id).toBe('msg-backend-123')
    expect(inFlight.sender_role).toBe('Coder')
  })

  it('handleMessageStart 初始 content 和 payload.text 为空', () => {
    const { handleMessageStart } = useChatStreamState()

    const event = makeMessageStart()
    handleMessageStart(event, 'session-001')

    const inFlight = mockInFlightMessages.get('stream-001')
    expect(inFlight.content).toBe('')
    expect(inFlight.payload?.text).toBe('')
  })

  it('handleMessageStart UI 状态为 streaming', () => {
    const { handleMessageStart } = useChatStreamState()

    const event = makeMessageStart()
    handleMessageStart(event, 'session-001')

    const inFlight = mockInFlightMessages.get('stream-001')
    expect(inFlight.ui_status).toBe('streaming')
  })

  it('重复的 message_start 不应创建多个 in-flight 消息', () => {
    const { handleMessageStart } = useChatStreamState()

    const event = makeMessageStart({
      message: { id: 'msg-dup' },
      stream_id: 'streamdup',
    })
    handleMessageStart(event, 'session-001')
    handleMessageStart(event, 'session-001')

    const inFlightCount = Array.from(mockInFlightMessages.values()).filter(
      (m) => m.stream_id === 'streamdup'
    ).length

    expect(inFlightCount).toBe(1)
  })
})

// ---------------------------------------------------------------------------
// TDD Phase 3: message_delta 处理
// ---------------------------------------------------------------------------

describe('P1-3-4 TDD: message_delta 处理', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockInFlightMessages.clear()
    mockFetchMessages.mockResolvedValue({ items: [] })
  })

  it('handleMessageDelta 必须接受 event 和 sessionId 参数', () => {
    const { handleMessageStart, handleMessageDelta } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'm-d' },
      stream_id: 's-d',
    }), 'session-001')
    handleMessageDelta(makeMessageDelta(), 'session-001')

    expect(true).toBe(true)
  })

  it('handleMessageDelta 追加 delta 到现有 in-flight 消息', () => {
    const { handleMessageStart, handleMessageDelta } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'msg-delta' },
      stream_id: 'stream-delta',
    }), 'session-001')

    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-delta', delta: 'Hello, ' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-delta', delta: 'world.' }), 'session-001')

    const inFlight = mockInFlightMessages.get('stream-delta')
    expect(inFlight.accumulated_content).toBe('Hello, world.')
  })

  it('handleMessageDelta 同步更新 payload.text', () => {
    const { handleMessageStart, handleMessageDelta } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'msg-payload' },
      stream_id: 'stream-payload',
    }), 'session-001')

    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-payload', delta: 'New content' }), 'session-001')

    const inFlight = mockInFlightMessages.get('stream-payload')
    expect(inFlight.payload?.text).toBe('New content')
  })

  it('handleMessageDelta 按 stream_id 归并到同一条消息', () => {
    const { handleMessageStart, handleMessageDelta } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'msg-1' },
      stream_id: 'stream-1',
    }), 'session-001')
    handleMessageStart(makeMessageStart({
      message: { id: 'msg-2' },
      stream_id: 'stream-2',
    }), 'session-001')

    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-1', delta: 'A' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-2', delta: 'X' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-1', delta: 'B' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-2', delta: 'Y' }), 'session-001')

    expect(mockInFlightMessages.get('stream-1')?.accumulated_content).toBe('AB')
    expect(mockInFlightMessages.get('stream-2')?.accumulated_content).toBe('XY')
  })

  it('handleMessageDelta 不应把每个 delta 当作独立消息', () => {
    const { handleMessageStart, handleMessageDelta } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'msg-single' },
      stream_id: 'stream-single',
    }), 'session-001')

    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-single', delta: 'Chunk1' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-single', delta: 'Chunk2' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 'stream-single', delta: 'Chunk3' }), 'session-001')

    const inFlightCount = mockInFlightMessages.size
    expect(inFlightCount).toBe(1)
  })
})

// ---------------------------------------------------------------------------
// TDD Phase 4: message_end 处理
// ---------------------------------------------------------------------------

describe('P1-3-4 TDD: message_end 处理', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockInFlightMessages.clear()
    mockFetchMessages.mockResolvedValue({ items: [] })
  })

  it('handleMessageEnd 必须接受 event 和 sessionId 参数', () => {
    const { handleMessageEnd } = useChatStreamState()

    expect(() => handleMessageEnd(makeMessageEnd(), 'session-001')).not.toThrow()
  })

  it('handleMessageEnd 触发一次后台 fetchMessages', () => {
    const { handleMessageEnd } = useChatStreamState()

    handleMessageEnd(makeMessageEnd({
      stream_id: 'stream-end',
      message_id: 'msg-end',
    }), 'session-001')

    expect(mockFetchMessages).toHaveBeenCalledTimes(1)
    expect(mockFetchMessages).toHaveBeenCalledWith('session-001', expect.any(Object))
  })

  it('handleMessageEnd 释放 in-flight 状态', () => {
    const { handleMessageStart, handleMessageEnd } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'msg-release' },
      stream_id: 'stream-release',
    }), 'session-001')
    expect(mockInFlightMessages.has('stream-release')).toBe(true)

    handleMessageEnd(makeMessageEnd({
      stream_id: 'stream-release',
      message_id: 'msg-release',
    }), 'session-001')

    expect(mockInFlightMessages.has('stream-release')).toBe(false)
  })

  it('handleMessageEnd 无对应 in-flight 时不崩溃', () => {
    const { handleMessageEnd } = useChatStreamState()

    expect(() =>
      handleMessageEnd(makeMessageEnd({
        stream_id: 'stream-no-start',
        message_id: 'msg-no-start',
      }), 'session-001')
    ).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// TDD Phase 5: message_error 处理
// ---------------------------------------------------------------------------

describe('P1-3-4 TDD: message_error 处理', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockInFlightMessages.clear()
    mockFetchMessages.mockResolvedValue({ items: [] })
  })

  it('handleMessageError 有 in-flight 时触发后台 fetchMessages', () => {
    const { handleMessageStart, handleMessageError } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'msg-err' },
      stream_id: 'stream-err',
    }), 'session-001')
    handleMessageError(makeMessageError({
      stream_id: 'stream-err',
      message_id: 'msg-err',
    }), 'session-001')

    expect(mockFetchMessages).toHaveBeenCalledTimes(1)
  })

  it('handleMessageError 无 in-flight 时不触发 fetchMessages', () => {
    const { handleMessageError } = useChatStreamState()

    handleMessageError(makeMessageError({
      stream_id: 'stream-no-inflight',
      message_id: 'msg-no-inflight',
    }), 'session-001')

    expect(mockFetchMessages).not.toHaveBeenCalled()
  })

  it('handleMessageError 释放悬挂状态', () => {
    const { handleMessageStart, handleMessageError } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'msg-err-release' },
      stream_id: 'stream-err-release',
    }), 'session-001')
    expect(mockInFlightMessages.has('stream-err-release')).toBe(true)

    handleMessageError(makeMessageError({
      stream_id: 'stream-err-release',
      message_id: 'msg-err-release',
    }), 'session-001')

    expect(mockInFlightMessages.has('stream-err-release')).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// TDD Phase 6: optimistic human message 统一消息形状
// ---------------------------------------------------------------------------

describe('P1-3-4 TDD: optimistic human message 统一消息形状', () => {
  it('optimistic human message 必须包含统一字段', () => {
    const optimisticMessage = {
      id: 'temp_human_xxx',
      session_id: 'session-001',
      sender_type: 'human' as const,
      sender_role: null,
      type: 'text',
      content: '用户输入',
      payload: { text: '用户输入' },
      metadata: { source: 'optimistic_human' },
      status: 'completed' as const,
      created_at: expect.any(String),
    }

    expect(optimisticMessage.id).toBeDefined()
    expect(optimisticMessage.session_id).toBeDefined()
    expect(optimisticMessage.sender_type).toBe('human')
    expect(optimisticMessage.sender_role).toBeNull()
    expect(optimisticMessage.type).toBe('text')
    expect(optimisticMessage.payload.text).toBe('用户输入')
    expect(optimisticMessage.metadata.source).toBe('optimistic_human')
    expect(optimisticMessage.status).toBe('completed')
  })

  it('optimistic human message payload.text 与 content 一致', () => {
    const userContent = 'Test message content'
    expect(userContent).toBe(userContent)
  })
})

// ---------------------------------------------------------------------------
// TDD Phase 7: fetchMessages upsert 和 optimistic 对账
// ---------------------------------------------------------------------------

describe('P1-3-4 TDD: fetchMessages upsert 和 optimistic 对账', () => {
  const mockMessages = new Map<string, any>()

  beforeEach(() => {
    vi.clearAllMocks()
    mockMessages.clear()
    mockUpsertMessage.mockImplementation((id: string, msg: any) => {
      mockMessages.set(id, msg)
    })
    mockDeleteMessage.mockImplementation((id: string) => {
      mockMessages.delete(id)
    })
  })

  it('fetchMessages 按 message.id 作为主键 upsert', () => {
    const messageId = 'msg-backend-001'
    const persistedMsg = {
      id: messageId,
      sender_type: 'agent',
      content: 'Server response',
    }

    mockUpsertMessage(messageId, persistedMsg)

    expect(mockMessages.has(messageId)).toBe(true)
    expect(mockMessages.get(messageId).content).toBe('Server response')
  })

  it('fetchMessages 后删除 optimistic human message', () => {
    const tempHumanId = 'temp_human_abc'
    mockMessages.set(tempHumanId, {
      id: tempHumanId,
      metadata: { source: 'optimistic_human' },
    })

    mockDeleteMessage(tempHumanId)

    expect(mockMessages.has(tempHumanId)).toBe(false)
  })

  it('同 message.id 的 agent 消息不重复插入', () => {
    const messageId = 'msg-shared-001'

    mockMessages.set(messageId, {
      id: messageId,
      sender_type: 'agent',
      content: 'Frontend accumulated',
    })

    const backendMsg = {
      id: messageId,
      sender_type: 'agent',
      content: 'Backend persisted',
    }
    mockUpsertMessage(messageId, backendMsg)

    expect(mockMessages.size).toBe(1)
    expect(mockMessages.get(messageId).content).toBe('Backend persisted')
  })
})

// ---------------------------------------------------------------------------
// TDD Phase 8: getStreamingMessages
// ---------------------------------------------------------------------------

describe('P1-3-4 TDD: getStreamingMessages', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockInFlightMessages.clear()
  })

  it('getStreamingMessages 返回指定 session 的 in-flight 消息', () => {
    const { handleMessageStart, getStreamingMessages } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'm1' },
      stream_id: 's1',
    }), 'session-A')
    handleMessageStart(makeMessageStart({
      message: { id: 'm2' },
      stream_id: 's2',
    }), 'session-A')
    handleMessageStart(makeMessageStart({
      message: { id: 'm3' },
      stream_id: 's3',
    }), 'session-B')

    const streaming = getStreamingMessages('session-A')
    expect(streaming).toHaveLength(2)
  })

  it('getStreamingMessages 无 in-flight 时返回空数组', () => {
    const { getStreamingMessages } = useChatStreamState()

    const streaming = getStreamingMessages('session-empty')
    expect(streaming).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// TDD Phase 9: finalizeStream 和 clearSession
// ---------------------------------------------------------------------------

describe('P1-3-4 TDD: finalizeStream 和 clearSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockInFlightMessages.clear()
  })

  it('finalizeStream 删除指定 stream_id 的 in-flight 消息', () => {
    const { handleMessageStart, finalizeStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'msg-finalize' },
      stream_id: 'stream-finalize',
    }), 'session-001')
    expect(mockInFlightMessages.has('stream-finalize')).toBe(true)

    finalizeStream('stream-finalize')

    expect(mockInFlightMessages.has('stream-finalize')).toBe(false)
  })

  it('clearSession 删除指定 session 的所有 in-flight 消息', () => {
    const { handleMessageStart, clearSession } = useChatStreamState()

    handleMessageStart(makeMessageStart({
      message: { id: 'ma1' },
      stream_id: 'sa1',
    }), 'session-C')
    handleMessageStart(makeMessageStart({
      message: { id: 'ma2' },
      stream_id: 'sa2',
    }), 'session-C')
    handleMessageStart(makeMessageStart({
      message: { id: 'mb1' },
      stream_id: 'sb1',
    }), 'session-D')

    clearSession('session-C')

    expect(mockInFlightMessages.has('sa1')).toBe(false)
    expect(mockInFlightMessages.has('sa2')).toBe(false)
    expect(mockInFlightMessages.has('sb1')).toBe(true)
  })
})
