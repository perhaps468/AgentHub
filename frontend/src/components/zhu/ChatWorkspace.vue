<template>
  <main class="chat-shell">
    <ChatHeader
      :current-session="currentSession"
      :current-session-id="currentSessionId"
      :connection-state="connectionState"
      :reconnect-attempt="reconnectAttempt"
      :format-time="formatTime"
      :workspace="workspace"
      @open-left="$emit('open-left')"
      @retry="$emit('retry')"
    />

    <!-- M4: Orchestration Banner with Run Status -->
    <section v-if="activeRun" class="orchestration-banner">
      <div class="orchestration-banner__head">
        <div>
          <div class="orchestration-banner__title">编排计划</div>
          <!-- M5: Show aggregated run status with different styles -->
          <div :class="['orchestration-banner__meta', `status--${runStatusClass}`]">
            Run {{ activeRun.id.substring(0, 8) }} · {{ runStatusText }}
          </div>
        </div>
        <div class="orchestration-banner__badge">{{ activeTasks.length }} tasks</div>
      </div>
      <div v-if="activeRun.summary" class="orchestration-banner__summary">{{ activeRun.summary }}</div>
      <div v-if="activeTasks.length" class="task-grid">
        <article v-for="task in activeTasks" :key="task.id" class="task-card">
          <div class="task-card__row">
            <span class="task-card__sequence">#{{ task.sequence }}</span>
            <!-- M4: Task status with color coding -->
            <span :class="['task-card__status', `task-status--${getTaskStatusClass(task.status)}`]">
              {{ task.status }}
            </span>
          </div>
          <div class="task-card__title">{{ task.title }}</div>
          <div class="task-card__goal">{{ task.goal }}</div>
          <div class="task-card__agent">{{ task.assigned_agent_id }}</div>
          <!-- M4: Show pending changes count for this task -->
          <div v-if="getPendingChangesCount(task.id) > 0" class="task-card__pending">
            {{ getPendingChangesCount(task.id) }} 待确认变更
          </div>
        </article>
      </div>
    </section>

    <!-- M4: Multiple Task-Aware Pending Change Cards -->
    <section v-if="sessionPendingChanges.length > 0" class="pending-changes-panel">
      <div class="pending-changes-panel__header">待确认变更</div>
      <div class="pending-changes-list">
        <article
          v-for="change in sessionPendingChanges"
          :key="change.change_id"
          class="pending-change-card"
          :class="{ 'pending-change-card--loading': loadingChangeId === change.change_id }"
        >
          <!-- Task-aware header -->
          <div class="pending-change-card__header">
            <span v-if="change.task_id" class="pending-change-card__task">
              Task {{ getTaskSequence(change.task_id) }}
            </span>
            <span class="pending-change-card__operation">{{ change.operation }}</span>
            <span :class="['pending-change-card__status', `status--${change.status}`]">
              {{ change.status }}
            </span>
          </div>

          <!-- File info -->
          <div class="pending-change-card__path">{{ change.path }}</div>
          <div class="pending-change-card__diff" v-html="renderDiff(change.unified_diff)"></div>

          <!-- Action buttons (only for pending_confirmation) -->
          <div v-if="change.status === 'pending_confirmation'" class="pending-change-card__actions">
            <button
              class="btn-apply"
              :disabled="loadingChangeId === change.change_id"
              @click="handleApply(change.change_id)"
            >
              {{ loadingChangeId === change.change_id ? '应用中...' : '确认' }}
            </button>
            <button
              class="btn-reject"
              :disabled="loadingChangeId === change.change_id"
              @click="handleReject(change.change_id)"
            >
              {{ loadingChangeId === change.change_id ? '取消中...' : '取消' }}
            </button>
          </div>

          <!-- Result display (for applied/rejected/failed) -->
          <div v-else class="pending-change-card__result">
            <span v-if="change.status === 'applied'" class="result--applied">已应用</span>
            <span v-else-if="change.status === 'rejected'" class="result--rejected">已拒绝</span>
            <span v-else-if="change.status === 'failed'" class="result--failed">失败</span>
          </div>
        </article>
      </div>
    </section>

    <!-- M4: Orchestration Summary Messages -->
    <section v-if="orchestrationSummaries.length > 0" class="summary-messages-panel">
      <div v-for="summary in orchestrationSummaries" :key="summary.id" class="summary-message">
        <div class="summary-message__content">{{ summary.content }}</div>
      </div>
    </section>

    <section class="chat-stream-panel">
      <ChatShowArea
        ref="chatShow"
        :targetId="currentSessionId || ''"
        :isChatRecordLoading="isLoadingMessages"
        :isSendLoading="isSendLoading"
        :isComplete="false"
      />
    </section>

    <section class="chat-composer-panel">
      <ChatInputArea
        ref="chatRef"
        :sessionId="currentSessionId || ''"
        :disabled="!currentSessionId"
        @send="$emit('send', $event)"
      />
    </section>
  </main>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'

