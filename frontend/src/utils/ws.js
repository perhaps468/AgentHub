import EventBus from '../utils/EventBus';

class WebSocketService {
  constructor() {
    this.ws = null;
    this.heartTimer = null;
    this.reconnectTimer = null;
    this.lockReconnect = false;
    this.token = null;
    this.reconnectCountMax = 10;
    this.reconnectCount = 0;
    this.isConnect = false;
    this.manualClose = false;
  }

  connect() {
    if (this.isConnect || this.ws) {
      console.log('WebSocket 已连接或正在连接中');
      return;
    }

    this.token = localStorage.getItem('x-token');
    if (!this.token) {
      console.error('❌ 未找到有效的 token，请检查 localStorage 中的 x-token');
      return;
    }

    this.manualClose = false;

    try {
      let wsUrl = import.meta.env.VITE_WS_URL;

      // 环境变量检查
      if (!wsUrl) {
        console.error('❌ WebSocket URL 未配置，请检查环境变量 VITE_WS_URL');
        // 提供默认值（开发环境）
        wsUrl = 'ws://127.0.0.1:9800';
        console.warn('使用默认 WebSocket URL:', wsUrl);
      }

      // URL 格式验证和修正
      if (!wsUrl.startsWith('ws://') && !wsUrl.startsWith('wss://')) {
        console.warn('WebSocket URL 缺少协议，自动添加 ws://');
        wsUrl = 'ws://' + wsUrl;
      }

      // 检查 IP 地址格式
      if (wsUrl.includes('117.0.0.1')) {
        console.error('❌ 检测到错误的 IP 地址 117.0.0.1，自动修正为 127.0.0.1');
        wsUrl = wsUrl.replace('117.0.0.1', '127.0.0.1');
      }

      const fullUrl = `${wsUrl}/ws?x-token=${this.token}`;
      console.log('wsUrl', wsUrl);
      console.log('token', this.token);

      console.log('🔗 正在连接到 WebSocket:', fullUrl);
      //websocket连接
      this.ws = new WebSocket(fullUrl);

      this.ws.onopen = this.onOpenHandler.bind(this);
      this.ws.onmessage = this.onMessageHandler.bind(this);
      this.ws.onclose = this.onCloseHandler.bind(this);
      this.ws.onerror = this.onErrorHandler.bind(this);
    } catch (error) {
      console.error('🚨 WebSocket 连接异常:', error);
      this.handleReconnection();
    }
  }
//连接建立
  onOpenHandler() {
    console.log('✅ WebSocket 连接成功');
    this.isConnect = true;
    this.reconnectCount = 0;
    this.clearTimers();
    this.startHeartbeat();

    // 发送连接成功事件
    EventBus.emit('websocket-connected');
  }
// 消息处理  
  onMessageHandler(event) {
    console.log('📨 收到 WebSocket 消息:', event.data);

    if (event.type !== 'message') {
      console.warn('接收到非消息事件:', event.type);
      return;
    }

    let wsContent;
    try {
      wsContent = JSON.parse(event.data);
    } catch (error) {
      console.error('❌ 解析 WebSocket 消息失败:', error, '原始数据:', event.data);
      return;
    }

    if (!wsContent.type) {
      console.warn('⚠️ 接收到没有类型的消息:', wsContent);
      return;
    }

    // 处理 token 过期
    if (wsContent.data && wsContent.data.code === -1) {
      console.log('🔑 Token 已过期，正在断开连接...');
      EventBus.emit('token-expired');
      this.disConnect();
      return;
    }

    this.handleMessageType(wsContent);
  }
//事件分发
  handleMessageType(wsContent) {
    switch (wsContent.type) {
      case 'msg':
        console.log('🚀 触发 on-receive-msg 事件:', wsContent.content);
        EventBus.emit('on-receive-msg', wsContent.content);
        break;
      case 'notify':
        try {
          if (wsContent.content?.content) {
            wsContent.content.content = JSON.parse(wsContent.content.content);
          }
          EventBus.emit('on-receive-notify', wsContent.content);
        } catch (error) {
          console.error('解析通知内容失败:', error);
        }
        break;
      case 'video':
        EventBus.emit('on-receive-video', wsContent.content);
        break;
      case 'file':
        EventBus.emit('on-receive-file', wsContent.content);
        break;
      case 'pong':
        console.log('❤️ 心跳确认');
        break;
      default:
        console.warn('未知消息类型:', wsContent.type);
    }
  }

