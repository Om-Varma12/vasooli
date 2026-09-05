import asyncio
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

# Database URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vasooli.seed")

async def seed_data():
    import asyncpg

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # 1. Clear existing data to avoid duplicates for the demo
        logger.info("Clearing existing demo data...")
        await conn.execute("DELETE FROM audit_log")
        await conn.execute("DELETE FROM promise_to_pay")
        await conn.execute("DELETE FROM recovery_events")

        # 2. Define the demo records
        # Structure: (record_id, customer, merchant, amount, root_cause, channel, tier, status, recovery_state, retries, promise_captured, message)
        records = [
            ("rec_om_001", "Om Varma", "Razorpay", 15000.0, "insufficient_funds", "voice", "high_value", "recovered", "RECOVERED", 1, True, "Call Transcript: Customer agreed to pay by Friday. Verified account balance issues."),
            ("rec_sarah_002", "Sarah Jenkins", "Netflix", 4500.0, "bank_downtime", "whatsapp", "standard", "pending", "RETRYING", 2, False, "WhatsApp: Hello Sarah, your payment failed due to bank downtime. Please try again."),
            ("rec_arjun_003", "Arjun Mehta", "LendingCorp", 25000.0, "risk_block", "none", "high_value", "stopped", "STOPPED", 5, False, None),
            ("rec_emily_004", "Emily Chen", "Spotify", 1200.0, "unknown", "pending", "standard", "pending", "PENDING", 0, False, None),
            ("rec_vikram_005", "Vikram Singh", "Zomato", 8000.0, "mandate_expired", "voice", "standard", "recovered", "RECOVERED", 1, True, "Call Transcript: Customer re-authorized the mandate during the call."),
            ("rec_chloe_006", "Chloe Dupont", "Apple", 6000.0, "insufficient_funds", "whatsapp", "standard", "unresolved", "RETRYING", 3, False, "WhatsApp: Hi Chloe, your Apple payment failed. Please top up your account."),
        ]

        for rec in records:
            rid, cust, merch, amt, rc, chan, tier, stat, rstate, retries, prom, msg = rec

            # Insert RecoveryEvent
            await conn.execute(
                """
                INSERT INTO recovery_events
                (record_id, customer_id, merchant_id, amount_inr, root_cause, channel, tier, status, retry_count, amount_recovered_inr, promise_captured, recovery_state, created_at, message_or_transcript)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                """,
                rid, cust, merch, amt, rc, chan, tier, stat, retries, (amt if stat == "recovered" else 0.0), prom, rstate, datetime.now() - timedelta(days=2), msg
            )

            # Insert Audit Logs to make the Audit Panel look real
            # Every record gets at least a 'classify' and 'policy' entry
            await conn.execute(
                "INSERT INTO audit_log (record_id, step, detail, created_at) VALUES ($1, $2, $3, $4)",
                rid, "classify", f"Diagnosed as {rc} with high confidence.", datetime.now() - timedelta(days=2)
            )
            await conn.execute(
                "INSERT INTO audit_log (record_id, step, detail, created_at) VALUES ($1, $2, $3, $4)",
                rid, "policy", f"Routed to {chan} based on {tier} tier policy.", datetime.now() - timedelta(days=2)
            )

            if chan != "none":
                await conn.execute(
                    "INSERT INTO audit_log (record_id, step, detail, created_at) VALUES ($1, $2, $3, $4)",
                    rid, f"execute:{chan}", f"Intervention triggered via {chan}.", datetime.now() - timedelta(days=1)
                )

            if stat == "recovered":
                await conn.execute(
                    "INSERT INTO audit_log (record_id, step, detail, created_at) VALUES ($1, $2, $3, $4)",
                    rid, "outcome", f"succeeded=True amount_recovered_inr={amt}", datetime.now() - timedelta(hours=12)
                )

            # If promise was captured, add a PTP record
            if prom:
                await conn.execute(
                    """
                    INSERT INTO promise_to_pay (record_id, customer_id, promised_amount, promised_date, status, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    rid, cust, amt, datetime.now().date() + timedelta(days=3), ("kept" if stat == "recovered" else "pending"), datetime.now() - timedelta(days=1)
                )

        logger.info("✅ Demo data seeded successfully!")

    except Exception as e:
        logger.error(f"❌ Seeding failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
