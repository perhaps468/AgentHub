-- P6 M4: Add task-aware columns to pending_changes table.
-- Enables attribution of pending changes to orchestration runs/tasks.
-- MySQL 5.7 compatible (no IF NOT EXISTS for columns, use procedural approach).

-- Step 1: Add run_id column
SET @run_col_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'pending_changes'
    AND COLUMN_NAME = 'run_id'
);
SET @sql = IF(@run_col_exists = 0,
  'ALTER TABLE pending_changes ADD COLUMN run_id CHAR(36) NULL COMMENT \'Associated orchestration run ID\' AFTER applied_at',
  'SELECT \'run_id already exists\'');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Step 2: Add task_id column
SET @task_col_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'pending_changes'
    AND COLUMN_NAME = 'task_id'
);
SET @sql = IF(@task_col_exists = 0,
  'ALTER TABLE pending_changes ADD COLUMN task_id CHAR(36) NULL COMMENT \'Associated orchestration task ID\' AFTER run_id',
  'SELECT \'task_id already exists\'');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Step 3: Add agent_id column
SET @agent_col_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'pending_changes'
    AND COLUMN_NAME = 'agent_id'
);
SET @sql = IF(@agent_col_exists = 0,
  'ALTER TABLE pending_changes ADD COLUMN agent_id VARCHAR(50) NULL COMMENT \'Agent that generated this change\' AFTER task_id',
  'SELECT \'agent_id already exists\'');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Step 4: Add batch_id column
SET @batch_col_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'pending_changes'
    AND COLUMN_NAME = 'batch_id'
);
SET @sql = IF(@batch_col_exists = 0,
  'ALTER TABLE pending_changes ADD COLUMN batch_id CHAR(36) NULL COMMENT \'Batch identifier for multi-change tasks\' AFTER agent_id',
  'SELECT \'batch_id already exists\'');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Step 5: Add indexes for run_id and task_id (for fast lookups in orchestration scenarios)
SET @idx_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'pending_changes'
    AND INDEX_NAME = 'idx_pending_changes_run_id'
);
SET @sql = IF(@idx_exists = 0,
  'CREATE INDEX idx_pending_changes_run_id ON pending_changes (run_id)',
  'SELECT \'idx_pending_changes_run_id already exists\'');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @idx_exists = (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'pending_changes'
    AND INDEX_NAME = 'idx_pending_changes_task_id'
);
SET @sql = IF(@idx_exists = 0,
  'CREATE INDEX idx_pending_changes_task_id ON pending_changes (task_id)',
  'SELECT \'idx_pending_changes_task_id already exists\'');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verify final schema
DESCRIBE pending_changes;
