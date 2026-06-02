import { computed, ref } from 'vue'
import type {
  StreamingMessage,
  RuntimeStateValue,
  RuntimeProcessNode,
  ChangePreviewEvent,
  PendingChange,
} from '@/types/agenthub'
import type { AgentRole } from '@shared/index'

interface InFlightStream {
  stream_id: string
  message_id?: string
  session_id: string
  sender_role: AgentRole
  content: string
  accumulated_content: string
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy'
  payload: { text: string }
  metadata: Record<string, unknown>
  ui_status: 'thinking' | 'streaming' | 'done' | 'syncing_interrupted'
  created_at: string
  runtime_nodes: RuntimeProcessNode[]
  runtime_state?: RuntimeStateValue
}

interface ApplyResultEvent {
  type: 'apply_result'
  change_id: string
  success: boolean
  status: string
  message: string
}

interface RepairStateEventData {
  type: 'repair_state'
  state: string
  attempt: number
  max_attempts: number
  message: string
}

const STATE_TO_UI: Record<string, InFlightStream['ui_status']> = {
  thinking: 'thinking',
  calling_tool: 'streaming',
  observing: 'thinking',
  responding: 'streaming',
  finished: 'done',
  error: 'streaming',
}

export function useChatStreamState() {
  const streams = ref<Map<string, InFlightStream>>(new Map())
  const pendingChanges = ref<Map<string, PendingChange>>(new Map())
  const currentSessionId = ref<string | null>(null)
  const repairState = ref<{
    state: string
    attempt: number
    maxAttempts: number
    message: string
  } | null>(null)

  function replaceStream(streamId: string, stream: InFlightStream) {
    const newMap = new Map(streams.value)
    newMap.set(streamId, { ...stream })
    streams.value = newMap
  }

  function ensureStream(
    streamId: string,
    sessionId: string,
    options: {
      messageId?: string
      senderRole?: AgentRole
      timestamp?: string
      type?: InFlightStream['type']
      uiStatus?: InFlightStream['ui_status']
    } = {},
  ): InFlightStream {
    const existing = streams.value.get(streamId)
    if (existing) {
      if (options.messageId && !existing.message_id) {
        existing.message_id = options.messageId
        replaceStream(streamId, existing)
      }
      return existing
    }

    const stream: InFlightStream = {
      stream_id: streamId,
      message_id: options.messageId,
      session_id: sessionId,
      sender_role: options.senderRole || 'PM',
      content: '',
      accumulated_content: '',
      type: options.type || 'text',
      payload: { text: '' },
      metadata: {},
      ui_status: options.uiStatus || 'thinking',
      created_at: options.timestamp || new Date().toISOString(),
      runtime_nodes: [],
      runtime_state: undefined,
    }

    clearOtherSessionStreams(sessionId, streamId)
    replaceStream(streamId, stream)
    console.log('[StreamState] ensured placeholder stream:', streamId, 'session:', sessionId)
    return stream
  }

  function clearOtherSessionStreams(sessionId: string, keepStreamId?: string) {
    const toDelete: string[] = []
    streams.value.forEach((stream, streamId) => {
      if (stream.session_id !== sessionId) return
      if (keepStreamId && streamId === keepStreamId) return
      toDelete.push(streamId)
    })

    if (toDelete.length === 0) return

    const newMap = new Map(streams.value)
    toDelete.forEach((id) => newMap.delete(id))
    streams.value = newMap
    console.log('[StreamState] cleared stale session streams:', sessionId, toDelete)
  }

  function getStreamingMessages(sessionId: string): StreamingMessage[] {
    const messages: StreamingMessage[] = []
    streams.value.forEach((stream) => {
      if (stream.session_id !== sessionId) return
      messages.push({
        stream_id: stream.stream_id,
        message_id: stream.message_id,
        session_id: stream.session_id,
        sender_type: 'agent',
        sender_role: stream.sender_role,
        content: stream.accumulated_content,
        ui_status: stream.ui_status,
        is_ephemeral: !stream.message_id,
        created_at: stream.created_at,
        type: stream.type || 'text',
        payload: { text: stream.accumulated_content },
        metadata: {
          ...(stream.metadata || {}),
          runtime_nodes: [...stream.runtime_nodes],
          runtime_state: stream.runtime_state,
        },
      })
    })
    return messages
  }

  function handleMessageStart(event: any, sessionId: string) {
    const { stream_id, message, agent_role, timestamp } = event

    if (!stream_id || !message) return

    clearOtherSessionStreams(sessionId, stream_id)
    if (streams.value.has(stream_id)) return

    const stream: InFlightStream = {
      stream_id,
      message_id: message.id,
      session_id: sessionId,
      sender_role: agent_role || message.sender_role,
      content: '',
      accumulated_content: '',
      type: message.type || 'text',
      payload: { text: '' },
      metadata: message.metadata || {},
      ui_status: 'thinking',
      created_at: timestamp || message.created_at || new Date().toISOString(),
      runtime_nodes: [],
      runtime_state: undefined,
    }

    replaceStream(stream_id, stream)
    console.log('[StreamState] message_start:', stream_id, 'session:', sessionId)
    return stream
  }

  function handleMessageDelta(event: any, sessionId: string) {
    const { stream_id, delta, message_id } = event

    if (!stream_id) return

    const stream = ensureStream(stream_id, sessionId, {
      messageId: message_id,
      senderRole: (event.agent_role || event.sender_role || 'PM') as AgentRole,
      timestamp: event.timestamp,
      uiStatus: 'thinking',
    })

    stream.accumulated_content += delta
    stream.content = stream.accumulated_content
    stream.payload.text = stream.accumulated_content

    if (message_id && !stream.message_id) {
      stream.message_id = message_id
    }

    if (stream.ui_status === 'thinking' && stream.accumulated_content.length >= 10) {
      stream.ui_status = 'streaming'
    }

    replaceStream(stream_id, stream)
    console.log(
      '[StreamState] message_delta:',
      stream_id,
      'delta:',
      delta.substring(0, 20),
      'total:',
      stream.accumulated_content.length,
    )
    return stream
  }

  function handleMessageEnd(event: any, sessionId: string) {
    const { stream_id, status, message_id, final_content } = event

    if (!stream_id) return

    const stream = streams.value.get(stream_id)
    if (!stream) {
      console.warn('[StreamState] message_end but no stream:', stream_id)
      return
    }

    if (final_content !== undefined && final_content !== null) {
      stream.accumulated_content = final_content
      stream.content = final_content
      stream.payload.text = final_content
    }

    stream.ui_status = status === 'completed' ? 'done' : 'syncing_interrupted'

    replaceStream(stream_id, stream)

    console.log(
      '[StreamState] message_end:',
      stream_id,
      'status:',
      status,
      'content length:',
      stream.accumulated_content.length,
    )

    clearOtherSessionStreams(sessionId, stream_id)
    finalizeStream(stream_id)
    return stream
  }

  function handleMessageError(event: any, sessionId: string) {
    const { stream_id, error_code, error_message } = event

    if (!stream_id) return

    const stream = streams.value.get(stream_id)
    if (stream) {
      stream.ui_status = 'syncing_interrupted'
      replaceStream(stream_id, stream)
      console.error('[StreamState] message_error:', stream_id, error_code, error_message)
    }

    clearOtherSessionStreams(sessionId, stream_id)
    finalizeStream(stream_id)

    return { stream, error_code, error_message }
  }

  function finalizeStream(streamId: string) {
    const newMap = new Map(streams.value)
    newMap.delete(streamId)
    streams.value = newMap
    console.log('[StreamState] finalize:', streamId)
  }

  function clearSession(sessionId: string) {
    const toDelete: string[] = []
    streams.value.forEach((stream, streamId) => {
      if (stream.session_id === sessionId) {
        toDelete.push(streamId)
      }
    })

    if (toDelete.length > 0) {
      const newMap = new Map(streams.value)
      toDelete.forEach((id) => newMap.delete(id))
      streams.value = newMap
    }
  }

  function hasInFlightStream(sessionId: string): boolean {
    for (const stream of streams.value.values()) {
      if (stream.session_id === sessionId) {
        return true
      }
    }
    return false
  }

  function getStream(streamId: string): InFlightStream | undefined {
    return streams.value.get(streamId)
  }

  function getSessionIdForStream(streamId: string): string | undefined {
    return streams.value.get(streamId)?.session_id
  }

  function handleToolEvent(event: any, sessionId: string): any {
    const { stream_id, tool_name, status, arguments: toolArgs, response } = event

    if (!stream_id) return null

    const stream = ensureStream(stream_id, sessionId, {
      messageId: event.message_id,
      senderRole: (event.agent_role || event.sender_role || 'PM') as AgentRole,
      timestamp: event.timestamp,
      uiStatus: 'thinking',
    })

    const node: RuntimeProcessNode = {
      stream_id,
      message_id: event.message_id || stream?.message_id || '',
      timestamp: event.timestamp || new Date().toISOString(),
      node_type: 'tool_event',
      tool_name,
      tool_status: status,
    }

    stream.runtime_nodes.push(node)
    replaceStream(stream_id, stream)

    console.log(`[StreamState] tool_event: ${tool_name} ${status}`, stream_id)
    return { stream_id, tool_name, status, arguments: toolArgs, response }
  }

  function handleRuntimeState(event: any, sessionId: string): any {
    const { stream_id, state, message_id, timestamp } = event

    if (!stream_id) return null

    const stream = ensureStream(stream_id, sessionId, {
      messageId: message_id,
      senderRole: (event.agent_role || event.sender_role || 'PM') as AgentRole,
      timestamp,
      uiStatus: STATE_TO_UI[state] ?? 'thinking',
    })

    const node: RuntimeProcessNode = {
      stream_id,
      message_id: message_id || stream?.message_id || '',
      timestamp: timestamp || new Date().toISOString(),
      node_type: 'runtime_state',
      state,
    }

    stream.runtime_nodes.push(node)
    stream.runtime_state = state
    stream.ui_status = STATE_TO_UI[state] ?? 'streaming'
    replaceStream(stream_id, stream)

    console.log(`[StreamState] runtime_state: ${state}`, stream_id)
    return { stream_id, state, message_id: message_id || stream?.message_id, timestamp }
  }

  function setCurrentSessionId(sessionId: string | null) {
    currentSessionId.value = sessionId
  }

  function getSessionPendingChanges(): PendingChange[] {
    const changes: PendingChange[] = []
    const sessionId = currentSessionId.value
    if (!sessionId) return changes

    pendingChanges.value.forEach((change) => {
      if (change.session_id === sessionId) {
        changes.push(change)
      }
    })
    return changes
  }

  const sessionPendingChanges = computed(() => getSessionPendingChanges())

  function handleChangePreview(event: ChangePreviewEvent, sessionId: string) {
    const { change_id, operation, path, unified_diff, status, stream_id, message_id } = event

    if (!change_id) return null

    if (pendingChanges.value.has(change_id)) return pendingChanges.value.get(change_id)

    if (stream_id) {
      ensureStream(stream_id, sessionId, {
        messageId: message_id,
        senderRole: 'PM',
        timestamp: event.timestamp,
        uiStatus: 'thinking',
      })
    }

    const change: PendingChange = {
      change_id,
      operation,
      path,
      unified_diff,
      status,
      session_id: sessionId,
      stream_id,
      message_id,
    }

    const newMap = new Map(pendingChanges.value)
    newMap.set(change_id, change)
    pendingChanges.value = newMap

    console.log('[StreamState] change_preview:', change_id, 'operation:', operation, 'path:', path)
    return change
  }

  function getPendingChanges(sessionId: string): PendingChange[] {
    const changes: PendingChange[] = []
    pendingChanges.value.forEach((change) => {
      if (change.session_id === sessionId) {
        changes.push(change)
      }
    })
    return changes
  }

  function updatePendingChangeStatus(changeId: string, status: PendingChange['status']) {
    const change = pendingChanges.value.get(changeId)
    if (!change) return

    const newMap = new Map(pendingChanges.value)
    newMap.set(changeId, { ...change, status })
    pendingChanges.value = newMap
  }

  function removePendingChange(changeId: string) {
    const newMap = new Map(pendingChanges.value)
    newMap.delete(changeId)
    pendingChanges.value = newMap
    console.log('[StreamState] pending_change removed:', changeId)
  }

  function clearSessionPendingChanges(sessionId: string) {
    const toDelete: string[] = []
    pendingChanges.value.forEach((change, changeId) => {
      if (change.session_id === sessionId) {
        toDelete.push(changeId)
      }
    })

    if (toDelete.length > 0) {
      const newMap = new Map(pendingChanges.value)
      toDelete.forEach((id) => newMap.delete(id))
      pendingChanges.value = newMap
    }
  }

  function handleApplyResult(event: ApplyResultEvent) {
    const { change_id, success, status } = event

    if (!change_id) return

    console.log('[StreamState] apply_result:', change_id, 'success:', success, 'status:', status)

    // Always update the status so the frontend can display the result
    // instead of removing the change (which causes the status to revert to default).
    updatePendingChangeStatus(change_id, status as PendingChange['status'])
  }

  function handleRepairState(event: RepairStateEventData) {
    const { state, attempt, max_attempts, message } = event

    repairState.value = {
      state: state || 'IDLE',
      attempt: attempt || 0,
      maxAttempts: max_attempts || 3,
      message: message || '',
    }

    console.log('[StreamState] repair_state:', state, 'attempt:', attempt, '/', max_attempts)
  }

  function clearRepairState() {
    repairState.value = null
  }

  function restorePendingChanges(
    items: Array<{
      change_id: string
      session_id: string
      message_id?: string
      stream_id?: string
      path: string
      operation: 'create' | 'update' | 'delete'
      unified_diff: string
      original_content?: string
      proposed_content?: string
      status: PendingChange['status']
      created_at?: string
      applied_at?: string
    }>,
    sessionId: string,
  ) {
    console.log('[StreamState] restorePendingChanges:', items.length, 'items for session:', sessionId)

    items.forEach((item) => {
      if (pendingChanges.value.has(item.change_id)) {
        console.log('[StreamState] Skipping existing change_id:', item.change_id)
        return
      }

      const change: PendingChange = {
        change_id: item.change_id,
        session_id: item.session_id || sessionId,
        message_id: item.message_id || '',
        stream_id: item.stream_id || '',
        operation: item.operation,
        path: item.path,
        unified_diff: item.unified_diff || '',
        status: item.status,
        original_content: item.original_content,
        proposed_content: item.proposed_content,
      }

      const newMap = new Map(pendingChanges.value)
      newMap.set(item.change_id, change)
      pendingChanges.value = newMap

      console.log('[StreamState] Restored pending change:', item.change_id, item.path, item.status)
    })
  }

  function clearInFlightStreams(sessionId: string) {
    const toDelete: string[] = []
    streams.value.forEach((stream, streamId) => {
      if (stream.session_id === sessionId) {
        toDelete.push(streamId)
      }
    })

    if (toDelete.length > 0) {
      const newMap = new Map(streams.value)
      toDelete.forEach((id) => newMap.delete(id))
      streams.value = newMap
      console.log('[StreamState] Cleared in-flight streams:', toDelete)
    }
  }

  return {
    streams,
    getStreamingMessages,
    handleMessageStart,
    handleMessageDelta,
    handleMessageEnd,
    handleMessageError,
    finalizeStream,
    clearSession,
    hasInFlightStream,
    getStream,
    getSessionIdForStream,
    handleToolEvent,
    handleRuntimeState,
    pendingChanges,
    sessionPendingChanges,
    setCurrentSessionId,
    handleChangePreview,
    getPendingChanges,
    getSessionPendingChanges,
    updatePendingChangeStatus,
    removePendingChange,
    clearSessionPendingChanges,
    handleApplyResult,
    repairState,
    handleRepairState,
    clearRepairState,
    restorePendingChanges,
    clearInFlightStreams,
    clearOtherSessionStreams,
  }
}
