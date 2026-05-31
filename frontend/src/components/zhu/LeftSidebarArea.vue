<template>
  <aside class="sidebar" :class="{ 'is-open': showLeft, 'is-collapsed': isCollapsed }">
    <SidebarRail
      :current-user="currentUser"
      :active-panel="activePanel"
      :show-user-popover="showUserPopover"
      :is-collapsed="isCollapsed"
      @update:active-panel="$emit('update:activePanel', $event)"
      @update:show-user-popover="$emit('update:showUserPopover', $event)"
      @edit-profile="$emit('edit-profile')"
      @logout="$emit('logout')"
      @toggle-collapse="$emit('toggle-collapse')"
    />

    <div class="sidebar-panel">
      <MessageListPanel
        :active-panel="activePanel"
        :search-value="searchValue"
        :filtered-sessions="filteredSessions"
        :current-session-id="currentSessionId"
        :is-loading="isLoadingList"
        :agents="agents"
        :format-time="formatTime"
        @update:search-value="$emit('update:searchValue', $event)"
        @new-session="$emit('new-session')"
        @select-session="$emit('select-session', $event)"
        @toggle-pin="$emit('toggle-pin', $event)"
        @toggle-archive="$emit('toggle-archive', $event)"
        @delete-session="$emit('delete-session', $event)"
        @toggle-collapse="$emit('toggle-collapse')"
      />

      <AgentListPanel
        :active-panel="activePanel"
        :search-value="agentSearchValue"
        :agents="filteredAgents"
        :selected-agent-id="selectedAgentId"
        :is-collapsed="isCollapsed"
        @update:search-value="$emit('update:agentSearchValue', $event)"
        @add-agent="$emit('add-agent')"
        @select-agent="$emit('select-agent', $event)"
        @toggle-collapse="$emit('toggle-collapse')"
      />
    </div>
  </aside>
</template>

<script lang="ts" setup>
import type { ConversationItem, SidebarAgent, SidebarPanel, SidebarUser } from '../../types/agenthub'
import AgentListPanel from './AgentListPanel.vue'
import MessageListPanel from './MessageListPanel.vue'
import SidebarRail from './SidebarRail.vue'

defineProps<{
  showLeft: boolean
  isCollapsed: boolean
  currentUser: SidebarUser
  activePanel: SidebarPanel
  showUserPopover: boolean
  searchValue: string
  agentSearchValue: string
  filteredSessions: ConversationItem[]
  currentSessionId: string
  isLoadingList: boolean
  agents: SidebarAgent[]
  filteredAgents: SidebarAgent[]
  selectedAgentId: string
  formatTime: (iso: string) => string
}>()

defineEmits<{
  (e: 'update:activePanel', panel: SidebarPanel): void
  (e: 'update:showUserPopover', value: boolean): void
  (e: 'update:searchValue', value: string): void
  (e: 'update:agentSearchValue', value: string): void
  (e: 'new-session'): void
  (e: 'select-session', item: ConversationItem): void
  (e: 'toggle-pin', item: ConversationItem): void
  (e: 'toggle-archive', item: ConversationItem): void
  (e: 'add-agent'): void
  (e: 'select-agent', agent: SidebarAgent): void
  (e: 'delete-session', item: ConversationItem): void
  (e: 'edit-profile'): void
  (e: 'logout'): void
  (e: 'toggle-collapse'): void
}>()
</script>

<style scoped>
/* ==================== 侧边栏布局 ==================== */
.sidebar {
  display: flex;
  height: 100%;
  overflow: hidden;
  background: transparent;
}

/* 图标栏固定宽度 */
.sidebar > :deep(*:first-child) {
  flex-shrink: 0;
  width: 72px;
}

/* 收起状态：隐藏面板区域 */
.sidebar-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  flex: 1;
  min-width: 0;
  width: 328px;
  padding: 10px 16px;
  overflow-y: auto;
  background: transparent;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.3s ease;
}

/* 收起状态 */
.sidebar.is-collapsed .sidebar-panel {
  width: 0;
  opacity: 0;
  overflow: hidden;
}

/* 滚动条样式 */
.sidebar-panel::-webkit-scrollbar {
  width: 4px;
}

.sidebar-panel::-webkit-scrollbar-track {
  background: transparent;
}

/* ==================== 响应式适配 ==================== */
@media (max-width: 900px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: min(340px, 90vw);
    z-index: 30;
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 8px 0 32px rgba(59, 130, 246, 0.15);
  }

  .sidebar.is-open {
    transform: translateX(0);
  }
}
</style>
