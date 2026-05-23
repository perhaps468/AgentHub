import EventBus from '../utils/EventBus'

type WsPayload = {
  type?: string
  content?: {
    content?: string
    [key: string]: unknown
  } | Record<string, unknown> | unknown
  data?: {
    code?: number
    [key: string]: unknown
  }
  [key: string]: unknown
}

type ReadyStateText = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED'

type WebSocketStatus = {
  isConnect: boolean
  readyState: ReadyStateText
  reconnectCount: number
}

class WebSocketService {
  private ws: WebSocket | null = null
  private heartTimer: ReturnType<typeof setInterval> | null = null
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private lockReconnect = false
  private token: string | null = null
  private reconnectCountMax = 10
  private reconnectCount = 0
  private isConnect = false
  private manualClose = false

  connect() {
    if (this.isConnect || this.ws) {
      console.log('WebSocket 已连接或正在连接中')
      return
    }

    this.token = localStorage.getItem('x-token')
    if (!this.token) {
      console.error('❌ 未找到有效的 token，请检查 localStorage 中的 x-token')
      return
    }

    this.manualClose = false

    try {
      let wsUrl = import.meta.env.VITE_WS_URL as string | undefined

      if (!wsUrl) {
        console.error('❌ WebSocket URL 未配置，请检查环境变量 VITE_WS_URL')
        wsUrl = 'ws://127.0.0.1:9800'
        console.warn('使用默认 WebSocket URL:', wsUrl)
      }

      if (!wsUrl.startsWith('ws://') && !wsUrl.startsWith('wss://')) {
        console.warn('WebSocket URL 缺少协议，自动添加 ws://')
        wsUrl = 'ws://' + wsUrl
      }

      if (wsUrl.includes('117.0.0.1')) {
        console.error('❌ 检测到错误的 IP 地址 117.0.0.1，自动修正为 127.0.0.1')
        wsUrl = wsUrl.replace('117.0.0.1', '127.0.0.1')
      }

      const fullUrl = `${wsUrl}/ws?x-token=${this.token}`
      console.log('wsUrl', wsUrl)
      console.log('token', this.token)
      console.log('🔗 正在连接到 WebSocket:', fullUrl)

      this.ws = new WebSocket(fullUrl)
      this.ws.onopen = this.onOpenHandler.bind(this)
      this.ws.onmessage = this.onMessageHandler.bind(this)
      this.ws.onclose = this.onCloseHandler.bind(this)
      this.ws.onerror = this.onErrorHandler.bind(this)
    } catch (error) {
      console.error('🚨 WebSocket 连接异常:', error)
      this.handleReconnection()
    }
  }

  onOpenHandler() {
    console.log('✅ WebSocket 连接成功')
    this.isConnect = true
    this.reconnectCount = 0
    this.clearTimers()
    this.startHeartbeat()
    EventBus.emit('websocket-connected')
  }

  onMessageHandler(event: MessageEvent<string>) {
    console.log('📨 收到 WebSocket 消息:', event.data)

    if (event.type !== 'message') {
      console.warn('接收到非消息事件:', event.type)
      return
    }

    let wsContent: WsPayload
    try {
      wsContent = JSON.parse(event.data) as WsPayload
    } catch (error) {
      console.error('❌ 解析 WebSocket 消息失败:', error, '原始数据:', event.data)
      return
    }

    if (!wsContent.type) {
      console.warn('⚠️ 接收到没有类型的消息:', wsContent)
      return
    }

    if (wsContent.data && wsContent.data.code === -1) {
      console.log('🔑 Token 已过期，正在断开连接...')
      EventBus.emit('token-expired')
      this.disConnect()
      return
    }

    this.handleMessageType(wsContent)
  }

