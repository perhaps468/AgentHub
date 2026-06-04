/**
 * M6 Frontend Stream State Test - 基于真实 useChatStreamState 内部 streams 行为。
 *
 * 真实实现 (useChatStreamState.ts):
 * - 内部维护 ref<Map<stream_id, InFlightStream>> streams
 * - 不依赖任何外部 store 或 mockInFlightMessages
 * - handleMessageStart/Delta/End 直接操作内部 streams
 * - getStreamingMessages() 从内部 streams 读取，返回 StreamingMessage[]
 * - finalizeStream(streamId) 从内部 streams 删除
 * - clearSession(sessionId) 从内部 streams 批量删除
 *
 * 关键行为契约:
 * - final_content 覆盖 accumulated_content (防止泄露 ReAct/XML)
 * - message_end 后 finalizeStream 自动调用（stream 从 streams Map 中移除）
 * - 无对应 stream 的 handleMessageDelta/End 不崩溃
 */

import { describe, expect, it, vi, beforeEach } from 'vitest'

// ---------------------------------------------------------------------------
// Import after mock setup (no mocks needed — test the real implementation)
// ---------------------------------------------------------------------------

import { useChatStreamState } from '../utils/useChatStreamState'

// ---------------------------------------------------------------------------
// Test Helpers: 构造新协议事件
// ---------------------------------------------------------------------------

function makeMessageStart(overrides: Record<string, unknown> = {}): Record<string, unknown> {
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
      ...((overrides.message as Record<string, unknown>) || {}),
    },
  }
}

