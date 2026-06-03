import { agenthubRequest } from '@/api/client'

export interface PendingChangeItem {
  change_id: string
  session_id: string
  message_id?: string | null
  stream_id?: string | null
  run_id?: string | null
  task_id?: string | null
  agent_id?: string | null
  batch_id?: string | null
  path: string
  operation: 'create' | 'update' | 'delete'
  unified_diff: string
  original_content?: string | null
  proposed_content?: string | null
  status: 'pending_confirmation' | 'applied' | 'rejected' | 'failed'
  created_at?: string | null
  applied_at?: string | null
}

export interface PendingChangeListResponse {
  items: PendingChangeItem[]
  total: number
  session_id: string
}

export interface ApplyChangeRequest {
  change_id: string
  session_id?: string
}

export interface ApplyChangeResponse {
  success: boolean
  change_id: string
  message: string
  status: 'applied' | 'rejected' | 'failed'
  ws_pushed?: boolean
  run_id?: string | null
  task_id?: string | null
  agent_id?: string | null
}

export const fetchPendingChanges = async (
  sessionId: string,
): Promise<PendingChangeListResponse> => {
  const { data } = await agenthubRequest.get<PendingChangeListResponse>('/pending-changes', {
    params: { session_id: sessionId },
  })
  return data
}

export const applyPendingChange = async (
  payload: ApplyChangeRequest,
): Promise<ApplyChangeResponse> => {
  const { data } = await agenthubRequest.post<ApplyChangeResponse>('/pending-changes/apply', payload)
  return data
}

export const rejectPendingChange = async (
  payload: ApplyChangeRequest,
): Promise<ApplyChangeResponse> => {
  const { data } = await agenthubRequest.post<ApplyChangeResponse>('/pending-changes/reject', payload)
  return data
}
