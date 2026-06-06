import { WS_BASE_URL } from '@/api/client'
import type { ComposerMention, SendMessagePayload } from '@/types/agenthub'

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
  stream_id?: string
  agent_role?: string
  timestamp?: string
  message?: {
    id: string
    session_id: string
    sender_type: string
    sender_role: string | null
    type: string
    content: string
    payload: Record<string, unknown>
    metadata: Record<string, unknown>
    status: string
    created_at: string
  }
  delta?: string
  status?: string
  error_code?: string
  error_message?: string
  final_content?: string
  content?: string
  content_type?: string
  created_at?: string
  tool_name?: string
  arguments?: Record<string, unknown>
  response?: string | null
  state?: string
  _runtime_nodes?: unknown[]
  change_id?: string
  operation?: 'create' | 'update' | 'delete'
  path?: string
  unified_diff?: string
  success?: boolean
  preview_id?: string
  preview_url?: string
  workspace_id?: string
  attempt?: number
  max_attempts?: number
  run_id?: string | null
  task_id?: string | null
  agent_id?: string | null
  batch_id?: string | null
}

type StateChangeHandler = (state: ConnectionState) => void
type MessageHandler = (msg: WsIncomingMessage, sessionId: string) => void

class WsClient {
  private ws: WebSocket | null = null
  private _sessionId = ''
  private _state: ConnectionState = 'disconnected'
  private reconnectAttempt = 0
  private readonly MAX_RECONNECT = 5
  private readonly BACKOFF = [1000, 2000, 4000, 8000, 16000]
  private readonly PING_INTERVAL = 30_000

  private pingTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private pongTimer: ReturnType<typeof setTimeout> | null = null
  private awaitingResponse = false

  private stateListeners = new Set<StateChangeHandler>()
  private messageListeners = new Set<MessageHandler>()

  get sessionId(): string {
    return this._sessionId
  }

  get state(): ConnectionState {
    return this._state
  }

  getReconnectAttempt(): number {
    return this.reconnectAttempt
  }

  connect(sessionId: string): void {
    if (this.ws) {
      this.disconnect()
    }

    this._sessionId = sessionId
    this.setState('connecting')

    const token = localStorage.getItem('x-token')
    const url = `${WS_BASE_URL}/${sessionId}${token ? `?x-token=${encodeURIComponent(token)}` : ''}`
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
    this.awaitingResponse = false
    this.reconnectAttempt = 0
    this.setState('disconnected')
  }

