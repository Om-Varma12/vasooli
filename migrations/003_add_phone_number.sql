-- Migration: Add phone number tracking to recovery events
-- Description: Enable lookup of RecoveryEvents by WhatsApp phone number for webhook identification

BEGIN;

ALTER TABLE public.recovery_events
ADD COLUMN phone_number TEXT;

CREATE INDEX idx_recovery_events_phone_number ON public.recovery_events(phone_number);

COMMIT;
