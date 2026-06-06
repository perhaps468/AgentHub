<template>
  <!-- 仅当消息面板激活时渲染 -->
  <template v-if="activePanel === 'messages'">
    <div class="sidebar-header">
      <div>
        <h1>消息列表</h1>
      </div>
      <span class="version-tag" :class="{ 'is-collapsed': isCollapsed }" title="点击收缩侧边栏" @click="$emit('toggle-collapse')">
        <el-icon><component :is=" props.isCollapsed ? Expand : Fold" /></el-icon>
      </span>
    </div>

    <!-- 搜索框 -->
    <div class="search-wrapper">
      <Search
        :value="searchValue"
        placeholder="搜索用户/会话"
        height="38px"
        width="100%"
        radius="12px"
        font-size="20px"
        background-color="rgb(var(--surface-muted))"
        @update:value="$emit('update:searchValue', $event)"
      />
    </div>

    <!-- 工具栏：新建对话 + 切换归档视图 -->
    <div class="toolbar-row">
      <button class="new-session-btn" type="button" @click="$emit('new-session')">
        新建对话
      </button>
      <button class="toolbar-btn" type="button" @click="toggleArchivedView">
        {{ showArchivedView ? '← 返回未归档' : '显示已归档' }}
      </button>
    </div>

    <!-- 会话列表 -->
    <div class="conversation-list">
      <!-- 加载态 -->
      <div v-if="isLoading" class="loading-hint">加载中...</div>

      <!-- P6-8: 统一排序（置顶优先 → 时间倒序），不再分割群聊/单聊 -->
      <template v-if="!showArchivedView">
        <button
          v-for="item in sortedActiveSessions"
          :key="item.id"
          class="conversation-item"
          :class="{ 'is-active': currentSessionId === item.id }"
          type="button"
          @click="$emit('select-session', item)"
        >
          <avatar
            v-if="item.mode === 'group'"
            :info="{ name: '群', avatar: '' }"
            size="38px"
            :style="groupConversationAvatarStyle"
          />
          <avatar
            v-else
            :info="{ name: item.title || '会话', avatar: getAgentAvatar(item, agents) }"
            size="38px"
          />
          <div class="conversation-copy">
            <div class="conversation-title-row">
              <template v-if="renamingId === item.id">
                <input
                  v-model="renamingValue"
                  class="rename-input"
                  type="text"
                  :data-renaming-id="item.id"
                  @keydown="handleRenameKeydown"
                  @blur="confirmRename"
                />
              </template>
              <template v-else>
                <span class="conversation-title">{{ item.title || (item.mode === 'group' ? '群聊' : '未命名会话') }}</span>
                <span v-if="item.mode === 'group'" class="mode-tag group">群聊</span>
                <svg v-if="item.is_pinned" width="15" height="15" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"  class="pin-icon"><path fill-rule="evenodd" clip-rule="evenodd" d="M18.2002 2.5C18.6419 2.50011 18.9999 2.85813 19 3.2998C19 3.74157 18.6419 4.0995 18.2002 4.09961H16V7.84863L16.0127 8.125C16.0719 8.76594 16.3366 9.3734 16.7705 9.85547L20.2842 13.7607C20.4228 13.9148 20.5 14.115 20.5 14.3223L20.4912 14.4932C20.4111 15.2832 19.7832 15.9111 18.9932 15.9912L18.8223 16H12.7998V21.7002C12.7997 22.1419 12.4418 22.5 12 22.5C11.5582 22.5 11.2003 22.1419 11.2002 21.7002V16H5.17773C4.30892 15.9998 3.59455 15.3394 3.50879 14.4932L3.5 14.3223C3.5 14.115 3.57717 13.9148 3.71582 13.7607L7.22949 9.85547C7.66335 9.3734 7.92806 8.76594 7.9873 8.125L8 7.84863V4.09961H5.7998C5.35807 4.0995 5 3.74157 5 3.2998C5.00011 2.85813 5.35813 2.50011 5.7998 2.5H18.2002ZM9.59961 7.84863C9.59961 8.98501 9.17913 10.0811 8.41895 10.9258L5.29199 14.4004H18.708L15.5811 10.9258C14.8209 10.0811 14.4004 8.98501 14.4004 7.84863V4.09961H9.59961V7.84863Z" fill="currentColor"></path></svg>
              </template>
            </div>
            <div class="conversation-snippet">{{ formatTime(item.updated_at) }}</div>
          </div>
          <div class="item-more-wrapper">
            <button class="item-more-btn" type="button" @click.stop="toggleMore(item.id)">⋯</button>
            <div v-if="activeMoreId === item.id" class="item-more-menu" @click.stop @mouseleave="activeMoreId = null">
              <button class="more-action danger" type="button" @click="doDelete(item)">删除会话</button>
              <div class="more-divider" />
              <button class="more-action" type="button" @click="doTogglePin(item)">
                {{ item.is_pinned ? '取消置顶' : '置顶' }}
              </button>
              <div class="more-divider" />
              <button class="more-action" type="button" @click="doToggleArchive(item)">归档</button>
              <div class="more-divider" />
              <button class="more-action" type="button" @click="startRename(item)">重命名</button>
            </div>
          </div>
        </button>
      </template>

      <!-- 显示归档模式：只显示已归档会话 -->
      <template v-else>
        <div v-if="archivedSessions.length === 0" class="empty-hint">暂无已归档会话</div>
        <button
          v-for="item in archivedSessions"
          :key="item.id"
          class="conversation-item"
          :class="{ 'is-active': currentSessionId === item.id }"
          type="button"
          @click="$emit('select-session', item)"
        >
          <avatar
            :info="{ name: item.title || '会话', avatar: getAgentAvatar(item, agents) }"
            size="38px"
            :style="{ opacity: 0.6 }"
          />
          <div class="conversation-copy">
            <div class="conversation-title-row">
              <template v-if="renamingId === item.id">
                <input
                  v-model="renamingValue"
                  class="rename-input"
                  type="text"
                  :data-renaming-id="item.id"
                  @keydown="handleRenameKeydown"
                  @blur="confirmRename"
                />
              </template>
              <template v-else>
                <span class="conversation-title" style="opacity: 0.6">{{ item.title || '未命名会话' }}</span>
                <span class="mode-tag archived">已归档</span>
              </template>
            </div>
            <div class="conversation-snippet">{{ formatTime(item.updated_at) }}</div>
          </div>
          <div class="item-more-wrapper">
            <button class="item-more-btn" type="button" @click.stop="toggleMore(item.id)">⋯</button>
            <div v-if="activeMoreId === item.id" class="item-more-menu" @click.stop @mouseleave="activeMoreId = null">
              <button class="more-action danger" type="button" @click="doDelete(item)">删除会话</button>
              <div class="more-divider" />
              <button class="more-action" type="button" @click="doToggleArchive(item)">取消归档</button>
              <div class="more-divider" />
              <button class="more-action" type="button" @click="startRename(item)">重命名</button>
            </div>
          </div>
        </button>
      </template>

      <!-- 空状态：无搜索结果 -->
      <div
        v-if="!isLoading && searchValue && filteredSessions.length === 0"
        class="empty-hint"
      >
        未找到匹配的会话
      </div>
      <!-- 空状态：无会话 -->
      <div
        v-else-if="!isLoading && !showArchivedView && activeSessions.length === 0"
        class="empty-hint"
      >
        暂无会话
      </div>
    </div>
  </template>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
