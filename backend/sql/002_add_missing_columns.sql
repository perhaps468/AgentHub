-- Migration: Add missing columns to messages table to match ORM model
-- Compatible with MySQL 5.7+

-- Add status column (maps to existing delivery_status data)
ALTER TABLE messages
  ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'completed';

-- Add type column (maps to existing content_type data)
ALTER TABLE messages
  ADD COLUMN type VARCHAR(20) NOT NULL DEFAULT 'text';

-- Add payload column (new field, defaults to empty object)
ALTER TABLE messages
  ADD COLUMN payload JSON NOT NULL DEFAULT ('{}');

-- Add msg_metadata column (new field, defaults to empty object)
ALTER TABLE messages
  ADD COLUMN msg_metadata JSON NOT NULL DEFAULT ('{}');

-- Verify
DESCRIBE messages;
