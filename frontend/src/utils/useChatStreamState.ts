import { computed, ref } from 'vue'
import type {
  StreamingMessage,
  RuntimeStateValue,
  RuntimeProcessNode,
  ChangePreviewEvent,
  PendingChange,
  PptPreviewModel,
} from '@/types/agenthub'
import type { AgentRole } from '@shared/index'
import { resolvePptImage } from '../constants/ppt-image-map'

interface InFlightStream {
  stream_id: string
  message_id?: string
  session_id: string
  sender_role: AgentRole
  content: string
  accumulated_content: string
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy' | 'ppt_data'
  payload: { text: string } | Record<string, unknown>
  metadata: Record<string, unknown>
  ui_status: 'thinking' | 'streaming' | 'done' | 'syncing_interrupted'
  created_at: string
  runtime_nodes: RuntimeProcessNode[]
  runtime_state?: RuntimeStateValue
  // M6: Change preview data for inline confirmation buttons
  change_preview?: ChangePreviewStreamData
  // M6: Track confirmed/rejected status for change previews
  change_status?: 'pending' | 'confirmed' | 'rejected'
}

interface RestoreTaskStreamSnapshot {
  run_id?: string
  tasks: Array<{
    id: string
    assigned_agent_id?: string
    agent_role?: string  // M6: actual agent role for display
    agent_name?: string  // M6: actual agent name for display
    latest_stream?: {
      stream_id: string
      message_id?: string
      status?: string
    } | null
  }>
}

interface ApplyResultEvent {
  type: 'apply_result'
  change_id: string
  success: boolean
  status: string
  message: string
  // M4: Task-aware fields
  run_id?: string | null
  task_id?: string | null
  agent_id?: string | null
}

interface RepairStateEventData {
  type: 'repair_state'
  state: string
  attempt: number
  max_attempts: number
  message: string
}

// M6-EXT: ppt_data 事件（来自 tool_event HTML→PPT 拦截）
interface PptDataFromToolEvent {
  type: 'ppt_data'
  ppt_data: Array<{
    pageTitle: string
    pageContent: string[] | string
    imgTag: string
  }>
  agent_role?: string
  stream_id?: string
  message_id?: string
  timestamp?: string
}

// M6: Change preview as message - for rendering confirmation buttons inline in chat
interface ChangePreviewStreamData {
  change_id: string
  operation: string
  path: string
  unified_diff: string
  status: string
  run_id?: string | null
  task_id?: string | null
  agent_id?: string | null
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

