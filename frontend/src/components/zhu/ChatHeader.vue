<template>
  <header class="chat-header">
    <div class="chat-header-main">
      <div class="chat-header-left">
        <div class="session-avatar-shell">
          <avatar :info="{ name: currentSession?.title, avatar: currentAgentAvatar }" size="20px" />
        </div>

        <div class="chat-header-copy">
          <div class="chat-header-title-row">
            <h2>{{ currentSession?.title || '选择或新建会话' }}</h2>
            <span v-if="currentSession?.mode === 'group'" class="session-mode-badge">Group</span>
          </div>

          <div class="chat-header-meta-row">
            <ConnectionStatus
              v-if="currentSessionId"
              :state="connectionState"
              :reconnectAttempt="reconnectAttempt"
              @retry="$emit('retry')"
            />

            <div v-if="workspace" class="workspace-badge" :title="workspace.root_path">
              <span class="workspace-icon">&#128193;</span>
              <span class="workspace-name">{{ workspace.name || workspaceRootName }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="summaryAgents.length > 0" ref="summaryRootRef" class="agent-summary-shell">
        <button
          class="agent-summary-trigger"
          data-testid="agent-summary-trigger"
          type="button"
          @click="togglePanel"
        >
          <div class="agent-summary-avatars">
            <div
              v-for="agent in visibleAgents"
              :key="agent.id"
              class="agent-summary-avatar"
              :data-agent-id="agent.id"
              :title="agent.name"
              data-testid="agent-summary-avatar"
            >
              <img v-if="agent.avatar" :src="agent.avatar" :alt="agent.name" />
              <span v-else>{{ agent.name.slice(0, 1) }}</span>
            </div>
            <div v-if="hiddenCount > 0" class="agent-summary-avatar more">+{{ hiddenCount }}</div>
          </div>
          <div class="agent-summary-copy">
            <span class="agent-summary-title">协作成员</span>
            <span class="agent-summary-meta compact" :class="summaryMetaTone">
              {{ summaryStatusText }}
            </span>
          </div>
        </button>

        <div v-if="isPanelOpen" class="agent-panel" data-testid="agent-panel">
          <button
            v-for="agent in summaryAgents"
            :key="agent.id"
            class="agent-panel-item"
            :class="{ selected: selectedAgentIds.has(agent.id) }"
            :data-testid="`agent-panel-item-${agent.id}`"
            type="button"
            @click="handlePickAgent(agent)"
          >
            <div class="agent-panel-avatar">
              <img v-if="agent.avatar" :src="agent.avatar" :alt="agent.name" />
              <span v-else>{{ agent.name.slice(0, 1) }}</span>
            </div>
            <div class="agent-panel-copy">
              <div class="agent-panel-name-row">
                <span class="agent-panel-name">{{ agent.name }}</span>
                <span v-if="agent.isPrimary" class="agent-panel-badge">Primary</span>
                <span v-if="selectedAgentIds.has(agent.id)" class="agent-panel-badge muted">Selected</span>
              </div>
              <div class="agent-panel-meta">
                <span class="agent-panel-status" :class="agent.status">{{ agent.status }}</span>
                <span v-if="agent.role">{{ agent.role }}</span>
              </div>
            </div>
          </button>
        </div>
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
  position: relative;
  z-index: 20;
  gap: 16px;
  min-height: 84px;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.18);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(248, 250, 252, 0.74));
  backdrop-filter: blur(14px);
  overflow: visible;
}

.chat-header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
  width: 100%;
  padding-right: 8px;
  overflow: visible;
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
  flex: 1;
}

.session-avatar-shell {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.14), rgba(34, 197, 94, 0.12));
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.chat-header-copy {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.chat-header-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.chat-header h2 {
  margin: 0;
  min-width: 0;
  font-size: 17px;
  font-weight: 700;
  color: #1e293b;
  line-height: 1.15;
  letter-spacing: -0.02em;
}

.session-mode-badge {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 9px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.chat-header-meta-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.agent-summary-shell {
  position: relative;
  z-index: 30;
  margin-left: auto;
  margin-right: 0;
  transform: translateX(-332px);
}

.agent-summary-trigger {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px 6px 6px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 10px 24px -20px rgba(15, 23, 42, 0.5);
  transition: all 0.18s ease;
}

.agent-summary-trigger:hover {
  transform: translateY(-1px);
  border-color: rgba(59, 130, 246, 0.24);
  box-shadow: 0 16px 30px -24px rgba(37, 99, 235, 0.42);
}

.agent-summary-avatars {
  display: flex;
  align-items: center;
}

.agent-summary-avatar,
.agent-panel-avatar {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #22c55e);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.92);
}

.agent-summary-avatar + .agent-summary-avatar {
  margin-left: -8px;
}

.agent-summary-avatar img,
.agent-panel-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.agent-summary-avatar.more {
  background: #e2e8f0;
  color: #475569;
}

.agent-summary-copy {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  line-height: 1.1;
}

.agent-summary-title {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}

.agent-summary-meta {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}

.agent-summary-meta.compact.online {
  color: #15803d;
}

.agent-summary-meta.compact.busy {
  color: #b45309;
}

.agent-summary-meta.compact.offline {
  color: #64748b;
}

.agent-panel {
  position: absolute;
  top: calc(100% + 10px);
  left: 50%;
  right: auto;
  z-index: 40;
  transform: translateX(-58%);
  min-width: 280px;
  padding: 8px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 50px -28px rgba(15, 23, 42, 0.4);
  backdrop-filter: blur(14px);
}

.agent-panel-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border-radius: 14px;
  transition: background 0.18s ease;
}

.agent-panel-item:hover {
  background: rgba(241, 245, 249, 0.92);
}

.agent-panel-item.selected {
  background: rgba(219, 234, 254, 0.55);
}

.agent-panel-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.agent-panel-name-row,
.agent-panel-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.agent-panel-name {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.agent-panel-badge {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  color: #2563eb;
  font-size: 10px;
  font-weight: 700;
}

.agent-panel-badge.muted {
  background: rgba(15, 23, 42, 0.06);
  color: #64748b;
}

.agent-panel-meta {
  font-size: 12px;
  color: #64748b;
}

.agent-panel-status.online {
  color: #16a34a;
}

.agent-panel-status.busy {
  color: #d97706;
}

.agent-panel-status.offline {
  color: #94a3b8;
}

.workspace-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  font-size: 11px;
  font-weight: 600;
  width: fit-content;
}

.workspace-icon {
  font-size: 12px;
}

.workspace-name {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .chat-header {
    min-height: auto;
    padding: 16px;
  }

  .chat-header-main,
  .chat-header-left {
    align-items: flex-start;
  }

  .chat-header h2 {
    font-size: 16px;
  }

  .agent-summary-trigger {
    max-width: 100%;
  }

  .agent-panel {
    min-width: min(280px, calc(100vw - 32px));
  }
}
</style>
