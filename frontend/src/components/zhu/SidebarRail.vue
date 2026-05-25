<template>
  <div class="sidebar-rail">
    <div class="rail-avatar-wrapper">
      <button class="rail-avatar" type="button" @click="$emit('update:showUserPopover', !showUserPopover)">
        <avatar :info="{ name: currentUser.name || 'Guest', avatar: currentUser.avatar }" size="44px" />
      </button>
      <Transition name="popover-fade">
        <div v-if="showUserPopover" class="user-popover">
          <div class="user-popover-header">
            <avatar :info="{ name: currentUser.name, avatar: currentUser.avatar }" size="56px" />
            <div class="user-popover-info">
              <span class="user-popover-name">{{ currentUser.name }}</span>
              <span class="user-popover-email">{{ currentUser.email || 'AgentHub 用户' }}</span>
            </div>
          </div>
          <div class="user-popover-actions">
            <button class="user-popover-btn" type="button" @click="$emit('edit-profile')">编辑资料</button>
            <button class="user-popover-btn logout" type="button" @click="$emit('logout')">退出登录</button>
          </div>
        </div>
      </Transition>
    </div>
    <button
      class="rail-button"
      :class="{ active: activePanel === 'messages' }"
      type="button"
      title="消息列表"
      @click="$emit('update:activePanel', 'messages')"
    >
      <ChatDotRound />
    </button>
    <button
      class="rail-button"
      :class="{ active: activePanel === 'agents' }"
      type="button"
      title="Agent 列表"
      @click="$emit('update:activePanel', 'agents')"
    >
      <User />
    </button>
  </div>
</template>

<script lang="ts" setup>
import { ChatDotRound, User } from '@element-plus/icons-vue'
import type { SidebarPanel, SidebarUser } from '../../types/agenthub'
import avatar from '../../veiws/img/avatar.vue'

defineProps<{
  currentUser: SidebarUser
  activePanel: SidebarPanel
  showUserPopover: boolean
}>()

defineEmits<{
  (e: 'update:activePanel', panel: SidebarPanel): void
  (e: 'update:showUserPopover', value: boolean): void
  (e: 'edit-profile'): void
  (e: 'logout'): void
}>()
</script>

<style scoped>
.sidebar-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 12px;
  background: rgb(var(--surface-muted));
  border-right: 1px solid rgb(var(--border-color));
}

.rail-avatar-wrapper {
  position: relative;
}

.rail-avatar,
.rail-button {
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  color: rgb(var(--text-secondary));
  background: transparent;
  border: none;
  cursor: pointer;
}

.rail-button :deep(svg) {
  width: 22px;
  height: 22px;
}

.rail-button.active,
.rail-button:hover,
.rail-avatar:hover {
  background: rgb(var(--primary-soft));
  color: rgb(var(--primary-strong));
}

.user-popover {
  position: absolute;
  top: 0;
  left: 56px;
  z-index: 100;
  width: 240px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  padding: 16px;
}

.user-popover-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.user-popover-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.user-popover-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
}

.user-popover-email {
  font-size: 12px;
  color: #666;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-popover-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-popover-btn {
  width: 100%;
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #333;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.user-popover-btn:hover {
  background: #f5f5f5;
}

.user-popover-btn.logout {
  color: #e53935;
  border-color: #ffcdd2;
}

.user-popover-btn.logout:hover {
  background: #ffebee;
}

.popover-fade-enter-active,
.popover-fade-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}
</style>
