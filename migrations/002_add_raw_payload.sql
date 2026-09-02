-- Migration: Add raw_payload to recovery_events
-- Description: Stores the original input event for pipeline re-runs (Test Trigger)

BEGIN;

ALTER TABLE public.recovery_events
ADD COLUMN IF NOT EXISTS raw_payload JSONB;

COMMIT;
