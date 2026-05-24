<template>
  <template v-if="activePanel === 'messages'">
    <div class="sidebar-header">
      <div>
        <h1>消息列表</h1>
      </div>
      <span class="version-tag">v1.1.3</span>
    </div>

    <Search
      :value="searchValue"
      placeholder="搜索用户/会话"
      height="38px"
      width="100%"
      radius="12px"
      font-size="14px"
      background-color="rgb(var(--surface-muted))"
      @update:value="$emit('update:searchValue', $event)"
    />

    <div class="toolbar-row">
      <button class="new-session-btn" type="button" @click="$emit('new-session')">
        新建对话
      </button>
      <button class="toolbar-btn" type="button" @click="$emit('update:showArchived', !showArchived)">
        {{ showArchived ? '隐藏归档' : '显示归档' }}
      </button>
    </div>

    <div class="conversation-list">
      <div v-if="isLoading" class="loading-hint">加载中...</div>

      <div v-if="agentConversations.length > 0" class="list-section">
        <div class="section-title">Agent 单聊</div>
        <button
          v-for="item in agentConversations"
          :key="item.id"
          class="conversation-item"
          :class="{ 'is-active': currentSessionId === item.id }"
          type="button"
          @click="$emit('select-session', item)"
        >
          <avatar :info="{ name: item.title || '会话', avatar: getAgentAvatar(item) }" size="38px" />
          <div class="conversation-copy">
            <div class="conversation-title-row">
              <span class="conversation-title">{{ item.title || '未命名会话' }}</span>
              <span v-if="item.mode === 'single'" class="mode-tag single">单聊</span>
              <dot_hint v-if="item.is_pinned" text="置顶" />
            </div>
            <div class="capability-tags" v-if="getAgentTags(item).length > 0">
              <span v-for="tag in getAgentTags(item).slice(0, 3)" :key="tag" class="capability-tag">{{ tag }}</span>
              <span v-if="getAgentTags(item).length > 3" class="capability-tag more">+{{ getAgentTags(item).length - 3 }}</span>
            </div>
            <div class="conversation-snippet">{{ formatTime(item.updated_at) }}</div>
          </div>
          <div class="conversation-actions">
            <button class="action-btn" type="button" @click.stop="$emit('toggle-pin', item)">{{ item.is_pinned ? '取消置顶' : '置顶' }}</button>
            <button class="action-btn" type="button" @click.stop="$emit('toggle-archive', item)">归档</button>
          </div>
        </button>
      </div>

      <div v-if="groupConversations.length > 0" class="list-section">
        <div class="section-title">群聊</div>
        <button
          v-for="item in groupConversations"
          :key="item.id"
          class="conversation-item"
          :class="{ 'is-active': currentSessionId === item.id }"
          type="button"
          @click="$emit('select-session', item)"
        >
          <avatar :info="{ name: '群', avatar: '' }" size="38px" :style="{ background: '#ff7043', color: '#fff' }" />
          <div class="conversation-copy">
            <div class="conversation-title-row">
              <span class="conversation-title">{{ item.title || '群聊' }}</span>
              <span class="mode-tag group">默认</span>
            </div>
            <div class="conversation-snippet">{{ formatTime(item.updated_at) }}</div>
          </div>
        </button>
      </div>

      <div v-if="!isLoading && filteredSessions.length === 0" class="empty-hint">
        暂无会话
      </div>
    </div>
  </template>
</template>

<script lang="ts" setup>
import type { ConversationItem, SidebarAgent, SidebarPanel } from '../../types/agenthub'
import Search from '../../veiws/Serach.vue'
import avatar from '../../veiws/img/avatar.vue'
import dot_hint from '../../veiws/left/dot-hint.vue'

const props = defineProps<{
  activePanel: SidebarPanel
  searchValue: string
  showArchived: boolean
  filteredSessions: ConversationItem[]
  agentConversations: ConversationItem[]
  groupConversations: ConversationItem[]
  currentSessionId: string
  isLoading: boolean
  agents: SidebarAgent[]
  formatTime: (iso: string) => string
}>()

defineEmits<{
  (e: 'update:searchValue', value: string): void
  (e: 'update:showArchived', value: boolean): void
  (e: 'new-session'): void
  (e: 'select-session', item: ConversationItem): void
  (e: 'toggle-pin', item: ConversationItem): void
  (e: 'toggle-archive', item: ConversationItem): void
}>()

const getAgentAvatar = (item: ConversationItem) => {
  const agent = props.agents.find((a) => item.title?.includes(a.name))
  return agent?.avatar || ''
}

const getAgentTags = (item: ConversationItem) => {
  const agent = props.agents.find((a) => item.title?.includes(a.name))
  return agent?.capabilityTags || []
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

.toolbar-row {
  display: flex;
  gap: 8px;
}

.new-session-btn {
  flex: 1;
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

.new-session-btn:hover {
  background: #333;
}

.toolbar-btn {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #666;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.toolbar-btn:hover {
  background: #f5f5f5;
}

.list-section {
  margin-bottom: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #666;
  margin-bottom: 8px;
  padding-left: 4px;
}

.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-height: 0;
  overflow-y: auto;
}

.loading-hint,
.empty-hint {
  text-align: center;
  color: rgb(var(--text-muted));
  font-size: 13px;
  padding: 20px 0;
}

.conversation-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  border: 1px solid transparent;
  text-align: left;
  background: transparent;
  cursor: pointer;
  position: relative;
}

.conversation-item:hover {
  background: #f9f9f9;
}

.conversation-item.is-active {
  background: #f3e5f5;
  border-color: rgba(156, 39, 176, 0.2);
}

.conversation-copy {
  min-width: 0;
  flex: 1;
}

.conversation-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.conversation-title {
  color: #1a1a1a;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mode-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.mode-tag.single {
  background: #e3f2fd;
  color: #1976d2;
}

.mode-tag.group {
  background: #fff3e0;
  color: #e65100;
}

.conversation-snippet {
  color: #999;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conversation-actions {
  display: none;
  flex-direction: column;
  gap: 4px;
}

.conversation-item:hover .conversation-actions {
  display: flex;
}

.action-btn {
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #666;
  font-size: 11px;
  cursor: pointer;
  white-space: nowrap;
}

.action-btn:hover {
  background: #f5f5f5;
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
