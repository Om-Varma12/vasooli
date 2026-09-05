import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional
from ..models import RecoveryEvent

logger = logging.getLogger("vasooli.services.sequencer")

class SequencerService:
    """
    The 'Brain' of the Mandate Sequencer.
    Handles retry intervals, state transitions, and compliance guardrails.
    """

    # Max retries before we stop and escalate
    MAX_RETRIES = 5

    # Backoff durations based on failure reason (in hours)
    BACKOFF_CONFIG = {
        "bank_downtime": 6,
        "insufficient_funds": 24,
        "timeout": 1,
        "otp_timeout": 2,
        "default": 12
    }

    @staticmethod
    def calculate_next_retry(last_reason: Optional[str]) -> datetime:
        """
        Calculates the next retry timestamp based on the failure reason.
        """
        reason = (last_reason or "default").lower()

        # Match reason to config, fallback to default
        delay_hours = SequencerService.BACKOFF_CONFIG.get(
            next((k for k in SequencerService.BACKOFF_CONFIG if k in reason), "default"),
            SequencerService.BACKOFF_CONFIG["default"]
        )

        return datetime.now().astimezone() + timedelta(hours=delay_hours)

    @staticmethod
    def determine_next_state(event: RecoveryEvent) -> str:
        """
        Determines the next state of the recovery process.
        Logic:
        - If retry_count >= MAX_RETRIES -> STOPPED
        - If last_failure_reason is terminal (e.g. account closed) -> FAILED
        - Else -> RETRYING
        """
        if event.retry_count >= SequencerService.MAX_RETRIES:
            logger.info(f"Max retries reached for {event.record_id}. Stopping.")
            return "STOPPED"

        reason = (event.last_failure_reason or "").lower()
        terminal_reasons = ["account_closed", "mandate_cancelled", "risk_block"]

        if any(term in reason for term in terminal_reasons):
            logger.info(f"Terminal failure for {event.record_id}: {reason}. Marking as FAILED.")
            return "FAILED"

        return "RETRYING"

    @staticmethod
    def should_execute(event: RecoveryEvent) -> bool:
        """
        Final check before execution:
        - State must be RETRYING
        - Current time must be >= next_retry_at
        - Must not be on a holiday/weekend (Simplified for now)
        """
        if event.recovery_state != "RETRYING":
            return False

        if event.next_retry_at and datetime.now().astimezone() < event.next_retry_at:
            return False

        return True
