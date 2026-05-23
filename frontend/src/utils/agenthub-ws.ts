import { WS_BASE_URL } from '@/api/client'
import type { SendMessagePayload, WsIncomingMessage } from '@/types/agenthub'

class AgentHubWsClient {
  private socket: WebSocket | null = null
  private sessionId = ''
  private heartbeatTimer: number | null = null
  private onMessageCallback: ((payload: WsIncomingMessage) => void) | null = null
  private onStateChangeCallback: ((state: 'connected' | 'connecting' | 'disconnected') => void) | null = null

  connect(sessionId: string) {
    if (!sessionId) return
    if (this.socket && this.sessionId === sessionId && this.socket.readyState <= 1) return

    this.disconnect()
    this.sessionId = sessionId
    this.onStateChangeCallback?.('connecting')
    this.socket = new WebSocket(`${WS_BASE_URL}/ws/${sessionId}`)

    this.socket.onopen = () => {
      this.onStateChangeCallback?.('connected')
      this.startHeartbeat()
    }

    this.socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as WsIncomingMessage
        if (payload.type === 'pong') return
        this.onMessageCallback?.(payload)
      } catch {
        this.onMessageCallback?.({ type: 'raw', data: event.data })
      }
    }

    this.socket.onclose = () => {
      this.stopHeartbeat()
      this.onStateChangeCallback?.('disconnected')
    }

    this.socket.onerror = () => {
      this.stopHeartbeat()
      this.onStateChangeCallback?.('disconnected')
    }
  }

  onMessage(callback: (payload: WsIncomingMessage) => void) {
    this.onMessageCallback = callback
  }

  onStateChange(callback: (state: 'connected' | 'connecting' | 'disconnected') => void) {
    this.onStateChangeCallback = callback
  }

  sendMessage(content: string) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return false
    const payload: SendMessagePayload = {
      action: 'send_message',
      session_id: this.sessionId,
      content,
    }
    this.socket.send(JSON.stringify(payload))
    return true
  }

  disconnect() {
    this.stopHeartbeat()
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = window.setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: 'ping' }))
      }
    }, 15000)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      window.clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }
}

export const agenthubWsClient = new AgentHubWsClient()