import type { ConversationItem, SidebarAgent, SidebarPanel } from '../../types/agenthub'
import avatar from '../../veiws/img/avatar.vue'
import dot_hint from '../../veiws/left/dot-hint.vue'
import Search from '../../veiws/Serach.vue'
import { Fold, Expand, Top } from '@element-plus/icons-vue'

const props = defineProps<{
  activePanel: SidebarPanel
  searchValue: string
  filteredSessions: ConversationItem[]
  currentSessionId: string
  isLoading: boolean
  agents: SidebarAgent[]
  formatTime: (iso: string) => string
  isCollapsed: boolean
}>()

const emit = defineEmits<{
  (e: 'update:searchValue', value: string): void
  (e: 'new-session'): void
  (e: 'select-session', item: ConversationItem): void
  (e: 'toggle-pin', item: ConversationItem): void
  (e: 'toggle-archive', item: ConversationItem): void
  (e: 'delete-session', item: ConversationItem): void
  (e: 'rename-session', item: ConversationItem, newTitle: string): void
  (e: 'toggle-collapse'): void
}>()

// ==================== 重命名状态 ====================
const renamingId = ref<string | null>(null)
const renamingValue = ref('')

const startRename = (item: ConversationItem) => {
  activeMoreId.value = null
  renamingId.value = item.id
  renamingValue.value = item.title || ''
  nextTick(() => {
    const inputs = document.querySelectorAll('.rename-input')
    inputs.forEach((input: Element) => {
      const el = input as HTMLElement
      if (el.dataset.renamingId === item.id) {
        const inputEl = input as HTMLInputElement
        inputEl.focus()
        inputEl.select()
      }
    })
  })
}

