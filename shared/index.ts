// =============================================================================
// AgentHub - 跨端 TypeScript 类型定义
// Source of Truth: shared/schemas/ws_messages.json
// 本文件从 JSON Schema 派生，前后端共享同一份类型定义。
// P1-3 统一协议已生效，旧协议类型已移除
// =============================================================================

// ========== 枚举类型 ==========

export type AgentRole = 'Human' | 'PM' | 'Planner' | 'Coder' | 'Reviewer' | 'System' | string;

// P1-3 统一协议消息类型 (替代旧 chat_stream/agent_typing/error)
export type UnifiedMessageType =
  | 'message_start'
  | 'message_delta'
  | 'message_end'
  | 'message_error';

export type ClientAction = 'send_message' | 'accept_code' | 'reject_code' | 'deploy';

export type TaskStatus = 'pending' | 'doing' | 'done' | 'rejected';

export type DiffStatus = 'pending' | 'accepted' | 'rejected';

export type ProjectStatus = 'active' | 'archived' | 'deleted';

export type ContentType = 'text' | 'code' | 'image' | 'file' | 'diff' | 'preview';

export type SenderType = 'human' | 'agent' | 'system';

// ========== P1-3 统一消息模型 ==========

export interface UnifiedMessage {
  id: string;
  session_id: string;
  sender_type: SenderType;
  sender_role?: AgentRole | null;
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy';
  content: string;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  status: 'pending' | 'streaming' | 'completed' | 'failed';
  created_at: string;
}

// ========== P1-3 统一协议事件类型 (服务端 → 客户端) ==========

export interface MessageStartEvent {
  type: 'message_start';
  agent_role: AgentRole;
  timestamp: string;
  stream_id: string;
  message: UnifiedMessage;
}

export interface MessageDeltaEvent {
  type: 'message_delta';
  agent_role: AgentRole;
  timestamp: string;
  stream_id: string;
  message_id: string;
  delta: string;
}

export interface MessageEndEvent {
  type: 'message_end';
  agent_role: AgentRole;
  timestamp: string;
  stream_id: string;
  message_id: string;
  status: 'completed' | 'failed';
}

export interface MessageErrorEvent {
  type: 'message_error';
  agent_role: AgentRole;
  timestamp: string;
  stream_id: string;
  message_id?: string;
  error_code: 'session_not_found' | 'invalid_request' | 'agent_busy' | 'fixed_responder_failed' | 'unknown';
  error_message: string;
}

// P1-3 统一服务端消息类型 (唯一真相源)
export type UnifiedServerMessage =
  | MessageStartEvent
  | MessageDeltaEvent
  | MessageEndEvent
  | MessageErrorEvent;

// ========== 客户端 → 服务端 消息类型 ==========

export interface SendMessage {
  action: 'send_message';
  session_id: string;
  content: string;
  mentioned_agents?: AgentRole[]; // P2 群聊功能
  parent_message_id?: string;
}

export interface AcceptCode {
  action: 'accept_code';
  diff_id: string;
}

export interface RejectCode {
  action: 'reject_code';
  diff_id: string;
  reason?: string;
}

export interface DeployCommand {
  action: 'deploy';
  project_id: string;
  deploy_type?: 'preview' | 'static' | 'container';
}

export type ClientMessage = SendMessage | AcceptCode | RejectCode | DeployCommand;

// ========== REST API 数据类型 ==========

export interface User {
  id: string;
  username: string;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  role: AgentRole;
  provider: string; // claude | openai | ollama
  model?: string;
  system_prompt?: string;
  avatar_url?: string;
  capabilities: string[];
  created_by?: string;
  created_at: string;
}

export interface Project {
  id: string;
  owner_id: string;
  name: string;
  description?: string;
  vfs_state: VFSState;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface VFSState {
  project_id: string;
  file_tree: VFSFileNode[];
  last_updated: string;
}

export interface VFSFileNode {
  path: string;
  type: 'file' | 'directory';
  version?: number;
}

export interface ChatSession {
  id: string;
  project_id: string;
  owner_id: string;
  title?: string;
  mode: 'single' | 'group';
  is_pinned: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

// REST API Message 类型 (与 UnifiedMessage 同构)
export interface Message {
  id: string;
  session_id: string;
  sender_type: SenderType;
  sender_role?: AgentRole | null;
  type: 'text' | 'code' | 'diff' | 'artifact' | 'deploy';
  content: string;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  status: 'pending' | 'streaming' | 'completed' | 'failed';
  created_at: string;
}

export interface CodeDiff {
  id: string;
  message_id: string;
  project_id: string;
  file_path: string;
  old_content?: string;
  new_content: string;
  diff_summary?: string;
  status: DiffStatus;
  created_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  session_id?: string;
  parent_task_id?: string;
  title: string;
  description?: string;
  status: TaskStatus;
  assignee?: AgentRole;
  priority: number;
  created_at: string;
  updated_at: string;
}

// ========== API 请求/响应类型 ==========

export interface CreateSessionRequest {
  project_id: string;
  title?: string;
  mode?: 'single' | 'group';
}

export interface CreateSessionResponse {
  session: ChatSession;
}

export interface GetMessagesRequest {
  session_id: string;
  limit?: number;
  before?: string; // message_id，游标分页
}

export interface GetMessagesResponse {
  messages: Message[];
  has_more: boolean;
  next_cursor?: string;
}

// ========== 工具类型 ==========

/** 从 UnifiedServerMessage 联合类型中提取特定类型 */
export type ExtractServerMessage<T extends UnifiedMessageType> = Extract<UnifiedServerMessage, { type: T }>;

/** 从 ClientMessage 联合类型中提取特定类型 */
export type ExtractClientMessage<T extends ClientAction> = Extract<ClientMessage, { action: T }>;

// ========== 前端本地状态类型 ==========

export interface StreamState {
  stream_id: string;
  message_id: string;
  accumulated_content: string;
  agent_role: AgentRole;
  is_final: boolean;
}
