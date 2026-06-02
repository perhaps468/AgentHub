import { agenthubRequest } from '@/api/client'
import type { AgentConfig, AgentProfile } from '@/types/agenthub'

export interface AgentListQuery {
  include_builtin?: boolean
  include_inactive?: boolean
}

export interface AgentPayload {
  name: string
  model: string
  platform?: string
  description?: string | null
  avatar_url?: string | null
  capability_tags: string[]
}

export const fetchDefaultAgent = async () => {
  const { data } = await agenthubRequest.get<AgentProfile>('/agents/default')
  return data
}

export const fetchAgents = async (params: AgentListQuery = {}) => {
  const { data } = await agenthubRequest.get<{ items: AgentProfile[]; total: number }>('/agents', { params })
  return data
}

export const fetchAgentConfig = async () => {
  const { data } = await agenthubRequest.get<AgentConfig>('/agents/config')
  return data
}

export const createAgent = async (payload: AgentPayload) => {
  const { data } = await agenthubRequest.post<AgentProfile>('/agents', payload)
  return data
}

export const updateAgent = async (agentId: string, payload: Partial<AgentPayload> & { is_active?: boolean }) => {
  const { data } = await agenthubRequest.patch<AgentProfile>(`/agents/${agentId}`, payload)
  return data
}