const confirmRename = () => {
  if (renamingId.value && renamingValue.value.trim()) {
    const item = props.filteredSessions.find(s => s.id === renamingId.value)
    if (item) {
      emit('rename-session', item, renamingValue.value.trim())
    }
  }
  cancelRename()
}

const cancelRename = () => {
  renamingId.value = null
  renamingValue.value = ''
}

const handleRenameKeydown = (e: KeyboardEvent) => {
  e.stopPropagation()
  if (e.key === 'Enter') {
    e.preventDefault()
    confirmRename()
  } else if (e.key === 'Escape') {
    e.preventDefault()
    cancelRename()
  }
}

import { nextTick } from 'vue'

// ==================== 归档视图开关 ====================
/** 当前是否处于归档视图 */
const showArchivedView = ref(false)

const toggleArchivedView = () => {
  showArchivedView.value = !showArchivedView.value
}

// ==================== 会话分组 & 排序 ====================

/** 所有活跃会话（未归档） */
const activeSessions = computed(() =>
  props.filteredSessions.filter((s) => !s.is_archived),
)

/** 所有已归档会话 */
const archivedSessions = computed(() =>
  [...props.filteredSessions.filter((s) => s.is_archived)].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  ),
)

/** P6-8: Unified sorted active sessions (pinned first → updated_at desc, mixing single+group). */
const sortedActiveSessions = computed(() =>
  [...activeSessions.value].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  }),
)

// ==================== 辅助函数 ====================

const getAgentAvatar = (item: ConversationItem, agents: SidebarAgent[]) => {
  if (!item.agent_id) return ''
  const agent = agents.find((a) => a.id === item.agent_id)
  return agent?.avatar || ''
}

const getAgentTags = (item: ConversationItem, agents: SidebarAgent[]) => {
  if (!item.agent_id) return []
  const agent = agents.find((a) => a.id === item.agent_id)
  return agent?.capabilityTags || []
}

const groupConversationAvatarStyle = {
  background: 'linear-gradient(135deg, #3b82f6 0%, #6366f1 100%)',
  color: '#fff',
}

// ==================== ... 操作菜单 ====================
/** 当前展开的 ... 菜单对应会话 ID */
const activeMoreId = ref<string | null>(null)

const toggleMore = (id: string) => {
  activeMoreId.value = activeMoreId.value === id ? null : id
}

const doTogglePin = (item: ConversationItem) => {
  activeMoreId.value = null
  emit('toggle-pin', item)
}

const doToggleArchive = (item: ConversationItem) => {
  activeMoreId.value = null
  emit('toggle-archive', item)
}

const doDelete = (item: ConversationItem) => {
  activeMoreId.value = null
  emit('delete-session', item)
}

// 点击空白区域关闭菜单
document.addEventListener('click', () => {
  activeMoreId.value = null
})
</script>

<style scoped>

/* ==================== 侧边栏头部 ==================== */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.sidebar-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1e40af;
  letter-spacing: -0.01em;
}
/* ==================== 搜索框容器 ==================== */
.search-wrapper {
  flex-shrink: 0;
}

/* ==================== 工具栏 ==================== */
.toolbar-row {
  display: flex;
  gap: 10px;
}

/* 新建对话按钮 */
.new-session-btn {
  flex: 1;
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

.new-session-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s ease;
}

