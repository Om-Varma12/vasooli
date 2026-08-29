"""
test_webhook_e2e.py
===================
Automated end-to-end pipeline tests for the Razorpay webhook processing path.

These tests exercise the FULL pipeline using properly-HMAC-signed webhook payloads
that are byte-for-byte identical to what Razorpay sends in Test Mode - the only
difference is that the *order* and *payment* are created locally rather than via
a real Razorpay checkout. All pipeline stages are real (no mocks): FastAPI endpoint,
signature verification, deduplication, queue, worker, classifier, decision engine,
executor, and audit log.

No Razorpay API credentials are required to run these tests.

Run with:
    pytest tests/test_webhook_e2e.py -v
"""

import sys
import os
import hmac
import hashlib
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from fastapi.testclient import TestClient

from vasooli.ingest.webhook_receiver import app
from vasooli.ingest.queue import enqueue, dequeue
from vasooli.ingest.dedupe_store import already_processed, mark_processed
from vasooli.worker import parse_webhook_to_event, process_next_event
from vasooli.audit.audit_log import AuditLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "thisismytestenv"


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute the HMAC-SHA256 signature Razorpay would attach."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _razorpay_payment_failed_payload(
    event_id="evt_e2e_payment_failed_001",
    payment_id="pay_e2e_001",
    order_id="order_e2e_001",
    amount_paise=99900,
    method="upi",
    error_code="PAYMENT_ERROR",
    error_description="Your payment failed as your bank account does not have sufficient funds.",
    customer_email="testuser@example.com",
    customer_contact="+919999999999",
    merchant_id="acc_merchant_test01",
    risk_tier="standard",
    dnd_flag=False,
):
    """Return a realistic Razorpay payment.failed webhook payload."""
    return {
        "id": event_id,
        "entity": "event",
        "account_id": merchant_id,
        "event": "payment.failed",
        "contains": ["payment"],
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "entity": "payment",
                    "amount": amount_paise,
                    "currency": "INR",
                    "status": "failed",
                    "order_id": order_id,
                    "invoice_id": None,
                    "international": False,
                    "method": method,
                    "amount_refunded": 0,
                    "refund_status": None,
                    "captured": False,
                    "description": "Test payment",
                    "card_id": None,
                    "bank": None,
                    "wallet": None,
                    "vpa": "failure@razorpay" if method == "upi" else None,
                    "email": customer_email,
                    "contact": customer_contact,
                    "customer_id": None,
                    "notes": {
                        "customer_risk_tier": risk_tier,
                        "dnd_flag": dnd_flag,
                    },
                    "fee": None,
                    "tax": None,
                    "error_code": error_code,
                    "error_description": error_description,
                    "error_source": "customer",
                    "error_step": "payment_authorization",
                    "error_reason": "payment_failed",
                    "acquirer_data": {
                        "rrn": None,
                        "upi_transaction_id": None,
                    },
                    "created_at": int(time.time()),
                }
            }
        },
        "created_at": int(time.time()),
    }


def _drain_queue():
    while dequeue(timeout=0) is not None:
        pass


# ---------------------------------------------------------------------------
# Stage 1 - FastAPI endpoint: signature handling
# ---------------------------------------------------------------------------

