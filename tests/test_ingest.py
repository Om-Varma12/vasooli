import sys
import os
import hmac
import hashlib
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient
from vasooli.ingest.signature import verify_signature
from vasooli.ingest.dedupe_store import already_processed, mark_processed
from vasooli.ingest.queue import enqueue, dequeue
from vasooli.ingest.webhook_receiver import app
from vasooli.worker import parse_webhook_to_event, process_next_event
from vasooli.audit.audit_log import AuditLog


def test_verify_signature():
    secret = "super_secret"
    body = b'{"event": "payment.failed"}'
    
    # Calculate correct signature
    correct_sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    
    assert verify_signature(body, correct_sig, secret) is True
    assert verify_signature(body, "wrong_sig", secret) is False
    assert verify_signature(body, correct_sig, "") is False


def test_deduplication_store():
    # Make sure we're starting clean or using local in-memory
    event_id = "evt_test_12345"
    
    # First check: should not be already processed
    assert already_processed(event_id) is False
    
    # Mark it
    mark_processed(event_id)
    
    # Second check: should be already processed
    assert already_processed(event_id) is True
    
    # Blank/None check
    assert already_processed("") is False


def test_queue_enqueue_dequeue():
    payload = {"id": "evt_queue_1", "event": "payment.failed"}
    
    # Ensure dequeue returns None when empty
    # We drain the queue first in case there is leftovers
    while dequeue() is not None:
        pass
        
    assert dequeue() is None
    
    # Enqueue payload
    enqueue(payload)
    
    # Dequeue it
    retrieved = dequeue()
    assert retrieved == payload
    
    # Queue should now be empty again
    assert dequeue() is None


def test_webhook_receiver_endpoint(monkeypatch):
    client = TestClient(app)
    secret = "webhook_secret"
    
    # Configure env secret using monkeypatch
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", secret)
    
    payload = {
        "id": "evt_webhook_endpoint_test",
        "event": "payment.failed",
        "account_id": "acc_123",
        "payload": {
            "payment": {
                "entity": {
                    "amount": 50000, # 500 INR in paise
                    "method": "upi",
                    "error_code": "insufficient_funds",
                    "notes": {"customer_risk_tier": "high_value", "dnd_flag": False}
                }
            }
        }
    }
    
    body_bytes = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
    
    # Test valid signature request
    response = client.post(
        "/webhooks/razorpay",
        content=body_bytes,
        headers={"X-Razorpay-Signature": sig}
    )
    assert response.status_code == 200
    assert response.json() == {"status": "queued"}
    
    # Test duplicate request
    response_dup = client.post(
        "/webhooks/razorpay",
        content=body_bytes,
        headers={"X-Razorpay-Signature": sig}
    )
    assert response_dup.status_code == 200
    assert response_dup.json() == {"status": "duplicate, ignored"}
    
    # Test invalid signature request
    response_invalid_sig = client.post(
        "/webhooks/razorpay",
        content=body_bytes,
        headers={"X-Razorpay-Signature": "invalid_sig"}
    )
    assert response_invalid_sig.status_code == 400
    assert "signature" in response_invalid_sig.json()["detail"]


def test_parse_webhook_to_event():
    # Nested Razorpay format
    payload = {
        "id": "evt_test_nested",
        "event": "payment.failed",
        "account_id": "acc_nested_merchant",
        "payload": {
            "payment": {
                "entity": {
                    "amount": 99900,  # 999.00 INR
                    "method": "upi",
                    "error_code": "insufficient_funds",
                    "notes": {
                        "customer_risk_tier": "high_value",
                        "dnd_flag": True
                    }
                }
            }
        }
    }
    
    event = parse_webhook_to_event(payload)
    assert event.record_id == "evt_test_nested"
    assert event.merchant_id == "acc_nested_merchant"
    assert event.amount_inr == 999.0
    assert event.reason_code == "insufficient_funds"
    assert event.customer_risk_tier == "high_value"
    assert event.dnd_flag is True
    
    # Flat dict format
    flat_payload = {
        "id": "evt_test_flat",
        "webhook_event": "subscription.pending",
        "merchant_id": "merchant_flat",
        "amount_inr": 450.50,
        "reason_code": "expired",
        "customer_risk_tier": "standard",
        "dnd_flag": False
    }
    event_flat = parse_webhook_to_event(flat_payload)
    assert event_flat.record_id == "evt_test_flat"
    assert event_flat.merchant_id == "merchant_flat"
    assert event_flat.amount_inr == 450.50
    assert event_flat.reason_code == "mandate_expired"
    assert event_flat.customer_risk_tier == "standard"
    assert event_flat.dnd_flag is False


def test_worker_processing(tmp_path):
    audit = AuditLog(path=tmp_path / "worker_test_audit.jsonl")
    
    # Drain queue first
    while dequeue() is not None:
        pass
        
    # Enqueue a mock payload
    payload = {
        "id": "evt_worker_test",
        "event": "payment.failed",
        "account_id": "acc_worker_merchant",
        "payload": {
            "payment": {
                "entity": {
                    "amount": 100000,  # 1000.00 INR
                    "method": "upi",
                    "error_code": "insufficient_funds",
                    "notes": {
                        "customer_risk_tier": "standard",
                        "dnd_flag": False
                    }
                }
            }
        }
    }
    enqueue(payload)
    
    # Run processor
    processed = process_next_event(audit)
    assert processed is True
    
    # Verify audit trail exists for this record
    trail = audit.for_record("evt_worker_test")
    assert len(trail) >= 4
    
    # Ensure queue is now empty
    assert process_next_event(audit) is False
