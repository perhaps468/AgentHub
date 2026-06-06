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
  // P8: Planner integration fields
  client_task_id?: string | null
  assignment_reason?: string | null
  depends_on?: string[] | null
}

// M4: Extended task statuses for confirmation flow
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
  // P8: Planning source field
  planning_source?: PlanningSource | null
  tasks: OrchestrationTask[]
}

// P8: Planning source enum
export type PlanningSource = 'planner' | 'planner_repaired' | 'fallback_splitter'

// M5: Extended run statuses for aggregation
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
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy'
  payload: { text: string }
  metadata: Record<string, unknown>
}

export interface PendingChange {
  change_id: string
  session_id: string
  message_id?: string
  stream_id?: string
  // M4: Task-aware fields for orchestration
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

// M4: Extended pending change statuses
export type PendingChangeStatus =
  | 'pending_confirmation'
  | 'applied'
  | 'rejected'
  | 'failed'

// M4: Apply/Reject response from API
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

// M4: Change preview event from WebSocket
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
  // M4: Task-aware fields
  run_id?: string | null
  task_id?: string | null
  agent_id?: string | null
  batch_id?: string | null
  // M6: Agent role for inline change preview
  agent_role?: string
}

export type RuntimeStateValue = 'thinking' | 'calling_tool' | 'observing' | 'responding' | 'finished' | 'error'

// Task B: Workspace interface
export interface Workspace {
  id: string
  owner_id: string
  root_path: string
  name: string
  created_at: string
}

// Session / Conversation item — mirrors backend SessionResponse
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
<<<<<<< Updated upstream
  updated_at: string
=======
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

// ==================== 发送消息协议 ====================
export interface SendMessagePayload {
  action: 'send_message'
  session_id: string
  content: string
  target_agent_ids?: string[]
  mentions?: ComposerMention[]
>>>>>>> Stashed changes
}

// ==================== 预览区状态 ====================
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
