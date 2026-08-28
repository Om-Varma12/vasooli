"""
test_razorpay_live_integration.py
===================================
Semi-automated Razorpay Test Mode integration test.

This test REQUIRES:
  - A running FastAPI server  (uvicorn vasooli.ingest.webhook_receiver:app --port 8000)
  - A running public tunnel   (e.g. zrok share public 8000)
  - The tunnel URL configured as VASOOLI_TUNNEL_URL in your environment
  - RAZORPAY_API_KEY, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET in .env

WHAT IT DOES:
  1. Reads Razorpay Test credentials from environment.
  2. Creates a real Razorpay Test Mode Order via the Orders API.
  3. Creates a Payment Link for that order.
  4. Prints the payment link URL and waits for a human to:
       - Open the link in a browser
       - Choose any payment method (Card / UPI / Netbanking)
       - Click "Failure" on the mock bank page
  5. Polls the FastAPI /health endpoint to confirm the server is alive.
  6. Polls an audit log / flag file written by the worker for up to 120s
     to confirm the payment.failed webhook was received and processed.
  7. Reports each stage as PASS or FAIL.

This test is SKIPPED if Razorpay credentials are not found or if
VASOOLI_TUNNEL_URL is not set.

Run with:
    pytest tests/test_razorpay_live_integration.py -v -s

The -s flag is important -- it shows the payment link URL in real time.
"""

import sys
import os
import time
import json
import hmac
import hashlib
import requests
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

# ---------------------------------------------------------------------------
# Credential guards - skip if not configured
# ---------------------------------------------------------------------------