class TestWebhookEndpointSignatures:
    """Test the FastAPI /webhooks/razorpay endpoint for signature correctness."""

    def setup_method(self):
        self.client = TestClient(app)
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = WEBHOOK_SECRET

    def _post(self, body, sig):
        return self.client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )

    def test_valid_signature_accepted(self):
        """Correct HMAC-SHA256 signature -> 200 queued."""
        _drain_queue()
        payload = _razorpay_payment_failed_payload(event_id="evt_sig_ok_001")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = self._post(body, sig)
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"

    def test_invalid_signature_rejected(self):
        """Tampered signature -> 400 with signature in detail."""
        payload = _razorpay_payment_failed_payload(event_id="evt_sig_bad_001")
        body = json.dumps(payload).encode()
        resp = self._post(body, "deadbeef" * 8)
        assert resp.status_code == 400
        assert "signature" in resp.json()["detail"].lower()

    def test_wrong_secret_rejected(self):
        """Signature computed with wrong secret -> 400."""
        payload = _razorpay_payment_failed_payload(event_id="evt_sig_wrongsec_001")
        body = json.dumps(payload).encode()
        sig = _sign(body, "completely_wrong_secret")
        resp = self._post(body, sig)
        assert resp.status_code == 400

    def test_body_tampered_after_signing(self):
        """Payload altered after signing -> 400."""
        payload = _razorpay_payment_failed_payload(event_id="evt_sig_tampered_001")
        body = json.dumps(payload).encode()
        sig = _sign(body)
        tampered = body.replace(b"payment.failed", b"payment.captured")
        resp = self._post(tampered, sig)
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Stage 2 - Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:
    """Test that duplicate webhook events are idempotently ignored."""

    def setup_method(self):
        self.client = TestClient(app)
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = WEBHOOK_SECRET

    def test_duplicate_event_ignored(self):
        """Same event_id arriving twice -> first queued, second ignored."""
        _drain_queue()
        payload = _razorpay_payment_failed_payload(event_id="evt_dup_test_e2e_001")
        body = json.dumps(payload).encode()
        sig = _sign(body)

        r1 = self.client.post("/webhooks/razorpay", content=body,
                              headers={"X-Razorpay-Signature": sig})
        r2 = self.client.post("/webhooks/razorpay", content=body,
                              headers={"X-Razorpay-Signature": sig})

        assert r1.status_code == 200
        assert r1.json()["status"] == "queued"
        assert r2.status_code == 200
        assert r2.json()["status"] == "duplicate, ignored"

    def test_ten_duplicates_only_one_queued(self):
        """10 identical events -> exactly 1 dequeued item."""
        _drain_queue()
        unique_id = f"evt_dup10_e2e_{int(time.time())}"
        payload = _razorpay_payment_failed_payload(event_id=unique_id)
        body = json.dumps(payload).encode()
        sig = _sign(body)

        for _ in range(10):
            self.client.post("/webhooks/razorpay", content=body,
                             headers={"X-Razorpay-Signature": sig})

        items = []
        while True:
            item = dequeue(timeout=0)
            if item is None:
                break
            items.append(item)

        assert len(items) == 1
        assert items[0]["id"] == unique_id

    def test_different_event_ids_both_queued(self):
        """Two distinct event IDs -> both queued."""
        _drain_queue()
        for i in range(2):
            eid = f"evt_distinct_{i}_{int(time.time())}"
            payload = _razorpay_payment_failed_payload(event_id=eid)
            body = json.dumps(payload).encode()
            sig = _sign(body)
            r = self.client.post("/webhooks/razorpay", content=body,
                                 headers={"X-Razorpay-Signature": sig})
            assert r.json()["status"] == "queued"

        count = 0
        while dequeue(timeout=0) is not None:
            count += 1
        assert count == 2


# ---------------------------------------------------------------------------
# Stage 3 - Payload parsing
# ---------------------------------------------------------------------------

