-- Migration 004: Add Mandate Sequencer fields to recovery_events
ALTER TABLE recovery_events ADD COLUMN IF NOT EXISTS recovery_state VARCHAR DEFAULT 'PENDING';
ALTER TABLE recovery_events ADD COLUMN IF NOT EXISTS next_retry_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE recovery_events ADD COLUMN IF NOT EXISTS last_failure_reason VARCHAR;

-- Rename retry_count_so_far to retry_count for consistency with the new model
-- Note: This is only if the column exists as retry_count_so_far
-- ALTER TABLE recovery_events RENAME COLUMN retry_count_so_far TO retry_count;

-- Since I changed the model from retry_count_so_far to retry_count,
-- I'll ensure retry_count exists.
ALTER TABLE recovery_events ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
