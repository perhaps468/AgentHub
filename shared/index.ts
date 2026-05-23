// =============================================================================
// AgentHub - 跨端 TypeScript 类型定义
// Source of Truth: shared/schemas/ws_messages.json
// 本文件从 JSON Schema 派生，前后端共享同一份类型定义。
// =============================================================================

// ========== 枚举类型 ==========

export type AgentRole = 'Human' | 'PM' | 'Planner' | 'Coder' | 'Reviewer' | 'System';

export type MessageType =
  | 'chat_stream'
  | 'task_update'
  | 'code_diff'
  | 'system_status'
  | 'vfs_update'
  | 'agent_typing'
  | 'deployment_status'
  | 'error';

export type ClientAction = 'send_message' | 'accept_code' | 'reject_code' | 'deploy';

export type TaskStatus = 'pending' | 'doing' | 'done' | 'rejected';

export type DiffStatus = 'pending' | 'accepted' | 'rejected';

export type ProjectStatus = 'active' | 'archived' | 'deleted';

export type ContentType = 'text' | 'code' | 'image' | 'file' | 'diff' | 'preview';

export type SenderType = 'human' | 'agent' | 'system';

// ========== 基础类型 ==========

export interface BaseMessage {
  type: MessageType;
  agent_role: AgentRole;
  timestamp: string; // ISO 8601
  stream_id: string; // 用于追踪同一消息的多个 chunk
}

// ========== 服务端 → 客户端 消息类型 ==========

export interface ChatStreamMessage extends BaseMessage {
  type: 'chat_stream';
  message_id: string;
  content_chunk: string; // 按句子 chunk，非逐 token
  is_final: boolean;
}

export interface TaskItem {
  id: string;
  title: string;
  description?: string;
  status: TaskStatus;
  assignee: AgentRole;
  priority?: number;
  dependencies?: string[];
}

export interface TaskUpdateMessage extends BaseMessage {
  type: 'task_update';
  tasks: TaskItem[];
}

export interface CodeDiffMessage extends BaseMessage {
  type: 'code_diff';
  diff_id: string;
  file_path: string;
  old_content: string;
  new_content: string; // 完整文件内容
  diff_summary: string;
  status: DiffStatus;
}

export interface SystemStatusMessage extends BaseMessage {
  type: 'system_status';
  status: 'connected' | 'disconnected' | 'phase_changed' | 'agent_joined' | 'agent_left';
  message: string;
  phase?: 'requirement' | 'planning' | 'coding' | 'review' | 'done';
}

export interface VFSUpdateMessage extends BaseMessage {
  type: 'vfs_update';
  action: 'create' | 'update' | 'delete' | 'accepted' | 'rejected';
  file_path: string;
  version?: number;
  diff_id?: string;
}

export interface AgentTypingMessage extends BaseMessage {
  type: 'agent_typing';
  is_typing: boolean;
  message?: string;
}

export interface DeploymentStatusMessage extends BaseMessage {
  type: 'deployment_status';
  project_id: string;
  status: 'pending' | 'building' | 'success' | 'failed';
  preview_url?: string;
  message?: string;
}

export type ErrorCode =
  | 'llm_timeout'
  | 'vfs_conflict'
  | 'invalid_request'
  | 'session_not_found'
  | 'unknown'
  | 'provider_not_configured'
  | 'provider_request_failed'
  | 'provider_response_invalid'
  | 'agent_busy';

export interface ErrorMessage extends BaseMessage {
  type: 'error';
  error_code: ErrorCode;
  error_message: string;
  diff_id?: string;
}

export type ServerMessage =
  | ChatStreamMessage
  | TaskUpdateMessage
  | CodeDiffMessage
  | SystemStatusMessage
  | VFSUpdateMessage
  | AgentTypingMessage
  | DeploymentStatusMessage
  | ErrorMessage;

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

export interface Message {
  id: string;
  session_id: string;
  sender_type: SenderType;
  sender_id?: string;
  sender_role?: AgentRole;
  content: string;
  content_type: ContentType;
  delivery_status?: 'completed' | 'interrupted';
  metadata: Record<string, unknown>;
  is_pinned: boolean;
  parent_message_id?: string;
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

/** 从 ServerMessage 联合类型中提取特定类型 */
export type ExtractServerMessage<T extends MessageType> = Extract<ServerMessage, { type: T }>;

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
