import { agenthubRequest } from '@/api/client'
import type { Workspace } from '@/types/agenthub'

export const fetchWorkspaceList = async () => {
  const { data } = await agenthubRequest.get<Workspace[]>('/workspaces')
  return data
}

export const createWorkspace = async (payload: { root_path: string }) => {
  const { data } = await agenthubRequest.post<Workspace>('/workspaces', payload)
  return data
}

export const fetchWorkspace = async (workspaceId: string) => {
  const { data } = await agenthubRequest.get<Workspace>(`/workspaces/${workspaceId}`)
  return data
}

export const savePptToWorkspace = async (
  workspaceId: string,
  fileName: string,
  blob: Blob,
): Promise<{ saved: boolean; path: string; name: string }> => {
  const formData = new FormData()
  formData.append("file", blob, `${fileName}.pptx`)
  const { data } = await agenthubRequest.post(
    `/workspaces/${workspaceId}/ppt`,
    formData,
    { params: { file_name: fileName } },
  )
  return data
}