import ChatInputArea from '../../veiws/Chat-input-area.vue'
import ChatShowArea from '../../veiws/Chat-show-area.vue'
import { useSessionStore } from '../../store/module/useSessionStore'
import type { ConversationItem, PendingChange, Workspace } from '../../types/agenthub'
import type { ConnectionState } from '../../utils/ws-client'
import ChatHeader from './ChatHeader.vue'

const props = defineProps<{
  currentSession: ConversationItem | null | undefined
  currentSessionId: string
  connectionState: ConnectionState
  reconnectAttempt: number
  isLoadingMessages: boolean
  isSendLoading: boolean
  formatTime: (iso: string) => string
  workspace: Workspace | null
}>()

const emit = defineEmits<{
  (e: 'open-left'): void
  (e: 'retry'): void
  (e: 'send', content: string): void
}>()

const sessionStore = useSessionStore()
const activeRun = computed(() => sessionStore.activeRun)
const activeTasks = computed(() => sessionStore.activeTasks)

// M4: Get pending changes from stream state
const sessionPendingChanges = computed(() => {
  return sessionStore.streamState.getPendingChanges(props.currentSessionId || '')
})

// M4: Track loading state for individual changes
const loadingChangeId = ref<string | null>(null)

// M4: Run status display text
const runStatusText = computed(() => {
  if (!activeRun.value) return ''
  const statusMap: Record<string, string> = {
    completed: '全部任务完成',
    partial: '部分任务完成',
    cancelled: '任务已取消',
    failed: '任务执行失败',
    running: '执行中',
    planned: '已计划',
    waiting_confirmation: '等待确认',
  }
  return statusMap[activeRun.value.status] || activeRun.value.status
})

// M4: Run status CSS class
const runStatusClass = computed(() => {
  if (!activeRun.value) return ''
  return activeRun.value.status
})

// M4: Get task status CSS class
function getTaskStatusClass(status: string): string {
  const statusMap: Record<string, string> = {
    completed: 'success',
    partial: 'warning',
    cancelled: 'muted',
    failed: 'error',
    running: 'info',
    waiting_confirmation: 'warning',
    planned: 'muted',
  }
  return statusMap[status] || 'muted'
}

// M4: Get pending changes count for a task
function getPendingChangesCount(taskId: string): number {
  return sessionPendingChanges.value.filter((c) => c.task_id === taskId).length
}

// M4: Get task sequence by ID
function getTaskSequence(taskId: string): number {
  const task = activeTasks.value.find((t) => t.id === taskId)
  return task?.sequence || 0
}

// M4: Render diff with basic HTML formatting
function renderDiff(diff: string): string {
  if (!diff) return ''
  // Simple diff rendering - replace newlines with <br>
  return diff
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
    .replace(/^\+ /gm, '<span class="diff-add">+ </span>')
    .replace(/^- /gm, '<span class="diff-remove">- </span>')
}

// M4: Handle apply action
async function handleApply(changeId: string) {
  if (loadingChangeId.value) return
  loadingChangeId.value = changeId

  try {
    const { applyPendingChange } = await import('@/api/modules/pendingChanges')
    await applyPendingChange({ change_id: changeId, session_id: props.currentSessionId || '' })
    // State will be updated via WebSocket event
  } catch (error) {
    console.error('Apply failed:', error)
  } finally {
    loadingChangeId.value = null
  }
}

// M4: Handle reject action
async function handleReject(changeId: string) {
  if (loadingChangeId.value) return
  loadingChangeId.value = changeId

  try {
    const { rejectPendingChange } = await import('@/api/modules/pendingChanges')
    await rejectPendingChange({ change_id: changeId, session_id: props.currentSessionId || '' })
    // State will be updated via WebSocket event
  } catch (error) {
    console.error('Reject failed:', error)
  } finally {
    loadingChangeId.value = null
  }
}

// M4: Get orchestration summary messages
const orchestrationSummaries = computed(() => {
  const messages = sessionStore.currentMessages
  return messages.filter((msg) => {
    const metadata = (msg as any).metadata || {}
    return metadata.is_orchestration_summary === true
  })
})
</script>

<style scoped>
.chat-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  overflow: hidden;
  background: transparent;
}

/* M4: Orchestration Banner */
.orchestration-banner {
  margin: 0 4px 10px;
  border: 1px solid rgba(59, 130, 246, 0.16);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.88));
  padding: 14px 16px;
}

.orchestration-banner__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.orchestration-banner__title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.orchestration-banner__meta {
  font-size: 12px;
  color: #475569;
}

