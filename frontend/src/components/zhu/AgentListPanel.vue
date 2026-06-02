<template>
  <template v-if="activePanel === 'agents'">
    <div class="sidebar-header">
      <div>
        <h1>Agent 列表</h1>
      </div>
      <span class="version-tag" :class="{ 'is-collapsed': isCollapsed }" title="点击收缩侧边栏" @click="$emit('toggle-collapse')">
        <el-icon><component :is=" props.isCollapsed ? Expand : Fold" /></el-icon>
      </span>
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
          <div class="agent-title-row">
            <span class="agent-name">{{ agent.name }}</span>
            <span class="agent-badge" :class="agent.isCustom ? 'custom' : 'builtin'">
              {{ agent.isCustom ? '自建' : '内置' }}
            </span>
          </div>
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
import { Fold, Expand } from '@element-plus/icons-vue'
import type { SidebarAgent, SidebarPanel } from '../../types/agenthub'
import Search from '../../veiws/Serach.vue'
import avatar from '../../veiws/img/avatar.vue'

const props = defineProps<{
  activePanel: SidebarPanel
  searchValue: string
  agents: SidebarAgent[]
  selectedAgentId: string
  isCollapsed: boolean
}>()

defineEmits<{
  (e: 'update:searchValue', value: string): void
  (e: 'add-agent'): void
  (e: 'select-agent', agent: SidebarAgent): void
  (e: 'toggle-collapse'): void
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
/* ==================== 侧边栏头部 ==================== */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.sidebar-header h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e40af;
  letter-spacing: -0.01em;
}

.version-tag {
  font-size: 25px;
  padding: 4px 10px;
  border-radius: 8px;
  color: #3b82f6;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.version-tag:hover,
.version-tag.is-collapsed {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(99, 102, 241, 0.15));
  border-color: rgba(59, 130, 246, 0.3);
}

/* ==================== 添加 Agent 按钮 ==================== */
.new-Agent-session-btn {
  padding: 12px 16px;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%);
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow:
    0 4px 14px rgba(59, 130, 246, 0.3),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  position: relative;
  overflow: hidden;
}

.new-Agent-session-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.new-Agent-session-btn:hover::before {
  left: 100%;
}

.new-Agent-session-btn:hover {
  transform: translateY(-2px);
  box-shadow:
    0 8px 20px rgba(59, 130, 246, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

/* ==================== Agent 列表 ==================== */
.agent-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.agent-list::-webkit-scrollbar {
  width: 4px;
}

.agent-list::-webkit-scrollbar-track {
  background: transparent;
}

.agent-list::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.2);
  border-radius: 2px;
}

/* 空状态 */
.empty-hint {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 40px 0;
  font-weight: 500;
}

/* ==================== Agent 项 ==================== */
.agent-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  width: 100%;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid transparent;
  text-align: left;
  background: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.agent-item:hover {
  background: rgba(59, 130, 246, 0.06);
  border-color: rgba(59, 130, 246, 0.12);
  transform: translateX(4px);
}

.agent-item.is-selected {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(99, 102, 241, 0.08));
  border-color: rgba(59, 130, 246, 0.25);
  box-shadow:
    0 4px 12px rgba(59, 130, 246, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

/* ==================== Agent 信息 ==================== */
.agent-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  flex: 1;
}

.agent-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.agent-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.agent-badge {
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 10px;
  font-weight: 600;
}

.agent-badge.builtin {
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
}

.agent-badge.custom {
  background: rgba(249, 115, 22, 0.12);
  color: #c2410c;
}

.agent-desc {
  font-size: 12px;
  color: #94a3b8;
}

/* ==================== 能力标签 ==================== */
.capability-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.capability-tag {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
  font-weight: 500;
  border: 1px solid rgba(59, 130, 246, 0.12);
}

.capability-tag.more {
  background: rgba(100, 116, 139, 0.1);
  color: #64748b;
  border-color: rgba(100, 116, 139, 0.15);
}
</style>
