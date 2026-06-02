<template>
  <header class="chat-header">
    <div class="chat-header-main">
      <button class="header-icon mobile-only" type="button" @click="$emit('open-left')">☰</button>
      <div>
        <p class="chat-header-kicker">
          {{ currentSession?.mode === 'group' ? '群聊协作' : '单聊会话' }}
        </p>
        <h2>{{ currentSession?.title || '选择或新建会话' }}</h2>
        <p class="chat-header-subtitle">
          {{ currentSession ? `创建于 ${formatTime(currentSession.created_at)}` : '点击左侧新建会话开始聊天' }}
        </p>
        <div v-if="workspace" class="workspace-badge" :title="workspace.root_path">
          <span class="workspace-icon">&#128193;</span>
          <span class="workspace-name">{{ workspace.name || workspaceRootName }}</span>
        </div>
      </div>
    </div>
    <div class="chat-header-right">
      <!-- P6-9: Group member status display -->
      <div v-if="currentSession?.mode === 'group' && currentSession.members?.length" class="group-members">
        <div
          v-for="member in currentSession.members"
          :key="member.id"
          class="member-chip"
          :class="{ 'is-primary': member.is_primary }"
        >
          <span class="member-status-dot"></span>
          <span class="member-name">{{ member.is_primary ? '主Agent' : `Agent` }}</span>
          <span class="member-health">{{ member.health_status === 'connected' ? '已连接' : member.health_status }}</span>
        </div>
      </div>
      <ConnectionStatus
        v-if="currentSessionId"
        :state="connectionState"
        :reconnectAttempt="reconnectAttempt"
        @retry="$emit('retry')"
      />
    </div>
  </header>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import ConnectionStatus from '../ConnectionStatus.vue'
import type { ConversationItem, Workspace } from '../../types/agenthub'
import type { ConnectionState } from '../../utils/ws-client'

const props = defineProps<{
  currentSession: ConversationItem | null | undefined
  currentSessionId: string
  connectionState: ConnectionState
  reconnectAttempt: number
  formatTime: (iso: string) => string
  workspace: Workspace | null
}>()

defineEmits<{
  (e: 'open-left'): void
  (e: 'retry'): void
}>()

const workspaceRootName = computed(() => {
  if (!props.workspace) return ''
  const parts = props.workspace.root_path.split(/[/\\]/)
  return parts[parts.length - 1] || props.workspace.root_path
})
</script>

<style scoped>
/* ==================== 聊天头部 ==================== */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 72px;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
  background: rgba(255, 255, 255, 0.5);
}

.chat-header-main {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.chat-header-kicker {
  margin: 0 0 4px;
  color: #94a3b8;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}

.chat-header h2 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.2;
}

.chat-header-subtitle {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
}

.workspace-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
  font-size: 11px;
  font-weight: 500;
}

.workspace-icon {
  font-size: 12px;
}

.workspace-name {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* P6-9: Group member chips */
.chat-header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.group-members {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.member-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.06);
  border: 1px solid rgba(59, 130, 246, 0.12);
  font-size: 11px;
  font-weight: 500;
  transition: all 0.2s ease;

  &.is-primary {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(99, 102, 241, 0.08));
    border-color: rgba(59, 130, 246, 0.25);
  }
}

.member-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 4px rgba(34, 197, 94, 0.4);
  flex-shrink: 0;
}

.member-name {
  color: #64748b;
  font-weight: 600;

  .is-primary & {
    color: #3b82f6;
  }
}

.member-health {
  color: #94a3b8;
  font-size: 10px;
}

.header-icon {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(59, 130, 246, 0.08);
  color: #64748b;
  font-size: 16px;
  transition: all 0.25s ease;
}

.header-icon:hover {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(99, 102, 241, 0.1));
  color: #3b82f6;
  transform: scale(1.05);
}

.mobile-only {
  display: none;
}

@media (max-width: 900px) {
  .mobile-only {
    display: inline-flex;
  }
}
</style>
