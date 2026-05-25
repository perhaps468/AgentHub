import { ref } from 'vue'
import type { StreamingMessage } from '@/types/agenthub'
import type { AgentRole } from '@shared/index'
import { useSessionStore } from '@/store/module/useSessionStore'

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
  full_content?: string
}

export function useChatStreamState() {
  const inFlightStreams = ref<Map<string, InFlightStream>>(new Map())

  function getInFlightMessagesMap(): Map<string, InFlightStream> | null {
    try {
      const store = useSessionStore()
      if ((store as any).inFlightMessages instanceof Map) {
        return (store as any).inFlightMessages as Map<string, InFlightStream>
      }
    } catch {
      // Store not available (e.g., in tests)
    }
    return null
  }

  function getStreamingMessages(sessionId: string): StreamingMessage[] {
    const messages: StreamingMessage[] = []

    const storeMap = getInFlightMessagesMap()
    if (storeMap) {
      storeMap.forEach((stream) => {
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
          })
        }
      })
    } else {
      inFlightStreams.value.forEach((stream) => {
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
          })
        }
      })
    }

    return messages
  }

  function handleMessageStart(event: any, sessionId: string) {
    const { stream_id, message, agent_role, timestamp } = event

    if (!stream_id || !message) return

    const storeMap = getInFlightMessagesMap()

    if (storeMap && storeMap.has(stream_id)) return
    if (!storeMap && inFlightStreams.value.has(stream_id)) return

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
    }

    if (storeMap) {
      storeMap.set(stream_id, stream)
    }
    inFlightStreams.value.set(stream_id, stream)

    return stream
  }

  function handleMessageDelta(event: any, sessionId: string) {
    const { stream_id, delta, message_id } = event

    if (!stream_id) return

    const storeMap = getInFlightMessagesMap()
    let stream = storeMap?.get(stream_id) || inFlightStreams.value.get(stream_id)
    if (!stream) return

    stream.accumulated_content += delta
    stream.content = stream.accumulated_content
    stream.payload.text = stream.accumulated_content

    if (message_id && !stream.message_id) {
      stream.message_id = message_id
    }

    if (storeMap) {
      storeMap.set(stream_id, { ...stream })
    }
    inFlightStreams.value.set(stream_id, stream)

    return stream
  }

  function handleMessageEnd(event: any, sessionId: string) {
    const { stream_id, status } = event

    if (!stream_id) return

    const storeMap = getInFlightMessagesMap()
    const stream = storeMap?.get(stream_id) || inFlightStreams.value.get(stream_id)

    if (stream) {
      stream.ui_status = status === 'completed' ? 'done' : 'syncing_interrupted'
      if (storeMap) {
        storeMap.set(stream_id, { ...stream })
      }
      inFlightStreams.value.set(stream_id, stream)
    }

    if (storeMap) {
      storeMap.delete(stream_id)
    }
    inFlightStreams.value.delete(stream_id)

    try {
      const store = useSessionStore()
      if (stream?.message_id) {
        store.mergeOrUpdateMessage(sessionId, {
          id: stream.message_id,
          session_id: sessionId,
          sender_type: 'agent',
          sender_role: stream.sender_role ?? null,
          content: stream.accumulated_content,
          type: stream.type ?? 'text',
          payload: stream.payload ?? { text: stream.accumulated_content },
          metadata: stream.metadata ?? {},
          status: status === 'completed' ? 'completed' : 'failed',
          created_at: stream.created_at ?? new Date().toISOString(),
        })
      }
      // fetchMessages 依赖 inFlightMessages 做 upsert 去重，
      // 所以先把 message_id 加入 store.inFlightMessages，等 fetchMessages 完成后再删除
      const pendingMessageId = stream?.message_id
      if (pendingMessageId) {
        store.inFlightMessages.set(pendingMessageId, {
          stream_id: stream_id,
          message_id: pendingMessageId,
          session_id: sessionId,
          sender_role: stream!.sender_role ?? null,
          content: stream!.accumulated_content,
          accumulated_content: stream!.accumulated_content,
          type: stream!.type ?? 'text',
          payload: stream!.payload ?? { text: stream!.accumulated_content },
          metadata: stream!.metadata ?? {},
          ui_status: status === 'completed' ? 'done' : 'syncing_interrupted',
          created_at: stream!.created_at ?? new Date().toISOString(),
        })
      }
      store.fetchMessages(sessionId, { page: 1 }).finally(() => {
        if (pendingMessageId) {
          store.inFlightMessages.delete(pendingMessageId)
        }
      })
    } catch {
      // Store not available
    }

    return stream
  }

  function handleMessageError(event: any, sessionId: string) {
    const { stream_id, error_code, error_message } = event

    if (!stream_id) return

    const storeMap = getInFlightMessagesMap()
    const stream = storeMap?.get(stream_id) || inFlightStreams.value.get(stream_id)

    if (stream) {
      stream.ui_status = 'syncing_interrupted'
      if (storeMap) {
        storeMap.set(stream_id, { ...stream })
      }
      inFlightStreams.value.set(stream_id, stream)
    }

    const hasInFlight = !!(storeMap?.has(stream_id) || inFlightStreams.value.has(stream_id))

    if (hasInFlight) {
      if (storeMap) {
        storeMap.delete(stream_id)
      }
      inFlightStreams.value.delete(stream_id)

      try {
        const store = useSessionStore()
        if (stream?.message_id) {
          store.mergeOrUpdateMessage(sessionId, {
            id: stream.message_id,
            session_id: sessionId,
            sender_type: 'agent',
            sender_role: stream.sender_role ?? null,
            content: stream.accumulated_content,
            type: stream.type ?? 'text',
            payload: stream.payload ?? { text: stream.accumulated_content },
            metadata: stream.metadata ?? {},
            status: 'failed',
            created_at: stream.created_at ?? new Date().toISOString(),
          })
        }
        const pendingMessageId = stream?.message_id
        if (pendingMessageId) {
          store.inFlightMessages.set(pendingMessageId, {
            stream_id: stream_id,
            message_id: pendingMessageId,
            session_id: sessionId,
            sender_role: stream!.sender_role ?? null,
            content: stream!.accumulated_content,
            accumulated_content: stream!.accumulated_content,
            type: stream!.type ?? 'text',
            payload: stream!.payload ?? { text: stream!.accumulated_content },
            metadata: stream!.metadata ?? {},
            ui_status: 'syncing_interrupted',
            created_at: stream!.created_at ?? new Date().toISOString(),
          })
        }
        store.fetchMessages(sessionId, { page: 1 }).finally(() => {
          if (pendingMessageId) {
            store.inFlightMessages.delete(pendingMessageId)
          }
        })
      } catch {
        // Store not available
      }
    }

    return { stream, hasInFlight, error_code, error_message }
  }

  function finalizeStream(streamId: string) {
    const storeMap = getInFlightMessagesMap()
    if (storeMap) {
      storeMap.delete(streamId)
    }
    inFlightStreams.value.delete(streamId)
  }

  function clearSession(sessionId: string) {
    const storeMap = getInFlightMessagesMap()

    const toDelete: string[] = []
    inFlightStreams.value.forEach((stream, streamId) => {
      if (stream.session_id === sessionId) {
        toDelete.push(streamId)
      }
    })

    toDelete.forEach((id) => {
      if (storeMap) {
        storeMap.delete(id)
      }
      inFlightStreams.value.delete(id)
    })
  }

  function hasInFlightStream(sessionId: string): boolean {
    const storeMap = getInFlightMessagesMap()
    if (storeMap) {
      for (const stream of storeMap.values()) {
        if (stream.session_id === sessionId) {
          return true
        }
      }
    }
    for (const stream of inFlightStreams.value.values()) {
      if (stream.session_id === sessionId) {
        return true
      }
    }
    return false
  }

  function checkStreamComplete(streamId: string): { isComplete: boolean; stream?: InFlightStream } {
    const stream = inFlightStreams.value.get(streamId)
    if (!stream || !stream.full_content) {
      return { isComplete: false }
    }

    if (stream.accumulated_content.length >= stream.full_content.length) {
      return { isComplete: true, stream }
    }

    return { isComplete: false }
  }

  return {
    getStreamingMessages,
    handleMessageStart,
    handleMessageDelta,
    handleMessageEnd,
    handleMessageError,
    finalizeStream,
    clearSession,
    hasInFlightStream,
    checkStreamComplete,
  }
}
