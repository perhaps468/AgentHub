-- P8: Add planning_source to orchestration_runs and new fields to orchestration_tasks
-- Idempotent migration - can be safely run multiple times.
-- 执行方式: 在 MySQL Workbench/Navicat 中直接运行，或 mysql 命令行 source 执行。

DELIMITER //

-- Part 1: Add planning_source to orchestration_runs
DROP PROCEDURE IF EXISTS add_planning_source_column//
CREATE PROCEDURE add_planning_source_column()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orchestration_runs'
      AND COLUMN_NAME = 'planning_source'
  ) THEN
    ALTER TABLE orchestration_runs
      ADD COLUMN planning_source VARCHAR(50) NULL DEFAULT 'fallback_splitter'
      COMMENT 'Source of task planning (fallback_splitter, llm_planner, etc.)';
  END IF;
END//

-- Part 2: Add client_task_id to orchestration_tasks
DROP PROCEDURE IF EXISTS add_client_task_id_column//
CREATE PROCEDURE add_client_task_id_column()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orchestration_tasks'
      AND COLUMN_NAME = 'client_task_id'
  ) THEN
    ALTER TABLE orchestration_tasks
      ADD COLUMN client_task_id VARCHAR(50) NULL
      COMMENT 'Client-provided task identifier for tracking';
  END IF;
END//

-- Part 3: Add assignment_reason to orchestration_tasks
DROP PROCEDURE IF EXISTS add_assignment_reason_column//
CREATE PROCEDURE add_assignment_reason_column()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orchestration_tasks'
      AND COLUMN_NAME = 'assignment_reason'
  ) THEN
    ALTER TABLE orchestration_tasks
      ADD COLUMN assignment_reason TEXT NULL
      COMMENT 'Reason for assigning this task to the agent';
  END IF;
END//

-- Part 4: Add depends_on to orchestration_tasks
DROP PROCEDURE IF EXISTS add_depends_on_column//
CREATE PROCEDURE add_depends_on_column()
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'orchestration_tasks'
      AND COLUMN_NAME = 'depends_on'
  ) THEN
    ALTER TABLE orchestration_tasks
      ADD COLUMN depends_on JSON NULL DEFAULT (JSON_ARRAY())
      COMMENT 'Array of task IDs this task depends on';
  END IF;
END//

-- Execute all procedures
CALL add_planning_source_column()//
CALL add_client_task_id_column()//
CALL add_assignment_reason_column()//
CALL add_depends_on_column()//

-- Cleanup procedures
DROP PROCEDURE IF EXISTS add_planning_source_column//
DROP PROCEDURE IF EXISTS add_client_task_id_column//
DROP PROCEDURE IF EXISTS add_assignment_reason_column//
DROP PROCEDURE IF EXISTS add_depends_on_column//

DELIMITER ;

-- Verify final schema
DESCRIBE orchestration_runs;
DESCRIBE orchestration_tasks;