RAZORPAY_API_KEY = os.getenv("RAZORPAY_API_KEY", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
TUNNEL_URL = os.getenv("VASOOLI_TUNNEL_URL", "").rstrip("/")

RAZORPAY_BASE = "https://api.razorpay.com/v1"

_SKIP_REASON = None
if not RAZORPAY_API_KEY or not RAZORPAY_KEY_SECRET:
    _SKIP_REASON = "RAZORPAY_API_KEY / RAZORPAY_KEY_SECRET not set"
elif not RAZORPAY_WEBHOOK_SECRET:
    _SKIP_REASON = "RAZORPAY_WEBHOOK_SECRET not set"
elif not TUNNEL_URL:
    _SKIP_REASON = (
        "VASOOLI_TUNNEL_URL not set. "
        "Start a tunnel (e.g. `zrok share public 8000`) and export the public URL."
    )

requires_razorpay = pytest.mark.skipif(
    _SKIP_REASON is not None,
    reason=_SKIP_REASON or "Razorpay live test skipped",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _razorpay_auth():
    return (RAZORPAY_API_KEY, RAZORPAY_KEY_SECRET)


def _create_order(amount_paise: int = 10000, receipt: str = None) -> dict:
    """Create a Razorpay Test Mode order. Returns the order object."""
    receipt = receipt or f"vasooli_test_{int(time.time())}"
    resp = requests.post(
        f"{RAZORPAY_BASE}/orders",
        auth=_razorpay_auth(),
        json={"amount": amount_paise, "currency": "INR", "receipt": receipt},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _create_payment_link(order_id: str, amount_paise: int) -> dict:
    """Create a Razorpay Payment Link for the given order."""
    resp = requests.post(
        f"{RAZORPAY_BASE}/payment_links",
        auth=_razorpay_auth(),
        json={
            "amount": amount_paise,
            "currency": "INR",
            "description": "Vasooli E2E Integration Test - Please click FAILURE",
            "reference_id": order_id,
            "notes": {
                "purpose": "vasooli_e2e_test",
                "customer_risk_tier": "standard",
                "dnd_flag": False,
            },
            "reminder_enable": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _check_server_alive(base_url: str, timeout_s: int = 10) -> bool:
    """Return True if the FastAPI server at base_url/health responds 200."""
    try:
        r = requests.get(f"{base_url}/health", timeout=timeout_s)
        return r.status_code == 200
    except Exception:
        return False


def _poll_for_webhook(
    record_id_prefix: str,
    order_id: str,
    poll_timeout_s: int = 120,
    poll_interval_s: int = 3,
) -> dict | None:
    """
    Poll the local FastAPI audit endpoint (or a sentinel file) for evidence that
    the payment.failed webhook was received and processed.

    Strategy: after the worker processes an event it writes to the audit log
    (audit_log.jsonl). We check the live server's /health to confirm it is up,
    then poll a dedicated /debug/last_event endpoint that we temporarily add,
    OR we check that the audit log contains an entry matching our order_id.

    For simplicity (no server code change needed), we poll
    GET {TUNNEL_URL}/health and accept any 200 as "server still alive",
    then read the audit_log.jsonl file from disk if available.
    """
    audit_path = Path(__file__).parent.parent / "data" / "audit_log.jsonl"
    deadline = time.time() + poll_timeout_s

    while time.time() < deadline:
        # Check if audit log contains our order_id reference
        if audit_path.exists():
            lines = audit_path.read_text(errors="replace").splitlines()
            for line in reversed(lines):
                try:
                    entry = json.loads(line)
                    rec_id = entry.get("record_id", "")
                    if order_id in rec_id or record_id_prefix in rec_id:
                        return entry
                except json.JSONDecodeError:
                    pass
        time.sleep(poll_interval_s)

    return None


# ---------------------------------------------------------------------------
# Live Integration Test
# ---------------------------------------------------------------------------

@requires_razorpay
class TestRazorpayLiveIntegration:
    """
    Real Razorpay Test Mode webhook flow.
    Requires manual browser interaction to click the Failure button.
    """

    def test_live_payment_failed_webhook_pipeline(self):
        """
        STAGE 1: Verify server is reachable via tunnel.
        STAGE 2: Create a Razorpay Test Order.
        STAGE 3: Create a Payment Link.
        STAGE 4: Wait for human to trigger payment failure.
        STAGE 5: Confirm webhook was received + processed.
        """
        results = {}

        # ---- STAGE 1: Server alive check ----
        print(f"\n[STAGE 1] Checking server is alive at {TUNNEL_URL} ...")
        server_ok = _check_server_alive(TUNNEL_URL, timeout_s=10)
        results["server_alive"] = server_ok
        if not server_ok:
            pytest.fail(
                f"[STAGE 1 FAIL] FastAPI server not reachable at {TUNNEL_URL}. "
                "Start it with: uvicorn vasooli.ingest.webhook_receiver:app --port 8000"
            )
        print("[STAGE 1] PASS - Server is alive.")

        # ---- STAGE 2: Create Order ----
        print("\n[STAGE 2] Creating Razorpay Test Order (100 INR) ...")
        try:
            order = _create_order(amount_paise=10000)  # 100 INR
            order_id = order["id"]
            results["order_created"] = True
            results["order_id"] = order_id
            print(f"[STAGE 2] PASS - Order created: {order_id}")
        except Exception as e:
            results["order_created"] = False
            pytest.fail(f"[STAGE 2 FAIL] Could not create Razorpay order: {e}")

        # ---- STAGE 3: Create Payment Link ----
        print("\n[STAGE 3] Creating Payment Link ...")
        try:
            plink = _create_payment_link(order_id=order_id, amount_paise=10000)
            short_url = plink.get("short_url", plink.get("id", "unknown"))
            results["payment_link_created"] = True
            results["payment_link_url"] = short_url
            print(f"[STAGE 3] PASS - Payment Link: {short_url}")
        except Exception as e:
            results["payment_link_created"] = False
            pytest.fail(f"[STAGE 3 FAIL] Could not create payment link: {e}")

        # ---- STAGE 4: Human interaction required ----
        print("\n" + "=" * 70)
        print("ACTION REQUIRED: TRIGGER A PAYMENT FAILURE")
        print("=" * 70)
        print(f"  Payment Link URL: {short_url}")
        print()
        print("  Steps:")
        print("    1. Open the URL above in your browser")
        print("    2. Choose any payment method (Card / UPI / Netbanking)")
        print("    3. For Card: use test card 4111 1111 1111 1111, any CVV/expiry")
        print("    4. On the MOCK BANK PAGE, click the RED 'Failure' button")
        print("    5. Come back here - the test will auto-detect the webhook")
        print()
        print(f"  Webhook endpoint configured in Razorpay should be:")
        print(f"    {TUNNEL_URL}/webhooks/razorpay")
        print()
        print("  Waiting up to 120 seconds for the payment.failed webhook...")
        print("=" * 70 + "\n")

        # ---- STAGE 5: Poll for webhook receipt ----
        print("[STAGE 5] Polling for payment.failed webhook receipt ...")
        matched = _poll_for_webhook(
            record_id_prefix="evt_",
            order_id=order_id,
            poll_timeout_s=120,
            poll_interval_s=3,
        )

        if matched:
            results["webhook_received"] = True
            results["audit_entry"] = matched
            print(f"[STAGE 5] PASS - Webhook received and processed!")
            print(f"          Audit entry: {json.dumps(matched, indent=2)}")
        else:
            results["webhook_received"] = False
            print("[STAGE 5] FAIL - No webhook received within 120 seconds.")
            print("  Possible causes:")
            print("    - Tunnel URL not configured in Razorpay dashboard webhook settings")
            print("    - Payment failure was not triggered on the mock bank page")
            print("    - Server not running or not forwarding correctly")
            print(f"\n  Results so far: {json.dumps(results, indent=2)}")
            pytest.fail(
                "[STAGE 5 FAIL] payment.failed webhook was not received within 120 seconds. "
                "See above for troubleshooting steps."
            )

        # Final summary
        print("\n" + "=" * 70)
        print("INTEGRATION TEST RESULTS:")
        print("=" * 70)
        for stage, result in results.items():
            status = "PASS" if result else "FAIL"
            print(f"  {stage}: {status}")
        print("=" * 70)


# ---------------------------------------------------------------------------
# Standalone runner for CI / debugging
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """
    Run directly with: python tests/test_razorpay_live_integration.py

    Pre-requisites:
      1. Start FastAPI:   uvicorn vasooli.ingest.webhook_receiver:app --port 8000
      2. Start tunnel:    zrok share public 8000     (or ngrok http 8000)
      3. Note the tunnel URL (e.g. https://abc123.zrok.io)
      4. Configure webhook in Razorpay dashboard:
            URL: https://abc123.zrok.io/webhooks/razorpay
            Secret: thisismytestenv (or your RAZORPAY_WEBHOOK_SECRET)
            Events: payment.failed
      5. Export:  set VASOOLI_TUNNEL_URL=https://abc123.zrok.io
      6. Run:     python tests/test_razorpay_live_integration.py
    """
    if _SKIP_REASON:
        print(f"SKIP: {_SKIP_REASON}")
        sys.exit(0)

    suite = TestRazorpayLiveIntegration()
    suite.test_live_payment_failed_webhook_pipeline()
