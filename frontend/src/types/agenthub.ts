export type SidebarMode = 'conversations' | 'agents'
export type SidebarPanel = 'messages' | 'agents'
export type ConversationMode = 'single' | 'group'
export type ConversationKind = 'legacy-group' | 'group' | 'single-agent' | 'private'
export type SenderType = 'human' | 'agent' | 'system'
export type PreviewType = 'empty' | 'code' | 'web' | 'ppt' | 'file'
export type AgentPlatform = 'claude-code' | 'codex' | 'opencode' | 'custom'

export interface AgentProfile {
  id: string
  owner_id?: string | null
  name: string
  avatar?: string | null
  avatar_url?: string | null
  platform: string
  capabilityTags?: string[]
  capability_tags?: string[]
  tool_permissions?: string[]
  is_builtin?: boolean
  is_active?: boolean
  status?: 'online' | 'offline'
  role?: string
  model?: string
  description?: string | null
  system_prompt?: string
}

export interface AgentConfig {
  available_models: string[]
  available_capability_tags: string[]
}

export interface AgentDraft {
  name: string
  model: string
  capabilityTags: string[]
  description?: string
  avatar?: string
  platform?: AgentPlatform
}

export interface SidebarAgent {
  id: string
  name: string
  avatar: string
  capabilityTags: string[]
  description?: string
  platform?: AgentPlatform
  isCustom?: boolean
  role?: string
  model?: string
  system_prompt?: string
}

// ── Session & Message Types ──────────────────────────────

export interface Workspace {
  id: string
  name: string
  root_path: string
}

export interface SessionMember {
  id: string
  session_id: string
  member_type: 'agent' | 'user'
  member_id: string
  is_primary: boolean
  health_status: string
  created_at: string
}

export interface ConversationItem {
  id: string
  owner_id: string
  workspace_id: string | null
  agent_id: string | null
  title: string | null
  mode: string
  is_pinned: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
  workspace?: Workspace | null
  members?: SessionMember[] | null
}

export interface ChatMessage {
  id: string
  session_id: string
  sender_type: string
  sender_role: string | null
  content: string
  type: string
  status: string
  payload: Record<string, unknown>
  metadata: Record<string, unknown>
  created_at: string
}

export interface CreateSessionPayload {
  owner_id?: string | null
  title?: string | null
  mode: 'single' | 'group'
  workspace_id: string
  agent_id?: string | null
  participant_agent_ids?: string[] | null
}

export interface UpdateSessionPayload {
  title?: string | null
  is_pinned?: boolean
  is_archived?: boolean
  workspace_id?: string | null
  agent_id?: string | null
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}
