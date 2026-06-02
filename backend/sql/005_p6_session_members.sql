-- P6: Create session_members table for group chat membership persistence.
-- Stores the primary agent and additional group members for each session.

CREATE TABLE IF NOT EXISTS session_members (
  id CHAR(36) PRIMARY KEY,
  session_id CHAR(36) NOT NULL,
  member_type VARCHAR(20) NOT NULL,
  member_id VARCHAR(100) NOT NULL,
  is_primary BOOLEAN NOT NULL DEFAULT FALSE,
  health_status VARCHAR(20) NOT NULL DEFAULT 'connected',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_session_members_session_id (session_id),
  INDEX idx_session_members_member_lookup (member_type, member_id),
  UNIQUE KEY uq_session_member (session_id, member_type, member_id),
  CONSTRAINT fk_session_members_session
    FOREIGN KEY (session_id)
    REFERENCES sessions(id)
    ON DELETE CASCADE,
  CONSTRAINT chk_session_members_member_type
    CHECK (member_type IN ('agent', 'user'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
