-- Bind sessions to a selected agent so runtime can route by session choice.

ALTER TABLE sessions
  ADD COLUMN IF NOT EXISTS agent_id VARCHAR(50) NULL
  COMMENT 'Selected agent ID for this session'
  AFTER workspace_id;

CREATE INDEX IF NOT EXISTS idx_sessions_agent_id ON sessions (agent_id);
