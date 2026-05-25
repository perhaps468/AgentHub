<template>
  <!-- 仅当消息面板激活时渲染 -->
  <template v-if="activePanel === 'messages'">
    <div class="sidebar-header">
      <div>
        <h1>消息列表</h1>
      </div>
      <span class="version-tag">v1.1.3</span>
    </div>

    <!-- 搜索框 -->
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

      <!-- 隐藏归档模式：显示未归档会话 -->
      <template v-if="!showArchivedView">
        <!-- Agent 单聊区（未归档） -->
        <div v-if="pinnedAgentSessions.length > 0" class="list-section">
          <div class="section-title">置顶</div>
          <button
            v-for="item in pinnedAgentSessions"
            :key="item.id"
            class="conversation-item"
            :class="{ 'is-active': currentSessionId === item.id }"
            type="button"
            @click="$emit('select-session', item)"
          >
            <avatar
              :info="{ name: item.title || '会话', avatar: getAgentAvatar(item, agents) }"
              size="38px"
            />
            <div class="conversation-copy">
              <div class="conversation-title-row">
                <span class="conversation-title">{{ item.title || '未命名会话' }}</span>
                <span class="mode-tag single">单聊</span>
                <dot_hint v-if="item.is_pinned" text="置顶" />
              </div>
              <div v-if="getAgentTags(item, agents).length > 0" class="capability-tags">
                <span
                  v-for="tag in getAgentTags(item, agents).slice(0, 3)"
                  :key="tag"
                  class="capability-tag"
                >{{ tag }}</span>
              </div>
              <div class="conversation-snippet">{{ formatTime(item.updated_at) }}</div>
            </div>
            <!-- 操作按钮 ... -->
            <div class="item-more-wrapper">
              <button class="item-more-btn" type="button" @click.stop="toggleMore(item.id)">⋯</button>
              <div v-if="activeMoreId === item.id" class="item-more-menu" @click.stop>
                <button class="more-action danger" type="button" @click="doDelete(item)">删除会话</button>
                <div class="more-divider" />
                <button class="more-action" type="button" @click="doTogglePin(item)">
                  {{ item.is_pinned ? '取消置顶' : '置顶' }}
                </button>
                <div class="more-divider" />
                <button class="more-action" type="button" @click="doToggleArchive(item)">归档</button>
              </div>
            </div>
          </button>
        </div>

        <div v-if="unpinnedAgentSessions.length > 0" class="list-section">
          <div v-if="pinnedAgentSessions.length > 0" class="section-title">Agent 单聊</div>
          <button
            v-for="item in unpinnedAgentSessions"
            :key="item.id"
            class="conversation-item"
            :class="{ 'is-active': currentSessionId === item.id }"
            type="button"
            @click="$emit('select-session', item)"
          >
            <avatar
              :info="{ name: item.title || '会话', avatar: getAgentAvatar(item, agents) }"
              size="38px"
            />
            <div class="conversation-copy">
              <div class="conversation-title-row">
                <span class="conversation-title">{{ item.title || '未命名会话' }}</span>
                <span class="mode-tag single">单聊</span>
              </div>
              <div v-if="getAgentTags(item, agents).length > 0" class="capability-tags">
                <span
                  v-for="tag in getAgentTags(item, agents).slice(0, 3)"
                  :key="tag"
                  class="capability-tag"
                >{{ tag }}</span>
              </div>
              <div class="conversation-snippet">{{ formatTime(item.updated_at) }}</div>
            </div>
            <div class="item-more-wrapper">
              <button class="item-more-btn" type="button" @click.stop="toggleMore(item.id)">⋯</button>
              <div v-if="activeMoreId === item.id" class="item-more-menu" @click.stop>
                <button class="more-action danger" type="button" @click="doDelete(item)">删除会话</button>
                <div class="more-divider" />
                <button class="more-action" type="button" @click="doTogglePin(item)">置顶</button>
                <div class="more-divider" />
                <button class="more-action" type="button" @click="doToggleArchive(item)">归档</button>
              </div>
            </div>
          </button>
        </div>

        <!-- 群聊区（未归档） -->
        <div v-if="pinnedGroupSessions.length > 0" class="list-section">
          <div class="section-title">群聊 · 置顶</div>
          <button
            v-for="item in pinnedGroupSessions"
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
            <div class="item-more-wrapper">
              <button class="item-more-btn" type="button" @click.stop="toggleMore(item.id)">⋯</button>
              <div v-if="activeMoreId === item.id" class="item-more-menu" @click.stop>
                <button class="more-action danger" type="button" @click="doDelete(item)">删除会话</button>
                <div class="more-divider" />
                <button class="more-action" type="button" @click="doTogglePin(item)">取消置顶</button>
                <div class="more-divider" />
                <button class="more-action" type="button" @click="doToggleArchive(item)">归档</button>
              </div>
            </div>
          </button>
        </div>

        <div v-if="unpinnedGroupSessions.length > 0" class="list-section">
          <div v-if="pinnedGroupSessions.length > 0" class="section-title">群聊</div>
          <button
            v-for="item in unpinnedGroupSessions"
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
            <div class="item-more-wrapper">
              <button class="item-more-btn" type="button" @click.stop="toggleMore(item.id)">⋯</button>
              <div v-if="activeMoreId === item.id" class="item-more-menu" @click.stop>
                <button class="more-action danger" type="button" @click="doDelete(item)">删除会话</button>
                <div class="more-divider" />
                <button class="more-action" type="button" @click="doTogglePin(item)">置顶</button>
                <div class="more-divider" />
                <button class="more-action" type="button" @click="doToggleArchive(item)">归档</button>
              </div>
            </div>
          </button>
        </div>
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
              <span class="conversation-title" style="opacity: 0.6">{{ item.title || '未命名会话' }}</span>
              <span class="mode-tag archived">已归档</span>
            </div>
            <div class="conversation-snippet">{{ formatTime(item.updated_at) }}</div>
          </div>
          <div class="item-more-wrapper">
            <button class="item-more-btn" type="button" @click.stop="toggleMore(item.id)">⋯</button>
            <div v-if="activeMoreId === item.id" class="item-more-menu" @click.stop>
              <button class="more-action danger" type="button" @click="doDelete(item)">删除会话</button>
              <div class="more-divider" />
              <button class="more-action" type="button" @click="doToggleArchive(item)">取消归档</button>
            </div>
          </div>
        </button>
      </template>

      <!-- 空状态 -->
      <div
        v-if="!isLoading && !showArchivedView && allActiveSessions.length === 0"
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

