<template>
  <template v-if="activePanel === 'agents'">
    <div class="sidebar-header">
      <div>
        <h1>Agent 列表</h1>
      </div>
      <span class="version-tag">v1.1.3</span>
    </div>

    <Search
      :value="searchValue"
      placeholder="搜索 Agent"
      height="38px"
      width="100%"
      radius="12px"
      font-size="14px"
      background-color="rgb(var(--surface-muted))"
      @update:value="$emit('update:searchValue', $event)"
    />

    <button class="new-Agent-session-btn" type="button" @click="$emit('add-agent')">
      + 添加自建 Agent
    </button>

    <div class="agent-list">
      <button
        v-for="agent in agents"
        :key="agent.id"
        class="agent-item"
        :class="{ 'is-selected': selectedAgentId === agent.id }"
        type="button"
        @click="$emit('select-agent', agent)"
      >
        <avatar :info="{ name: agent.name, avatar: agent.avatar }" size="42px" :style="getAgentAvatarStyle(agent)" />
        <div class="agent-info">
          <span class="agent-name">{{ agent.name }}</span>
          <span class="agent-desc">{{ agent.description || getAgentPlatformLabel(agent) }}</span>
          <div class="capability-tags">
            <span v-for="tag in getVisibleCapabilityTags(agent.capabilityTags)" :key="tag" class="capability-tag">{{ tag }}</span>
            <span v-if="agent.capabilityTags.length > 3" class="capability-tag more">+{{ agent.capabilityTags.length - 3 }}</span>
          </div>
        </div>
      </button>
      <div v-if="agents.length === 0" class="empty-hint">
        暂无 Agent
      </div>
    </div>
  </template>
</template>

<script lang="ts" setup>
import type { SidebarAgent, SidebarPanel } from '../../types/agenthub'
import Search from '../../veiws/Serach.vue'
import avatar from '../../veiws/img/avatar.vue'

defineProps<{
  activePanel: SidebarPanel
  searchValue: string
  agents: SidebarAgent[]
  selectedAgentId: string
}>()

defineEmits<{
  (e: 'update:searchValue', value: string): void
  (e: 'add-agent'): void
  (e: 'select-agent', agent: SidebarAgent): void
}>()

const getVisibleCapabilityTags = (tags: string[]) => tags.slice(0, 3)

const getAgentAvatarStyle = (agent: SidebarAgent) => {
  const colors: Record<string, string> = {
    'claude-code': '#e65100',
    codex: '#e65100',
    opencode: '#7b1fa2',
    custom: '#ff7043',
  }
  const bg = colors[agent.platform || 'custom'] || '#9e9e9e'
  return { '--avatar-bg': bg }
}

const getAgentPlatformLabel = (agent: SidebarAgent) => {
  const labels: Record<string, string> = {
    'claude-code': 'Claude',
    codex: 'Codex',
    opencode: 'OpenCode',
    custom: '自建',
  }
  return labels[agent.platform || 'custom'] || agent.platform || ''
}
</script>

<style scoped>
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sidebar-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  line-height: 1.2;
}

.version-tag {
  font-size: 12px;
  color: #9c27b0;
  font-weight: 500;
}

.new-Agent-session-btn {
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid #1a1a1a;
  background: #1a1a1a;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.agent-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  overflow-y: auto;
}

.empty-hint {
  text-align: center;
  color: rgb(var(--text-muted));
  font-size: 13px;
  padding: 20px 0;
}

.agent-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid transparent;
  text-align: left;
  background: transparent;
  cursor: pointer;
}

.agent-item:hover {
  background: #f9f9f9;
}

.agent-item.is-selected {
  background: #f3e5f5;
  border-color: rgba(156, 39, 176, 0.2);
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #1a1a1a;
}

.agent-desc {
  font-size: 12px;
  color: #999;
}

.capability-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}

.capability-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #f5f5f5;
  color: #666;
}

.capability-tag.more {
  background: #e0e0e0;
  color: #999;
}
</style>
