<template>
  <aside class="sidebar" :class="{ 'is-open': showLeft }">
    <SidebarRail
      :current-user="currentUser"
      :active-panel="activePanel"
      :show-user-popover="showUserPopover"
      @update:active-panel="$emit('update:activePanel', $event)"
      @update:show-user-popover="$emit('update:showUserPopover', $event)"
      @edit-profile="$emit('edit-profile')"
      @logout="$emit('logout')"
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
      />

      <AgentListPanel
        :active-panel="activePanel"
        :search-value="agentSearchValue"
        :agents="filteredAgents"
        :selected-agent-id="selectedAgentId"
        @update:search-value="$emit('update:agentSearchValue', $event)"
        @add-agent="$emit('add-agent')"
        @select-agent="$emit('select-agent', $event)"
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
}>()
</script>

<style scoped>
/* ==================== 侧边栏布局 ==================== */
.sidebar {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  height: 100%;
  overflow: hidden;
  background: transparent;
}

/* ==================== 侧边栏面板区域 ==================== */
.sidebar-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 16px;
  min-width: 0;
  overflow-y: auto;
  background: transparent;
}

/* 滚动条样式 */
.sidebar-panel::-webkit-scrollbar {
  width: 4px;
}

.sidebar-panel::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-panel::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.2);
  border-radius: 2px;
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
