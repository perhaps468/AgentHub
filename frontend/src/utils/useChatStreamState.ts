import { ref } from 'vue'
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
  // Task A: 运行时过程节点，用于最小回放
  runtime_nodes: RuntimeProcessNode[]
  // Task A: 当前 agent 执行阶段
  runtime_state?: RuntimeStateValue
}

export function useChatStreamState() {
  // 统一的流状态存储
  const streams = ref<Map<string, InFlightStream>>(new Map())

  function getStreamingMessages(sessionId: string): StreamingMessage[] {
    const messages: StreamingMessage[] = []
    streams.value.forEach((stream) => {
      if (stream.session_id === sessionId) {
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
      }
    })
    return messages
  }

  function handleMessageStart(event: any, sessionId: string) {
    const { stream_id, message, agent_role, timestamp } = event

    if (!stream_id || !message) return

    // 避免重复创建
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
      ui_status: 'streaming',
      created_at: timestamp || message.created_at || new Date().toISOString(),
      runtime_nodes: [],  // Task A: 初始化运行时过程节点列表
      runtime_state: undefined,  // Task A: 初始无阶段
    }

    // 创建新 Map 触发响应式更新
    const newMap = new Map(streams.value)
    newMap.set(stream_id, stream)
    streams.value = newMap

    console.log('[StreamState] message_start:', stream_id, 'session:', sessionId)
    return stream
  }

  function handleMessageDelta(event: any, sessionId: string) {
    const { stream_id, delta, message_id } = event

    if (!stream_id) return

    const stream = streams.value.get(stream_id)
    if (!stream) {
      console.warn('[StreamState] message_delta but no stream:', stream_id)
      return
    }

    // 累加内容
    stream.accumulated_content += delta
    stream.content = stream.accumulated_content
    stream.payload.text = stream.accumulated_content

    if (message_id && !stream.message_id) {
      stream.message_id = message_id
    }

    // 创建新 Map 触发响应式更新
    const newMap = new Map(streams.value)
    newMap.set(stream_id, { ...stream })
    streams.value = newMap

    console.log('[StreamState] message_delta:', stream_id, 'delta:', delta.substring(0, 20), 'total:', stream.accumulated_content.length)
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

    // Prefer final_content (extracted answer from task_complete) over accumulated XML
    if (final_content !== undefined && final_content !== null) {
      stream.accumulated_content = final_content
      stream.content = final_content
      stream.payload.text = final_content
    }

    stream.ui_status = status === 'completed' ? 'done' : 'syncing_interrupted'

    // 创建新 Map 触发响应式更新
    const newMap = new Map(streams.value)
    newMap.set(stream_id, { ...stream })
    streams.value = newMap

    console.log('[StreamState] message_end:', stream_id, 'status:', status, 'content length:', stream.accumulated_content.length)

    // 从流中移除
    finalizeStream(stream_id)

    // 返回 stream 以便调用者可以合并消息
    return stream
  }

  function handleMessageError(event: any, sessionId: string) {
    const { stream_id, error_code, error_message } = event

    if (!stream_id) return

    const stream = streams.value.get(stream_id)
    if (stream) {
      stream.ui_status = 'syncing_interrupted'

      const newMap = new Map(streams.value)
      newMap.set(stream_id, { ...stream })
      streams.value = newMap

      console.error('[StreamState] message_error:', stream_id, error_code, error_message)
    }

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

  // ---------------------------------------------------------------------------
  // Task A: handleToolEvent — 记录工具执行事件到最小回放节点列表
  // ---------------------------------------------------------------------------

  function handleToolEvent(event: any, sessionId: string): any {
    const { stream_id, tool_name, status, arguments: toolArgs, response } = event

    if (!stream_id) return null

    const stream = streams.value.get(stream_id)

    const node: RuntimeProcessNode = {
      stream_id,
      message_id: event.message_id || stream?.message_id || '',
      timestamp: event.timestamp || new Date().toISOString(),
      node_type: 'tool_event',
      tool_name,
      tool_status: status,
    }

    if (stream) {
      stream.runtime_nodes.push(node)
      const newMap = new Map(streams.value)
      newMap.set(stream_id, { ...stream })
      streams.value = newMap
    }

    console.log(
      `[StreamState] tool_event: ${tool_name} ${status}`,
      stream_id
    )

    return { stream_id, tool_name, status, arguments: toolArgs, response }
  }

  // ---------------------------------------------------------------------------
  // Task A: handleRuntimeState — 记录运行时状态变化到最小回放节点列表
  // ---------------------------------------------------------------------------

  const STATE_TO_UI: Record<string, InFlightStream['ui_status']> = {
    thinking: 'thinking',
    calling_tool: 'streaming',
    observing: 'thinking',
    responding: 'streaming',
    finished: 'done',
    error: 'streaming',
  }

  function handleRuntimeState(event: any, sessionId: string): any {
    const { stream_id, state, message_id, timestamp } = event

    if (!stream_id) return null

    const stream = streams.value.get(stream_id)

    const node: RuntimeProcessNode = {
      stream_id,
      message_id: message_id || stream?.message_id || '',
      timestamp: timestamp || new Date().toISOString(),
      node_type: 'runtime_state',
      state,
    }

    if (stream) {
      stream.runtime_nodes.push(node)
      stream.runtime_state = state
      stream.ui_status = STATE_TO_UI[state] ?? 'streaming'
      const newMap = new Map(streams.value)
      newMap.set(stream_id, { ...stream })
      streams.value = newMap
    }

    console.log(`[StreamState] runtime_state: ${state}`, stream_id)

    return { stream_id, state, message_id: message_id || stream?.message_id, timestamp }
  }

  // ---------------------------------------------------------------------------
  // Task C-2: Pending Change 管理
  // ---------------------------------------------------------------------------

  // 待确认的 pending changes
  const pendingChanges = ref<Map<string, PendingChange>>(new Map())

  function handleChangePreview(event: ChangePreviewEvent, sessionId: string) {
    const { change_id, operation, path, unified_diff, status, stream_id, message_id } = event

    if (!change_id) return null

    // 避免重复添加
    if (pendingChanges.value.has(change_id)) return pendingChanges.value.get(change_id)

    const change: PendingChange = {
      change_id,
      operation,
      path,
      unified_diff,
      status,
      stream_id,
      message_id,
    }

    // 创建新 Map 触发响应式更新
    const newMap = new Map(pendingChanges.value)
    newMap.set(change_id, change)
    pendingChanges.value = newMap

    console.log('[StreamState] change_preview:', change_id, 'operation:', operation, 'path:', path)

    return change
  }

  function getPendingChanges(sessionId: string): PendingChange[] {
    const changes: PendingChange[] = []
    pendingChanges.value.forEach((change) => {
      if (change.message_id?.includes(sessionId) || change.stream_id?.includes(sessionId)) {
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
      if (change.message_id?.includes(sessionId) || change.stream_id?.includes(sessionId)) {
        toDelete.push(changeId)
      }
    })

    if (toDelete.length > 0) {
      const newMap = new Map(pendingChanges.value)
      toDelete.forEach((id) => newMap.delete(id))
      pendingChanges.value = newMap
    }
  }

  // ---------------------------------------------------------------------------
  // Task C-4: apply_result 处理
  // ---------------------------------------------------------------------------

  interface ApplyResultEvent {
    type: 'apply_result'
    change_id: string
    success: boolean
    status: string
    message: string
  }

  function handleApplyResult(event: ApplyResultEvent) {
    const { change_id, success, status, message } = event

    if (!change_id) return

    console.log('[StreamState] apply_result:', change_id, 'success:', success, 'status:', status)

    if (success) {
      // 成功后从待确认列表移除
      removePendingChange(change_id)
    } else {
      // 失败后更新状态
      const newStatus = status as PendingChange['status']
      updatePendingChangeStatus(change_id, newStatus)
    }
  }

  // ---------------------------------------------------------------------------
  // Task D-2: repair_state 处理
  // ---------------------------------------------------------------------------

  // 当前修复状态
  const repairState = ref<{
    state: string
    attempt: number
    maxAttempts: number
    message: string
  } | null>(null)

  interface RepairStateEventData {
    type: 'repair_state'
    state: string
    attempt: number
    max_attempts: number
    message: string
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
    // Task A: Runtime 扩展事件处理
    handleToolEvent,
    handleRuntimeState,
    // Task C-2: Pending Change 管理
    pendingChanges,
    handleChangePreview,
    getPendingChanges,
    updatePendingChangeStatus,
    removePendingChange,
    clearSessionPendingChanges,
    // Task C-4: apply_result 处理
    handleApplyResult,
    // Task D-2: repair_state 处理
    repairState,
    handleRepairState,
    clearRepairState,
  }
}
