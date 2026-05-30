import { ref } from 'vue'
import type { StreamingMessage } from '@/types/agenthub'
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
          metadata: stream.metadata || {},
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
      ui_status: 'thinking',
      created_at: timestamp || message.created_at || new Date().toISOString(),
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

    // Buffer threshold: stay in 'thinking' until we have enough content,
    // then switch to 'streaming' so the UI starts rendering tokens.
    // This prevents short truncated prefixes (like "我我" / "李白") from being shown.
    if (stream.ui_status === 'thinking' && stream.accumulated_content.length >= 10) {
      stream.ui_status = 'streaming'
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
  }
}