.new-session-btn:hover::before {
  left: 100%;
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

.new-session-btn:hover {
  transform: translateY(-2px);
  box-shadow:
    0 8px 20px rgba(59, 130, 246, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

/* 工具栏按钮 */
.toolbar-btn {
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(59, 130, 246, 0.15);
  background: rgba(255, 255, 255, 0.5);
  color: #64748b;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.3);
  color: #3b82f6;
}

/* ==================== 列表分区 ==================== */
.list-section {
  margin-bottom: 12px;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  margin-bottom: 10px;
  padding-left: 4px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* ==================== 会话列表 ==================== */
.conversation-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  padding-right: 4px;
  height: 90%;
}
.conversation-list::-webkit-scrollbar {
  width: 4px;
}

.conversation-list::-webkit-scrollbar-track {
  background: transparent;
}

.conversation-list::-webkit-scrollbar-thumb {
  background: rgba(59, 130, 246, 0.2);
  border-radius: 2px;
}

/* 加载与空状态 */
.loading-hint,
.empty-hint {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 40px 0;
  font-weight: 500;
}

/* ==================== 会话项 ==================== */
.conversation-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  width: 100%;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid transparent;
  text-align: left;
  background: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  position: relative;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.conversation-item:hover {
  background-color: #f0f4ff;
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.12);
  transform: translateX(2px);
  z-index: 1000;
}

.conversation-item.is-active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(99, 102, 241, 0.08));
  border-color: rgba(59, 130, 246, 0.25);
  z-index: 1;
  transform: translateX(4px);
  box-shadow:
    0 4px 12px rgba(59, 130, 246, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.conversation-copy {
  min-width: 0;
  flex: 1;
}

.conversation-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  flex-wrap: wrap;
}

.conversation-title {
  color: #1e293b;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 110px;
  overflow: hidden;
}

/* 置顶图标 */
.pin-icon {
  color:#00000059;
  font-size: 14px;
  flex-shrink: 0;
  animation: pin-pulse 2s ease-in-out infinite;
}

@keyframes pin-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}

/* 重命名输入框 */
.rename-input {
  flex: 1;
  min-width: 0;
  padding: 4px 8px;
  border: 1px solid #3b82f6;
  border-radius: 6px;
  background: #fff;
  color: #1e293b;
  font-size: 14px;
  font-weight: 600;
  outline: none;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
  transition: all 0.2s ease;
}

.rename-input:focus {
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25);
}

/* 模式标签 */
.mode-tag {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 6px;
  font-weight: 600;
}

.mode-tag.single {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(99, 102, 241, 0.1));
  color: #2563eb;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.mode-tag.group {
  background: linear-gradient(135deg, rgba(251, 146, 60, 0.15), rgba(249, 115, 22, 0.1));
  color: #ea580c;
  border: 1px solid rgba(251, 146, 60, 0.2);
}

.mode-tag.archived {
  background: rgba(100, 116, 139, 0.1);
  color: #64748b;
  border: 1px solid rgba(100, 116, 139, 0.15);
}

.conversation-snippet {
  color: #94a3b8;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 10px;
}

/* ==================== 更多操作菜单 ==================== */
.item-more-wrapper {
  position: relative;
  flex-shrink: 0;
}

.item-more-btn {
  padding: 6px 10px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 16px;
  cursor: pointer;
  opacity: 0;
  transition: all 0.2s ease;
}

.conversation-item:hover .item-more-btn {
  opacity: 1;
}

.item-more-btn:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
}

.item-more-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  z-index: 999;
  min-width: 140px;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(59, 130, 246, 0.1);
  border-radius: 14px;
  box-shadow:
    0 15px 35px rgba(59, 130, 246, 0.12),
    0 5px 15px rgba(0, 0, 0, 0.08);
  padding: 6px;
}

.more-action {
  display: block;
  position: relative;
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: transparent;
  color: #475569;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.15s ease;
  z-index: 999;
}

.more-action:hover {
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
  z-index: 999;
}

.more-action.danger {
  color: #ef4444;
}

.more-action.danger:hover {
  background: rgba(239, 68, 68, 0.08);
  color: #dc2626;
}

.more-divider {
  height: 1px;
  margin: 4px 0;
  background: rgba(59, 130, 246, 0.08);
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
</style>
