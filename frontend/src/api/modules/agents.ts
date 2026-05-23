import { agenthubRequest } from '@/api/client'
import type { AgentProfile } from '@/types/agenthub'

export const fetchDefaultAgent = async () => {
  const { data } = await agenthubRequest.get<AgentProfile>('/agents/default')
  return data
}
