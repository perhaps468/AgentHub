import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import {
  fetchConversationList,
  fetchConversationDetail,
  createConversation,
  updateConversation as updateConversationApi,
  fetchConversationMessages,
  deleteConversation,
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

// In-flight stream type for streaming messages (P1-3-4)
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

/**
 * 后端 desc() 排序时，消息顺序是 [A_n, H_n, A_(n-1), H_(n-1), ...]。
 * 本函数按对话轮次重组：每对 H+A 为一轮，轮次内 H→A，新轮在前。
 * 输入 desc 顺序 → 输出 asc 顺序（H→A，新在下）。
 */
function reorganizeByRounds(messages: ChatMessage[]): ChatMessage[] {
  const rounds: ChatMessage[][] = []
  // 两两一组（A, H），因为 desc 时 A 排在 H 前面
  for (let i = 0; i < messages.length; i += 2) {
    // 假设第 i 条是 agent，第 i+1 条是 human
    const agentMsg = messages[i]
    const humanMsg = messages[i + 1]
    if (agentMsg && humanMsg) {
      // 确保 H 在 A 前
      if (agentMsg.sender_type === 'agent' && humanMsg.sender_type === 'human') {
        rounds.push([humanMsg, agentMsg])
      } else if (agentMsg.sender_type === 'human' && humanMsg?.sender_type === 'agent') {
        // 边界情况：偶数条时最后一组可能顺序反了
        rounds.push([agentMsg, humanMsg])
      } else {
        // 单条情况或其他组合，直接加
        rounds.push([agentMsg])
        if (humanMsg) rounds.push([humanMsg])
      }
    } else if (agentMsg) {
      rounds.push([agentMsg])
    } else if (humanMsg) {
      rounds.push([humanMsg])
    }
  }
  // rounds 本身是按最新轮次在前排列的 [[H_8, A_8], [H_7, A_7], ...]
  // reverse rounds 数组让最新沉到末尾（但不破坏每对内部的 H→A 顺序）
  // 再 flat: [[H_1, A_1], [H_2, A_2], ...] → [H_1, A_1, H_2, A_2, ...]
  return rounds.reverse().flat()
}

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

    // In-flight streaming messages (P1-3-4 reconciliation)
    const inFlightMessages = ref<Map<string, InFlightStream>>(new Map())

    const streamState = useChatStreamState()

    // ── Getters ──────────────────────────────────────────────
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

    // ── Actions ──────────────────────────────────────────────

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
          let updatedList: ChatMessage[] = []
          for (const msg of res.items) {
            if (msg.metadata?.source === 'optimistic_human') {
              continue
            }
            updatedList.push(msg)
          }
          // 后端 desc() 排序会导致 A 在 H 前面，按轮次重组
          updatedList = reorganizeByRounds(updatedList)
          messageMap.value[sessionId] = updatedList
        } else {
          // page>1 时，加载更早的消息，追加到列表顶部
          const existing = messageMap.value[sessionId] ?? []
          const newItems: ChatMessage[] = []
          for (const msg of res.items) {
            if (msg.metadata?.source === 'optimistic_human') {
              continue
            }
            newItems.push(msg)
          }
          const reorganized = reorganizeByRounds(newItems)
          messageMap.value[sessionId] = [...reorganized, ...existing]
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

    function upsertMessage(messageId: string, msg: ChatMessage) {
      // upsert based on message.id
      const list = messageMap.value[currentSessionId.value]
      if (!list) return
      const idx = list.findIndex((m) => m.id === messageId)
      if (idx !== -1) {
        messageMap.value[currentSessionId.value][idx] = msg
      } else {
        messageMap.value[currentSessionId.value].push(msg)
      }
    }

    function deleteMessage(messageId: string) {
      const list = messageMap.value[currentSessionId.value]
      if (!list) return
      messageMap.value[currentSessionId.value] = list.filter((m) => m.id !== messageId)
    }

    function clearMessages(sessionId: string) {
      delete messageMap.value[sessionId]
      delete messagePageMap.value[sessionId]
      // Clear in-flight messages for this session
      inFlightMessages.value.forEach((_, streamId) => {
        const stream = inFlightMessages.value.get(streamId)
        if (stream && stream.session_id === sessionId) {
          inFlightMessages.value.delete(streamId)
        }
      })
      streamState.clearSession(sessionId)
    }

    function setConnectionState(state: ConnectionState) {
      connectionState.value = state
    }

    function setCurrentSessionId(id: string | null) {
      currentSessionId.value = id
    }

    async function deleteSession(sessionId: string) {
      await deleteConversation(sessionId)
      if (sessionList.value) {
        sessionList.value = sessionList.value.filter((s) => s.id !== sessionId)
      }
      clearMessages(sessionId)
      if (currentSessionId.value === sessionId) {
        currentSessionId.value = null
        currentSession.value = null
      }
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
      inFlightMessages,
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
      deleteSession,
      appendMessage,
      appendHumanMessage,
      mergeOrUpdateMessage,
      upsertMessage,
      deleteMessage,
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
