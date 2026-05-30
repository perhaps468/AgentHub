export type SidebarMode = 'conversations' | 'agents'
export type SidebarPanel = 'messages' | 'agents'
export type ConversationMode = 'single' | 'group'
export type ConversationKind = 'legacy-group' | 'group' | 'single-agent' | 'private'
export type SenderType = 'human' | 'agent' | 'system'
export type PreviewType = 'empty' | 'code' | 'web' | 'ppt' | 'file'
export type AgentPlatform = 'claude-code' | 'codex' | 'opencode' | 'custom'

export interface AgentProfile {
  id: string
  name: string
  avatar?: string | null
  avatar_url?: string | null
  platform: string
  capabilityTags: string[]
  status?: 'online' | 'offline'
  role?: string
  model?: string
}

export interface SidebarAgent {
  id: string
  name: string
  avatar: string
  capabilityTags: string[]
  description?: string
  platform?: AgentPlatform
  isCustom?: boolean
}

export interface SidebarUser {
  id: string
  name: string
  avatar: string
  email?: string
  bio?: string
}

export interface PersonProfile {
  id: string
  name: string
  avatar?: string | null
  role?: string
}

// ---------------------------------------------------------------------------
// Workspace (Task B)
// Task B+C-1: Added 'name' field for frontend display
// ---------------------------------------------------------------------------

export interface Workspace {
  id: string
  owner_id: string
  root_path: string
  name: string
  created_at: string
}

export interface WorkspaceSummary {
  id: string
  name: string
  root_path: string
}

export interface ConversationItem {
  id: string
  owner_id: string
  title: string | null
  mode: ConversationMode
  is_pinned: boolean
  is_archived: boolean
  workspace_id: string | null
  workspace: WorkspaceSummary | null
  created_at: string
  updated_at: string
}

export interface MessageReference {
  id: string
  senderName: string
  summary: string
}

export interface MessageCodeArtifact {
  fileName: string
  language: string
  code: string
}

export interface MessageFileArtifact {
  fileName: string
  fileSize?: string
  fileType?: string
  downloadUrl?: string
}

export interface MessagePreviewArtifact {
  title: string
  url?: string
  description?: string
}

export interface MentionEntity {
  id: string
  name: string
  mentionType: 'member' | 'agent' | 'all'
}

export type ComposerNode =
  | { type: 'text'; text: string }
  | { type: 'emoji'; text: string }
  | { type: 'mention'; entity: MentionEntity }
  | { type: 'line-break' }

export interface ComposerFile {
  uid: string
  file: File
  name: string
  size: number
  type: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  url?: string
}

export interface ComposerDraft {
  sessionId: string
  text: string
  nodes: ComposerNode[]
  mentions: MentionEntity[]
  files: ComposerFile[]
  replyTo?: {
    messageId: string
    summary: string
    senderName: string
  } | null
}

export interface ChatMessage {
  id: string
  session_id: string
  sender_type: SenderType
  sender_role: string | null
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy'
  content: string
  payload: Record<string, unknown>
  metadata: Record<string, unknown>
  status: 'pending' | 'streaming' | 'completed' | 'failed'
  created_at: string
}

export interface StreamingMessage {
  stream_id: string
  message_id?: string
  session_id: string
  sender_type: SenderType
  sender_role: string | null
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy'
  content: string
  payload: Record<string, unknown>
  metadata: Record<string, unknown>
  ui_status: 'thinking' | 'streaming' | 'done' | 'syncing_interrupted'
  is_ephemeral: boolean
  created_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface CreateSessionPayload {
  title?: string | null
  mode: ConversationMode
  workspace_id: string  // Required - Task B+C-1
}

export interface UpdateSessionPayload {
  title?: string | null
  is_pinned?: boolean
  is_archived?: boolean
  workspace_id?: string | null
}

// ---------------------------------------------------------------------------
// Task C-2 - Pending Change Preview 事件类型
// ---------------------------------------------------------------------------

export interface SendMessagePayload {
  action: 'send_message'
  session_id: string
  content: string
}

export interface PreviewState {
  type: PreviewType
  title: string
  language?: string
  code?: string
  url?: string
  description?: string
  fileName?: string
  fileSize?: string
  fileType?: string
}

export interface WsIncomingMessage {
  type: string
  message?: ChatMessage
  data?: unknown
}

// ---------------------------------------------------------------------------
// Task A - Runtime 扩展事件类型
// ---------------------------------------------------------------------------

export type RuntimeStateValue =
  | 'thinking'
  | 'calling_tool'
  | 'observing'
  | 'responding'
  | 'finished'
  | 'error'

export interface ToolEvent {
  type: 'tool_event'
  stream_id: string
  message_id: string
  tool_name: string
  status: 'started' | 'finished'
  arguments: Record<string, unknown>
  response: string | null
  timestamp?: string
}

export interface RuntimeStateEvent {
  type: 'runtime_state'
  stream_id: string
  message_id: string
  state: RuntimeStateValue
  timestamp: string
}

// ---------------------------------------------------------------------------
// Task A - Runtime 过程事件最小回放模型
// ---------------------------------------------------------------------------

export interface RuntimeProcessNode {
  stream_id: string
  message_id: string
  timestamp: string
  node_type: 'runtime_state' | 'tool_event'
  state?: RuntimeStateValue
  tool_name?: string
  tool_status?: 'started' | 'finished'
}

export interface RuntimeProcessReplay {
  stream_id: string
  nodes: RuntimeProcessNode[]
}

// ---------------------------------------------------------------------------
// Task C-2 - Pending Change Preview 事件类型
// ---------------------------------------------------------------------------

export interface ChangePreviewEvent {
  type: 'change_preview'
  stream_id: string
  message_id: string
  change_id: string
  operation: 'create' | 'update' | 'delete'
  path: string
  unified_diff: string
  status: 'pending_confirmation' | 'applied' | 'rejected'
  timestamp: string
}

// Pending Change 状态管理
export type PendingChangeStatus = 'pending_confirmation' | 'applied' | 'rejected' | 'failed'

export interface PendingChange {
  change_id: string
  operation: 'create' | 'update' | 'delete'
  path: string
  unified_diff: string
  status: PendingChangeStatus
  stream_id: string
  message_id: string
}