const props = defineProps<{
  activePanel: SidebarPanel
  searchValue: string
  filteredSessions: ConversationItem[]
  currentSessionId: string
  isLoading: boolean
  agents: SidebarAgent[]
  formatTime: (iso: string) => string
}>()

const emit = defineEmits<{
  (e: 'update:searchValue', value: string): void
  (e: 'new-session'): void
  (e: 'select-session', item: ConversationItem): void
  (e: 'toggle-pin', item: ConversationItem): void
  (e: 'toggle-archive', item: ConversationItem): void
  (e: 'delete-session', item: ConversationItem): void
}>()

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

/** 活跃会话中所有单聊（置顶优先 → 更新时间倒序） */
const sortedAgentSessions = computed(() =>
  [...activeSessions.value.filter((s) => s.mode === 'single')].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  }),
)

/** 活跃会话中所有群聊（置顶优先 → 更新时间倒序） */
const sortedGroupSessions = computed(() =>
  [...activeSessions.value.filter((s) => s.mode === 'group')].sort((a, b) => {
    if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
  }),
)

const pinnedAgentSessions = computed(() => sortedAgentSessions.value.filter((s) => s.is_pinned))
const unpinnedAgentSessions = computed(() => sortedAgentSessions.value.filter((s) => !s.is_pinned))
const pinnedGroupSessions = computed(() => sortedGroupSessions.value.filter((s) => s.is_pinned))
const unpinnedGroupSessions = computed(() => sortedGroupSessions.value.filter((s) => !s.is_pinned))
const allActiveSessions = computed(() => activeSessions.value)

// ==================== 辅助函数 ====================

const getAgentAvatar = (item: ConversationItem, agents: SidebarAgent[]) => {
  const agent = agents.find((a) => item.title?.includes(a.name))
  return agent?.avatar || ''
}

const getAgentTags = (item: ConversationItem, agents: SidebarAgent[]) => {
  const agent = agents.find((a) => item.title?.includes(a.name))
  return agent?.capabilityTags || []
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
  transition: background 0.15s;
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

/* 列表分区 */
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
  min-height: 85%;
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
  background: #e3f2fd;
  border-color: #1976d2;
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

.mode-tag.archived {
  background: #f5f5f5;
  color: #999;
}

.conversation-snippet {
  color: #999;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ==================== ... 操作菜单 ==================== */
.item-more-wrapper {
  position: relative;
  flex-shrink: 0;
}

.item-more-btn {
  padding: 2px 6px;
  border-radius: 4px;
  border: none;
  background: transparent;
  color: #999;
  font-size: 16px;
  cursor: pointer;
  line-height: 1;
  opacity: 0;
  transition: opacity 0.15s;
}

.conversation-item:hover .item-more-btn {
  opacity: 1;
}

.item-more-btn:hover {
  background: #e8e8e8;
  color: #333;
}

.item-more-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 4px);
  z-index: 200;
  min-width: 120px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  padding: 4px 0;
}

.more-action {
  display: block;
  width: 100%;
  padding: 8px 14px;
  border: none;
  background: transparent;
  color: #333;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s;
}

.more-action:hover {
  background: #f5f5f5;
}

.more-action.danger {
  color: #e53935;
}

.more-action.danger:hover {
  background: #ffebee;
}

.more-divider {
  height: 1px;
  margin: 4px 0;
  background: #f0f0f0;
}

/* 能力标签 */
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
</style>
