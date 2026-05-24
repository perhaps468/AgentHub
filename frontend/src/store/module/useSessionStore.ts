import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import {
  fetchConversationList,
  fetchConversationDetail,
  createConversation,
  updateConversation as updateConversationApi,
  fetchConversationMessages,
} from '@/api/modules/session'
import type {
  ConversationItem,
  CreateSessionPayload,
  UpdateSessionPayload,
  ChatMessage,
  StreamingMessage,
} from '@/types/agenthub'
import type { ConnectionState } from '@/utils/ws-client'
import { useChatStreamState } from '@/utils/useChatStreamState'

export const useSessionStore = defineStore(
  'session',
  () => {
    // ── State ────────────────────────────────────────────────
    const sessionList = ref<ConversationItem[]>([])
    const currentSessionId = ref<string | null>(null)
    const currentSession = ref<ConversationItem | null>(null)
    const messageMap = ref<Record<string, ChatMessage[]>>({})
    const messagePageMap = ref<Record<string, { page: number; hasMore: boolean; total: number }>>({})
    const connectionState = ref<ConnectionState>('disconnected')
    const isLoadingList = ref(false)
    const isLoadingMessages = ref(false)

    const streamState = useChatStreamState()

    // ── Getters ──────────────────────────────────────────────
    const currentMessages = computed(() => {
      if (!currentSessionId.value) return []
      return messageMap.value[currentSessionId.value] ?? []
    })

    const currentStreamingMessages = computed(() => {
      if (!currentSessionId.value) return []
      return streamState.getStreamingMessages.value(currentSessionId.value)
    })

    const currentPageInfo = computed(() => {
      if (!currentSessionId.value) return { page: 1, hasMore: false, total: 0 }
      return (
        messagePageMap.value[currentSessionId.value] ?? { page: 1, hasMore: false, total: 0 }
      )
    })

    // ── Actions ──────────────────────────────────────────────

    async function fetchSessionList(params: {
      owner_id: string
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
      if (!sessionList.value) {
        sessionList.value = []
      }
      sessionList.value.unshift(res)
      return res
    }

    async function updateSession(sessionId: string, payload: UpdateSessionPayload) {
      const res = await updateConversationApi(sessionId, payload)
      if (sessionList.value) {
        const idx = sessionList.value.findIndex((s) => s.id === sessionId)
        if (idx !== -1) {
          sessionList.value[idx] = res
        }
      }
      if (currentSession.value?.id === sessionId) {
        currentSession.value = res
      }
      return res
    }

    async function archiveSession(sessionId: string) {
      await updateSession(sessionId, { is_archived: true })
      if (sessionList.value) {
        sessionList.value = sessionList.value.filter((s) => s.id !== sessionId)
      }
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

        if (page === 1) {
          messageMap.value[sessionId] = res.items
        } else {
          const existing = messageMap.value[sessionId] ?? []
          messageMap.value[sessionId] = [...existing, ...res.items]
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

    function appendMessage(sessionId: string, msg: ChatMessage) {
      if (!messageMap.value[sessionId]) {
        messageMap.value[sessionId] = []
      }
      if (msg.id && messageMap.value[sessionId].some((m) => m.id === msg.id)) return
      messageMap.value[sessionId].push(msg)
    }

    function appendHumanMessage(sessionId: string, msg: ChatMessage) {
      if (!messageMap.value[sessionId]) {
        messageMap.value[sessionId] = []
      }
      if (msg.id && messageMap.value[sessionId].some((m) => m.id === msg.id)) return
      messageMap.value[sessionId].push(msg)
    }

    function mergeOrUpdateMessage(sessionId: string, msg: ChatMessage) {
      if (!messageMap.value[sessionId]) {
        messageMap.value[sessionId] = []
      }
      const existingIndex = messageMap.value[sessionId].findIndex((m) => m.id === msg.id)
      if (existingIndex !== -1) {
        messageMap.value[sessionId][existingIndex] = msg
      } else {
        messageMap.value[sessionId].push(msg)
      }
    }

    function clearMessages(sessionId: string) {
      delete messageMap.value[sessionId]
      delete messagePageMap.value[sessionId]
      streamState.clearSession(sessionId)
    }

    function setConnectionState(state: ConnectionState) {
      connectionState.value = state
    }

    function setCurrentSessionId(id: string | null) {
      currentSessionId.value = id
    }

    return {
      // state
      sessionList,
      currentSessionId,
      currentSession,
      messageMap,
      messagePageMap,
      connectionState,
      isLoadingList,
      isLoadingMessages,
      streamState,
      // getters
      currentMessages,
      currentStreamingMessages,
      currentPageInfo,
      // actions
      fetchSessionList,
      fetchSessionDetail,
      createSession,
      updateSession,
      archiveSession,
      fetchMessages,
      appendMessage,
      appendHumanMessage,
      mergeOrUpdateMessage,
      clearMessages,
      setConnectionState,
      setCurrentSessionId,
    }
  },
  {
    persist: {
      key: 'session-store',
      pick: ['currentSessionId'],
    },
  } as any,
)
