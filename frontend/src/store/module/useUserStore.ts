import { defineStore } from 'pinia'
import type { UserInfo } from '../../types/login'
export const useUserInfoStore = defineStore('user-info', {
  state: () => ({
    userId: '',
    userName: '',
    email: '',
    avatar: '',
  }),
  actions: {
    async setUserInfo(userInfo: UserInfo) {
      this.userId = String(userInfo.userId)
      this.userName = userInfo.userName
      this.email = userInfo.email
      this.avatar = userInfo.avatar ?? ''
    },
    async clearUserInfo() {
      this.userId = ''
      this.userName = ''
      this.email = ''
      this.avatar = ''
    },
    async setUserAvatar(avatar: string) {
      this.avatar = avatar
    },
    async setUserName(name: string) {
      this.userName = name
    },
    async setEmail(email: string) {
      this.email = email
    },
  },
})
