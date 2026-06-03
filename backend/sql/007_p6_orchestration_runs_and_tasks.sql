-- P6 M1/M3: orchestration run/task persistence for multi-agent group execution.
-- Adds orchestration_runs and orchestration_tasks used by planning and subtask execution.

CREATE TABLE IF NOT EXISTS orchestration_runs (
  id CHAR(36) PRIMARY KEY,
  session_id CHAR(36) NOT NULL,
  trigger_message_id CHAR(36) NOT NULL,
  planner_agent_id VARCHAR(50) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'planned',
  summary TEXT DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_orchestration_runs_session_id (session_id),
  INDEX idx_orchestration_runs_trigger_message_id (trigger_message_id),
  INDEX idx_orchestration_runs_planner_agent_id (planner_agent_id),
  CONSTRAINT fk_orchestration_runs_session
    FOREIGN KEY (session_id)
    REFERENCES sessions(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_orchestration_runs_trigger_message
    FOREIGN KEY (trigger_message_id)
    REFERENCES messages(id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE IF NOT EXISTS orchestration_tasks (
  id CHAR(36) PRIMARY KEY,
  run_id CHAR(36) NOT NULL,
  parent_task_id CHAR(36) DEFAULT NULL,
  sequence INT NOT NULL,
  assigned_agent_id VARCHAR(50) NOT NULL,
  kind VARCHAR(50) NOT NULL DEFAULT 'file_write',
  title VARCHAR(255) NOT NULL,
  goal TEXT NOT NULL,
  input_payload JSON NOT NULL,
  result_payload JSON DEFAULT NULL,
  error_payload JSON DEFAULT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'planned',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_orchestration_tasks_run_id (run_id),
  INDEX idx_orchestration_tasks_parent_task_id (parent_task_id),
  INDEX idx_orchestration_tasks_assigned_agent_id (assigned_agent_id),
  CONSTRAINT fk_orchestration_tasks_run
    FOREIGN KEY (run_id)
    REFERENCES orchestration_runs(id)
    ON DELETE CASCADE,
  CONSTRAINT fk_orchestration_tasks_parent_task
    FOREIGN KEY (parent_task_id)
    REFERENCES orchestration_tasks(id)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
