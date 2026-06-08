// 用户信息
export interface UserInfo {
    id: string
    name: string
    avatar: string | null
    type: string
    badge: string[] | null
}

// 发送消息参数
export interface SendMessageParams extends Record<string, unknown> {
    msgContent: string
    targetId: string
    type: string
    source: string
    referenceMsgId?: string
}

// 发送消息响应
export interface SendMessageResponse {
    code: number
    msg: string
    data: MessageRecord
}

// 消息内容项
export interface MessageContent {
    type: 'text' | 'at' | 'emoji' | 'image' | 'file'
    content: string
}

// 消息记录
export interface MessageRecord {
    id: string
    fromId: string
    toId: string
    fromInfo: UserInfo
    message: string 
    //string | MessageContent[]
    referenceMsg: any | null
    atUser: any | null
    isShowTime: boolean
    type: string
    source: string
    createTime: string
    updateTime: string
}

// 获取消息记录参数
export interface RecordParams {
    index: number
    num: number
    targetId: string
}

// API响应
export interface MessageResponse {
    code: number
    msg: string
    data: MessageRecord[]
}

/**
 * PPT 单页数据结构，对应后端 ppt_data 中的每一页
 */
export interface PptPageItem {
  pageTitle: string
  pageContent: string[]
  imgTag: string
}

/**
 * PPT 消息完整载荷，后端推送 message.type === 'ppt_data' 时的数据结构
 */
export interface PptMessageData {
  agent_role?: string
  timestamp?: string
  stream_id?: string
  message_id?: string
  ppt_data: PptPageItem[]
}
