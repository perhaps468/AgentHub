-- ============================================================
-- Fixed SQL dump: Phase 1 (CREATE TABLE without FKs, no data)
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username` varchar(50) NOT NULL COMMENT '登录用户名，同时也是显示名称',
  `password` varchar(255) NOT NULL COMMENT '登录密码（明文）',
  `avatar` longtext COMMENT '头像URL或base64',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户表';

DROP TABLE IF EXISTS `sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sessions` (
  `id` char(36) NOT NULL,
  `owner_id` varchar(100) NOT NULL,
  `workspace_id` varchar(36) DEFAULT NULL,
  `agent_id` varchar(50) DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `mode` varchar(20) NOT NULL DEFAULT 'single',
  `is_pinned` tinyint(1) NOT NULL DEFAULT '0',
  `is_archived` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_sessions_owner_updated` (`owner_id`,`updated_at`),
  KEY `idx_sessions_archived` (`owner_id`,`is_archived`),
  KEY `ix_sessions_workspace_id` (`workspace_id`),
  KEY `idx_sessions_agent_id` (`agent_id`),
  CONSTRAINT `chk_sessions_mode` CHECK (mode IN ('single', 'group'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `agents`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `agents` (
  `id` varchar(50) NOT NULL COMMENT 'Agent ID，内置 Agent 使用稳定字符串 ID',
  `owner_id` varchar(100) DEFAULT NULL COMMENT '所属用户 ID；内置 Agent 为 NULL',
  `name` varchar(100) NOT NULL COMMENT 'Agent 展示名称',
  `role` varchar(50) NOT NULL COMMENT 'Agent 角色，如 PM / Coder',
  `provider` varchar(50) NOT NULL DEFAULT 'qwen_openai_compatible' COMMENT 'Provider 标识，如 qwen_openai_compatible / doubao',
  `model` varchar(100) NOT NULL COMMENT '模型标识',
  `system_prompt` text NOT NULL COMMENT 'System Prompt',
  `platform` varchar(20) NOT NULL DEFAULT 'custom' COMMENT 'claude-code / codex / opencode / custom',
  `description` varchar(500) DEFAULT NULL COMMENT 'Agent 简介',
  `avatar_url` varchar(500) DEFAULT NULL COMMENT '头像地址',
  `capability_tags` json NOT NULL COMMENT '能力标签数组',
  `tool_permissions` json NOT NULL COMMENT '工具权限占位字段',
  `is_builtin` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否内置 Agent',
  `is_active` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否可用',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_agents_owner_id` (`owner_id`),
  KEY `idx_agents_is_builtin` (`is_builtin`),
  KEY `idx_agents_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='统一 Agent 表';

DROP TABLE IF EXISTS `workspaces`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workspaces` (
  `id` char(36) NOT NULL,
  `owner_id` varchar(100) NOT NULL,
  `root_path` varchar(512) NOT NULL,
  `name` varchar(255) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_workspaces_owner` (`owner_id`),
  KEY `idx_workspaces_root` (`owner_id`,`root_path`(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `messages`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `messages` (
  `id` char(36) NOT NULL,
  `session_id` char(36) NOT NULL,
  `sender_type` varchar(20) NOT NULL,
  `sender_role` varchar(50) DEFAULT NULL,
  `content` text NOT NULL,
  `type` varchar(20) NOT NULL DEFAULT 'text',
  `status` varchar(20) NOT NULL DEFAULT 'completed',
  `payload` json NOT NULL,
  `msg_metadata` json NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY `idx_messages_session_created` (`session_id`,`created_at`),
  CONSTRAINT `chk_messages_sender_type` CHECK (`sender_type` IN ('human','agent','system')),
  CONSTRAINT `chk_messages_status` CHECK (`status` IN ('pending','streaming','completed','failed')),
  CONSTRAINT `chk_messages_type` CHECK (`type` IN ('text','code','diff','artifact','deploy'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `orchestration_runs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orchestration_runs` (
  `id` char(36) NOT NULL,
  `session_id` char(36) NOT NULL,
  `trigger_message_id` char(36) NOT NULL,
  `planner_agent_id` varchar(50) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'planned',
  `summary` text,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `planning_source` varchar(50) DEFAULT 'fallback_splitter' COMMENT 'Source of task planning (fallback_splitter, llm_planner, etc.)',
  PRIMARY KEY (`id`),
  KEY `idx_orchestration_runs_session_id` (`session_id`),
  KEY `idx_orchestration_runs_trigger_message_id` (`trigger_message_id`),
  KEY `idx_orchestration_runs_planner_agent_id` (`planner_agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `pending_changes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `pending_changes` (
  `id` char(36) NOT NULL,
  `change_id` char(36) NOT NULL,
  `session_id` char(36) NOT NULL,
  `message_id` char(36) DEFAULT NULL,
  `stream_id` char(36) DEFAULT NULL,
  `path` text NOT NULL,
  `operation` varchar(20) NOT NULL,
  `unified_diff` longtext NOT NULL,
  `original_content` text,
  `proposed_content` text,
  `status` varchar(30) NOT NULL DEFAULT 'pending_confirmation',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `applied_at` datetime DEFAULT NULL,
  `run_id` char(36) DEFAULT NULL,
  `task_id` char(36) DEFAULT NULL,
  `agent_id` varchar(50) DEFAULT NULL,
  `batch_id` char(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `change_id` (`change_id`),
  KEY `idx_pending_changes_change_id` (`change_id`),
  KEY `idx_pending_changes_session_id` (`session_id`),
  KEY `idx_pending_changes_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `session_members`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `session_members` (
  `id` char(36) NOT NULL,
  `session_id` char(36) NOT NULL,
  `member_type` varchar(20) NOT NULL,
  `member_id` varchar(100) NOT NULL,
  `is_primary` tinyint(1) NOT NULL DEFAULT '0',
  `health_status` varchar(20) NOT NULL DEFAULT 'connected',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_session_member` (`session_id`,`member_type`,`member_id`),
  KEY `idx_session_members_session_id` (`session_id`),
  KEY `idx_session_members_member_lookup` (`member_type`,`member_id`),
  CONSTRAINT `chk_session_members_member_type` CHECK (`member_type` IN ('agent','user'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

DROP TABLE IF EXISTS `orchestration_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orchestration_tasks` (
  `id` char(36) NOT NULL,
  `run_id` char(36) NOT NULL,
  `parent_task_id` char(36) DEFAULT NULL,
  `sequence` int NOT NULL,
  `assigned_agent_id` varchar(50) NOT NULL,
  `kind` varchar(50) NOT NULL DEFAULT 'file_write',
  `title` varchar(255) NOT NULL,
  `goal` text NOT NULL,
  `input_payload` json NOT NULL,
  `result_payload` json DEFAULT NULL,
  `error_payload` json DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'planned',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `client_task_id` varchar(50) DEFAULT NULL COMMENT 'Client-provided task identifier for tracking',
  `assignment_reason` text COMMENT 'Reason for assigning this task to the agent',
  `depends_on` json DEFAULT (json_array()) COMMENT 'Array of task IDs this task depends on',
  PRIMARY KEY (`id`),
  KEY `idx_orchestration_tasks_run_id` (`run_id`),
  KEY `idx_orchestration_tasks_parent_task_id` (`parent_task_id`),
  KEY `idx_orchestration_tasks_assigned_agent_id` (`assigned_agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- Phase 2: Add FOREIGN KEY constraints in topological order
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

ALTER TABLE `messages` ADD CONSTRAINT `fk_messages_session` FOREIGN KEY (`session_id`) REFERENCES `sessions` (`id`) ON DELETE CASCADE;
ALTER TABLE `orchestration_runs` ADD CONSTRAINT `fk_orchestration_runs_session` FOREIGN KEY (`session_id`) REFERENCES `sessions` (`id`) ON DELETE CASCADE;
ALTER TABLE `pending_changes` ADD CONSTRAINT `fk_pending_changes_session` FOREIGN KEY (`session_id`) REFERENCES `sessions` (`id`) ON DELETE CASCADE;
ALTER TABLE `session_members` ADD CONSTRAINT `fk_session_members_session` FOREIGN KEY (`session_id`) REFERENCES `sessions` (`id`) ON DELETE CASCADE;
ALTER TABLE `orchestration_tasks` ADD CONSTRAINT `fk_orchestration_tasks_run` FOREIGN KEY (`run_id`) REFERENCES `orchestration_runs` (`id`) ON DELETE CASCADE;
ALTER TABLE `orchestration_tasks` ADD CONSTRAINT `fk_orchestration_tasks_parent_task` FOREIGN KEY (`parent_task_id`) REFERENCES `orchestration_tasks` (`id`) ON DELETE SET NULL;

SET FOREIGN_KEY_CHECKS = 1;

-- Done.