    // Do NOT clear other streams - we support multiple streams per session
    // Previously this was: clearOtherSessionStreams(sessionId, streamId)
    replaceStream(streamId, stream)
    console.log('[StreamState] ensured placeholder stream:', streamId, 'session:', sessionId)
    return stream
  }

  function clearOtherSessionStreams(sessionId: string, keepStreamId?: string) {
    // Only clear streams from OTHER sessions, NOT the specified sessionId
    // This preserves sibling task streams in the same session
    const toDelete: string[] = []
    streams.value.forEach((stream, streamId) => {
      if (stream.session_id === sessionId) return  // Keep streams in this session
      if (keepStreamId && streamId === keepStreamId) return  // Keep the specified stream
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
        accumulated_content: stream.accumulated_content,
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

    // Do NOT clear other session streams - we support multiple streams per session
    // This was the old behavior: clearOtherSessionStreams(sessionId, stream_id)
    if (streams.value.has(stream_id)) return

    const initialContent = typeof message.content === 'string' && message.content.length > 0
      ? message.content
      : typeof message.payload?.text === 'string'
        ? message.payload.text
        : ''

    const stream: InFlightStream = {
      stream_id,
      message_id: message.id,
      session_id: sessionId,
      sender_role: agent_role || message.sender_role,
      content: initialContent,
      accumulated_content: initialContent,
      type: message.type || 'text',
      payload: { text: initialContent },
      metadata: {
        ...(message.metadata || {}),
        ...(event.run_id ? { run_id: event.run_id } : {}),
        ...(event.task_id ? { task_id: event.task_id } : {}),
        ...(event.agent_id ? { agent_id: event.agent_id } : {}),
      },
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

    // Do NOT finalize - keep stream in map so it can be queried
    // Callers should use finalizeStream() explicitly when ready to remove
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

    // Do NOT clear sibling streams - they may still be running
    finalizeStream(stream_id)

    return { stream, error_code, error_message }
  }

  function finalizeStream(streamId: string) {
    // Only finalize if stream exists
    if (!streams.value.has(streamId)) return
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

  function getStreamIdForTask(taskId: string): string | undefined {
    for (const [streamId, stream] of streams.value.entries()) {
      if (stream.metadata?.task_id === taskId) {
        return streamId
      }
    }
    return undefined
  }

  function getStreamForTask(taskId: string): InFlightStream | undefined {
    const streamId = getStreamIdForTask(taskId)
    return streamId ? streams.value.get(streamId) : undefined
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

  function restoreTaskStreams(sessionId: string, snapshot: RestoreTaskStreamSnapshot) {
    snapshot.tasks.forEach((task) => {
      const latestStream = task.latest_stream
      if (!latestStream?.stream_id) return

      // M6: Use actual agent role/name from task data instead of hardcoded 'PM'
      const senderRole = (task.agent_role as AgentRole) || 'PM'

      const stream = ensureStream(latestStream.stream_id, sessionId, {
        messageId: latestStream.message_id,
        senderRole: senderRole,
        timestamp: new Date().toISOString(),
        uiStatus: latestStream.status === 'completed' ? 'done' : 'thinking',
      })

      stream.metadata = {
        ...(stream.metadata || {}),
        ...(snapshot.run_id ? { run_id: snapshot.run_id } : {}),
        task_id: task.id,
        ...(task.assigned_agent_id ? { agent_id: task.assigned_agent_id } : {}),
        ...(task.agent_role ? { agent_role: task.agent_role } : {}),
        ...(task.agent_name ? { agent_name: task.agent_name } : {}),
      }

      if (latestStream.message_id) {
        stream.message_id = latestStream.message_id
      }
      if (latestStream.status === 'completed') {
        stream.ui_status = 'done'
      }

      replaceStream(latestStream.stream_id, stream)
    })
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

  // M6: Task status update callback - replaces window.dispatchEvent as primary sync
  let _onTaskStatusUpdate: ((taskId: string, runId: string | null, status: string) => void) | null = null

  function setOnTaskStatusUpdate(callback: (taskId: string, runId: string | null, status: string) => void) {
    _onTaskStatusUpdate = callback
  }

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

    // M4: Include task-aware fields from event
    const change: PendingChange = {
      change_id,
      operation,
      path,
      unified_diff,
      status,
      session_id: sessionId,
      stream_id,
      message_id,
      // M4: Task-aware fields
      run_id: event.run_id || null,
      task_id: event.task_id || null,
      agent_id: event.agent_id || null,
      batch_id: event.batch_id || null,
    }

    const newMap = new Map(pendingChanges.value)
    newMap.set(change_id, change)
    pendingChanges.value = newMap

    console.log('[StreamState] change_preview:', change_id, 'operation:', operation, 'path:', path)
    return change
  }

  // M6: Handle change_preview as an inline message with confirmation buttons
  // This replaces the panel-based approach where changes are shown in a separate section
  function handleChangePreviewAsMessage(event: ChangePreviewEvent, sessionId: string): InFlightStream | null {
    const { change_id, operation, path, unified_diff, status, stream_id, message_id, run_id, task_id, agent_id, agent_role, timestamp } = event

    if (!change_id || !stream_id) {
      console.warn('[StreamState] handleChangePreviewAsMessage: missing change_id or stream_id')
      return null
    }

    const taskStream = task_id ? getStreamForTask(task_id) : undefined
    const previewStreamId = streams.value.has(stream_id)
      ? stream_id
      : taskStream?.stream_id || `change_preview_${change_id}`
    const senderRole = (
      agent_role
      || taskStream?.sender_role
      || (taskStream?.metadata?.agent_role as AgentRole | undefined)
      || 'Agent'
    ) as AgentRole

    // Build the confirmation message content
    const operationText = operation === 'create' ? '创建' : operation === 'update' ? '更新' : '删除'
    const content = `我将${operationText}文件 \`${path}\`，内容如下：

\`\`\`
${formatDiffForDisplay(unified_diff)}
\`\`\`

请确认是否执行此操作：`

    // Also store in pendingChanges map for backend sync
    const change: PendingChange = {
      change_id,
      operation,
      path,
      unified_diff,
      status,
      session_id: sessionId,
      stream_id: previewStreamId,
      message_id: message_id || '',
      run_id: run_id || null,
      task_id: task_id || null,
      agent_id: agent_id || null,
      batch_id: event.batch_id || null,
    }
    const newMap = new Map(pendingChanges.value)
    newMap.set(change_id, change)
    pendingChanges.value = newMap

    // Create a stream for this change preview
    const stream = ensureStream(previewStreamId, sessionId, {
      messageId: message_id,
      senderRole,
      timestamp: timestamp || new Date().toISOString(),
      uiStatus: 'done',
      type: 'text',
    })

    // Update stream with change preview data
    stream.accumulated_content = content
    stream.content = content
    stream.payload.text = content
    stream.change_preview = {
      change_id,
      operation,
      path,
      unified_diff,
      status,
      run_id: run_id || null,
      task_id: task_id || null,
      agent_id: agent_id || null,
    }
    stream.change_status = 'pending'
    stream.metadata = {
      ...(stream.metadata || {}),
      ...(run_id ? { run_id } : {}),
      ...(task_id ? { task_id } : {}),
      ...(agent_id ? { agent_id } : {}),
      ...(agent_role ? { agent_role } : {}),
      is_change_preview: true,
    }

    replaceStream(previewStreamId, stream)
    console.log('[StreamState] handleChangePreviewAsMessage:', change_id, 'operation:', operation, 'path:', path)
    return stream
  }

  // M6: Format diff for display in message content
  function formatDiffForDisplay(diff: string): string {
    if (!diff) return ''
    // Extract content from diff format (remove +++ and --- lines)
    const lines = diff.split('\n')
    const contentLines: string[] = []
    for (const line of lines) {
      if (line.startsWith('+++') || line.startsWith('---') || line.startsWith('@@')) continue
      contentLines.push(line)
    }
    return contentLines.join('\n').trim()
  }

  // M6: Update change preview status (confirmed/rejected)
  function updateChangePreviewStatus(changeId: string, status: 'confirmed' | 'rejected') {
    // Find the stream associated with this change
    for (const [streamId, stream] of streams.value.entries()) {
      if (stream.change_preview?.change_id === changeId) {
        stream.change_status = status
        if (status === 'confirmed') {
          stream.accumulated_content = `${stream.accumulated_content}\n\n✅ 已确认写入`
        } else {
          stream.accumulated_content = `${stream.accumulated_content}\n\n❌ 已取消`
        }
        stream.content = stream.accumulated_content
        stream.payload.text = stream.accumulated_content
        replaceStream(streamId, stream)
        break
      }
    }

    // Also update pendingChanges map
    updatePendingChangeStatus(changeId, status === 'confirmed' ? 'applied' : 'rejected')
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
    const { change_id, success, status, task_id } = event

    if (!change_id) return

    console.log('[StreamState] apply_result:', change_id, 'success:', success, 'status:', status, 'task_id:', task_id)

    // Always update the status so the frontend can display the result
    // instead of removing the change (which causes the status to revert to default).
    updatePendingChangeStatus(change_id, status as PendingChange['status'])

    // M6: If this is a task-aware change, trigger task status update callback
    // Primary: call the registered callback (replaces window.dispatchEvent as main sync)
    // Secondary: still dispatch window event for non-store components as optional subscription
    if (task_id) {
      const change = pendingChanges.value.get(change_id)
      if (change?.task_id) {
        const newStatus = status === 'applied' ? 'completed' : status === 'rejected' ? 'rejected' : null
        if (newStatus) {
          // M6: Primary sync via callback
          if (_onTaskStatusUpdate) {
            _onTaskStatusUpdate(change.task_id, change.run_id ?? null, newStatus)
          }
          // Secondary: window event for optional subscription (non-store components)
          window.dispatchEvent(new CustomEvent('orchestration:task-status-update', {
            detail: {
              task_id: change.task_id,
              run_id: change.run_id,
              status: newStatus,
            }
          }))
        }
      }
    }
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

  // M6-EXT: 从 tool_event 拦截到的 HTML 幻灯片数据，转换为 PPT 预览模型
  function handlePptDataFromTool(event: PptDataFromToolEvent, sessionId: string) {
    const { ppt_data, agent_role, stream_id, message_id, timestamp } = event
    if (!ppt_data || !ppt_data.length) return

    console.log('[StreamState] ppt_data from tool:', stream_id, 'slides:', ppt_data.length)

    const normalizedPptData = ppt_data.map((page) => ({
      pageTitle: page.pageTitle || '',
      pageContent: Array.isArray(page.pageContent) ? page.pageContent : [String(page.pageContent || '')],
      imgTag: page.imgTag || '',
    }))

    // 构造 PPT 预览模型，写入 previewPpt，触发右侧预览区打开
    const model: PptPreviewModel = {
      title: '演示文稿',
      agentRole: agent_role || 'PM',
      createdAt: timestamp || new Date().toISOString(),
      slides: normalizedPptData.map((page, idx) => ({
        id: `tool-slide-${idx}`,
        title: page.pageTitle || `第 ${idx + 1} 页`,
        bullets: page.pageContent,
        imgTag: page.imgTag || '',
        imageUrl: resolvePptImage(page.imgTag || '', idx),
      })),
    }
    // previewPpt.value = model

    const pptPayload = {
      agent_role: agent_role || 'PM',
      timestamp: timestamp || new Date().toISOString(),
      stream_id: stream_id || '',
      message_id: message_id || stream_id || '',
      ppt_data: normalizedPptData,
    }

    // 同步更新 stream：让聊天区按真正的 ppt_data 消息渲染 PPT 卡片
    const stream = streams.value.get(stream_id || '')
    if (stream) {
      const updated = { ...stream }
      updated.type = 'ppt_data'
      updated.content = JSON.stringify(pptPayload)
      updated.accumulated_content = JSON.stringify(pptPayload)
      updated.payload = pptPayload
      updated.metadata = {
        ...(updated.metadata || {}),
        ppt_data: normalizedPptData,
        agent_role: agent_role || 'PM',
      }
      updated.ui_status = 'done'
      replaceStream(stream_id || '', updated)
    } else if (stream_id) {
      // 若无对应 stream，创建一个临时流条目用于展示 PPT 卡片
      const newStream: InFlightStream = {
        stream_id,
        message_id: message_id || stream_id,
        session_id: sessionId,
        sender_role: (agent_role as AgentRole) || 'PM',
        content: JSON.stringify(pptPayload),
        accumulated_content: JSON.stringify(pptPayload),
        type: 'ppt_data',
        payload: pptPayload,
        metadata: {
          ppt_data: normalizedPptData,
          agent_role: agent_role || 'PM',
        },
        ui_status: 'done',
        created_at: timestamp || new Date().toISOString(),
        runtime_nodes: [],
      }
      replaceStream(stream_id, newStream)
    }
  }

  function restorePendingChanges(
    items: Array<{
      change_id: string
      session_id: string
      message_id?: string
      stream_id?: string
      // M4: Task-aware fields
      run_id?: string | null
      task_id?: string | null
      agent_id?: string | null
      batch_id?: string | null
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
      const change: PendingChange = {
        change_id: item.change_id,
        session_id: item.session_id || sessionId,
        message_id: item.message_id || '',
        stream_id: item.stream_id || '',
        // M4: Task-aware fields
        run_id: item.run_id || null,
        task_id: item.task_id || null,
        agent_id: item.agent_id || null,
        batch_id: item.batch_id || null,
        operation: item.operation,
        path: item.path,
        unified_diff: item.unified_diff || '',
        status: item.status,
        original_content: item.original_content,
        proposed_content: item.proposed_content,
        created_at: item.created_at || null,
        applied_at: item.applied_at || null,
      }

      const newMap = new Map(pendingChanges.value)
      newMap.set(item.change_id, change)
      pendingChanges.value = newMap

      console.log('[StreamState] Restored pending change:', item.change_id, item.path, item.status, 'task_id:', item.task_id)
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

  // M6: Preview diff state for side panel
  const previewDiff = ref<PendingChange | null>(null)

  // M6: Set preview diff to show in side panel
  function setPreviewDiff(change: PendingChange | null) {
    previewDiff.value = change
  }

  // M6: Clear preview diff
  function clearPreviewDiff() {
    previewDiff.value = null
  }

  // PPT 预览状态：存储当前要预览的 PPT 模型
  const previewPpt = ref<PptPreviewModel | null>(null)

  /** 设置 PPT 预览模型，打开右侧预览区 */
  function setPreviewPpt(ppt: PptPreviewModel | null) {
    previewPpt.value = ppt
  }

  /** 清空 PPT 预览状态，关闭右侧预览区 */
  function clearPreviewPpt() {
    previewPpt.value = null
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
    getStreamIdForTask,
    getSessionIdForStream,
    ensureStream,
    handleToolEvent,
    handleRuntimeState,
    pendingChanges,
    sessionPendingChanges,
    setCurrentSessionId,
    handleChangePreview,
    handleChangePreviewAsMessage, // M6: new method for inline change preview
    updateChangePreviewStatus,    // M6: update change preview confirmation status
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
    restoreTaskStreams,
    clearInFlightStreams,
    clearOtherSessionStreams,
    // M6: Task status update callback for store integration
    setOnTaskStatusUpdate,
    // M6: Preview diff state
    previewDiff,
    setPreviewDiff,
    clearPreviewDiff,
    // PPT 预览状态
    previewPpt,
    setPreviewPpt,
    clearPreviewPpt,
    handlePptDataFromTool,
  }
}