class TestPayloadParsing:
    """Test parse_webhook_to_event covers Razorpay nested format correctly."""

    def test_payment_failed_upi(self):
        p = _razorpay_payment_failed_payload(
            event_id="evt_parse_upi",
            amount_paise=150000,
            method="upi",
            error_code="PAYMENT_ERROR",
            merchant_id="acc_upi_merchant",
            risk_tier="high_value",
            dnd_flag=True,
        )
        event = parse_webhook_to_event(p)
        assert event.record_id == "evt_parse_upi"
        assert event.merchant_id == "acc_upi_merchant"
        assert event.amount_inr == 1500.0
        assert event.customer_risk_tier == "high_value"
        assert event.dnd_flag is True

    def test_payment_failed_card(self):
        p = _razorpay_payment_failed_payload(
            event_id="evt_parse_card",
            amount_paise=50000,
            method="card",
            error_code="insufficient_funds",
        )
        event = parse_webhook_to_event(p)
        assert event.record_id == "evt_parse_card"
        assert event.amount_inr == 500.0
        assert event.reason_code == "insufficient_funds"

    def test_missing_notes_defaults(self):
        """If notes are absent, defaults should not crash."""
        p = _razorpay_payment_failed_payload(event_id="evt_parse_no_notes")
        p["payload"]["payment"]["entity"].pop("notes", None)
        event = parse_webhook_to_event(p)
        assert event.record_id == "evt_parse_no_notes"
        assert event.customer_risk_tier == "standard"
        assert event.dnd_flag is False

    def test_amount_conversion(self):
        """Paise to INR conversion must be exact."""
        for paise, expected_inr in [(100, 1.0), (9999, 99.99), (100000, 1000.0)]:
            p = _razorpay_payment_failed_payload(
                event_id=f"evt_amount_{paise}", amount_paise=paise
            )
            event = parse_webhook_to_event(p)
            assert abs(event.amount_inr - expected_inr) < 0.001, \
                f"{paise} paise -> expected {expected_inr} INR, got {event.amount_inr}"


# ---------------------------------------------------------------------------
# Stage 4 - Queue
# ---------------------------------------------------------------------------

