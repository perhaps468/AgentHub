<template>
  <ToastProvider>
    <Dialog
      :is-open="globalStore.isOpenGlobalDialog"
      :title="globalStore.dialogTitle"
      :content="globalStore.dialogContent"
      @ok="handlerLogout"
      @cancel="handlerLogout"
    />
    <div class="app-shell" :data-theme="themeStore.theme">
      <RouterView />
    </div>
  </ToastProvider>
</template>

<script setup>
import { RouterView, useRouter } from 'vue-router'
import { useThemeStore } from './store/module/useThemeStore'
import ToastProvider from './veiws/ToastProvider.vue'
import Dialog from './veiws/theme/Dialog.vue'
import { useGlobalStore } from './store/module/useGlobalStore'
import { ws } from './utils/ws-client'
import { useUserInfoStore } from './store/module/useUserStore'

const themeStore = useThemeStore()
const globalStore = useGlobalStore()
const userInfoStore = useUserInfoStore()
const router = useRouter()
const handlerLogout = () => {
  localStorage.removeItem('x-token')
  userInfoStore.clearUserInfo()
  ws.disConnect()
  router.push('/login')
  globalStore.closeGlobalDialog()
}
</script>

<style scoped lang="scss">
.app-shell {
  min-height: 100vh;
  background: rgb(var(--background-color));
  color: rgb(var(--text-color));
}
</style>
