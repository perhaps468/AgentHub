import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import {
  createConversation,
  deleteConversation,
  fetchConversationDetail,
  fetchConversationList,
  fetchConversationMessages,
  fetchLatestRun,
  fetchRun,
  fetchActiveRun as fetchActiveRunApi,
  updateConversation as updateConversationApi,
} from '@/api/modules/session'
import { fetchPendingChanges } from '@/api/modules/pendingChanges'
import type {
  ChatMessage,
  ConversationItem,
  CreateSessionPayload,
  OrchestrationRun,
  OrchestrationTask,
  UpdateSessionPayload,
} from '@/types/agenthub'
import { useChatStreamState } from '@/utils/useChatStreamState'
import type { ConnectionState } from '@/utils/ws-client'

export interface InFlightStream {
  stream_id: string
  message_id?: string
  session_id: string
  sender_role: string | null
  content: string
  accumulated_content: string
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy'
  payload: { text: string }
  metadata: Record<string, unknown>
  ui_status: 'thinking' | 'streaming' | 'done' | 'syncing_interrupted'
  created_at: string
}

function toChronologicalOrder(messages: ChatMessage[]): ChatMessage[] {
  return [...messages].reverse()
}

export const useSessionStore = defineStore(
  'session',
  () => {
    const sessionList = ref<ConversationItem[]>([])
    const currentSessionId = ref<string | null>(null)
    const currentSession = ref<ConversationItem | null>(null)
    const messageMap = ref<Record<string, ChatMessage[]>>({})
    const messagePageMap = ref<Record<string, { page: number; hasMore: boolean; total: number }>>({})
    const connectionState = ref<ConnectionState>('disconnected')
    const isLoadingList = ref(false)
    const isLoadingMessages = ref(false)
    const activeRun = ref<OrchestrationRun | null>(null)
    const activeTasks = ref<OrchestrationTask[]>([])
    const inFlightMessages = ref<Map<string, InFlightStream>>(new Map())
    const streamState = useChatStreamState()

    const currentMessages = computed(() => {
      if (!currentSessionId.value) return []
      return messageMap.value[currentSessionId.value] ?? []
    })

    const currentStreamingMessages = computed(() => {
      if (!currentSessionId.value) return []
      return streamState.getStreamingMessages(currentSessionId.value)
    })

    const currentPageInfo = computed(() => {
      if (!currentSessionId.value) return { page: 1, hasMore: false, total: 0 }
      return (
        messagePageMap.value[currentSessionId.value] ?? { page: 1, hasMore: false, total: 0 }
      )
    })

    async function fetchSessionList(params: {
      page?: number
      page_size?: number
      include_archived?: boolean
    }) {
      isLoadingList.value = true
      try {
        const res = await fetchConversationList(params)
        sessionList.value = res.items
        return res
      } finally {
        isLoadingList.value = false
      }
    }

    async function fetchSessionDetail(sessionId: string) {
      const res = await fetchConversationDetail(sessionId)
      currentSession.value = res
      return res
    }

    async function createSession(payload: CreateSessionPayload) {
      const res = await createConversation(payload)
      sessionList.value.unshift(res)
      return res
    }

    async function updateSession(sessionId: string, payload: UpdateSessionPayload) {
      const res = await updateConversationApi(sessionId, payload)
      const idx = sessionList.value.findIndex((s) => s.id === sessionId)
      if (idx !== -1) {
        sessionList.value[idx] = res
      }
      if (currentSession.value?.id === sessionId) {
        currentSession.value = res
      }
      return res
    }

    async function archiveSession(sessionId: string) {
      await updateSession(sessionId, { is_archived: true })
      sessionList.value = sessionList.value.filter((s) => s.id !== sessionId)
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = null
        currentSession.value = null
      }
    }

    async function fetchMessages(
      sessionId: string,
      opts: { page?: number; page_size?: number } = {},
    ) {
      isLoadingMessages.value = true
      try {
        const page = opts.page ?? 1
        const res = await fetchConversationMessages(sessionId, opts)
        const filtered = res.items.filter((msg) => msg.metadata?.source !== 'optimistic_human')

        if (page === 1) {
          messageMap.value[sessionId] = toChronologicalOrder(filtered)
        } else {
          const existing = messageMap.value[sessionId] ?? []
          messageMap.value[sessionId] = [...toChronologicalOrder(filtered), ...existing]
        }

        messagePageMap.value[sessionId] = {
          page: res.page,
          hasMore: res.has_more,
          total: res.total,
        }
        return res
      } finally {
        isLoadingMessages.value = false
      }
    }

    async function restorePendingChangesForSession(
      sessionId: string,
      opts: { clearExisting?: boolean; clearInFlight?: boolean } = {},
    ) {
      const { clearExisting = true, clearInFlight = false } = opts

      if (clearExisting) {
        streamState.clearSessionPendingChanges(sessionId)
      }
      if (clearInFlight) {
        streamState.clearInFlightStreams(sessionId)
      }

      const res = await fetchPendingChanges(sessionId)
      streamState.restorePendingChanges(res.items, sessionId)
      return res
    }

    async function fetchLatestRunForSession(sessionId: string) {
      const run = await fetchLatestRun(sessionId)
      activeRun.value = run
      activeTasks.value = run?.tasks ?? []
      if (run) {
        streamState.restoreTaskStreams(sessionId, {
          run_id: run.id,
          tasks: run.tasks.map((task) => ({
            id: task.id,
            assigned_agent_id: task.assigned_agent_id,
            latest_stream: task.result_payload?.stream_id
              ? {
                  stream_id: String(task.result_payload.stream_id),
                  message_id: task.result_payload?.message_id ? String(task.result_payload.message_id) : undefined,
                  status: task.status,
                }
              : task.error_payload?.stream_id
                ? {
                    stream_id: String(task.error_payload.stream_id),
                    status: task.status,
                  }
                : null,
          })),
        })
      }
      return run
    }

    // M4: Get pending changes by task
    function getPendingChangesByTask(taskId: string): ReturnType<typeof streamState.getPendingChanges> {
      const allChanges = streamState.getPendingChanges(currentSessionId.value || '')
      return allChanges.filter((c) => c.task_id === taskId)
    }

    // M4: Get pending changes by run
    function getPendingChangesByRun(runId: string): ReturnType<typeof streamState.getPendingChanges> {
      const allChanges = streamState.getPendingChanges(currentSessionId.value || '')
      return allChanges.filter((c) => c.run_id === runId)
    }

    // M4: Update task status from apply/reject result
    function updateTaskStatus(taskId: string, status: string) {
      const taskIndex = activeTasks.value.findIndex((t) => t.id === taskId)
      if (taskIndex !== -1) {
        activeTasks.value[taskIndex] = {
          ...activeTasks.value[taskIndex],
          status: status as any,
        }
      }
    }

    // M4: Get task by ID
    function getTaskById(taskId: string) {
      return activeTasks.value.find((t) => t.id === taskId)
    }

    // M4: Check if all tasks are in terminal state
    function areAllTasksTerminal(): boolean {
      const terminalStates = ['completed', 'rejected', 'cancelled', 'failed']
      return activeTasks.value.every((t) => terminalStates.includes(t.status))
    }

    // M6: Fetch active run for session recovery
    async function fetchActiveRun(sessionId: string) {
      const res = await fetchActiveRunApi(sessionId)
      if (res.run) {
        activeRun.value = res.run
        activeTasks.value = res.tasks || []
        // Restore task streams for UI attribution
        if (res.run) {
          streamState.restoreTaskStreams(sessionId, {
            run_id: res.run.id,
            tasks: (res.tasks || []).map((task: any) => ({
              id: task.id,
              assigned_agent_id: task.assigned_agent_id,
              latest_stream: task.result_payload?.stream_id
                ? {
                    stream_id: String(task.result_payload.stream_id),
                    message_id: task.result_payload?.message_id ? String(task.result_payload.message_id) : undefined,
                    status: task.status,
                  }
                : task.error_payload?.stream_id
                  ? {
                      stream_id: String(task.error_payload.stream_id),
                      status: task.status,
                    }
                  : null,
            })),
          })
        }
        // Restore pending changes if any
        if (res.pending_changes && res.pending_changes.length > 0) {
          streamState.restorePendingChanges(res.pending_changes, sessionId)
        }
      } else {
        activeRun.value = null
        activeTasks.value = []
      }
      return res
    }

    // M6: Restore complete orchestration state for a session
    async function restoreOrchestrationState(sessionId: string) {
      // Fetch active run and pending changes together
      const res = await fetchActiveRun(sessionId)
      return res
    }

    async function fetchRunById(runId: string) {
      const run = await fetchRun(runId)
      activeRun.value = run
      activeTasks.value = run.tasks
      streamState.restoreTaskStreams(run.session_id, {
        run_id: run.id,
        tasks: run.tasks.map((task) => ({
          id: task.id,
          assigned_agent_id: task.assigned_agent_id,
          latest_stream: task.result_payload?.stream_id
            ? {
                stream_id: String(task.result_payload.stream_id),
                message_id: task.result_payload?.message_id ? String(task.result_payload.message_id) : undefined,
                status: task.status,
              }
            : task.error_payload?.stream_id
              ? {
                  stream_id: String(task.error_payload.stream_id),
                  status: task.status,
                }
              : null,
        })),
      })
      return run
    }

    function appendMessage(sessionId: string, msg: ChatMessage) {
      const existing = messageMap.value[sessionId] ?? []
      if (msg.id && existing.some((m) => m.id === msg.id)) return
      messageMap.value = {
        ...messageMap.value,
        [sessionId]: [...existing, msg],
      }
    }

    function appendHumanMessage(sessionId: string, msg: ChatMessage) {
      appendMessage(sessionId, msg)
    }

    function mergeOrUpdateMessage(sessionId: string, msg: ChatMessage) {
      const existing = messageMap.value[sessionId] ?? []
      const existingIndex = existing.findIndex((m) => m.id === msg.id)
      if (existingIndex !== -1) {
        const updated = [...existing]
        updated[existingIndex] = msg
        messageMap.value = {
          ...messageMap.value,
          [sessionId]: updated,
        }
        return
      }
      appendMessage(sessionId, msg)
    }

    function upsertMessage(messageId: string, msg: ChatMessage) {
      const sessionId = currentSessionId.value
      const list = sessionId ? messageMap.value[sessionId] : undefined
      if (!list) return
      const idx = list.findIndex((m) => m.id === messageId)
      if (idx !== -1) {
        const updated = [...list]
        updated[idx] = msg
        messageMap.value = {
          ...messageMap.value,
          [sessionId]: updated,
        }
        return
      }
      messageMap.value = {
        ...messageMap.value,
        [sessionId]: [...list, msg],
      }
    }

    function deleteMessage(messageId: string) {
      const sessionId = currentSessionId.value
      if (!sessionId) return
      const list = messageMap.value[sessionId]
      if (!list) return
      messageMap.value[sessionId] = list.filter((m) => m.id !== messageId)
    }

    function clearMessages(sessionId: string) {
      delete messageMap.value[sessionId]
      delete messagePageMap.value[sessionId]
      inFlightMessages.value.forEach((_, streamId) => {
        const stream = inFlightMessages.value.get(streamId)
        if (stream?.session_id === sessionId) {
          inFlightMessages.value.delete(streamId)
        }
      })
      streamState.clearSession(sessionId)
      if (activeRun.value?.session_id === sessionId) {
        activeRun.value = null
        activeTasks.value = []
      }
    }

    function setConnectionState(state: ConnectionState) {
      connectionState.value = state
    }

    function setCurrentSessionId(id: string | null) {
      currentSessionId.value = id
      streamState.setCurrentSessionId(id)
      if (id === null) {
        activeRun.value = null
        activeTasks.value = []
      }
    }

    async function deleteSession(sessionId: string) {
      await deleteConversation(sessionId)
      sessionList.value = sessionList.value.filter((s) => s.id !== sessionId)
      clearMessages(sessionId)
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = null
        currentSession.value = null
      }
    }

    return {
      sessionList,
      currentSessionId,
      currentSession,
      messageMap,
      messagePageMap,
      connectionState,
      isLoadingList,
      isLoadingMessages,
      activeRun,
      activeTasks,
      inFlightMessages,
      streamState,
      currentMessages,
      currentStreamingMessages,
      currentPageInfo,
      fetchSessionList,
      fetchSessionDetail,
      createSession,
      updateSession,
      archiveSession,
      fetchMessages,
      restorePendingChangesForSession,
      fetchLatestRun: fetchLatestRunForSession,
      fetchRun: fetchRunById,
      deleteSession,
      appendMessage,
      appendHumanMessage,
      mergeOrUpdateMessage,
      upsertMessage,
      deleteMessage,
      clearMessages,
      setConnectionState,
      setCurrentSessionId,
      // M4: Task-aware methods
      getPendingChangesByTask,
      getPendingChangesByRun,
      updateTaskStatus,
      getTaskById,
      areAllTasksTerminal,
      // M6: Active run recovery methods
      fetchActiveRun,
      restoreOrchestrationState,
    }
  },
  {
    persist: {
      key: 'session-store',
      pick: ['currentSessionId'],
    },
  } as any,
)
