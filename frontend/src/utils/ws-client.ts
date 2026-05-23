import { WS_BASE_URL } from '@/api/client'
import type { ChatMessage } from '@/types/agenthub'

export type ConnectionState =
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'reconnecting'
  | 'failed'

export type WsIncomingMessage = {
  type: string
  message_id?: string
  session_id?: string
  sender_type?: string
  sender_role?: string | null
  content?: string
  content_type?: string
  created_at?: string
  error_code?: string
  error_message?: string
}

type StateChangeHandler = (state: ConnectionState) => void
type MessageHandler = (msg: WsIncomingMessage) => void

class WsClient {
  private ws: WebSocket | null = null
  private sessionId = ''
  private state: ConnectionState = 'disconnected'
  private reconnectAttempt = 0
  private readonly MAX_RECONNECT = 5
  private readonly BACKOFF = [1000, 2000, 4000, 8000, 16000]
  private readonly PING_INTERVAL = 30_000

  private pingTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private pongTimer: ReturnType<typeof setTimeout> | null = null

  private stateListeners = new Set<StateChangeHandler>()
  private messageListeners = new Set<MessageHandler>()

  connect(sessionId: string): void {
    if (this.ws) {
      this.disconnect()
    }

    this.sessionId = sessionId
    this.setState('connecting')

    const token = localStorage.getItem('x-token')
    const url = `${WS_BASE_URL}/${sessionId}${token ? `?x-token=${token}` : ''}`
    console.log(`[WsClient] Connecting to ${url}`)

    try {
      this.ws = new WebSocket(url)
      this.ws.onopen = this.onOpen.bind(this)
      this.ws.onmessage = this.onMessage.bind(this)
      this.ws.onclose = this.onClose.bind(this)
      this.ws.onerror = this.onError.bind(this)
    } catch (err) {
      console.error('[WsClient] Connection error:', err)
      this.handleFailure()
    }
  }

  disconnect(): void {
    this.clearTimers()
    if (this.ws) {
      this.ws.onclose = null
      this.ws.close(1000, 'manual')
      this.ws = null
    }
    this.reconnectAttempt = 0
    this.setState('disconnected')
  }

  sendMessage(content: string): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WsClient] Cannot send — not connected')
      return false
    }

    const payload = {
      action: 'send_message',
      session_id: this.sessionId,
      content,
    }

    try {
      this.ws.send(JSON.stringify(payload))
      console.log('[WsClient] Sent:', payload)
      return true
    } catch (err) {
      console.error('[WsClient] Send error:', err)
      return false
    }
  }

  manualRetry(): void {
    if (this.state === 'failed') {
      this.reconnectAttempt = 0
      if (this.sessionId) {
        this.connect(this.sessionId)
      }
    }
  }

  onStateChange(cb: StateChangeHandler): () => void {
    this.stateListeners.add(cb)
    cb(this.state)
    return () => this.stateListeners.delete(cb)
  }

  onReceiveMessage(cb: MessageHandler): () => void {
    this.messageListeners.add(cb)
    return () => this.messageListeners.delete(cb)
  }

  getState(): ConnectionState {
    return this.state
  }

  getReconnectAttempt(): number {
    return this.reconnectAttempt
  }

  private setState(s: ConnectionState): void {
    this.state = s
    this.stateListeners.forEach((cb) => cb(s))
  }

  private onOpen(): void {
    console.log('[WsClient] Connected')
    this.reconnectAttempt = 0
    this.setState('connected')
    this.startPing()
  }

  private onMessage(event: MessageEvent<string>): void {
    let msg: WsIncomingMessage
    try {
      msg = JSON.parse(event.data) as WsIncomingMessage
    } catch {
      console.warn('[WsClient] Failed to parse message:', event.data)
      return
    }

    if (msg.type === 'pong') {
      console.log('[WsClient] Pong received')
      this.stopPongTimer()
      return
    }

    if (msg.type === 'error') {
      console.error('[WsClient] Server error:', msg.error_code, msg.error_message)
      return
    }

    console.log('[WsClient] Message:', msg)
    this.messageListeners.forEach((cb) => cb(msg))
  }

  private onClose(event: CloseEvent): void {
    console.log(`[WsClient] Closed (code=${event.code}, reason=${event.reason})`)
    this.clearTimers()

    if (event.code === 1000) {
      this.setState('disconnected')
      return
    }

    this.handleReconnect()
  }

  private onError(event: Event): void {
    console.error('[WsClient] Error:', event)
    this.clearTimers()
    this.handleReconnect()
  }

  private handleReconnect(): void {
    if (this.reconnectAttempt >= this.MAX_RECONNECT) {
      console.error('[WsClient] Max reconnect attempts reached')
      this.setState('failed')
      return
    }

    this.setState('reconnecting')
    const delay = this.BACKOFF[this.reconnectAttempt] ?? this.BACKOFF[this.BACKOFF.length - 1]!
    console.log(
      `[WsClient] Reconnecting in ${delay}ms (${this.reconnectAttempt + 1}/${this.MAX_RECONNECT})`,
    )

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempt++
      if (this.sessionId) {
        this.connect(this.sessionId)
      }
    }, delay)
  }

  private handleFailure(): void {
    this.setState('failed')
  }

  private startPing(): void {
    this.stopPongTimer()
    this.pingTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
        console.log('[WsClient] Ping sent')
        this.startPongTimer()
      }
    }, this.PING_INTERVAL)
  }

  private startPongTimer(): void {
    this.stopPongTimer()
    this.pongTimer = setTimeout(() => {
      console.error('[WsClient] Pong timeout — forcing reconnect')
      if (this.ws) {
        this.ws.close(4000, 'pong_timeout')
      }
    }, 10_000)
  }

  private stopPongTimer(): void {
    if (this.pongTimer) {
      clearTimeout(this.pongTimer)
      this.pongTimer = null
    }
  }

  private clearTimers(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer)
      this.pingTimer = null
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.stopPongTimer()
  }
}

export const wsClient = new WsClient()
export const getWsClientState = () => wsClient.getState()
export const getWsClientReconnectAttempt = () => wsClient.getReconnectAttempt()