  handleMessageType(wsContent: WsPayload) {
    switch (wsContent.type) {
      case 'msg':
        console.log('🚀 触发 on-receive-msg 事件:', wsContent.content)
        EventBus.emit('on-receive-msg', wsContent.content)
        break
      case 'notify': {
        try {
          if (
            wsContent.content &&
            typeof wsContent.content === 'object' &&
            'content' in wsContent.content &&
            typeof wsContent.content.content === 'string'
          ) {
            wsContent.content.content = JSON.parse(wsContent.content.content) as string | Record<string, unknown>
          }
          EventBus.emit('on-receive-notify', wsContent.content)
        } catch (error) {
          console.error('解析通知内容失败:', error)
        }
        break
      }
      case 'video':
        EventBus.emit('on-receive-video', wsContent.content)
        break
      case 'file':
        EventBus.emit('on-receive-file', wsContent.content)
        break
      case 'pong':
        console.log('❤️ 心跳确认')
        break
      default:
        console.warn('未知消息类型:', wsContent.type)
    }
  }

  onCloseHandler(event: CloseEvent) {
    console.log('🔌 WebSocket 已关闭:', {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean,
    })

    this.isConnect = false
    this.clearTimers()

    if (this.manualClose) {
      console.log('👋 手动断开连接，不进行重连')
      EventBus.emit('websocket-manual-disconnect')
      this.ws = null
      return
    }

    this.ws = null
    EventBus.emit('websocket-disconnected')
    this.handleReconnection()
  }

  onErrorHandler(event: Event) {
    console.error('🚨 WebSocket 错误:', {
      type: event.type,
      target: event.target,
    })

    this.isConnect = false
    this.clearTimers()
    EventBus.emit('websocket-error', event)

    if (!this.manualClose) {
      this.handleReconnection()
    }
  }

  handleReconnection() {
    if (this.lockReconnect || this.manualClose) return

    if (this.reconnectCount >= this.reconnectCountMax) {
      console.error('🛑 达到最大重连尝试次数')
      EventBus.emit('websocket-max-retries')
      return
    }

    this.lockReconnect = true
    const delay = Math.min(1000 * 2 ** this.reconnectCount, 30000)

    console.log(`🔄 将在 ${delay}ms 后重连... (尝试 ${this.reconnectCount + 1}/${this.reconnectCountMax})`)

    this.reconnectTimer = setTimeout(() => {
      this.lockReconnect = false
      this.reconnectCount++
      this.connect()
    }, delay)
  }

  send(message: string | Record<string, unknown>) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        const payload = typeof message === 'string' ? message : JSON.stringify(message)
        this.ws.send(payload)
        console.log('📤 发送消息:', payload)
        return true
      } catch (error) {
        console.error('❌ 发送消息失败:', error)
        return false
      }
    }

    console.warn('⚠️ WebSocket 未连接，无法发送消息。当前状态:', this.ws ? this.ws.readyState : '无连接')
    return false
  }

  startHeartbeat() {
    this.heartTimer = setInterval(() => {
      if (this.isConnect) {
        const success = this.send('heart')
        if (success) {
          console.log('❤️ 发送心跳')
        }
      }
    }, 9900)
  }

  clearTimers() {
    if (this.heartTimer) {
      clearInterval(this.heartTimer)
      this.heartTimer = null
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  disConnect() {
    console.log('👋 手动断开 WebSocket 连接')
    this.manualClose = true
    this.isConnect = false
    this.clearTimers()

    if (this.ws) {
      this.ws.close(1000, '手动断开连接')
      this.ws = null
    }

    this.token = null
    this.reconnectCount = 0
  }

  getStatus(): WebSocketStatus {
    const states: Record<number, ReadyStateText> = {
      0: 'CONNECTING',
      1: 'OPEN',
      2: 'CLOSING',
      3: 'CLOSED',
    }

    return {
      isConnect: this.isConnect,
      readyState: this.ws ? states[this.ws.readyState] : 'CLOSED',
      reconnectCount: this.reconnectCount,
    }
  }
}

const webSocketService = new WebSocketService()

export default {
  connect: () => webSocketService.connect(),
  disConnect: () => webSocketService.disConnect(),
  send: (message: string | Record<string, unknown>) => webSocketService.send(message),
  getStatus: () => webSocketService.getStatus(),
}

