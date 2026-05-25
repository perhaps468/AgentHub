import { agenthubRequest } from '@/api/client'
import type {
  ConversationItem,
  CreateSessionPayload,
  PaginatedResponse,
  UpdateSessionPayload,
  ChatMessage,
} from '@/types/agenthub'

export const fetchConversationList = async (params: {
  owner_id: string
  include_archived?: boolean
  page?: number
  page_size?: number
}) => {
  const { data } = await agenthubRequest.get<PaginatedResponse<ConversationItem>>('/sessions', {
    params,
  })
  return data
}

export const createConversation = async (payload: CreateSessionPayload) => {
  const { data } = await agenthubRequest.post<ConversationItem>('/sessions', payload)
  return data
}

export const fetchConversationDetail = async (sessionId: string) => {
  const { data } = await agenthubRequest.get<ConversationItem>(`/sessions/${sessionId}`)
  return data
}

export const updateConversation = async (sessionId: string, payload: UpdateSessionPayload) => {
  const { data } = await agenthubRequest.patch<ConversationItem>(`/sessions/${sessionId}`, payload)
  return data
}

export const fetchConversationMessages = async (
  sessionId: string,
  params: { page?: number; page_size?: number } = {},
) => {
  const { data } = await agenthubRequest.get<PaginatedResponse<ChatMessage>>(
    `/sessions/${sessionId}/messages`,
    { params },
  )
  return data
}

export const deleteConversation = async (sessionId: string) => {
  const { data } = await agenthubRequest.delete<{ code: number; msg: string }>(`/sessions/${sessionId}`)
  return data
}

