"""
Supabase PostgreSQL enrichment database tracking payment profiles.

Maintains a table 'account_history' to record:
- Past bounce count
- Past bounce reason codes
- Last successful payment date
- Per-channel attempts and successes (to calculate response rates)

If the database is unreachable or query fails, it fails open / degrades gracefully
by returning clean defaults rather than crashing the ingestion pipeline.
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


def get_conn():
    """Return a fresh database connection."""
    if not DB_URL:
        raise ValueError("DATABASE_URL environment variable is not set.")
    return psycopg2.connect(DB_URL)


def init_db() -> None:
    """Initialize the account_history table in PostgreSQL if it does not exist."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS account_history (
                        customer_id TEXT PRIMARY KEY,
                        bounce_count INTEGER DEFAULT 0,
                        bounce_reasons TEXT DEFAULT '',
                        last_successful_charge_date TEXT,
                        whatsapp_successes INTEGER DEFAULT 0,
                        whatsapp_attempts INTEGER DEFAULT 0,
                        voice_successes INTEGER DEFAULT 0,
                        voice_attempts INTEGER DEFAULT 0,
                        retry_successes INTEGER DEFAULT 0,
                        retry_attempts INTEGER DEFAULT 0
                    );
                """)
                # Create an index on customer_id (already created since it's PRIMARY KEY)
            conn.commit()
        logging.info("[account_history] Database initialized successfully.")
    except Exception as e:
        logging.error(f"[account_history] Failed to initialize database: {e}")


def get_history(customer_id: str) -> dict:
    """
    Fetch payment history and bounce context for a customer.
    If the customer does not exist or database fails, returns clean defaults.
    """
    default_history = {
        "past_bounce_count": 0,
        "past_bounce_reasons": [],
        "last_successful_charge_date": None,
        "channel_response_rates": {
            "whatsapp_attempts": 0,
            "whatsapp_successes": 0,
            "voice_attempts": 0,
            "voice_successes": 0,
            "retry_attempts": 0,
            "retry_successes": 0,
        }
    }
    if not DB_URL:
        return default_history

    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    "SELECT * FROM account_history WHERE customer_id = %s",
                    (customer_id,)
                )
                row = cur.fetchone()
                if not row:
                    return default_history

                reasons_str = row["bounce_reasons"] or ""
                reasons_list = [r.strip() for r in reasons_str.split(",") if r.strip()]

                return {
                    "past_bounce_count": row["bounce_count"] or 0,
                    "past_bounce_reasons": reasons_list,
                    "last_successful_charge_date": row["last_successful_charge_date"],
                    "channel_response_rates": {
                        "whatsapp_attempts": row["whatsapp_attempts"] or 0,
                        "whatsapp_successes": row["whatsapp_successes"] or 0,
                        "voice_attempts": row["voice_attempts"] or 0,
                        "voice_successes": row["voice_successes"] or 0,
                        "retry_attempts": row["retry_attempts"] or 0,
                        "retry_successes": row["retry_successes"] or 0,
                    }
                }
    except Exception as e:
        logging.error(f"[account_history] Error fetching history for {customer_id}: {e}")
        # Degrade gracefully
        try:
            from ..audit.dead_letter import write as dlq_write
            dlq_write(record_id=customer_id, stage="enrich", error=f"db_fetch_error: {e}")
        except Exception:
            pass
        return default_history


def record_bounce(customer_id: str, reason_code: str) -> None:
    """
    Log a new bounce / failure event. Increments bounce_count and appends reason_code.
    Creates profile record if it does not already exist.
    """
    if not DB_URL:
        return

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Upsert into PostgreSQL
                cur.execute("""
                    INSERT INTO account_history (customer_id, bounce_count, bounce_reasons)
                    VALUES (%s, 1, %s)
                    ON CONFLICT (customer_id) DO UPDATE SET
                        bounce_count = account_history.bounce_count + 1,
                        bounce_reasons = CASE 
                            WHEN account_history.bounce_reasons IS NULL OR account_history.bounce_reasons = '' THEN EXCLUDED.bounce_reasons
                            ELSE account_history.bounce_reasons || ',' || EXCLUDED.bounce_reasons
                        END;
                """, (customer_id, reason_code))
            conn.commit()
    except Exception as e:
        logging.error(f"[account_history] Error recording bounce for {customer_id}: {e}")
        try:
            from ..audit.dead_letter import write as dlq_write
            dlq_write(record_id=customer_id, stage="enrich", error=f"db_record_bounce_error: {e}")
        except Exception:
            pass


def record_outcome(customer_id: str, channel: str, succeeded: bool) -> None:
    """
    Log the outcome of an execution attempt on a channel (whatsapp/voice/retry).
    Increments attempts, updates successes and last_successful_charge_date on success.
    """
    if not DB_URL or channel not in ("whatsapp", "voice", "retry"):
        return

    attempts_col = f"{channel}_attempts"
    successes_col = f"{channel}_successes"
    success_inc = 1 if succeeded else 0
    now_str = datetime.now(timezone.utc).isoformat()

    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                # Dynamic SQL safe here because columns are whitelisted against literal strings
                query = f"""
                    INSERT INTO account_history (
                        customer_id, {attempts_col}, {successes_col}, last_successful_charge_date
                    )
                    VALUES (%s, 1, %s, %s)
                    ON CONFLICT (customer_id) DO UPDATE SET
                        {attempts_col} = account_history.{attempts_col} + 1,
                        {successes_col} = account_history.{successes_col} + %s,
                        last_successful_charge_date = CASE 
                            WHEN %s THEN EXCLUDED.last_successful_charge_date 
                            ELSE account_history.last_successful_charge_date 
                        END;
                """
                cur.execute(query, (customer_id, success_inc, now_str, success_inc, succeeded))
            conn.commit()
    except Exception as e:
        logging.error(f"[account_history] Error recording outcome for {customer_id} on {channel}: {e}")
        try:
            from ..audit.dead_letter import write as dlq_write
            dlq_write(record_id=customer_id, stage="enrich", error=f"db_record_outcome_error: {e}")
        except Exception:
            pass
