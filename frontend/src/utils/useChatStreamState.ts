import { ref, computed } from 'vue'
import type { StreamingMessage } from '@/types/agenthub'
import type { ChatStreamMessage, AgentTypingMessage, ErrorMessage, AgentRole } from '@shared/index'

interface InFlightStream {
  stream_id: string
  message_id?: string
  session_id: string
  sender_role: AgentRole
  accumulated_content: string
  ui_status: 'thinking' | 'streaming' | 'done' | 'syncing_interrupted'
  created_at: string
  full_content?: string
}

export function useChatStreamState() {
  const inFlightStreams = ref<Map<string, InFlightStream>>(new Map())

  const getStreamingMessages = computed(() => {
    return (sessionId: string): StreamingMessage[] => {
      const messages: StreamingMessage[] = []
      
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
      
      return messages
    }
  })

  function handleAgentTyping(msg: AgentTypingMessage, sessionId: string) {
    const { stream_id, is_typing, agent_role, timestamp } = msg

    if (is_typing) {
      if (!inFlightStreams.value.has(stream_id)) {
        inFlightStreams.value.set(stream_id, {
          stream_id,
          session_id: sessionId,
          sender_role: agent_role,
          accumulated_content: '',
          ui_status: 'thinking',
          created_at: timestamp,
        })
      }
    } else {
      const stream = inFlightStreams.value.get(stream_id)
      if (stream && stream.ui_status === 'thinking' && !stream.message_id) {
        inFlightStreams.value.delete(stream_id)
      }
    }
  }

  function handleChatStream(msg: any, sessionId: string) {
    const stream_id = msg.stream_id || msg.message_id || `stream_${Date.now()}`
    const message_id = msg.message_id
    const agent_role = msg.sender_role || 'PM'
    const timestamp = msg.created_at || new Date().toISOString()
    
    const content_chunk = msg.content_chunk
    const content = msg.content
    const is_final = msg.is_final

    let stream = inFlightStreams.value.get(stream_id)

    if (!stream) {
      stream = {
        stream_id,
        message_id,
        session_id: sessionId,
        sender_role: agent_role,
        accumulated_content: '',
        ui_status: 'streaming',
        created_at: timestamp,
      }
      inFlightStreams.value.set(stream_id, stream)
    }

    if (!stream.message_id && message_id) {
      stream.message_id = message_id
      stream.ui_status = 'streaming'
    }

    if (content) {
      stream.full_content = content
      simulateStreamingChunks(stream_id, content)
      return { shouldFinalize: false, stream }
    }

    if (content_chunk) {
      stream.accumulated_content += content_chunk
    }

    if (is_final) {
      stream.ui_status = 'done'
      return { shouldFinalize: true, stream }
    }

    return { shouldFinalize: false, stream }
  }

  function simulateStreamingChunks(streamId: string, fullContent: string) {
    const stream = inFlightStreams.value.get(streamId)
    if (!stream) return

    const segments = parseContentSegments(fullContent)
    let segmentIndex = 0
    let charIndex = 0

    const intervalId = setInterval(() => {
      if (segmentIndex >= segments.length) {
        clearInterval(intervalId)
        stream.ui_status = 'done'
        return
      }

      const segment = segments[segmentIndex]
      
      if (segment.type === 'code') {
        stream.accumulated_content += segment.content
        segmentIndex++
        charIndex = 0
      } else {
        const chunkSize = 3
        const remaining = segment.content.length - charIndex
        
        if (remaining <= 0) {
          segmentIndex++
          charIndex = 0
          return
        }

        const chunk = segment.content.slice(charIndex, charIndex + chunkSize)
        stream.accumulated_content += chunk
        charIndex += chunkSize
      }
    }, 30)
  }

  function parseContentSegments(content: string): Array<{ type: 'text' | 'code', content: string }> {
    const segments: Array<{ type: 'text' | 'code', content: string }> = []
    const codeBlockRegex = /```[\s\S]*?```/g
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = codeBlockRegex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        segments.push({
          type: 'text',
          content: content.slice(lastIndex, match.index)
        })
      }
      
      segments.push({
        type: 'code',
        content: match[0]
      })
      
      lastIndex = match.index + match[0].length
    }

    if (lastIndex < content.length) {
      segments.push({
        type: 'text',
        content: content.slice(lastIndex)
      })
    }

    return segments.length > 0 ? segments : [{ type: 'text', content }]
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

  function handleError(msg: ErrorMessage, sessionId: string, onRefetch: () => Promise<void>) {
    const { stream_id } = msg
    const stream = inFlightStreams.value.get(stream_id)

    if (!stream) return

    if (stream.ui_status === 'thinking' && !stream.message_id) {
      inFlightStreams.value.delete(stream_id)
      return
    }

    if (stream.message_id) {
      stream.ui_status = 'syncing_interrupted'
      onRefetch().then(() => {
        inFlightStreams.value.delete(stream_id)
      })
    }
  }

  function finalizeStream(streamId: string) {
    inFlightStreams.value.delete(streamId)
  }

  function clearSession(sessionId: string) {
    const toDelete: string[] = []
    inFlightStreams.value.forEach((stream, streamId) => {
      if (stream.session_id === sessionId) {
        toDelete.push(streamId)
      }
    })
    toDelete.forEach((id) => inFlightStreams.value.delete(id))
  }

  function hasInFlightStream(sessionId: string): boolean {
    for (const stream of inFlightStreams.value.values()) {
      if (stream.session_id === sessionId) {
        return true
      }
    }
    return false
  }

  return {
    getStreamingMessages,
    handleAgentTyping,
    handleChatStream,
    handleError,
    finalizeStream,
    clearSession,
    hasInFlightStream,
    checkStreamComplete,
  }
}
