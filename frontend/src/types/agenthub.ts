export interface OrchestrationTask {
  id: string
  run_id: string
  parent_task_id?: string | null
  sequence: number
  assigned_agent_id: string
  kind: string
  title: string
  goal: string
  input_payload: Record<string, unknown>
  result_payload?: Record<string, unknown> | null
  error_payload?: Record<string, unknown> | null
  status: TaskStatus
  client_task_id?: string | null
  assignment_reason?: string | null
  depends_on?: string[] | null
}

export type TaskStatus =
  | 'planned'
  | 'running'
  | 'waiting_confirmation'
  | 'completed'
  | 'rejected'
  | 'cancelled'
  | 'failed'

export interface OrchestrationRun {
  id: string
  session_id: string
  trigger_message_id: string
  planner_agent_id: string
  status: RunStatus
  summary?: string | null
  planning_source?: PlanningSource | null
  tasks: OrchestrationTask[]
}

export type PlanningSource = 'planner' | 'planner_repaired' | 'fallback_splitter'

export type RunStatus =
  | 'planned'
  | 'running'
  | 'waiting_confirmation'
  | 'completed'
  | 'partial'
  | 'cancelled'
  | 'failed'

export interface RuntimeProcessNode {
  stream_id: string
  message_id: string
  timestamp: string
  node_type: 'tool_event' | 'runtime_state' | 'change_preview'
  tool_name?: string
  tool_status?: string
  state?: string
}

export interface StreamingMessage {
  stream_id: string
  message_id?: string
  session_id: string
  sender_type: 'agent' | 'human'
  sender_role: string | null
  content: string
  accumulated_content: string
  ui_status: 'thinking' | 'streaming' | 'done' | 'syncing_interrupted'
  is_ephemeral: boolean
  created_at: string
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy' | 'ppt_data'
  payload: { text: string } | Record<string, unknown>
  metadata: Record<string, unknown>
}

export interface PendingChange {
  change_id: string
  session_id: string
  message_id?: string
  stream_id?: string
  run_id?: string | null
  task_id?: string | null
  agent_id?: string | null
  batch_id?: string | null
  operation: 'create' | 'update' | 'delete'
  path: string
  unified_diff: string
  status: PendingChangeStatus
  original_content?: string
  proposed_content?: string
  created_at?: string | null
  applied_at?: string | null
}

export type PendingChangeStatus =
  | 'pending_confirmation'
  | 'applied'
  | 'rejected'
  | 'failed'

export interface ApplyChangeResponse {
  success: boolean
  change_id: string
  message: string
  status: PendingChangeStatus
  ws_pushed: boolean
  run_id?: string | null
  task_id?: string | null
  agent_id?: string | null
}

export interface ChangePreviewEvent {
  type: 'change_preview'
  change_id: string
  stream_id?: string
  message_id?: string
  operation: 'create' | 'update' | 'delete'
  path: string
  unified_diff: string
  status: PendingChangeStatus
  timestamp?: string
  run_id?: string | null
  task_id?: string | null
  agent_id?: string | null
  batch_id?: string | null
  agent_role?: string
}

export type RuntimeStateValue = 'thinking' | 'calling_tool' | 'observing' | 'responding' | 'finished' | 'error'

export interface Workspace {
  id: string
  owner_id: string
  root_path: string
  name: string
  created_at: string
}

export type SessionMemberStatus = 'online' | 'busy' | 'offline'

export interface SessionMember {
  id: string
  session_id: string
  member_type: 'agent' | 'user'
  member_id: string
  is_primary: boolean
  health_status?: string
  status: SessionMemberStatus
  agent_name?: string | null
  agent_avatar?: string | null
  agent_role?: string | null
  created_at: string
}

export interface ConversationItem {
  id: string
  owner_id: string
  workspace_id: string | null
  agent_id: string | null
  title: string | null
  mode: 'single' | 'group'
  is_pinned: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
  workspace?: Workspace | null
  members?: SessionMember[]
  description?: string | null
}

export interface SessionMemberStatusEvent {
  type: 'session_member_status'
  session_id: string
  member_id: string
  agent_id?: string | null
  status: SessionMemberStatus
  timestamp?: string
}

export type ComposerAgent = {
  id: string
  name: string
  avatar?: string | null
  status: SessionMemberStatus
  role?: string | null
}

export interface ComposerMention {
  agentId: string
  agentName: string
}

export interface SessionAgentOption extends ComposerAgent {
  isPrimary: boolean
}

export type ComposerNode =
  | { type: 'text'; content: string }
  | { type: 'agent-chip'; agent: ComposerAgent }

export interface ComposerSubmitPayload {
  text: string
  targetAgentIds: string[]
  selectedAgents: ComposerAgent[]
  mentions: ComposerMention[]
  nodes: ComposerNode[]
}

export interface SendMessagePayload {
  action: 'send_message'
  session_id: string
  content: string
  target_agent_ids?: string[]
  mentions?: ComposerMention[]
  reference?: {
    msg_id: string
    content: string
    sender: string
  }
}

/**
 * PPT 单页标准化视图模型：经过解析层处理后的前端可用数据结构
 */
export interface PptSlideViewModel {
  id: string
  title: string
  bullets: string[]
  imgTag: string
  imageUrl: string
}

/**
 * PPT 预览模型：标准化解析后的完整 PPT 数据
 * 由 ppt-data.ts 的 buildPptPreviewModel() 产出
 */
export interface PptPreviewModel {
  title: string
  agentRole: string
  createdAt: string
  slides: PptSlideViewModel[]
}

export type PreviewState =
  | { type: 'empty'; title?: string }
  | { type: 'code'; title?: string; code: string }
  | { type: 'web'; title?: string; url: string; description?: string }
  | {
      type: 'diff'
      title?: string
      change_id: string
      operation: 'create' | 'update' | 'delete'
      path: string
      unified_diff: string
    }
  | {
      // PPT 预览状态：复用右侧统一预览区，携带标准化后的幻灯片数据
      type: 'ppt'
      title?: string
      agentRole?: string
      createdAt?: string
      slides: PptSlideViewModel[]
      workspaceId?: string
    }

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface ChatMessage {
  id: string
  session_id: string
  sender_type: 'agent' | 'human'
  sender_role: string | null
  content: string
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy' | 'ppt_data'
  payload: Record<string, unknown>
  metadata: Record<string, unknown>
  status: string
  created_at: string
}

export interface CreateSessionPayload {
  owner_id?: string
  title: string
  mode: 'single' | 'group'
  workspace_id: string
  agent_id?: string
  participant_agent_ids?: string[]
}

export interface UpdateSessionPayload {
  title?: string
  is_pinned?: boolean
  is_archived?: boolean
}

export interface SidebarUser {
  id: string
  name: string
  avatar: string
  bio?: string
}

export interface SidebarAgent {
  id: string
  name: string
  avatar: string
  description?: string
  capabilityTags: string[]
  platform?: string
  isCustom?: boolean
  role?: string | null
  model?: string | null
  system_prompt?: string | null
}

export type SidebarPanel = 'messages' | 'agents'
export type ConversationMode = 'single' | 'group'

export interface AgentDraft {
  id?: string
  name: string
  avatar?: string
  description?: string
  capabilityTags: string[]
  platform?: string
  model?: string
}