  sendMessage(payload: {
    content: string
    targetAgentIds?: string[]
    mentions?: ComposerMention[]
  }): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WsClient] Cannot send — not connected')
      return false
    }

    const out: SendMessagePayload = {
      action: 'send_message',
      session_id: this.sessionId,
      content: payload.content,
    }

    if (payload.targetAgentIds && payload.targetAgentIds.length > 0) {
      out.target_agent_ids = payload.targetAgentIds
    }
    if (payload.mentions && payload.mentions.length > 0) {
      out.mentions = payload.mentions
    }

    try {
      this.ws.send(JSON.stringify(out))
      this.awaitingResponse = true
      console.log('[WsClient] Sent:', out)
      return true
    } catch (err) {
      console.error('[WsClient] Send error:', err)
      return false
    }
  }

  manualRetry(): void {
    if (this._state === 'failed') {
      this.reconnectAttempt = 0
      if (this._sessionId) {
        this.connect(this._sessionId)
      }
    }
  }

  onStateChange(cb: StateChangeHandler): () => void {
    this.stateListeners.add(cb)
    cb(this._state)
    return () => this.stateListeners.delete(cb)
  }

  onReceiveMessage(cb: MessageHandler): () => void {
    this.messageListeners.add(cb)
    return () => this.messageListeners.delete(cb)
  }

  private setState(s: ConnectionState): void {
    this._state = s
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

    if (msg.type === 'message_end' || msg.type === 'message_error' || msg.type === 'error') {
      this.awaitingResponse = false
    }

    console.log('[WsClient] Message:', msg)
    this.messageListeners.forEach((cb) => cb(msg, this._sessionId))
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
      if (this._sessionId) {
        this.connect(this._sessionId)
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
        if (!this.awaitingResponse) {
          this.startPongTimer()
        }
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

class MultiWsManager {
  private clients = new Map<string, WsClient>()
  private _activeSessionId: string | null = null
  private globalMessageListeners = new Set<(msg: WsIncomingMessage, sessionId: string) => void>()

  getClient(sessionId: string): WsClient | undefined {
    return this.clients.get(sessionId)
  }

  connect(sessionId: string): void {
    let client = this.clients.get(sessionId)
    if (!client) {
      client = new WsClient()
      client.onReceiveMessage((msg, sid) => {
        this.globalMessageListeners.forEach((cb) => cb(msg, sid))
      })
      this.clients.set(sessionId, client)
    }
    this._activeSessionId = sessionId
    client.connect(sessionId)
  }

  disconnect(sessionId?: string): void {
    if (sessionId) {
      const client = this.clients.get(sessionId)
      if (client) {
        client.disconnect()
        this.clients.delete(sessionId)
      }
      if (this._activeSessionId === sessionId) {
        this._activeSessionId = null
      }
    } else {
      this.clients.forEach((client) => client.disconnect())
      this.clients.clear()
      this._activeSessionId = null
    }
  }

  send(
    sessionId: string,
    payload: { content: string; targetAgentIds?: string[]; mentions?: ComposerMention[] },
  ): boolean {
    const client = this.clients.get(sessionId)
    if (!client) {
      console.warn('[MultiWsManager] Not connected to session:', sessionId)
      return false
    }
    return client.sendMessage(payload)
  }

  getState(sessionId: string): ConnectionState {
    return this.clients.get(sessionId)?.state ?? 'disconnected'
  }

  getStatus(sessionId: string): { isConnect: boolean; readyState: ConnectionState; reconnectCount: number } {
    const client = this.clients.get(sessionId)
    return {
      isConnect: client?.state === 'connected',
      readyState: client?.state ?? 'disconnected',
      reconnectCount: client?.getReconnectAttempt() ?? 0,
    }
  }

  get activeState(): ConnectionState {
    if (!this._activeSessionId) return 'disconnected'
    return this.clients.get(this._activeSessionId)?.state ?? 'disconnected'
  }

  get activeSessionId(): string | null {
    return this._activeSessionId
  }

  setActive(sessionId: string): void {
    this._activeSessionId = sessionId
  }

  manualRetry(sessionId: string): void {
    this.clients.get(sessionId)?.manualRetry()
  }

  onReceiveMessage(cb: (msg: WsIncomingMessage, sessionId: string) => void): () => void {
    this.globalMessageListeners.add(cb)
    return () => this.globalMessageListeners.delete(cb)
  }

  onStateChange(sessionId: string, cb: (state: ConnectionState) => void): () => void {
    const client = this.clients.get(sessionId)
    if (!client) {
      cb('disconnected')
      return () => {}
    }
    return client.onStateChange(cb)
  }

  getConnectedSessionIds(): string[] {
    return Array.from(this.clients.keys())
  }
}

const _manager = new MultiWsManager()

export const ws = {
  connect: (sessionId: string) => _manager.connect(sessionId),
  disconnect: (sessionId?: string) => _manager.disconnect(sessionId),
  send: (sessionId: string, payload: { content: string; targetAgentIds?: string[]; mentions?: ComposerMention[] }) =>
    _manager.send(sessionId, payload),
  getState: (sessionId: string) => _manager.getState(sessionId),
  getStatus: (sessionId: string) => _manager.getStatus(sessionId),
  onStateChange: (sessionId: string, cb: (state: ConnectionState) => void) =>
    _manager.onStateChange(sessionId, cb),
  onReceiveMessage: (cb: (msg: WsIncomingMessage, sessionId: string) => void) => _manager.onReceiveMessage(cb),
  manualRetry: (sessionId: string) => _manager.manualRetry(sessionId),
  getActiveSessionId: () => _manager.activeSessionId,
  setActive: (sessionId: string) => _manager.setActive(sessionId),
  getConnectedSessions: () => _manager.getConnectedSessionIds(),
}

export const getWsClientReconnectAttempt = (): number => {
  const activeSessionId = _manager.activeSessionId
  if (!activeSessionId) return 0
  return _manager.getClient(activeSessionId)?.getReconnectAttempt() ?? 0
}
