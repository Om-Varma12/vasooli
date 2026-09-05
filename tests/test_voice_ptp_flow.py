import asyncio
import json
import pytest
import redis
from httpx import AsyncClient
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

# Import from the app
from src.vasooli.api.main import app
from src.vasooli.api.deps import AsyncSessionLocal
from src.vasooli.api.routes.voice import redis_client
from src.vasooli.models import RecoveryEvent, PromiseToPay
from sqlalchemy import select

@pytest.mark.asyncio
async def test_voice_ptp_flow():
    """
    Test the end-to-end Voice PTP flow:
    1. Setup session in Redis
    2. Call /voice/init -> Check TwiML
    3. Call /voice/handle-response -> Check DB capture
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # --- Setup Mock Data ---
        token = "test-call-token-123"
        record_id = "rec_test_001"
        customer_id = "cust_test_001"
        amount = 1500.0
        merchant_id = "TestMerchant"

        # Manually seed Redis session as VoiceAdapter would
        session_context = {
            "record_id": record_id,
            "customer_id": customer_id,
            "amount_inr": amount,
            "merchant_id": merchant_id,
        }
        redis_client.set(f"voice:session:{token}", json.dumps(session_context), ex=3600)

        # Mock RecoveryEvent in DB
        async with AsyncSessionLocal() as db:
            # Clean up first
            # await db.execute(...)
            event = RecoveryEvent(
                record_id=record_id,
                customer_id=customer_id,
                amount_inr=amount,
                merchant_id=merchant_id,
                phone_number="+919876543210",
                promise_captured=False
            )
            db.add(event)
            await db.commit()

        # --- Step 1: Voice Init ---
        response_init = await ac.post(f"/voice/init?token={token}")
        assert response_init.status_code == 200
        assert "text/xml" in response_init.headers["content-type"]
        assert "Namaste!" in response_init.text
        assert "Gather" in response_init.text

        # --- Step 2: Handle Response (DTMF Promise) ---
        # Simulate Twilio sending a POST request with Digits=1
        response_handle = await ac.post(
            f"/voice/handle-response?token={token}",
            data={"Digits": "1"}
        )
        assert response_handle.status_code == 200
        assert "Dhanyawad" in response_handle.text

        # --- Step 3: Verify DB Persistence ---
        async with AsyncSessionLocal() as db:
            # Verify RecoveryEvent is updated
            res = await db.execute(select(RecoveryEvent).where(RecoveryEvent.record_id == record_id))
            event_updated = res.scalar_one()
            assert event_updated.promise_captured is True

            # Verify PromiseToPay record exists
            res_ptp = await db.execute(select(PromiseToPay).where(PromiseToPay.record_id == record_id))
            ptp_record = res_ptp.scalar_one()
            assert ptp_record is not None
            assert ptp_record.promised_amount == amount
            assert ptp_record.status == "pending"

        print("\nVoice PTP Flow Verified Successfully!")

if __name__ == "__main__":
    asyncio.run(test_voice_ptp_flow())