  onCloseHandler(event) {
    console.log('🔌 WebSocket 已关闭:', {
      code: event.code,
      reason: event.reason,
      wasClean: event.wasClean
    });

    this.isConnect = false;
    this.clearTimers();

    if (this.manualClose) {
      console.log('👋 手动断开连接，不进行重连');
      EventBus.emit('websocket-manual-disconnect');
      return;
    }

    EventBus.emit('websocket-disconnected');
    this.handleReconnection();
  }

  onErrorHandler(error) {
    console.error('🚨 WebSocket 错误:', {
      type: error.type,
      target: error.target
    });

    this.isConnect = false;
    this.clearTimers();

    EventBus.emit('websocket-error', error);

    if (!this.manualClose) {
      this.handleReconnection();
    }
  }
  // 重连机制
  handleReconnection() {
    if (this.lockReconnect || this.manualClose) return;

    if (this.reconnectCount >= this.reconnectCountMax) {
      console.error('🛑 达到最大重连尝试次数');
      EventBus.emit('websocket-max-retries');
      return;
    }

    this.lockReconnect = true;

    // 指数退避重连策略
    const delay = Math.min(1000 * Math.pow(2, this.reconnectCount), 30000);

    console.log(`🔄 将在 ${delay}ms 后重连... (尝试 ${this.reconnectCount + 1}/${this.reconnectCountMax})`);

    this.reconnectTimer = setTimeout(() => {
      this.lockReconnect = false;
      this.reconnectCount++;
      this.connect(this.token);
    }, delay);
  }

  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        if (typeof message !== 'string') {
          message = JSON.stringify(message);
        }
        this.ws.send(message);
        console.log('📤 发送消息:', message);
        return true;
      } catch (error) {
        console.error('❌ 发送消息失败:', error);
        return false;
      }
    } else {
      console.warn('⚠️ WebSocket 未连接，无法发送消息。当前状态:', this.ws ? this.ws.readyState : '无连接');
      return false;
    }
  }
  // 心跳维护
  startHeartbeat() {
    this.heartTimer = setInterval(() => {
      if (this.isConnect) {
        const success = this.send('heart');
        if (success) {
          console.log('❤️ 发送心跳');
        }
      }
    }, 9900);
  }

  clearTimers() {
    if (this.heartTimer) {
      clearInterval(this.heartTimer);
      this.heartTimer = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
// 资源清理
  disConnect() {
    console.log('👋 手动断开 WebSocket 连接');
    this.manualClose = true;
    this.isConnect = false;
    this.clearTimers();

    if (this.ws) {
      this.ws.close(1000, '手动断开连接');
      this.ws = null;
    }

    this.token = null;
    this.reconnectCount = 0;
  }

  getStatus() {
    const states = {
      0: 'CONNECTING',
      1: 'OPEN',
      2: 'CLOSING',
      3: 'CLOSED'
    };

    return {
      isConnect: this.isConnect,
      readyState: this.ws ? states[this.ws.readyState] : 'CLOSED',
      reconnectCount: this.reconnectCount
    };
  }
}

// 创建单例实例
const webSocketService = new WebSocketService();

export default {
  connect: (token) => webSocketService.connect(token),
  disConnect: () => webSocketService.disConnect(),
  send: (message) => webSocketService.send(message),
  getStatus: () => webSocketService.getStatus()
};