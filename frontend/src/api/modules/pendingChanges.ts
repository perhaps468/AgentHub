import { agenthubRequest } from '@/api/client'

export interface ApplyChangeRequest {
  change_id: string
  session_id?: string  // Task C-4: 用于 WebSocket 事件推送
}

export interface ApplyChangeResponse {
  success: boolean
  change_id: string
  message: string
  status: 'applied' | 'rejected' | 'failed'  // Task C-4: 状态字段
}

export const applyPendingChange = async (changeId: string, sessionId?: string): Promise<ApplyChangeResponse> => {
  const payload: ApplyChangeRequest = { change_id: changeId }
  if (sessionId) {
    payload.session_id = sessionId
  }
  const { data } = await agenthubRequest.post<ApplyChangeResponse>('/pending-changes/apply', payload)
  return data
}

export const rejectPendingChange = async (changeId: string): Promise<ApplyChangeResponse> => {
  // For now, we can handle rejection client-side by removing the pending change
  // In future, we may want a server-side rejection API
  return {
    success: true,
    change_id: changeId,
    message: 'Change rejected by user',
    status: 'rejected',
  }
}
