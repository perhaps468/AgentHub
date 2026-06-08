<template>
  <!-- 左侧菜单栏：头像 + 消息列表按钮 + Agent 列表按钮 -->
  <div class="sidebar-rail">
    <!-- 头像按钮 -->
    <div class="rail-avatar-wrapper">
      <button class="rail-avatar" type="button" @click="$emit('update:showUserPopover', !showUserPopover)">
        <avatar :info="{ name: currentUser.name , avatar: currentUser.avatar }" size="44px" />
      </button>
    </div>

    <!-- 用户信息弹框 -->
    <Transition name="popover-fade" @mouseleave="$emit('update:showUserPopover', false)">
      <div v-if="showUserPopover" class="user-popover" >
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

    <button
      class="rail-button"
      :class="{ 'is-collapsed': isCollapsed }"
      title="收起侧边栏"
      v-if="isCollapsed===true"
      @click="handleToggleCollapse"
    >
      <el-icon><component :is="isCollapsed ? Expand : Fold" /></el-icon>
    </button>
    <div v-else class="rail-button-group">
        <!-- 消息列表入口按钮 -->
        <button
          class="rail-button"
          :class="{ active: activePanel === 'messages' }"
          type="button"
          title="消息列表"
          @click="$emit('update:activePanel', 'messages')"
        >
          <ChatDotRound />
        </button>

        <!-- Agent 列表入口按钮 -->
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
  </div>
</template>

<script lang="ts" setup>
import { ChatDotRound, User, Fold, Expand } from '@element-plus/icons-vue'
import type { SidebarPanel, SidebarUser } from '../../types/agenthub'
import avatar from '../../veiws/img/avatar.vue'

defineProps<{
  currentUser: SidebarUser
  activePanel: SidebarPanel
  showUserPopover: boolean
  isCollapsed: boolean
}>()

const emit = defineEmits<{
  (e: 'update:activePanel', panel: SidebarPanel): void
  (e: 'update:showUserPopover', value: boolean): void
  (e: 'edit-profile'): void
  (e: 'logout'): void
  (e: 'toggle-collapse'): void
}>()

const handleToggleCollapse = () => {
  emit('toggle-collapse')
}
</script>

<style scoped>
/* ==================== 侧边栏图标栏容器 ==================== */
.sidebar-rail {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  width: 70px;
  padding: 18px 10px;
  background: rgba(var(--surface-color), 0.72);
  border-right: 1px solid rgb(var(--border-color));
}

/* ==================== 头像容器 ==================== */
.rail-avatar-wrapper {
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(var(--border-color), 0.78);
}

/* 按钮组容器 */
.rail-button-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ==================== 按钮基础样式 ==================== */
.rail-button,.rail-avatar {
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: rgb(var(--text-muted));
  background: transparent;
  border: 1px solid transparent;
  cursor: pointer;
  position: relative;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.rail-button :deep(svg) {
  width: 19px;
  height: 19px;
}

/* ==================== 激活与悬停状态 ==================== */
.rail-button.active,
.rail-button.is-collapsed {
  background: rgb(var(--primary-soft));
  color: rgb(var(--primary-strong));
  border-color: rgba(var(--primary-color), 0.18);
  box-shadow: inset 3px 0 0 rgb(var(--primary-color));
}

.rail-button:hover {
  background: rgba(var(--surface-muted), 0.84);
  color: rgb(var(--text-secondary));
  border-color: rgba(var(--border-color), 0.9);
}

.rail-button.active:hover,
.rail-button.is-collapsed:hover {
  background: rgb(var(--primary-soft));
  color: rgb(var(--primary-strong));
}

.rail-avatar:hover {
  background: rgba(var(--surface-muted), 0.8);
  border-color: rgba(var(--border-color), 0.9);
  box-shadow: var(--shadow-soft);
}

/* ==================== 用户信息弹框 ==================== */
.user-popover {
  position: absolute;
  top: 8px;
  left: 62px;
  z-index: 100;
  width: 268px;
  background: rgb(var(--surface-color));
  border-radius: 14px;
  box-shadow: var(--shadow-md);
  padding: 18px;
  border: 1px solid rgb(var(--border-color));
  animation: popoverFadeIn 0.18s ease;
}

@keyframes popoverFadeIn {
  from {
    opacity: 0;
    transform: translateX(-6px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* ==================== 弹框头部 ==================== */
.user-popover-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
  padding-bottom: 14px;
  border-bottom: 1px solid rgb(var(--border-color));
}

.user-popover-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.user-popover-name {
  font-size: 16px;
  font-weight: var(--font-weight-strong);
  color: rgb(var(--text-color));
}

.user-popover-email {
  font-size: 12px;
  color: rgb(var(--text-muted));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ==================== 弹框操作按钮 ==================== */
.user-popover-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.user-popover-btn {
  width: 100%;
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid rgb(var(--border-color));
  background: rgb(var(--surface-elevated));
  color: rgb(var(--text-secondary));
  font-size: 13px;
  font-weight: var(--font-weight-strong);
  cursor: pointer;
  transition:
    background 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease;
}

.user-popover-btn:hover {
  background: rgb(var(--primary-soft));
  border-color: rgba(var(--primary-color), 0.24);
  color: rgb(var(--primary-strong));
}

.user-popover-btn.logout {
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.2);
  background: rgba(239, 68, 68, 0.05);
}

.user-popover-btn.logout:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: #ef4444;
  color: #dc2626;
}

/* ==================== 弹框过渡动画 ==================== */
.popover-fade-enter-active,
.popover-fade-leave-active {
  transition:
    opacity 0.16s ease,
    transform 0.16s ease;
}

.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: translateX(-6px);
}
</style>
