"""
Tier-2 classification: LLM fallback for whatever the rule tier couldn't confidently bucket
(reason_code == "unclassified_bank_response" in the synthetic batch, ~8% of records).

STATUS: Live. Calls Groq Cloud Inference to classify bank decline signals.
Provides fail-open degradation to UNKNOWN if credentials are missing or API fails.
"""
import os
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

from ..models import RootCause
from ..llm_config import LLM_MODEL
from ..audit.dead_letter import write as dlq_write

# Load environment variables at module load
load_dotenv()

CONFIDENCE_THRESHOLD = 0.6
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "llm_classify.txt"

logger = logging.getLogger("vasooli.classify")


def _load_prompt_template() -> str:
    """Safely load the prompt template from file, with inline fallback if missing."""
    try:
        if PROMPT_PATH.exists():
            return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to load prompt template from {PROMPT_PATH}: {e}")

    # Fallback inline template in case of disk issues
    return """
System:
You are an expert financial transaction classification assistant for Vasooli.
Allowed Root Causes: insufficient_funds, bank_downtime, mandate_expired, risk_block.
Input:
- Webhook Event: {webhook_event}
- Payment Method: {payment_method}
- Category: {category}
- Amount: INR {amount_inr}
- Decline Reason Code: {reason_code}
- Retry Count So Far: {retry_count_so_far}
- Customer Risk Tier: {customer_risk_tier}
- Days Overdue: {days_overdue}
- Past Bounce Count: {past_bounce_count}
- Past Bounce Reasons: {past_bounce_reasons}

Instructions:
Classify into one allowed root cause. Return a raw JSON object with keys: "cause", "reason", "confidence".
"""


def classify_by_llm(event) -> tuple[RootCause, str, float]:
    """Public entrypoint for LLM classification fallback."""
    cause, reason, confidence = _call_llm(event)
    if confidence < CONFIDENCE_THRESHOLD:
        reason += (
            f" [confidence {confidence:.2f} below threshold {CONFIDENCE_THRESHOLD} — "
            "should route to human-review queue]"
        )
    return cause, reason, confidence


def _call_llm(event) -> tuple[RootCause, str, float]:
    """Infers root cause from decline event using Groq Cloud API."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not configured in env. Falling back to UNKNOWN.")
        return (
            RootCause.UNKNOWN,
            f"GROQ_API_KEY missing - bypassed LLM classification for reason_code='{event.reason_code}'",
            0.0,
        )

    # 1. Format the prompt
    try:
        template = _load_prompt_template()
        prompt_text = template.format(
            webhook_event=event.webhook_event,
            payment_method=event.payment_method.value if hasattr(event.payment_method, "value") else str(event.payment_method),
            category=event.category.value if hasattr(event.category, "value") else str(event.category),
            amount_inr=event.amount_inr,
            reason_code=event.reason_code,
            retry_count_so_far=event.retry_count_so_far,
            customer_risk_tier=event.customer_risk_tier,
            days_overdue=event.days_overdue,
            past_bounce_count=event.past_bounce_count,
            past_bounce_reasons=json.dumps(event.past_bounce_reasons),
        )
    except Exception as e:
        err_msg = f"Failed to format prompt template: {e}"
        logger.error(err_msg)
        dlq_write(record_id=event.record_id, stage="classify", error=err_msg)
        return RootCause.UNKNOWN, err_msg, 0.0

    # 2. Call Groq
    try:
        client = Groq(api_key=api_key)
        # qwen/qwen3.8-27b on Groq generally supports json_object format
        completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        response_content = completion.choices[0].message.content or ""
    except Exception as e:
        err_msg = f"Groq API call failed: {e}"
        logger.error(err_msg)
        dlq_write(record_id=event.record_id, stage="classify", error=err_msg)
        return RootCause.UNKNOWN, err_msg, 0.0

    # 3. Parse JSON response
    try:
        cleaned_content = response_content.strip()
        # Handle cases where LLM returns markdown code blocks wrapping the JSON
        if cleaned_content.startswith("```"):
            start = cleaned_content.find("{")
            end = cleaned_content.rfind("}")
            if start != -1 and end != -1:
                cleaned_content = cleaned_content[start:end+1]

        data = json.loads(cleaned_content)
        cause_str = data.get("cause", "").lower().strip()
        reason = data.get("reason", "LLM classified")
        confidence = float(data.get("confidence", 0.0))

        # Map to enum
        try:
            cause_enum = RootCause(cause_str)
            # We don't allow LLM to override cancellation intent gate
            if cause_enum == RootCause.CANCELLATION_INTENT:
                cause_enum = RootCause.UNKNOWN
                reason = f"LLM incorrectly returned cancellation_intent. Details: {reason}"
        except ValueError:
            logger.warning(f"LLM returned invalid RootCause value '{cause_str}'. Defaulting to UNKNOWN.")
            cause_enum = RootCause.UNKNOWN
            reason = f"LLM returned invalid cause '{cause_str}'. Details: {reason}"

        return cause_enum, reason, confidence

    except (json.JSONDecodeError, ValueError, TypeError) as e:
        err_msg = f"LLM classification parsing failed. Raw response: {response_content!r}. Error: {e}"
        logger.error(err_msg)
        dlq_write(record_id=event.record_id, stage="classify", error=err_msg)
        return RootCause.UNKNOWN, f"Parsing failed for LLM response: {e}", 0.0
