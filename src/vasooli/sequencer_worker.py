"""
Vasooli Sequencer Worker.
Periodically polls the database for due recovery events and triggers the orchestrator.
"""
import asyncio
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import select

from .api.deps import AsyncSessionLocal
from .api.models import RecoveryEvent
from .services.sequencer_service import SequencerService
from .orchestrator import run_one
from .audit.audit_log import AuditLog
from .models import FailureEvent

# Load env vars
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(threadName)s: %(message)s"
)
logger = logging.getLogger("vasooli.sequencer_worker")

# Configuration
POLL_INTERVAL = 60  # Check every 60 seconds

async def process_due_events():
    """
    Finds all events in 'RETRYING' state that are due for retry and processes them.
    """
    async with AsyncSessionLocal() as session:
        # 1. Find due events
        now = datetime.now().astimezone()
        query = (
            select(RecoveryEvent)
            .where(RecoveryEvent.recovery_state == "RETRYING")
            .where(RecoveryEvent.next_retry_at <= now)
        )
        result = await session.execute(query)
        due_events = result.scalars().all()

        if not due_events:
            return

        logger.info(f"Found {len(due_events)} due events for retry.")

        for event in due_events:
            try:
                # 2. Mark as PROCESSING to prevent concurrent execution
                event.recovery_state = "PROCESSING"
                await session.commit()

                # 3. Convert DB model to FailureEvent for the orchestrator
                failure_event = FailureEvent(
                    record_id=event.record_id,
                    merchant_id=event.merchant_id,
                    customer_id=event.customer_id,
                    amount_inr=float(event.amount_inr),
                    retry_count_so_far=event.retry_count,
                    raw_payload={"recovery_state": event.recovery_state}
                )

                # 4. Run through orchestrator
                audit = AuditLog()
                outcome = run_one(failure_event, audit)

                # 5. Update state based on outcome
                event.retry_count += 1

                if outcome["succeeded"]:
                    event.recovery_state = "RECOVERED"
                else:
                    next_state = SequencerService.determine_next_state(event)
                    event.recovery_state = next_state
                    if next_state == "RETRYING":
                        event.next_retry_at = SequencerService.calculate_next_retry(event.reason)
                    else:
                        event.next_retry_at = None

                event.status = "recovered" if outcome["succeeded"] else "pending"
                await session.commit()
                logger.info(f"Processed event {event.record_id} -> {event.recovery_state}")

            except Exception as e:
                logger.error(f"Failed to process event {event.record_id}: {e}")
                event.recovery_state = "RETRYING" # Put it back to retry
                await session.commit()

async def main():
    logger.info("Starting Vasooli Sequencer Worker...")

    while True:
        try:
            await process_due_events()
        except Exception as e:
            logger.error(f"Error in sequencer loop: {e}")

        await asyncio.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    asyncio.run(main())
