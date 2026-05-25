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
        :show-archived="showArchived"
        :filtered-sessions="filteredSessions"
        :agent-conversations="agentConversations"
        :group-conversations="groupConversations"
        :current-session-id="currentSessionId"
        :is-loading="isLoadingList"
        :agents="agents"
        :format-time="formatTime"
        @update:search-value="$emit('update:searchValue', $event)"
        @update:show-archived="$emit('update:showArchived', $event)"
        @new-session="$emit('new-session')"
        @select-session="$emit('select-session', $event)"
        @toggle-pin="$emit('toggle-pin', $event)"
        @toggle-archive="$emit('toggle-archive', $event)"
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
  showArchived: boolean
  filteredSessions: ConversationItem[]
  agentConversations: ConversationItem[]
  groupConversations: ConversationItem[]
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
  (e: 'update:showArchived', value: boolean): void
  (e: 'new-session'): void
  (e: 'select-session', item: ConversationItem): void
  (e: 'toggle-pin', item: ConversationItem): void
  (e: 'toggle-archive', item: ConversationItem): void
  (e: 'add-agent'): void
  (e: 'select-agent', agent: SidebarAgent): void
  (e: 'edit-profile'): void
  (e: 'logout'): void
}>()
</script>

<style scoped>
.sidebar {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  height: 100vh;
  overflow: hidden;
  background: rgb(var(--surface-color));
  border-right: 1px solid rgb(var(--border-color));
}

.sidebar-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 20px 18px 18px;
  min-width: 0;
  overflow-y: auto;
}

@media (max-width: 900px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: min(320px, 88vw);
    z-index: 30;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }

  .sidebar.is-open {
    transform: translateX(0);
  }
}
</style>
