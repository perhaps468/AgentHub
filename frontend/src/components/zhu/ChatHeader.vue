<template>
  <header class="chat-header">
    <div class="chat-header-main">
      <div class="chat-header-left">
        <avatar :info="{ name: currentSession?.title, avatar: '' }" :size="38" />
      </div>
      <div class="chat-header-right">
        <h2>{{ currentSession?.title || '选择或新建会话' }}</h2>
        <div >
        <ConnectionStatus
          v-if="currentSessionId"
          :state="connectionState"
          :reconnectAttempt="reconnectAttempt"
          @retry="$emit('retry')"
        />
      </div>
        <div v-if="workspace" class="workspace-badge" :title="workspace.root_path">
          <span class="workspace-icon">&#128193;</span>
          <span class="workspace-name">{{ workspace.name || workspaceRootName }}</span>
        </div>
      </div>
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

.chat-header h2 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.2;
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
  flex-direction: column;
  gap: 5px;
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
