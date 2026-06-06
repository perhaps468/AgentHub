<template>
  <header class="chat-header">
    <div class="chat-header-main">
      <div class="chat-header-left">
        <avatar :info="{ name: currentSession?.title, avatar: currentAgentAvatar }" size="20px" />
      </div>

      <div ref="summaryRootRef" class="chat-header-right">
        <div class="chat-title-row">
          <div class="chat-title-copy">
            <h2>{{ currentSession?.title || '选择或新建会话' }}</h2>
            <div v-if="workspace" class="workspace-badge" :title="workspace.root_path">
              <span class="workspace-icon">📁</span>
              <span class="workspace-name">{{ workspace.name || workspaceRootName }}</span>
            </div>
          </div>

          <button
            v-if="summaryAgents.length > 0"
            type="button"
            class="agent-summary-trigger"
            data-testid="agent-summary-trigger"
            @click="togglePanel"
          >
            <span class="agent-summary-avatars">
              <span
                v-for="agent in visibleAgents"
                :key="agent.id"
                class="agent-summary-avatar"
                :data-agent-id="agent.id"
                data-testid="agent-summary-avatar"
              >
                <img v-if="agent.avatar" :src="agent.avatar" :alt="agent.name" />
                <span v-else>{{ agent.name.slice(0, 1) }}</span>
                <span class="agent-summary-status" :class="`status-${agent.status}`"></span>
              </span>
            </span>
            <span class="agent-summary-meta compact">
              <span class="agent-summary-meta-dot" :class="`status-${summaryMetaTone}`"></span>
              <span>{{ summaryStatusText }}</span>
            </span>
            <span class="agent-summary-tail">
              <span v-if="hiddenCount > 0" class="agent-summary-extra">+{{ hiddenCount }}</span>
              <span v-else class="agent-summary-extra chevron">{{ isPanelOpen ? '^' : 'v' }}</span>
            </span>
          </button>
        </div>

        <div v-if="isPanelOpen" class="agent-panel" data-testid="agent-panel">
          <button
            v-for="agent in summaryAgents"
            :key="agent.id"
            type="button"
            class="agent-panel-item"
            :class="{ 'is-selected': selectedAgentIds.has(agent.id) }"
            :data-testid="`agent-panel-item-${agent.id}`"
            @click="handlePickAgent(agent)"
          >
            <span class="agent-panel-avatar">
              <img v-if="agent.avatar" :src="agent.avatar" :alt="agent.name" />
              <span v-else>{{ agent.name.slice(0, 1) }}</span>
            </span>
            <span class="agent-panel-copy">
              <span class="agent-panel-topline">
                <span class="agent-panel-name">{{ agent.name }}</span>
                <span v-if="agent.isPrimary" class="agent-panel-badge">Primary</span>
                <span v-if="selectedAgentIds.has(agent.id)" class="agent-panel-badge selected">Selected</span>
              </span>
              <span class="agent-panel-meta">
                {{ agent.status }}
                <span v-if="agent.role"> · {{ agent.role }}</span>
              </span>
            </span>
          </button>
        </div>

        <ConnectionStatus
          v-if="currentSessionId"
          :state="connectionState"
          :reconnectAttempt="reconnectAttempt"
          @retry="$emit('retry')"
        />
      </div>
    </div>
  </header>
</template>

<script lang="ts" setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import ConnectionStatus from '../ConnectionStatus.vue'
import type {
  ComposerAgent,
  ConversationItem,
  SessionMember,
  SessionMemberStatus,
  Workspace,
} from '../../types/agenthub'
import type { ConnectionState } from '../../utils/ws-client'
import avatar from '../../veiws/img/avatar.vue'

type HeaderAgentSummaryItem = {
  id: string
  name: string
  avatar?: string | null
  status: SessionMemberStatus
  role?: string | null
  isPrimary: boolean
}

const props = defineProps<{
  currentSession: ConversationItem | null | undefined
  currentSessionId: string
  connectionState: ConnectionState
  reconnectAttempt: number
  formatTime: (iso: string) => string
  workspace: Workspace | null
  selectedAgents?: ComposerAgent[]
}>()

const emit = defineEmits<{
  (e: 'open-left'): void
  (e: 'retry'): void
  (e: 'pick-agent', agent: ComposerAgent): void
}>()

const isPanelOpen = ref(false)
const summaryRootRef = ref<HTMLElement | null>(null)

const statusRank: Record<SessionMemberStatus, number> = {
  online: 0,
  busy: 1,
  offline: 2,
}

const workspaceRootName = computed(() => {
  if (!props.workspace) return ''
  const parts = props.workspace.root_path.split(/[/\\]/)
  return parts[parts.length - 1] || props.workspace.root_path
})

const summaryAgents = computed<HeaderAgentSummaryItem[]>(() => {
  const members = props.currentSession?.members ?? []

  return members
    .filter((member): member is SessionMember => member.member_type === 'agent')
    .map((member) => ({
      id: member.member_id,
      name: member.agent_name || member.member_id,
      avatar: member.agent_avatar,
      status: member.status,
      role: member.agent_role,
      isPrimary: Boolean(member.is_primary),
    }))
    .sort((left, right) => {
      const rankDiff = statusRank[left.status] - statusRank[right.status]
      if (rankDiff !== 0) return rankDiff
      return left.name.localeCompare(right.name)
    })
})

