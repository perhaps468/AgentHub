CREATE TABLE IF NOT EXISTS sessions (
  id CHAR(36) PRIMARY KEY,
  owner_id VARCHAR(100) NOT NULL,
  title VARCHAR(255),
  mode VARCHAR(20) NOT NULL DEFAULT 'single',
  is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
  is_archived BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_sessions_owner_updated (owner_id, updated_at),
  INDEX idx_sessions_archived (owner_id, is_archived),
  CONSTRAINT chk_sessions_mode CHECK (mode IN ('single', 'group'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS messages (
  id CHAR(36) NOT NULL,
  session_id CHAR(36) NOT NULL,
  sender_type VARCHAR(20) NOT NULL,
  sender_role VARCHAR(50) DEFAULT NULL,
  content TEXT NOT NULL,
  content_type VARCHAR(20) NOT NULL DEFAULT 'text',
  delivery_status VARCHAR(20) NOT NULL DEFAULT 'completed',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_messages_session_created (session_id, created_at),
  CONSTRAINT fk_messages_session FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE,
  CONSTRAINT chk_messages_content_type CHECK (content_type = 'text'),
  CONSTRAINT chk_messages_sender_type CHECK (sender_type IN ('human', 'agent', 'system'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