.orchestration-banner__meta.status--completed { color: #059669; }
.orchestration-banner__meta.status--partial { color: #d97706; }
.orchestration-banner__meta.status--cancelled { color: #64748b; }
.orchestration-banner__meta.status--failed { color: #dc2626; }
.orchestration-banner__meta.status--running { color: #2563eb; }

.orchestration-banner__badge {
  border-radius: 999px;
  padding: 6px 10px;
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
  font-size: 12px;
  font-weight: 600;
}

.orchestration-banner__summary {
  margin-top: 8px;
  color: #475569;
  font-size: 12px;
}

.task-grid {
  margin-top: 12px;
  display: grid;
  gap: 10px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.task-card {
  border-radius: 14px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.task-card__row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.task-card__sequence,
.task-card__status {
  font-size: 12px;
  color: #2563eb;
  font-weight: 600;
}

.task-card__status.task-status--success { color: #059669; }
.task-card__status.task-status--warning { color: #d97706; }
.task-card__status.task-status--error { color: #dc2626; }
.task-card__status.task-status--muted { color: #94a3b8; }
.task-card__status.task-status--info { color: #2563eb; }

.task-card__title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 6px;
}

.task-card__goal,
.task-card__agent {
  color: #475569;
  font-size: 12px;
}

.task-card__pending {
  margin-top: 8px;
  padding: 4px 8px;
  background: rgba(217, 119, 6, 0.12);
  color: #d97706;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

/* M4: Pending Changes Panel */
.pending-changes-panel {
  margin: 0 4px 10px;
  border: 1px solid rgba(217, 119, 6, 0.2);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255, 252, 245, 0.96), rgba(254, 243, 228, 0.88));
  padding: 14px 16px;
}

.pending-changes-panel__header {
  font-size: 14px;
  font-weight: 700;
  color: #92400e;
  margin-bottom: 12px;
}

.pending-changes-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pending-change-card {
  border-radius: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(217, 119, 6, 0.15);
  transition: opacity 0.2s;
}

.pending-change-card--loading {
  opacity: 0.7;
  pointer-events: none;
}

.pending-change-card__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.pending-change-card__task {
  padding: 2px 8px;
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.pending-change-card__operation {
  font-size: 12px;
  color: #475569;
  font-weight: 500;
}

.pending-change-card__status {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.pending-change-card__status.status--pending_confirmation {
  background: rgba(217, 119, 6, 0.12);
  color: #d97706;
}

.pending-change-card__status.status--applied {
  background: rgba(5, 150, 105, 0.12);
  color: #059669;
}

.pending-change-card__status.status--rejected {
  background: rgba(100, 116, 139, 0.12);
  color: #64748b;
}

.pending-change-card__status.status--failed {
  background: rgba(220, 38, 38, 0.12);
  color: #dc2626;
}

.pending-change-card__path {
  font-size: 13px;
  font-family: 'JetBrains Mono', monospace;
  color: #1e293b;
  margin-bottom: 8px;
}

.pending-change-card__diff {
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
  background: rgba(0, 0, 0, 0.03);
  border-radius: 8px;
  padding: 8px;
  max-height: 120px;
  overflow-y: auto;
  margin-bottom: 12px;
}

.pending-change-card__diff :deep(.diff-add) { color: #059669; }
.pending-change-card__diff :deep(.diff-remove) { color: #dc2626; }

.pending-change-card__actions {
  display: flex;
  gap: 8px;
}

.btn-apply,
.btn-reject {
  flex: 1;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-apply {
  background: #059669;
  color: white;
}

.btn-apply:hover:not(:disabled) {
  background: #047857;
}

.btn-reject {
  background: transparent;
  color: #64748b;
  border: 1px solid #cbd5e1;
}

.btn-reject:hover:not(:disabled) {
  background: #f1f5f9;
}

.btn-apply:disabled,
.btn-reject:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pending-change-card__result {
  text-align: center;
  padding: 8px;
  font-size: 13px;
  font-weight: 600;
}

.result--applied { color: #059669; }
.result--rejected { color: #64748b; }
.result--failed { color: #dc2626; }

/* M4: Summary Messages Panel */
.summary-messages-panel {
  margin: 0 4px 10px;
}

.summary-message {
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(139, 92, 246, 0.08));
  border-radius: 12px;
  border-left: 4px solid #6366f1;
}

.summary-message__content {
  font-size: 13px;
  color: #334155;
  white-space: pre-wrap;
}

/* Original Chat Panels */
.chat-stream-panel {
  min-height: 0;
  flex: 1;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 16px;
  margin: 0 4px;
  display: flex;
  flex-direction: column;
}

.chat-composer-panel {
  border-top: none;
  background: transparent;
  padding-top: 8px;
}
</style>