const visibleAgents = computed(() => summaryAgents.value.slice(0, 3))

const hiddenCount = computed(() => Math.max(summaryAgents.value.length - visibleAgents.value.length, 0))

const summaryStatusText = computed(() => {
  const counts = summaryAgents.value.reduce(
    (acc, agent) => {
      acc[agent.status] += 1
      return acc
    },
    { online: 0, busy: 0, offline: 0 },
  )

  if (counts.busy > 0) {
    return `${counts.online} online · ${counts.busy} busy`
  }
  if (counts.offline > 0) {
    return `${counts.online} online · ${counts.offline} offline`
  }
  return `${counts.online} online`
})

const summaryMetaTone = computed<SessionMemberStatus>(() => {
  if (summaryAgents.value.some((agent) => agent.status === 'busy')) return 'busy'
  if (summaryAgents.value.some((agent) => agent.status === 'online')) return 'online'
  return 'offline'
})

const selectedAgentIds = computed(() => new Set((props.selectedAgents ?? []).map((agent) => agent.id)))

const currentAgentAvatar = computed(() => {
  const primary = summaryAgents.value.find((agent) => agent.isPrimary)
  return primary?.avatar || summaryAgents.value[0]?.avatar || ''
})

function handleDocumentPointerDown(event: PointerEvent) {
  const target = event.target
  if (!(target instanceof Node)) return
  const root = summaryRootRef.value
  if (!root) return
  if (!root.contains(target)) {
    setPanelOpen(false)
  }
}

watch(
  () => props.currentSessionId,
  () => {
    setPanelOpen(false)
  },
)

function updateDocumentListener(enabled: boolean) {
  if (typeof document === 'undefined') return
  if (enabled) {
    document.addEventListener('pointerdown', handleDocumentPointerDown)
    return
  }
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
}

function setPanelOpen(open: boolean) {
  if (isPanelOpen.value === open) return
  isPanelOpen.value = open
  updateDocumentListener(open)
}

function togglePanel() {
  setPanelOpen(!isPanelOpen.value)
}

onBeforeUnmount(() => {
  updateDocumentListener(false)
})

function handlePickAgent(agent: HeaderAgentSummaryItem) {
  if (selectedAgentIds.value.has(agent.id)) {
    setPanelOpen(false)
    return
  }

  emit('pick-agent', {
    id: agent.id,
    name: agent.name,
    avatar: agent.avatar ?? null,
    status: agent.status,
    role: agent.role ?? null,
  })
  setPanelOpen(false)
}
</script>

<style scoped>
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 64px;
  padding: 14px 24px;
  border-bottom: 1px solid rgba(59, 130, 246, 0.08);
  background: rgba(255, 255, 255, 0.5);
}

.chat-header-main {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  width: 100%;
}

.chat-header-right {
  position: relative;
  display: flex;
  flex: 1;
  min-width: 0;
  flex-direction: column;
  gap: 8px;
}

.chat-title-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.chat-title-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
}

.chat-header h2 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.2;
  min-width: 0;
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
  width: fit-content;
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

.agent-summary-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: min(320px, 100%);
  margin-left: auto;
  padding: 7px 10px;
  border-radius: 16px;
  border: 1px solid rgba(59, 130, 246, 0.12);
  background: rgba(248, 250, 252, 0.92);
  cursor: pointer;
}

.agent-summary-avatars {
  display: inline-flex;
  align-items: center;
  padding-left: 10px;
  flex-shrink: 0;
}

.agent-summary-avatar {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-left: -10px;
  overflow: hidden;
  border: 2px solid #fff;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.12);
  color: #1e293b;
  font-size: 11px;
  font-weight: 700;
}

.agent-summary-avatar img,
.agent-panel-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.agent-summary-status {
  position: absolute;
  right: -1px;
  bottom: -1px;
  width: 9px;
  height: 9px;
  border: 2px solid #fff;
  border-radius: 999px;
  background: #22c55e;
}

.status-busy {
  background: #f59e0b;
}

.status-offline {
  background: #94a3b8;
}

.agent-panel-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  text-align: left;
}

.agent-summary-meta,
.agent-panel-meta {
  color: #64748b;
  font-size: 12px;
}

.agent-summary-meta.compact {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  white-space: nowrap;
}

.agent-summary-meta-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #22c55e;
  flex-shrink: 0;
}

.agent-summary-tail {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.agent-summary-extra {
  color: #475569;
  font-size: 12px;
  font-weight: 700;
}

.chevron {
  font-size: 12px;
  line-height: 1;
}

.agent-panel {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: min(360px, 100%);
  padding: 10px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.14);
}

.agent-panel-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px;
  border-radius: 14px;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.agent-panel-item.is-selected {
  background: rgba(59, 130, 246, 0.08);
}

.agent-panel-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  overflow: hidden;
  border-radius: 12px;
  background: rgba(59, 130, 246, 0.1);
  color: #1e293b;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.agent-panel-topline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.agent-panel-name {
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
}

.agent-panel-badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.12);
  color: #2563eb;
  font-size: 11px;
  font-weight: 600;
}

.agent-panel-badge.selected {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}
</style>
