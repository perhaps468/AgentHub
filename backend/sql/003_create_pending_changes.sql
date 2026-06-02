-- Migration: Create pending_changes table for Task CE
-- Stores pending file changes that require user confirmation

CREATE TABLE IF NOT EXISTS pending_changes (
  id CHAR(36) PRIMARY KEY,
  change_id CHAR(36) NOT NULL UNIQUE,
  session_id CHAR(36) NOT NULL,
  message_id CHAR(36) DEFAULT NULL,
  stream_id CHAR(36) DEFAULT NULL,
  path TEXT NOT NULL,
  operation VARCHAR(20) NOT NULL,
  unified_diff LONGTEXT NOT NULL,
  original_content TEXT DEFAULT NULL,
  proposed_content TEXT DEFAULT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'pending_confirmation',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  applied_at DATETIME DEFAULT NULL,
  INDEX idx_pending_changes_change_id (change_id),
  INDEX idx_pending_changes_session_id (session_id),
  INDEX idx_pending_changes_status (status),
  CONSTRAINT fk_pending_changes_session
    FOREIGN KEY (session_id)
    REFERENCES sessions(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
