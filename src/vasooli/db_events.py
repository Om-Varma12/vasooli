"""
Database utility for recording event-level recovery data.
Handles writes to recovery_events, promise_to_pay, and audit_log.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional
import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv

# Load env file
load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
logger = logging.getLogger("vasooli.db_events")

def get_conn():
    """Return a fresh database connection."""
    if not DB_URL:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(DB_URL)

def write_recovery_event(
    record_id: str,
    customer_id: str,
    merchant_id: Optional[str],
    amount_inr: float,
    root_cause: str,
    channel: str,
    tier: str,
    status: str,
    retry_count: int,
    message: Optional[str],
    reason: Optional[str],
    amount_recovered: float = 0.0,
    promise_captured: bool = False
) -> None:
    """Writes a final record of a recovery attempt to the database."""
    if not DB_URL:
        return

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.recovery_events (
                        record_id, customer_id, merchant_id, amount_inr, root_cause,
                        channel, tier, status, retry_count_so_far,
                        message_or_transcript, reason, amount_recovered_inr, promise_captured
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (record_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        amount_recovered_inr = EXCLUDED.amount_recovered_inr,
                        promise_captured = EXCLUDED.promise_captured;
                """, (
                    record_id, customer_id, merchant_id, amount_inr, root_cause,
                    channel, tier, status, retry_count, message, reason, amount_recovered, promise_captured
                ))
            conn.commit()
    except Exception as e:
        logger.error(f"[db_events] Error writing recovery event for {record_id}: {e}")

def write_promise(
    record_id: str,
    customer_id: str,
    amount: float,
    promised_date: Optional[str],
    status: str = 'pending'
) -> None:
    """Records a commitment to pay made by a customer."""
    if not DB_URL:
        return

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.promise_to_pay (
                        record_id, customer_id, promised_amount, promised_date, status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                """, (record_id, customer_id, amount, promised_date, status))
            conn.commit()
    except Exception as e:
        logger.error(f"[db_events] Error writing promise for {record_id}: {e}")

def write_audit_entry(record_id: str, step: str, detail: str) -> None:
    """Writes a structured audit log entry to the database."""
    if not DB_URL:
        return

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO public.audit_log (record_id, step, detail)
                    VALUES (%s, %s, %s)
                """, (record_id, step, detail))
            conn.commit()
    except Exception as e:
        logger.error(f"[db_events] Error writing audit entry for {record_id}: {e}")
