import { defineStore } from 'pinia'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: 'light',
  }),
  actions: {
    async setTheme(newTheme:string) {
      this.theme = newTheme
      document.documentElement.setAttribute('data-theme', newTheme)
    },
  },
})
