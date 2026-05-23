import { defineStore } from 'pinia'
import type { MessageRecord, UserInfo } from '../../types/message'

export const useChatMsgStore = defineStore('chat-msg', {
  state: () => ({
    referenceMsg: null as MessageRecord | null, //要引用的消息
    userListMap: new Map<string, UserInfo>(), //全部用户
  }),
  actions: {
    setReferenceMsg(msg: MessageRecord) {
      this.referenceMsg = msg
    },
    setUserListMap(map: Map<string, UserInfo>) {
      this.userListMap = map
    },
  },
})