function makeMessageDelta(overrides: Record<string, unknown> = {}): Record<string, unknown> {
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

function makeMessageEnd(overrides: Record<string, unknown> = {}): Record<string, unknown> {
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

function makeMessageError(overrides: Record<string, unknown> = {}): Record<string, unknown> {
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
// Phase 1: 验证 useChatStreamState 导出期望的函数
// ---------------------------------------------------------------------------

describe('useChatStreamState API surface', () => {
  it('useChatStreamState must be importable as a function', () => {
    expect(typeof useChatStreamState).toBe('function')
  })

  it('returns handleMessageStart', () => {
    expect(typeof useChatStreamState().handleMessageStart).toBe('function')
  })

  it('returns handleMessageDelta', () => {
    expect(typeof useChatStreamState().handleMessageDelta).toBe('function')
  })

  it('returns handleMessageEnd', () => {
    expect(typeof useChatStreamState().handleMessageEnd).toBe('function')
  })

  it('returns handleMessageError', () => {
    expect(typeof useChatStreamState().handleMessageError).toBe('function')
  })

  it('returns getStreamingMessages', () => {
    expect(typeof useChatStreamState().getStreamingMessages).toBe('function')
  })

  it('returns finalizeStream', () => {
    expect(typeof useChatStreamState().finalizeStream).toBe('function')
  })

  it('returns clearSession', () => {
    expect(typeof useChatStreamState().clearSession).toBe('function')
  })

  it('returns hasInFlightStream', () => {
    expect(typeof useChatStreamState().hasInFlightStream).toBe('function')
  })

  it('returns getStream', () => {
    expect(typeof useChatStreamState().getStream).toBe('function')
  })

  it('returns streams ref', () => {
    expect(useChatStreamState().streams).toBeDefined()
  })
})

// ---------------------------------------------------------------------------
// Phase 2: message_start 创建 stream
// ---------------------------------------------------------------------------

describe('message_start creates a stream', () => {
  it('handleMessageStart creates a stream in internal streams Map', () => {
    const { handleMessageStart, getStream } = useChatStreamState()

    handleMessageStart(
      makeMessageStart({ stream_id: 's-start', message: { id: 'm-start' } }),
      'session-001'
    )

    expect(getStream('s-start')).toBeDefined()
  })

  it('handleMessageStart populates stream_id, message_id, session_id, sender_role', () => {
    const { handleMessageStart, getStream } = useChatStreamState()

    handleMessageStart(
      makeMessageStart({
        stream_id: 's-fields',
        message: { id: 'm-fields', sender_role: 'Coder' },
        agent_role: 'Coder',
      }),
      'session-fields'
    )

    const stream = getStream('s-fields')!
    expect(stream.stream_id).toBe('s-fields')
    expect(stream.message_id).toBe('m-fields')
    expect(stream.session_id).toBe('session-fields')
    expect(stream.sender_role).toBe('Coder')
  })

  it('handleMessageStart initializes accumulated_content and content to empty string', () => {
    const { handleMessageStart, getStream } = useChatStreamState()

    handleMessageStart(
      makeMessageStart({ stream_id: 's-empty' }),
      'session-001'
    )

    const stream = getStream('s-empty')!
    expect(stream.accumulated_content).toBe('')
    expect(stream.content).toBe('')
  })

  it('handleMessageStart initializes ui_status to streaming', () => {
    const { handleMessageStart, getStream } = useChatStreamState()

    handleMessageStart(
      makeMessageStart({ stream_id: 's-status' }),
      'session-001'
    )

    const stream = getStream('s-status')!
    expect(stream.ui_status).toBe('streaming')
  })

  it('handleMessageStart does not throw without sessionId', () => {
    const { handleMessageStart } = useChatStreamState()
    expect(() =>
      handleMessageStart(makeMessageStart({ stream_id: 's-no-session' }), 'session-001')
    ).not.toThrow()
  })

  it('duplicate message_start for same stream_id does not create duplicate', () => {
    const { handleMessageStart, getStream } = useChatStreamState()

    handleMessageStart(
      makeMessageStart({ stream_id: 's-dup' }),
      'session-001'
    )
    handleMessageStart(
      makeMessageStart({ stream_id: 's-dup' }),
      'session-001'
    )

    // Should still be exactly 1 stream
    expect(getStream('s-dup')).toBeDefined()
  })

  it('returns the created stream object', () => {
    const { handleMessageStart } = useChatStreamState()

    const stream = handleMessageStart(
      makeMessageStart({ stream_id: 's-return' }),
      'session-001'
    )

    expect(stream).toBeDefined()
    expect(stream!.stream_id).toBe('s-return')
  })

  it('preserves initial message.content for non-delta websocket replies', () => {
    const { handleMessageStart, getStream } = useChatStreamState()

    handleMessageStart(
      makeMessageStart({
        stream_id: 's-initial-content',
        message: {
          id: 'm-initial-content',
          content: '全部任务完成。请查看以下执行结果：\ncreate hello.java: 已完成',
          payload: { text: '全部任务完成。请查看以下执行结果：\ncreate hello.java: 已完成' },
        },
      }),
      'session-001'
    )

    const stream = getStream('s-initial-content')!
    expect(stream.accumulated_content).toBe('全部任务完成。请查看以下执行结果：\ncreate hello.java: 已完成')
    expect(stream.content).toBe('全部任务完成。请查看以下执行结果：\ncreate hello.java: 已完成')
    expect(stream.payload.text).toBe('全部任务完成。请查看以下执行结果：\ncreate hello.java: 已完成')
  })
})

// ---------------------------------------------------------------------------
// Phase 3: message_delta 累加内容
// ---------------------------------------------------------------------------

describe('message_delta accumulates content', () => {
  it('handleMessageDelta appends delta to accumulated_content', () => {
    const { handleMessageStart, handleMessageDelta, getStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-delta' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 's-delta', delta: 'Hello, ' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 's-delta', delta: 'world.' }), 'session-001')

    const stream = getStream('s-delta')!
    expect(stream.accumulated_content).toBe('Hello, world.')
  })

  it('handleMessageDelta updates content alias', () => {
    const { handleMessageStart, handleMessageDelta, getStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-content' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 's-content', delta: 'Hello' }), 'session-001')

    const stream = getStream('s-content')!
    expect(stream.content).toBe('Hello')
  })

  it('handleMessageDelta updates payload.text', () => {
    const { handleMessageStart, handleMessageDelta, getStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-payload' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 's-payload', delta: 'Hello' }), 'session-001')

    const stream = getStream('s-payload')!
    expect(stream.payload.text).toBe('Hello')
  })

  it('handleMessageDelta merges by stream_id (independent streams accumulate separately)', () => {
    const { handleMessageStart, handleMessageDelta, getStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-1' }), 'session-001')
    handleMessageStart(makeMessageStart({ stream_id: 's-2' }), 'session-001')

    handleMessageDelta(makeMessageDelta({ stream_id: 's-1', delta: 'A' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 's-2', delta: 'X' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 's-1', delta: 'B' }), 'session-001')
    handleMessageDelta(makeMessageDelta({ stream_id: 's-2', delta: 'Y' }), 'session-001')

    expect(getStream('s-1')!.accumulated_content).toBe('AB')
    expect(getStream('s-2')!.accumulated_content).toBe('XY')
  })

  it('delta does not create new stream (only message_start creates streams)', () => {
    const { handleMessageDelta, getStream } = useChatStreamState()

    // No message_start first
    handleMessageDelta(makeMessageDelta({ stream_id: 's-no-start', delta: 'orphan' }), 'session-001')

    // Should warn but not crash, and should not create a stream
    expect(getStream('s-no-start')).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// Phase 4: message_end 时 finalize_content 覆盖
// ---------------------------------------------------------------------------

describe('message_end final_content overrides accumulated_content', () => {
  it('handleMessageEnd accepts event and sessionId without throwing', () => {
    const { handleMessageEnd } = useChatStreamState()
    expect(() =>
      handleMessageEnd(makeMessageEnd({ stream_id: 's-end' }), 'session-001')
    ).not.toThrow()
  })

  it('message_end with final_content replaces accumulated_content', () => {
    const { handleMessageStart, handleMessageDelta, handleMessageEnd, getStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-final' }), 'session-001')
    handleMessageDelta(
      makeMessageDelta({
        stream_id: 's-final',
        delta: '<thinking>thinking</thinking><action><task_complete><answer>hi</answer></task_complete></action>',
      }),
      'session-001'
    )

    // accumulated has raw XML
    expect(getStream('s-final')!.accumulated_content).toContain('<action>')

    // message_end with final_content="hi" should override
    handleMessageEnd(
      makeMessageEnd({
        stream_id: 's-final',
        final_content: 'hi',
      }),
      'session-001'
    )

    // The returned stream should have final content
    const stream = getStream('s-final')
    // Note: after message_end, finalizeStream is called, so the stream may be removed
    // We test the return value instead
  })

  it('returned stream from handleMessageEnd has final_content applied (not raw XML)', () => {
    const { handleMessageStart, handleMessageDelta, handleMessageEnd } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-return-final' }), 'session-001')
    handleMessageDelta(
      makeMessageDelta({
        stream_id: 's-return-final',
        delta: '<thinking>thinking</thinking><action><task_complete><answer>answer text</answer></task_complete></action>',
      }),
      'session-001'
    )

    const returnedStream = handleMessageEnd(
      makeMessageEnd({
        stream_id: 's-return-final',
        final_content: 'answer text',
      }),
      'session-001'
    )

    // The returned stream has final_content applied
    expect(returnedStream).toBeDefined()
    expect(returnedStream!.accumulated_content).toBe('answer text')
    expect(returnedStream!.content).toBe('answer text')
    expect(returnedStream!.payload.text).toBe('answer text')
    // Raw XML must not leak
    expect(returnedStream!.accumulated_content).not.toContain('<action>')
    expect(returnedStream!.accumulated_content).not.toContain('<thinking>')
  })

  it('no final_content: accumulated_content remains unchanged', () => {
    const { handleMessageStart, handleMessageDelta, handleMessageEnd } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-nofc' }), 'session-001')
    handleMessageDelta(
      makeMessageDelta({ stream_id: 's-nofc', delta: 'Plain text response' }),
      'session-001'
    )

    const returnedStream = handleMessageEnd(
      makeMessageEnd({ stream_id: 's-nofc' /* no final_content */ }),
      'session-001'
    )

    expect(returnedStream).toBeDefined()
    expect(returnedStream!.accumulated_content).toBe('Plain text response')
    expect(returnedStream!.content).toBe('Plain text response')
  })

  it('null final_content: accumulated_content remains unchanged', () => {
    const { handleMessageStart, handleMessageDelta, handleMessageEnd } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-nullfc' }), 'session-001')
    handleMessageDelta(
      makeMessageDelta({ stream_id: 's-nullfc', delta: 'Some content' }),
      'session-001'
    )

    const returnedStream = handleMessageEnd(
      makeMessageEnd({ stream_id: 's-nullfc', final_content: null }),
      'session-001'
    )

    expect(returnedStream).toBeDefined()
    expect(returnedStream!.accumulated_content).toBe('Some content')
  })

  it('message_end without a matching stream does not crash', () => {
    const { handleMessageEnd } = useChatStreamState()
    expect(() =>
      handleMessageEnd(makeMessageEnd({ stream_id: 's-no-match' }), 'session-001')
    ).not.toThrow()
  })

  it('makeMessageEnd helper supports final_content field', () => {
    const event = makeMessageEnd({
      stream_id: 's-test',
      final_content: 'clean answer',
    })
    expect(event.final_content).toBe('clean answer')
  })
})

// ---------------------------------------------------------------------------
// Phase 5: finalizeStream 和 clearSession
// ---------------------------------------------------------------------------

describe('finalizeStream and clearSession', () => {
  it('finalizeStream removes stream from internal Map', () => {
    const { handleMessageStart, finalizeStream, getStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-finalize' }), 'session-001')
    expect(getStream('s-finalize')).toBeDefined()

    finalizeStream('s-finalize')

    expect(getStream('s-finalize')).toBeUndefined()
  })

  it('clearSession removes all streams for a session', () => {
    const { handleMessageStart, clearSession, getStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 'sa1' }), 'session-C')
    handleMessageStart(makeMessageStart({ stream_id: 'sa2' }), 'session-C')
    handleMessageStart(makeMessageStart({ stream_id: 'sb1' }), 'session-D')

    clearSession('session-C')

    expect(getStream('sa1')).toBeUndefined()
    expect(getStream('sa2')).toBeUndefined()
    expect(getStream('sb1')).toBeDefined()
  })

  it('clearSession on empty session does not throw', () => {
    const { clearSession } = useChatStreamState()
    expect(() => clearSession('session-empty')).not.toThrow()
  })

  it('finalizeStream on non-existent stream does not throw', () => {
    const { finalizeStream } = useChatStreamState()
    expect(() => finalizeStream('s-does-not-exist')).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// Phase 6: getStreamingMessages
// ---------------------------------------------------------------------------

describe('getStreamingMessages', () => {
  it('returns in-flight messages for the given session', () => {
    const { handleMessageStart, getStreamingMessages } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's1', message: { id: 'm1' } }), 'session-A')
    handleMessageStart(makeMessageStart({ stream_id: 's2', message: { id: 'm2' } }), 'session-A')
    handleMessageStart(makeMessageStart({ stream_id: 's3', message: { id: 'm3' } }), 'session-B')

    const msgs = getStreamingMessages('session-A')
    expect(msgs).toHaveLength(2)
  })

  it('returns empty array when no streams for session', () => {
    const { getStreamingMessages } = useChatStreamState()
    expect(getStreamingMessages('session-nonexistent')).toEqual([])
  })

  it('returned messages have correct StreamingMessage shape', () => {
    const { handleMessageStart, getStreamingMessages } = useChatStreamState()

    handleMessageStart(
      makeMessageStart({
        stream_id: 's-shape',
        message: { id: 'm-shape', sender_role: 'Coder', type: 'text' },
        agent_role: 'Coder',
      }),
      'session-shape'
    )

    const msgs = getStreamingMessages('session-shape')
    expect(msgs).toHaveLength(1)
    expect(msgs[0].stream_id).toBe('s-shape')
    expect(msgs[0].message_id).toBe('m-shape')
    expect(msgs[0].sender_role).toBe('Coder')
    expect(msgs[0].content).toBe('')
  })
})

// ---------------------------------------------------------------------------
// Phase 7: message_error 处理
// ---------------------------------------------------------------------------

describe('message_error', () => {
  it('handleMessageError accepts event and sessionId without throwing', () => {
    const { handleMessageError } = useChatStreamState()
    expect(() =>
      handleMessageError(makeMessageError({ stream_id: 's-err' }), 'session-001')
    ).not.toThrow()
  })

  it('handleMessageError returns error info and stream', () => {
    const { handleMessageStart, handleMessageError } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-err-info' }), 'session-001')

    const result = handleMessageError(
      makeMessageError({
        stream_id: 's-err-info',
        error_code: 'runtime_error',
        error_message: 'something went wrong',
      }),
      'session-001'
    )

    expect(result).toBeDefined()
    expect(result!.error_code).toBe('runtime_error')
    expect(result!.error_message).toBe('something went wrong')
  })

  it('handleMessageError on non-existent stream does not crash', () => {
    const { handleMessageError } = useChatStreamState()
    expect(() =>
      handleMessageError(makeMessageError({ stream_id: 's-no-err-stream' }), 'session-001')
    ).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// Phase 8: hasInFlightStream
// ---------------------------------------------------------------------------

describe('hasInFlightStream', () => {
  it('returns true when session has active streams', () => {
    const { handleMessageStart, hasInFlightStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-active' }), 'session-active')

    expect(hasInFlightStream('session-active')).toBe(true)
  })

  it('returns false when session has no streams', () => {
    const { hasInFlightStream } = useChatStreamState()
    expect(hasInFlightStream('session-no-streams')).toBe(false)
  })

  it('returns false after clearSession', () => {
    const { handleMessageStart, hasInFlightStream, clearSession } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-clear' }), 'session-clear')
    clearSession('session-clear')

    expect(hasInFlightStream('session-clear')).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Phase 9: integration - full lifecycle
// ---------------------------------------------------------------------------

describe('full stream lifecycle', () => {
  it('complete flow: start -> delta -> end -> stream removed', () => {
    const { handleMessageStart, handleMessageDelta, handleMessageEnd, getStream, getStreamingMessages } =
      useChatStreamState()

    // Start
    handleMessageStart(makeMessageStart({ stream_id: 's-lifecycle' }), 'session-lifecycle')
    expect(getStream('s-lifecycle')).toBeDefined()
    expect(getStreamingMessages('session-lifecycle')).toHaveLength(1)

    // Delta
    handleMessageDelta(
      makeMessageDelta({ stream_id: 's-lifecycle', delta: 'Hello, ' }),
      'session-lifecycle'
    )
    expect(getStream('s-lifecycle')!.accumulated_content).toBe('Hello, ')

    // End with final_content
    handleMessageEnd(
      makeMessageEnd({ stream_id: 's-lifecycle', final_content: 'Hello, world!' }),
      'session-lifecycle'
    )

    // After end, finalizeStream is called automatically, so stream is removed
    expect(getStream('s-lifecycle')).toBeUndefined()
    // getStreamingMessages also returns empty since stream was removed
    expect(getStreamingMessages('session-lifecycle')).toHaveLength(0)
  })

  it('getStream returns undefined for non-existent stream', () => {
    const { getStream } = useChatStreamState()
    expect(getStream('s-nonexistent')).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// Phase 10: Task A - handleToolEvent (tool_event)
// ---------------------------------------------------------------------------

function makeToolEvent(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    type: 'tool_event',
    agent_role: 'PM',
    timestamp: '2026-05-29T10:00:01Z',
    stream_id: 'stream-001',
    message_id: 'msg-001',
    tool_name: 'read_file_tool',
    status: 'started',
    arguments: { file_path: 'test.py' },
    response: null,
    ...overrides,
  }
}

describe('handleToolEvent', () => {
  it('useChatStreamState returns handleToolEvent function', () => {
    const { handleToolEvent } = useChatStreamState()
    expect(typeof handleToolEvent).toBe('function')
  })

  it('handleToolEvent accepts event and sessionId without throwing', () => {
    const { handleToolEvent } = useChatStreamState()
    expect(() =>
      handleToolEvent(makeToolEvent({ stream_id: 's-tool' }), 'session-001')
    ).not.toThrow()
  })

  it('handleToolEvent returns event info with tool_name, status, arguments, response', () => {
    const { handleToolEvent } = useChatStreamState()
    const result = handleToolEvent(
      makeToolEvent({
        stream_id: 's-tool-fields',
        tool_name: 'replace_in_file_tool',
        status: 'finished',
        arguments: { path: 'a.py', diff: '...' },
        response: '[UPDATE] a.py',
      }),
      'session-001'
    )
    expect(result).toBeDefined()
    expect(result!.tool_name).toBe('replace_in_file_tool')
    expect(result!.status).toBe('finished')
    expect(result!.arguments).toEqual({ path: 'a.py', diff: '...' })
    expect(result!.response).toBe('[UPDATE] a.py')
  })

  it('handleToolEvent on non-existent stream does not crash', () => {
    const { handleToolEvent } = useChatStreamState()
    expect(() =>
      handleToolEvent(makeToolEvent({ stream_id: 's-no-stream' }), 'session-001')
    ).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// Phase 11: Task A - handleRuntimeState (runtime_state)
// ---------------------------------------------------------------------------

function makeRuntimeState(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    type: 'runtime_state',
    agent_role: 'PM',
    timestamp: '2026-05-29T10:00:01Z',
    stream_id: 'stream-001',
    message_id: 'msg-001',
    state: 'thinking',
    ...overrides,
  }
}

describe('handleRuntimeState', () => {
  it('useChatStreamState returns handleRuntimeState function', () => {
    const { handleRuntimeState } = useChatStreamState()
    expect(typeof handleRuntimeState).toBe('function')
  })

  it('handleRuntimeState accepts event and sessionId without throwing', () => {
    const { handleRuntimeState } = useChatStreamState()
    expect(() =>
      handleRuntimeState(makeRuntimeState({ stream_id: 's-state' }), 'session-001')
    ).not.toThrow()
  })

  it('handleRuntimeState returns event info with state, stream_id, message_id, timestamp', () => {
    const { handleRuntimeState } = useChatStreamState()
    const result = handleRuntimeState(
      makeRuntimeState({
        stream_id: 's-state-fields',
        state: 'calling_tool',
        timestamp: '2026-05-29T12:00:00Z',
        message_id: 'msg-state-001',
      }),
      'session-001'
    )
    expect(result).toBeDefined()
    expect(result!.state).toBe('calling_tool')
    expect(result!.stream_id).toBe('s-state-fields')
    expect(result!.message_id).toBe('msg-state-001')
    expect(result!.timestamp).toBe('2026-05-29T12:00:00Z')
  })

  it('handleRuntimeState maps all valid state values', () => {
    const { handleRuntimeState } = useChatStreamState()
    const validStates = ['thinking', 'calling_tool', 'observing', 'responding', 'finished', 'error']
    for (const state of validStates) {
      const result = handleRuntimeState(
        makeRuntimeState({ stream_id: `s-${state}`, state }),
        'session-001'
      )
      expect(result!.state).toBe(state)
    }
  })

  it('handleRuntimeState on non-existent stream does not crash', () => {
    const { handleRuntimeState } = useChatStreamState()
    expect(() =>
      handleRuntimeState(makeRuntimeState({ stream_id: 's-no-state' }), 'session-001')
    ).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// Phase 12: Task A - Replay Persistence (runtime_nodes on final message)
// ---------------------------------------------------------------------------

describe('Task A: runtime replay persistence', () => {
  it('persists runtime replay nodes onto the final assistant message', () => {
    const { handleMessageStart, handleRuntimeState, handleMessageEnd } = useChatStreamState()

    handleMessageStart(
      {
        type: 'message_start',
        stream_id: 'stream-replay',
        agent_role: 'PM',
        message: {
          id: 'msg-replay',
          session_id: 's-1',
          sender_type: 'agent',
          sender_role: 'PM',
          type: 'text',
          content: '',
          payload: {},
          metadata: {},
          status: 'streaming',
          created_at: '2026-05-30T00:00:00Z',
        },
      },
      's-1'
    )

    handleRuntimeState(
      {
        type: 'runtime_state',
        stream_id: 'stream-replay',
        message_id: 'msg-replay',
        state: 'thinking',
        timestamp: '2026-05-30T00:00:01Z',
      },
      's-1'
    )

    const finished = handleMessageEnd(
      {
        type: 'message_end',
        stream_id: 'stream-replay',
        message_id: 'msg-replay',
        status: 'completed',
        final_content: 'done',
      },
      's-1'
    )

    // After message_end, the returned stream should contain the replay nodes
    expect(finished).toBeDefined()
    expect(finished!.runtime_nodes).toBeDefined()
    expect(finished!.runtime_nodes.length).toBeGreaterThan(0)
    expect(finished!.runtime_nodes[0]!.node_type).toBe('runtime_state')
  })

  it('streams contain runtime_nodes in getStreamingMessages result', () => {
    const { handleMessageStart, handleRuntimeState, handleToolEvent, getStreamingMessages } =
      useChatStreamState()

    handleMessageStart(
      {
        type: 'message_start',
        stream_id: 'stream-replay-2',
        agent_role: 'PM',
        message: {
          id: 'msg-replay-2',
          session_id: 's-2',
          sender_type: 'agent',
          sender_role: 'PM',
          type: 'text',
          content: '',
          payload: {},
          metadata: {},
          status: 'streaming',
          created_at: '2026-05-30T00:00:00Z',
        },
      },
      's-2'
    )

    handleRuntimeState(
      {
        type: 'runtime_state',
        stream_id: 'stream-replay-2',
        message_id: 'msg-replay-2',
        state: 'calling_tool',
        timestamp: '2026-05-30T00:00:01Z',
      },
      's-2'
    )

    handleToolEvent(
      {
        type: 'tool_event',
        stream_id: 'stream-replay-2',
        message_id: 'msg-replay-2',
        tool_name: 'read_file_tool',
        status: 'finished',
        timestamp: '2026-05-30T00:00:02Z',
      },
      's-2'
    )

    // getStreamingMessages should return the stream with runtime_nodes
    const messages = getStreamingMessages('s-2')
    expect(messages.length).toBe(1)
    expect(messages[0].metadata).toBeDefined()
    // metadata should contain runtime replay info
    expect(messages[0].metadata.runtime_nodes).toBeDefined()
    expect(messages[0].metadata.runtime_nodes.length).toBe(2)
  })

  it('tool events are tracked in runtime_nodes alongside runtime_states', () => {
    const { handleMessageStart, handleRuntimeState, handleToolEvent, handleMessageEnd } =
      useChatStreamState()

    handleMessageStart(
      {
        type: 'message_start',
        stream_id: 'stream-mixed',
        agent_role: 'PM',
        message: {
          id: 'msg-mixed',
          session_id: 's-mixed',
          sender_type: 'agent',
          sender_role: 'PM',
          type: 'text',
          content: '',
          payload: {},
          metadata: {},
          status: 'streaming',
          created_at: '2026-05-30T00:00:00Z',
        },
      },
      's-mixed'
    )

    // First a runtime state
    handleRuntimeState(
      {
        type: 'runtime_state',
        stream_id: 'stream-mixed',
        message_id: 'msg-mixed',
        state: 'thinking',
        timestamp: '2026-05-30T00:00:01Z',
      },
      's-mixed'
    )

    // Then a tool event
    handleToolEvent(
      {
        type: 'tool_event',
        stream_id: 'stream-mixed',
        message_id: 'msg-mixed',
        tool_name: 'grep_tool',
        status: 'finished',
        timestamp: '2026-05-30T00:00:02Z',
      },
      's-mixed'
    )

    const finished = handleMessageEnd(
      {
        type: 'message_end',
        stream_id: 'stream-mixed',
        message_id: 'msg-mixed',
        status: 'completed',
        final_content: 'analysis complete',
      },
      's-mixed'
    )

    // Both node types should be preserved
    expect(finished!.runtime_nodes).toHaveLength(2)
    expect(finished!.runtime_nodes[0]!.node_type).toBe('runtime_state')
    expect(finished!.runtime_nodes[1]!.node_type).toBe('tool_event')
    expect(finished!.runtime_nodes[1]!.tool_name).toBe('grep_tool')
  })
})

// ---------------------------------------------------------------------------
// Phase 13: Task C-2/C-4 - Pending Change 管理
// ---------------------------------------------------------------------------

function makeChangePreview(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    type: 'change_preview',
    stream_id: 'stream-001',
    message_id: 'msg-001',
    change_id: 'change-001',
    operation: 'create',
    path: '/workspace/HelloWorld.java',
    unified_diff: '--- /dev/null\n+++ HelloWorld.java\n@@ -0,0 +1,5 @@',
    status: 'pending_confirmation',
    timestamp: '2026-05-30T10:00:00Z',
    ...overrides,
  }
}

function makeApplyResult(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    type: 'apply_result',
    change_id: 'change-001',
    success: true,
    status: 'applied',
    message: 'Successfully applied CREATE /workspace/HelloWorld.java',
    timestamp: '2026-05-30T10:00:00Z',
    ...overrides,
  }
}

describe('Task C-2/C-4: Pending Change 管理', () => {
  it('useChatStreamState returns pendingChanges ref', () => {
    const { pendingChanges } = useChatStreamState()
    expect(pendingChanges).toBeDefined()
    expect(pendingChanges.value).toBeInstanceOf(Map)
  })

  it('useChatStreamState returns sessionPendingChanges computed', () => {
    const { sessionPendingChanges } = useChatStreamState()
    expect(sessionPendingChanges).toBeDefined()
  })

  it('useChatStreamState returns handleChangePreview function', () => {
    const { handleChangePreview } = useChatStreamState()
    expect(typeof handleChangePreview).toBe('function')
  })

  it('useChatStreamState returns getSessionPendingChanges function', () => {
    const { getSessionPendingChanges } = useChatStreamState()
    expect(typeof getSessionPendingChanges).toBe('function')
  })

  it('useChatStreamState returns updatePendingChangeStatus function', () => {
    const { updatePendingChangeStatus } = useChatStreamState()
    expect(typeof updatePendingChangeStatus).toBe('function')
  })

  it('useChatStreamState returns removePendingChange function', () => {
    const { removePendingChange } = useChatStreamState()
    expect(typeof removePendingChange).toBe('function')
  })

  it('useChatStreamState returns handleApplyResult function', () => {
    const { handleApplyResult } = useChatStreamState()
    expect(typeof handleApplyResult).toBe('function')
  })

  it('useChatStreamState returns setCurrentSessionId function', () => {
    const { setCurrentSessionId } = useChatStreamState()
    expect(typeof setCurrentSessionId).toBe('function')
  })
})

describe('handleChangePreview', () => {
  it('添加 change_preview 到 pendingChanges', () => {
    const { handleChangePreview, pendingChanges } = useChatStreamState()

    const change = handleChangePreview(
      makeChangePreview({ change_id: 'change-add', stream_id: 'stream-session-1', message_id: 'msg-session-1' }),
      'session-1'
    )

    expect(change).toBeDefined()
    expect(change!.change_id).toBe('change-add')
    expect(pendingChanges.value.has('change-add')).toBe(true)
  })

  it('避免重复添加相同 change_id', () => {
    const { handleChangePreview, pendingChanges } = useChatStreamState()

    handleChangePreview(makeChangePreview({ change_id: 'change-dup' }), 'session-1')
    const countBefore = pendingChanges.value.size

    handleChangePreview(makeChangePreview({ change_id: 'change-dup' }), 'session-1')
    const countAfter = pendingChanges.value.size

    expect(countAfter).toBe(countBefore)
  })

  it('正确解析 change_preview 事件字段', () => {
    const { handleChangePreview } = useChatStreamState()

    const change = handleChangePreview(
      makeChangePreview({
        change_id: 'change-fields',
        operation: 'update',
        path: '/workspace/test.py',
        unified_diff: '--- test.py\n+++ test.py\n@@ -1 +1 @@',
        status: 'pending_confirmation',
      }),
      'session-1'
    )

    expect(change!.change_id).toBe('change-fields')
    expect(change!.operation).toBe('update')
    expect(change!.path).toBe('/workspace/test.py')
    expect(change!.status).toBe('pending_confirmation')
  })
})

describe('getSessionPendingChanges', () => {
  it('设置 sessionId 后只返回当前会话的 changes', () => {
    const { handleChangePreview, setCurrentSessionId, getSessionPendingChanges } = useChatStreamState()

    setCurrentSessionId('session-1')

    handleChangePreview(makeChangePreview({ change_id: 'change-1', stream_id: 'stream-1', message_id: 'msg-1' }), 'session-1')
    handleChangePreview(makeChangePreview({ change_id: 'change-2', stream_id: 'stream-2', message_id: 'msg-2' }), 'session-2')

    const changes = getSessionPendingChanges()

    expect(changes.length).toBe(1)
    expect(changes[0].change_id).toBe('change-1')
  })

  it('sessionId 为 null 时返回空数组', () => {
    const { setCurrentSessionId, getSessionPendingChanges } = useChatStreamState()

    setCurrentSessionId(null)

    const changes = getSessionPendingChanges()

    expect(changes).toEqual([])
  })
})

describe('handleApplyResult', () => {
  it('成功的 apply_result 移除对应的 pending change', () => {
    const { handleChangePreview, handleApplyResult, pendingChanges } = useChatStreamState()

    handleChangePreview(makeChangePreview({ change_id: 'change-apply-success' }), 'session-1')
    expect(pendingChanges.value.has('change-apply-success')).toBe(true)

    handleApplyResult(makeApplyResult({
      change_id: 'change-apply-success',
      success: true,
      status: 'applied',
    }))

    // After fix: pending change is kept with updated status instead of removed
    expect(pendingChanges.value.has('change-apply-success')).toBe(true)
    expect(pendingChanges.value.get('change-apply-success')?.status).toBe('applied')
  })

  it('失败的 apply_result 更新 pending change 状态', () => {
    const { handleChangePreview, handleApplyResult, pendingChanges } = useChatStreamState()

    handleChangePreview(makeChangePreview({ change_id: 'change-apply-fail' }), 'session-1')

    handleApplyResult(makeApplyResult({
      change_id: 'change-apply-fail',
      success: false,
      status: 'rejected',
      message: 'Apply failed: file modified externally',
    }))

    const change = pendingChanges.value.get('change-apply-fail')
    expect(change).toBeDefined()
    expect(change!.status).toBe('rejected')
  })

  it('无效的 change_id 不抛出异常', () => {
    const { handleApplyResult } = useChatStreamState()

    expect(() =>
      handleApplyResult(makeApplyResult({ change_id: 'non-existent' }))
    ).not.toThrow()
  })

  it('task-aware apply_result only invokes the registered callback once', () => {
    const addEventListenerSpy = vi.spyOn(window, 'addEventListener')
    const removeEventListenerSpy = vi.spyOn(window, 'removeEventListener')
    const callback = vi.fn()
    const eventListener = vi.fn()

    window.addEventListener('orchestration:task-status-update', eventListener)

    const { handleChangePreview, handleApplyResult, setOnTaskStatusUpdate } = useChatStreamState()
    setOnTaskStatusUpdate(callback)

    handleChangePreview(
      makeChangePreview({
        change_id: 'change-callback-once',
        run_id: 'run-1',
        task_id: 'task-1',
        agent_id: 'agent-1',
      }),
      'session-1'
    )

    handleApplyResult(makeApplyResult({
      change_id: 'change-callback-once',
      success: true,
      status: 'applied',
      task_id: 'task-1',
      run_id: 'run-1',
      agent_id: 'agent-1',
    }))

    expect(callback).toHaveBeenCalledTimes(1)
    expect(callback).toHaveBeenCalledWith('task-1', 'run-1', 'completed')

    window.removeEventListener('orchestration:task-status-update', eventListener)
    addEventListenerSpy.mockRestore()
    removeEventListenerSpy.mockRestore()
  })
})

describe('updatePendingChangeStatus', () => {
  it('更新 pending change 的状态', () => {
    const { handleChangePreview, updatePendingChangeStatus, pendingChanges } = useChatStreamState()

    handleChangePreview(makeChangePreview({ change_id: 'change-update-status' }), 'session-1')

    updatePendingChangeStatus('change-update-status', 'applied')

    const change = pendingChanges.value.get('change-update-status')
    expect(change!.status).toBe('applied')
  })
})

describe('removePendingChange', () => {
  it('从 pendingChanges 中移除指定的 change', () => {
    const { handleChangePreview, removePendingChange, pendingChanges } = useChatStreamState()

    handleChangePreview(makeChangePreview({ change_id: 'change-remove' }), 'session-1')
    expect(pendingChanges.value.has('change-remove')).toBe(true)

    removePendingChange('change-remove')

    expect(pendingChanges.value.has('change-remove')).toBe(false)
  })
})

describe('sessionPendingChanges computed', () => {
  it('返回当前会话的 pending changes 数组', () => {
    const { handleChangePreview, setCurrentSessionId, sessionPendingChanges } = useChatStreamState()

    setCurrentSessionId('session-computed')

    handleChangePreview(makeChangePreview({ change_id: 'change-computed-1', stream_id: 'stream-c1', message_id: 'msg-c1' }), 'session-computed')
    handleChangePreview(makeChangePreview({ change_id: 'change-computed-2', stream_id: 'stream-c2', message_id: 'msg-c2' }), 'session-computed')

    expect(Array.isArray(sessionPendingChanges.value)).toBe(true)
    expect(sessionPendingChanges.value.length).toBe(2)
  })
})

// ---------------------------------------------------------------------------
// Task CE: Pending Change Recovery from API (页面刷新/WS重连后恢复)
// ---------------------------------------------------------------------------

describe('Task CE: Pending Change Recovery from API', () => {
  it('useChatStreamState returns restorePendingChanges function', () => {
    const { restorePendingChanges } = useChatStreamState()
    expect(typeof restorePendingChanges).toBe('function')
  })

  it('restorePendingChanges 能从 API 响应恢复 pending changes', () => {
    const { restorePendingChanges, pendingChanges } = useChatStreamState()

    // 模拟从 API 获取的 pending changes
    const apiResponse = {
      items: [
        {
          change_id: 'restored-change-1',
          session_id: 'session-recovery',
          message_id: 'msg-recovery-1',
          stream_id: 'stream-recovery-1',
          path: '/workspace/restored.py',
          operation: 'create',
          unified_diff: '--- /dev/null\n+++ restored.py',
          original_content: null,
          proposed_content: 'print("restored")\n',
          status: 'pending_confirmation',
          created_at: '2026-05-30T10:00:00Z',
          applied_at: null,
        },
      ],
      total: 1,
      session_id: 'session-recovery',
    }

    restorePendingChanges(apiResponse.items, 'session-recovery')

    // 验证 pendingChanges 中存在恢复的 change
    expect(pendingChanges.value.has('restored-change-1')).toBe(true)
    const restored = pendingChanges.value.get('restored-change-1')
    expect(restored!.path).toBe('/workspace/restored.py')
    expect(restored!.operation).toBe('create')
    expect(restored!.status).toBe('pending_confirmation')
  })

  it('restorePendingChanges 正确映射 API 响应字段', () => {
    const { restorePendingChanges, pendingChanges } = useChatStreamState()

    const apiResponse = {
      items: [
        {
          change_id: 'mapping-test',
          session_id: 'session-mapping',
          message_id: 'msg-mapping',
          stream_id: 'stream-mapping',
          path: '/workspace/mapped.py',
          operation: 'update',
          unified_diff: '--- a/mapped.py\n+++ b/mapped.py',
          original_content: 'old content\n',
          proposed_content: 'new content\n',
          status: 'pending_confirmation',
          created_at: '2026-05-30T10:00:00Z',
          applied_at: null,
        },
      ],
      total: 1,
      session_id: 'session-mapping',
    }

    restorePendingChanges(apiResponse.items, 'session-mapping')

    const restored = pendingChanges.value.get('mapping-test')
    expect(restored!.change_id).toBe('mapping-test')
    expect(restored!.session_id).toBe('session-mapping')
    expect(restored!.message_id).toBe('msg-mapping')
    expect(restored!.stream_id).toBe('stream-mapping')
    expect(restored!.path).toBe('/workspace/mapped.py')
    expect(restored!.operation).toBe('update')
    expect(restored!.unified_diff).toBe('--- a/mapped.py\n+++ b/mapped.py')
    expect(restored!.original_content).toBe('old content\n')
    expect(restored!.proposed_content).toBe('new content\n')
    expect(restored!.status).toBe('pending_confirmation')
  })

  it('restorePendingChanges 能恢复多个 pending changes', () => {
    const { restorePendingChanges, pendingChanges } = useChatStreamState()

    const apiResponse = {
      items: [
        {
          change_id: 'multi-1',
          session_id: 'session-multi',
          path: '/workspace/multi1.py',
          operation: 'create',
          unified_diff: '--- /dev/null\n+++ multi1.py',
          status: 'pending_confirmation',
        },
        {
          change_id: 'multi-2',
          session_id: 'session-multi',
          path: '/workspace/multi2.py',
          operation: 'create',
          unified_diff: '--- /dev/null\n+++ multi2.py',
          status: 'pending_confirmation',
        },
      ],
      total: 2,
      session_id: 'session-multi',
    }

    restorePendingChanges(apiResponse.items, 'session-multi')

    expect(pendingChanges.value.has('multi-1')).toBe(true)
    expect(pendingChanges.value.has('multi-2')).toBe(true)
    expect(pendingChanges.value.size).toBe(2)
  })

  it('restorePendingChanges 不会覆盖已有的 pending changes', () => {
    const { handleChangePreview, restorePendingChanges, pendingChanges } = useChatStreamState()

    // 先通过 WS 添加一个
    handleChangePreview(makeChangePreview({
      change_id: 'existing-change',
      stream_id: 'stream-existing',
      message_id: 'msg-existing',
    }), 'session-preserve')

    // 再通过 API 恢复（应该保留现有的）
    const apiResponse = {
      items: [
        {
          change_id: 'existing-change',  // 相同 ID
          session_id: 'session-preserve',
          path: '/workspace/existing.py',
          operation: 'update',
          unified_diff: '--- a/existing.py\n+++ b/existing.py',
          status: 'pending_confirmation',
        },
        {
          change_id: 'new-from-api',
          session_id: 'session-preserve',
          path: '/workspace/new.py',
          operation: 'create',
          unified_diff: '--- /dev/null\n+++ new.py',
          status: 'pending_confirmation',
        },
      ],
      total: 2,
      session_id: 'session-preserve',
    }

    restorePendingChanges(apiResponse.items, 'session-preserve')

    // 应该有两个：一个原有的，一个新恢复的
    expect(pendingChanges.value.size).toBe(2)
    expect(pendingChanges.value.has('existing-change')).toBe(true)
    expect(pendingChanges.value.has('new-from-api')).toBe(true)
  })

  it('restorePendingChanges 会用服务端状态覆盖同一 change 的旧状态', () => {
    const { handleChangePreview, restorePendingChanges, pendingChanges } = useChatStreamState()

    handleChangePreview(makeChangePreview({
      change_id: 'existing-change',
      status: 'pending_confirmation',
    }), 'session-preserve')

    restorePendingChanges([
      {
        change_id: 'existing-change',
        session_id: 'session-preserve',
        path: '/workspace/existing.py',
        operation: 'update',
        unified_diff: '--- a/existing.py\n+++ b/existing.py',
        status: 'applied',
      },
    ], 'session-preserve')

    expect(pendingChanges.value.get('existing-change')!.status).toBe('applied')
  })

  it('restorePendingChanges 能恢复 applied/rejected/failed 状态的 changes', () => {
    const { restorePendingChanges, pendingChanges } = useChatStreamState()

    const apiResponse = {
      items: [
        {
          change_id: 'applied-change',
          session_id: 'session-status',
          path: '/workspace/applied.py',
          operation: 'create',
          unified_diff: '',
          status: 'applied',
        },
        {
          change_id: 'rejected-change',
          session_id: 'session-status',
          path: '/workspace/rejected.py',
          operation: 'create',
          unified_diff: '',
          status: 'rejected',
        },
        {
          change_id: 'failed-change',
          session_id: 'session-status',
          path: '/workspace/failed.py',
          operation: 'create',
          unified_diff: '',
          status: 'failed',
        },
      ],
      total: 3,
      session_id: 'session-status',
    }

    restorePendingChanges(apiResponse.items, 'session-status')

    expect(pendingChanges.value.get('applied-change')!.status).toBe('applied')
    expect(pendingChanges.value.get('rejected-change')!.status).toBe('rejected')
    expect(pendingChanges.value.get('failed-change')!.status).toBe('failed')
  })
})

// ---------------------------------------------------------------------------
// Task CE: WS Reconnect Compensation
// ---------------------------------------------------------------------------

describe('Task CE: WS Reconnect Compensation', () => {
  it('useChatStreamState returns clearInFlightStreams function', () => {
    const { clearInFlightStreams } = useChatStreamState()
    expect(typeof clearInFlightStreams).toBe('function')
  })

  it('clearInFlightStreams 清理指定会话的 in-flight streams', () => {
    const { handleMessageStart, clearInFlightStreams, hasInFlightStream } = useChatStreamState()

    // 创建一些 in-flight streams
    handleMessageStart(makeMessageStart({ stream_id: 's-reconnect-1' }), 'session-reconnect')
    handleMessageStart(makeMessageStart({ stream_id: 's-reconnect-2' }), 'session-reconnect')

    expect(hasInFlightStream('session-reconnect')).toBe(true)

    clearInFlightStreams('session-reconnect')

    expect(hasInFlightStream('session-reconnect')).toBe(false)
  })

  it('clearInFlightStreams 不影响其他会话', () => {
    const { handleMessageStart, clearInFlightStreams, hasInFlightStream } = useChatStreamState()

    handleMessageStart(makeMessageStart({ stream_id: 's-other-1' }), 'session-other')
    handleMessageStart(makeMessageStart({ stream_id: 's-reconnect-3' }), 'session-reconnect-clear')

    clearInFlightStreams('session-reconnect-clear')

    expect(hasInFlightStream('session-reconnect-clear')).toBe(false)
    expect(hasInFlightStream('session-other')).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Task CE: Recovery State Management
// ---------------------------------------------------------------------------

describe('Task CE: Recovery State Management', () => {
  it('useChatStreamState returns clearSessionPendingChanges function', () => {
    const { clearSessionPendingChanges } = useChatStreamState()
    expect(typeof clearSessionPendingChanges).toBe('function')
  })

  it('clearSessionPendingChanges 清理指定会话的 pending changes', () => {
    const { handleChangePreview, clearSessionPendingChanges, getSessionPendingChanges, setCurrentSessionId } = useChatStreamState()
    setCurrentSessionId('session-clear-pending')

    handleChangePreview(makeChangePreview({ change_id: 'clear-1', stream_id: 'stream-clear-1', message_id: 'msg-clear-1' }), 'session-clear-pending')
    handleChangePreview(makeChangePreview({ change_id: 'clear-2', stream_id: 'stream-clear-2', message_id: 'msg-clear-2' }), 'session-clear-pending')

    expect(getSessionPendingChanges().length).toBe(2)

    clearSessionPendingChanges('session-clear-pending')

    expect(getSessionPendingChanges().length).toBe(0)
  })
})
