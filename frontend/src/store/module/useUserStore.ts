import { defineStore } from 'pinia'
import type { UserInfo } from '../../types/login'
export const useUserInfoStore = defineStore('user-info', {
  state: () => ({
    userId: '',
    userName: '',
    avatar: '',
  }),
  actions: {
    async setUserInfo(userInfo: UserInfo) {
      this.userId = String(userInfo.userId)
      this.userName = userInfo.userName
      this.avatar = userInfo.avatar || 'msg10.jpg';
    },
    async clearUserInfo() {
      this.userId = ''
      this.userName = ''
      this.avatar = ''
    },
    async setUserAvatar(avatar: string) {
      this.avatar = avatar
    },
    async setUserName(name: string) {
      this.userName = name
    },
  },
})