class TestQueue:
    """Test FIFO queue mechanics."""

    def test_fifo_ordering(self):
        _drain_queue()
        ids = [f"evt_fifo_{i}" for i in range(5)]
        for eid in ids:
            enqueue({"id": eid, "event": "payment.failed"})

        received = []
        while True:
            item = dequeue(timeout=0)
            if item is None:
                break
            received.append(item["id"])

        assert received == ids

    def test_empty_queue_returns_none(self):
        _drain_queue()
        assert dequeue(timeout=0) is None

    def test_timeout_respected(self):
        _drain_queue()
        t0 = time.time()
        result = dequeue(timeout=1)
        elapsed = time.time() - t0
        assert result is None
        assert elapsed >= 0.9, f"Expected >= 0.9s, got {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# Stage 5 - Full pipeline: endpoint -> queue -> worker -> audit
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """End-to-end: HTTP POST -> signature check -> dedup -> queue -> worker -> audit."""

    def setup_method(self):
        self.client = TestClient(app)
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = WEBHOOK_SECRET

    def test_full_pipeline_payment_failed(self, tmp_path):
        """Full pipeline for a real payment.failed webhook payload."""
        _drain_queue()
        audit = AuditLog(path=tmp_path / "e2e_audit.jsonl")

        unique_id = f"evt_e2e_full_{int(time.time() * 1000)}"
        payload = _razorpay_payment_failed_payload(
            event_id=unique_id,
            amount_paise=75000,
            method="upi",
            error_code="PAYMENT_ERROR",
            risk_tier="standard",
        )
        body = json.dumps(payload).encode()
        sig = _sign(body)

        # 1. POST to FastAPI endpoint
        resp = self.client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 200, f"Endpoint rejected: {resp.json()}"
        assert resp.json()["status"] == "queued"

        # 2. Worker processes the event
        processed = process_next_event(audit)
        assert processed is True, "Worker found nothing in queue"

        # 3. Audit trail was written
        trail = audit.for_record(unique_id)
        steps = {entry["step"] for entry in trail}
        assert "classify" in steps, f"classify step missing. Trail: {trail}"
        assert "policy" in steps, f"policy step missing. Trail: {trail}"
        assert any(s.startswith("execute:") for s in steps), \
            f"execute step missing. Trail: {trail}"
        assert "outcome" in steps, f"outcome step missing. Trail: {trail}"

        # 4. Queue is now empty
        assert process_next_event(audit) is False

    def test_pipeline_high_value_customer(self, tmp_path):
        """High-value customer (5000 INR) should be processed."""
        _drain_queue()
        audit = AuditLog(path=tmp_path / "e2e_audit_hv.jsonl")

        unique_id = f"evt_e2e_hv_{int(time.time() * 1000)}"
        payload = _razorpay_payment_failed_payload(
            event_id=unique_id,
            amount_paise=500000,
            method="card",
            error_code="PAYMENT_ERROR",
            risk_tier="high_value",
        )
        body = json.dumps(payload).encode()
        resp = self.client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": _sign(body)},
        )
        assert resp.status_code == 200
        processed = process_next_event(audit)
        assert processed is True

        trail = audit.for_record(unique_id)
        assert len(trail) >= 4, f"Expected >= 4 audit entries, got {len(trail)}"

    def test_pipeline_dnd_customer(self, tmp_path):
        """DND-flagged customer should be processed without crashing."""
        _drain_queue()
        audit = AuditLog(path=tmp_path / "e2e_audit_dnd.jsonl")

        unique_id = f"evt_e2e_dnd_{int(time.time() * 1000)}"
        payload = _razorpay_payment_failed_payload(
            event_id=unique_id,
            amount_paise=20000,
            method="upi",
            error_code="PAYMENT_ERROR",
            dnd_flag=True,
        )
        body = json.dumps(payload).encode()
        resp = self.client.post(
            "/webhooks/razorpay",
            content=body,
            headers={"X-Razorpay-Signature": _sign(body)},
        )
        assert resp.status_code == 200
        processed = process_next_event(audit)
        assert processed is True

        trail = audit.for_record(unique_id)
        assert any("execute:" in e["step"] for e in trail), \
            "Execute step missing for DND customer"

    def test_pipeline_concurrent_events(self, tmp_path):
        """Multiple distinct events processed sequentially all produce audit trails."""
        _drain_queue()
        audit = AuditLog(path=tmp_path / "e2e_audit_concurrent.jsonl")
        n = 5

        ids = []
        for i in range(n):
            eid = f"evt_e2e_concurrent_{i}_{int(time.time() * 1000)}"
            ids.append(eid)
            payload = _razorpay_payment_failed_payload(
                event_id=eid,
                amount_paise=(i + 1) * 10000,
                method="upi" if i % 2 == 0 else "card",
            )
            body = json.dumps(payload).encode()
            self.client.post(
                "/webhooks/razorpay",
                content=body,
                headers={"X-Razorpay-Signature": _sign(body)},
            )

        for _ in range(n):
            processed = process_next_event(audit)
            assert processed is True

        for eid in ids:
            trail = audit.for_record(eid)
            assert len(trail) >= 4, f"Event {eid}: expected >= 4 audit entries, got {len(trail)}"


# ---------------------------------------------------------------------------
# Stage 6 - Error handling scenarios
# ---------------------------------------------------------------------------

class TestErrorScenarios:
    """Edge cases: missing event ID, invalid JSON, missing secret env var."""

    def setup_method(self):
        self.client = TestClient(app)
        os.environ["RAZORPAY_WEBHOOK_SECRET"] = WEBHOOK_SECRET

    def test_missing_event_id_rejected(self):
        """Payload without id field -> 400."""
        payload = {"event": "payment.failed", "payload": {}}
        body = json.dumps(payload).encode()
        sig = _sign(body)
        resp = self.client.post(
            "/webhooks/razorpay", content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 400

    def test_invalid_json_rejected(self):
        """Non-JSON body -> 400."""
        body = b"this is not json at all"
        sig = _sign(body)
        resp = self.client.post(
            "/webhooks/razorpay", content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 400

    def test_empty_body_rejected(self):
        """Empty body -> 400 (invalid JSON)."""
        body = b""
        sig = _sign(body)
        resp = self.client.post(
            "/webhooks/razorpay", content=body,
            headers={"X-Razorpay-Signature": sig},
        )
        assert resp.status_code == 400

    def test_health_endpoint(self):
        """/health endpoint should return 200."""
        resp = self.client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
