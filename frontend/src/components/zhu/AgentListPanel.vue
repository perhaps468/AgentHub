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
      <div
        v-for="agent in visibleAgents"
        :key="agent.id"
        class="agent-item-wrapper"
        :class="{ 'is-selected': selectedAgentId === agent.id }"
      >
        <button
          class="agent-item"
          type="button"
          @click="$emit('select-agent', agent)"
        >
          <avatar :info="{ name: agent.name, avatar: agent.avatar }" size="42px" :style="getAgentAvatarStyle(agent)" />
          <div class="agent-info">
            <div class="agent-title-row">
              <span class="agent-name">{{ agent.name }}</span>
              <span class="agent-badge" :class="getAgentBadgeClass(agent)">
                {{ getAgentBadgeLabel(agent) }}
              </span>
            </div>
            <span class="agent-desc">{{ agent.description || getAgentPlatformLabel(agent) }}</span>
            <div class="capability-tags">
              <span v-for="tag in getVisibleCapabilityTags(agent.capabilityTags)" :key="tag" class="capability-tag">{{ tag }}</span>
              <span v-if="agent.capabilityTags.length > 3" class="capability-tag more">+{{ agent.capabilityTags.length - 3 }}</span>
            </div>
          </div>
        </button>
        <div v-if="agent.isCustom" class="agent-actions">
          <button class="agent-action-btn edit" type="button" aria-label="编辑 Agent" @click.stop="$emit('edit-agent', agent)">
            <el-icon><Edit /></el-icon>
          </button>
          <button class="agent-action-btn delete" type="button" aria-label="删除 Agent" @click.stop="$emit('delete-agent', agent)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
      </div>
      <div v-if="visibleAgents.length === 0" class="empty-hint">
        暂无 Agent
      </div>
    </div>
  </template>

  <!-- Agent 信息弹窗 -->
  <AgentInfoDialog
    v-model="showInfoDialog"
    :agent="selectedAgentForInfo"
  />
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
import { Fold, Expand, Edit, Delete } from '@element-plus/icons-vue'
import type { SidebarAgent, SidebarPanel } from '../../types/agenthub'
import Search from '../../veiws/Serach.vue'
import avatar from '../../veiws/img/avatar.vue'
import AgentInfoDialog from './AgentInfoDialog.vue'

const props = defineProps<{
  activePanel: SidebarPanel
  searchValue: string
  agents: SidebarAgent[]
  selectedAgentId: string
  isCollapsed: boolean
}>()

const emit = defineEmits<{
  (e: 'update:searchValue', value: string): void
  (e: 'add-agent'): void
  (e: 'select-agent', agent: SidebarAgent): void
  (e: 'edit-agent', agent: SidebarAgent): void
  (e: 'delete-agent', agent: SidebarAgent): void
  (e: 'toggle-collapse'): void
}>()

// Agent 信息弹窗
const showInfoDialog = ref(false)
const selectedAgentForInfo = ref<SidebarAgent | null>(null)

const showAgentInfo = (agent: SidebarAgent) => {
  selectedAgentForInfo.value = agent
  showInfoDialog.value = true
}

const visibleAgents = computed(() =>
  props.agents.filter((agent) => {
    if (!agent.isCustom && agent.role === 'PM') {
      return false
    }
    if (agent.name === 'PM Agent' || agent.name === 'Primary PM Agent' || agent.name === '主 PM Agent') {
      return false
    }
    return true
  }),
)

const getVisibleCapabilityTags = (tags: string[]) => tags.slice(0, 3)

const isGroupHostAgent = (agent: SidebarAgent) => agent.id.startsWith('group_host_') || agent.name === '群聊主Agent'

const getAgentBadgeLabel = (agent: SidebarAgent) => (isGroupHostAgent(agent) || !agent.isCustom ? '内置' : '自建')

const getAgentBadgeClass = (agent: SidebarAgent) => (isGroupHostAgent(agent) || !agent.isCustom ? 'builtin' : 'custom')

const getAgentPlatformLabel = (agent: SidebarAgent) => {
  const labels: Record<string, string> = {
    'claude-code': 'Claude',
    codex: 'Codex',
    opencode: 'OpenCode',
    custom: '自建',
  }
  return labels[agent.platform || 'custom'] || agent.platform || ''
}

const getAgentAvatarStyle = (agent: SidebarAgent) => {
  if (agent.avatar) {
    return undefined
  }

  return {
    background: 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)',
    color: '#fff',
  }
}
</script>

<style scoped lang="less">
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

/* ==================== Agent 项容器 ==================== */
.agent-item-wrapper {
  position: relative;
  border-radius: 14px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.4);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.agent-item-wrapper:hover {
  background: rgba(59, 130, 246, 0.06);
  border-color: rgba(59, 130, 246, 0.12);
}

.agent-item-wrapper.is-selected {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(99, 102, 241, 0.08));
  border-color: rgba(59, 130, 246, 0.25);
  box-shadow:
    0 4px 12px rgba(59, 130, 246, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

/* ==================== Agent 项 ==================== */
.agent-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  width: 100%;
  padding: 16px;
  border-radius: 14px;
  border: none;
  text-align: left;
  background: transparent;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ==================== 操作按钮 ==================== */
.agent-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 2px;
  border-radius: 8px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.16s ease, background 0.16s ease, box-shadow 0.16s ease;
}

.agent-item-wrapper:hover .agent-actions,
.agent-actions:focus-within {
  opacity: 1;
  pointer-events: auto;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.1);
}

.agent-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: background 0.14s ease, color 0.14s ease;
}

.agent-action-btn:hover,
.agent-action-btn:focus-visible {
  background: rgba(59, 130, 246, 0.1);
  color: #2563eb;
  outline: none;
}

.agent-action-btn.delete:hover,
.agent-action-btn.delete:focus-visible {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
}

.agent-action-btn .el-icon {
  font-size: 14px;
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
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
  border: 1px solid rgba(59, 130, 246, 0.2);
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

/* ==================== 右键菜单 ==================== */
.context-menu-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
}

.context-menu {
  position: fixed;
  z-index: 10000;
  min-width: 140px;
  padding: 6px;
  background: #fff;
  border-radius: 12px;
  box-shadow:
    0 10px 40px rgba(0, 0, 0, 0.15),
    0 2px 10px rgba(0, 0, 0, 0.08),
    0 0 0 1px rgba(0, 0, 0, 0.05);
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-size: 13px;
  font-weight: 500;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(59, 130, 246, 0.08);
    color: #3b82f6;
  }

  &.danger {
    color: #ef4444;

    &:hover {
      background: rgba(239, 68, 68, 0.1);
      color: #dc2626;
    }
  }
}

/* 右键菜单动画 */
.context-menu-enter-active {
  transition: all 0.15s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.context-menu-leave-active {
  transition: all 0.1s ease-out;
}

.context-menu-enter-from {
  opacity: 0;
  transform: scale(0.9) translateY(-8px);
}

.context-menu-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
