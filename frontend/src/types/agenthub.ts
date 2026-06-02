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
