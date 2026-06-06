<template>
  <header class="chat-header">
    <div class="chat-header-main">
      <div class="chat-header-left">
        <avatar :info="{ name: currentSession?.title, avatar: currentAgentAvatar }" size="20px" />
      </div>
      <div class="chat-header-right">
        <h2>{{ currentSession?.title || '选择或新建会话' }}</h2>
        <div class="header-right-items">
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
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.2;
}

.chat-header-right {
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.header-right-items {
  display: flex;
  flex-direction: column;
}

.workspace-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding-top:5px;
  border-radius: 999px;
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