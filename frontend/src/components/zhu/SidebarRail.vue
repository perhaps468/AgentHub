<template>
  <!-- 左侧菜单栏：头像 + 消息列表按钮 + Agent 列表按钮 -->
  <div class="sidebar-rail">
    <!-- 头像 + 用户信息弹框 -->
    <div class="rail-avatar-wrapper">
      <button class="rail-avatar" type="button" @click="$emit('update:showUserPopover', !showUserPopover)">
        <avatar :info="{ name: currentUser.name || '管理员', avatar: currentUser.avatar }" size="44px" />
      </button>

      <!-- 用户信息弹框 -->
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
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 20px 12px;
  background: transparent;
  border-right: 1px solid rgba(59, 130, 246, 0.2);
}

/* ==================== 头像容器 ==================== */
.rail-avatar-wrapper {
  position: relative;
}

/* 按钮组容器 */
.rail-button-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* ==================== 头像与按钮基础样式 ==================== */
.rail-avatar,
.rail-button {
  width: 46px;
  height: 46px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  color: #64748b;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(59, 130, 246, 0.1);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.rail-button :deep(svg) {
  width: 22px;
  height: 22px;
}

/* ==================== 激活与悬停状态 ==================== */
.rail-button.active,
.rail-button.is-collapsed,
.rail-button:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(99, 102, 241, 0.1));
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.3);
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.rail-avatar:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(99, 102, 241, 0.15));
  border-color: rgba(59, 130, 246, 0.4);
  transform: scale(1.08);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.25);
}

/* ==================== 用户信息弹框 ==================== */
.user-popover {
  position: absolute;
  top: 0;
  left: 58px;
  z-index: 100;
  width: 280px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  box-shadow:
    0 20px 50px rgba(59, 130, 246, 0.15),
    0 8px 16px rgba(0, 0, 0, 0.08);
  padding: 24px;
  border: 1px solid rgba(59, 130, 246, 0.1);
  animation: popoverFadeIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes popoverFadeIn {
  from {
    opacity: 0;
    transform: translateX(-12px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

/* ==================== 弹框头部 ==================== */
.user-popover-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.1);
}

.user-popover-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.user-popover-name {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
}

.user-popover-email {
  font-size: 13px;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ==================== 弹框操作按钮 ==================== */
.user-popover-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.user-popover-btn {
  width: 100%;
  padding: 12px 18px;
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.15);
  background: rgba(59, 130, 246, 0.05);
  color: #475569;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.user-popover-btn:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(99, 102, 241, 0.08));
  border-color: rgba(59, 130, 246, 0.3);
  color: #3b82f6;
  transform: translateY(-1px);
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
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.popover-fade-enter-from,
.popover-fade-leave-to {
  opacity: 0;
  transform: translateX(-12px) scale(0.95);
}
</style>
