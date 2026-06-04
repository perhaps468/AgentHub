-- P6 M4: Add task-aware columns to pending_changes table.
-- Enables attribution of pending changes to orchestration runs/tasks.
-- MySQL compatible, idempotent.
-- 执行方式: 在 MySQL Workbench/Navicat 中直接运行，或 mysql 命令行 source 执行。

DELIMITER //

-- Step 1: Add run_id column (idempotent)
DROP PROCEDURE IF EXISTS add_run_id_column//
CREATE PROCEDURE add_run_id_column()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'pending_changes'
      AND COLUMN_NAME = 'run_id'
  ) THEN
    ALTER TABLE pending_changes ADD COLUMN run_id CHAR(36) NULL COMMENT 'Associated orchestration run ID' AFTER applied_at;
  END IF;
END//

-- Step 2: Add task_id column (idempotent)
DROP PROCEDURE IF EXISTS add_task_id_column//
CREATE PROCEDURE add_task_id_column()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'pending_changes'
      AND COLUMN_NAME = 'task_id'
  ) THEN
    ALTER TABLE pending_changes ADD COLUMN task_id CHAR(36) NULL COMMENT 'Associated orchestration task ID' AFTER run_id;
  END IF;
END//

-- Step 3: Add agent_id column (idempotent)
DROP PROCEDURE IF EXISTS add_agent_id_column//
CREATE PROCEDURE add_agent_id_column()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'pending_changes'
      AND COLUMN_NAME = 'agent_id'
  ) THEN
    ALTER TABLE pending_changes ADD COLUMN agent_id VARCHAR(50) NULL COMMENT 'Agent that generated this change' AFTER task_id;
  END IF;
END//

-- Step 4: Add batch_id column (idempotent)
DROP PROCEDURE IF EXISTS add_batch_id_column//
CREATE PROCEDURE add_batch_id_column()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'pending_changes'
      AND COLUMN_NAME = 'batch_id'
  ) THEN
    ALTER TABLE pending_changes ADD COLUMN batch_id CHAR(36) NULL COMMENT 'Batch identifier for multi-change tasks' AFTER agent_id;
  END IF;
END//

-- Step 5: Add index for run_id (idempotent)
DROP PROCEDURE IF EXISTS add_idx_run_id//
CREATE PROCEDURE add_idx_run_id()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'pending_changes'
      AND INDEX_NAME = 'idx_pending_changes_run_id'
  ) THEN
    CREATE INDEX idx_pending_changes_run_id ON pending_changes (run_id);
  END IF;
END//

-- Step 6: Add index for task_id (idempotent)
DROP PROCEDURE IF EXISTS add_idx_task_id//
CREATE PROCEDURE add_idx_task_id()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.STATISTICS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'pending_changes'
      AND INDEX_NAME = 'idx_pending_changes_task_id'
  ) THEN
    CREATE INDEX idx_pending_changes_task_id ON pending_changes (task_id);
  END IF;
END//

-- Execute all procedures
CALL add_run_id_column()//
CALL add_task_id_column()//
CALL add_agent_id_column()//
CALL add_batch_id_column()//
CALL add_idx_run_id()//
CALL add_idx_task_id()//

-- Cleanup procedures
DROP PROCEDURE IF EXISTS add_run_id_column//
DROP PROCEDURE IF EXISTS add_task_id_column//
DROP PROCEDURE IF EXISTS add_agent_id_column//
DROP PROCEDURE IF EXISTS add_batch_id_column//
DROP PROCEDURE IF EXISTS add_idx_run_id//
DROP PROCEDURE IF EXISTS add_idx_task_id//

DELIMITER ;

-- Verify final schema
DESCRIBE pending_changes;
