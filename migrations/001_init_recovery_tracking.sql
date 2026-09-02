-- Migration: Create Recovery Events, Promises, and Audit Log tables
-- Description: Transition from simple aggregates to detailed event-level tracking

BEGIN;

-- 1. Recovery Events Table
-- The primary source of truth for the dashboard
CREATE TABLE IF NOT EXISTS public.recovery_events (
    record_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    merchant_id TEXT NULL,
    amount_inr NUMERIC NOT NULL,
    root_cause TEXT NOT NULL,
    channel TEXT NOT NULL,              -- retry | whatsapp | voice | human_handoff
    tier TEXT NOT NULL,                 -- retry | whatsapp | voice | human_handoff | stopped
    status TEXT NOT NULL,               -- recovered | pending | unresolved | stopped
    retry_count_so_far INTEGER NULL DEFAULT 0,
    message_or_transcript TEXT NULL,
    reason TEXT NULL,                   -- the decide-layer's plain-language reason
    amount_recovered_inr NUMERIC NULL DEFAULT 0,
    promise_captured BOOLEAN NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT recovery_events_pkey PRIMARY KEY (record_id)
);

-- 2. Promise to Pay Table
-- Tracks commitments made during voice calls
CREATE TABLE IF NOT EXISTS public.promise_to_pay (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    promised_amount NUMERIC NOT NULL,
    promised_date DATE NULL,
    status TEXT NOT NULL DEFAULT 'pending',   -- pending | kept | broken
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE NULL,
    CONSTRAINT promise_to_pay_record_fkey FOREIGN KEY (record_id) REFERENCES recovery_events (record_id)
);

-- 3. Audit Log Table
-- Structured version of the audit trail
CREATE TABLE IF NOT EXISTS public.audit_log (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    record_id TEXT NOT NULL,
    step TEXT NOT NULL,       -- classify | policy | execute:<channel> | outcome
    detail TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT audit_log_record_fkey FOREIGN KEY (record_id) REFERENCES recovery_events (record_id)
);

COMMIT;
