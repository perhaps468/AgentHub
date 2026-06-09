-- Migration: 009
-- Description: Migrate users.avatar column from VARCHAR(500) to LONGTEXT to support longer avatar URLs
-- Author: system
-- Date: 2026-06-05

ALTER TABLE `users` MODIFY COLUMN `avatar` LONGTEXT NULL DEFAULT NULL COMMENT '用户头像';
