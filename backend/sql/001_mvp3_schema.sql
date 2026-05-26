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
  type VARCHAR(20) NOT NULL DEFAULT 'text',
  status VARCHAR(20) NOT NULL DEFAULT 'completed',
  payload JSON NOT NULL DEFAULT '{}',
  msg_metadata JSON NOT NULL DEFAULT '{}',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_messages_session_created (session_id, created_at),
  CONSTRAINT chk_messages_sender_type CHECK (sender_type IN ('human', 'agent', 'system')),
  CONSTRAINT chk_messages_type CHECK (type IN ('text', 'code', 'diff', 'artifact', 'deploy')),
  CONSTRAINT chk_messages_status CHECK (status IN ('pending', 'streaming', 'completed', 'failed')),
  CONSTRAINT fk_messages_session
    FOREIGN KEY (session_id)
    REFERENCES sessions(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
 id              BIGINT UNSIGNED   PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
 username        VARCHAR(50)       NOT NULL UNIQUE COMMENT '登录用户名，同时也是显示名称',
 password        VARCHAR(255)      NOT NULL COMMENT '登录密码（明文）',
 avatar          VARCHAR(500)      DEFAULT NULL COMMENT '头像URL',
 created_at      DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 新增测试用户
INSERT INTO users (username, password) VALUES
   ('gy', 'admin123'),
   ('ljw', 'admin123');
