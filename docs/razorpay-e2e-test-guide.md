# Razorpay Webhook E2E Integration Test Guide

This document explains how to run the full Razorpay Test Mode webhook integration
tests for the Vasooli project.

## Two Test Suites

| File | Type | Razorpay creds needed? | Tunnel needed? |
|------|------|----------------------|----------------|
| `tests/test_webhook_e2e.py` | Automated | No | No |
| `tests/test_razorpay_live_integration.py` | Semi-automated | Yes | Yes |

---

## Suite 1 — Automated E2E Tests (`test_webhook_e2e.py`)

These tests exercise the **complete pipeline** using properly HMAC-SHA256 signed
Razorpay-format payloads — identical to what Razorpay actually sends. No Razorpay
API credentials or tunnel are required.

**Pipeline stages tested:**
1. FastAPI `/webhooks/razorpay` endpoint
2. `X-Razorpay-Signature` verification (valid, invalid, wrong secret, tampered body)
3. Duplicate event deduplication (10 identical events ? 1 processed)
4. `payment.failed` payload parsing (UPI, card, amount conversion paise?INR)
5. In-memory FIFO queue correctness and timeout behaviour
6. Full worker ? classifier ? decision engine ? executor ? audit pipeline
7. Error handling (missing ID, invalid JSON, empty body)

### Running

```bash
# From project root
pytest tests/test_webhook_e2e.py -v
```

Expected output: all tests pass in seconds with no external dependencies.

---

## Suite 2 — Live Integration Test (`test_razorpay_live_integration.py`)

This test creates a **real Razorpay Test Mode order and payment link**, then waits
for you to trigger a payment failure in the browser. It verifies that Razorpay
sends a `payment.failed` webhook to your local server and that the full pipeline
processes it.

### Environment Variables Required

```env
RAZORPAY_API_KEY=rzp_test_TVFRmUi2vqjWOX
RAZORPAY_KEY_SECRET=o7yJxXxrqe00Cqt5MSERSF8s
RAZORPAY_WEBHOOK_SECRET=thisismytestenv
VASOOLI_TUNNEL_URL=https://<your-tunnel-subdomain>.<tunnel-provider>.io
```

### Step-by-Step Setup

#### Step 1 — Start the FastAPI webhook receiver

```bash
# From project root
uvicorn vasooli.ingest.webhook_receiver:app --port 8000 --reload
```

Verify it is running:
```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

#### Step 2 — Start a tunnel to expose localhost:8000

> **Note:** Many common tunnels (ngrok, webhook.site, requestbin) are blacklisted
> by Razorpay. Use **zrok** which Razorpay recommends.

**Using zrok (recommended):**
```bash
# Install zrok: https://docs.zrok.io/docs/getting-started
zrok share public 8000
```

Note the public URL printed (e.g. `https://abc123.zrok.io`).

**Alternative — Using ngrok (if not blocked):**
```bash
ngrok http 8000
```

Note the HTTPS forwarding URL (e.g. `https://abc123.ngrok.io`).

#### Step 3 — Configure Razorpay Test Mode Webhook

1. Log in to [Razorpay Dashboard](https://dashboard.razorpay.com/)
2. Switch to **Test Mode** (toggle in top bar)
3. Go to **Settings ? Webhooks ? + Add New Webhook**
4. Fill in:
   - **Webhook URL:** `https://<your-tunnel-url>/webhooks/razorpay`
   - **Secret:** `thisismytestenv` (must match `RAZORPAY_WEBHOOK_SECRET` in `.env`)
   - **Active Events:** Select `payment.failed`
5. Click **Create Webhook**

#### Step 4 — Export the tunnel URL

```bash
# PowerShell
$env:VASOOLI_TUNNEL_URL = "https://abc123.zrok.io"

# CMD
set VASOOLI_TUNNEL_URL=https://abc123.zrok.io

# Bash
export VASOOLI_TUNNEL_URL=https://abc123.zrok.io
```

#### Step 5 — Load .env credentials

```bash
# PowerShell (load .env manually)
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}
```

Or use `python-dotenv` via a conftest or pytest-dotenv plugin.

#### Step 6 — Run the live integration test

```bash
pytest tests/test_razorpay_live_integration.py -v -s
```

The `-s` flag is required to see the payment link URL printed in real time.

#### Step 7 — Trigger the payment failure

When the test prints the payment link URL:

1. Open the URL in your browser
2. Choose **Netbanking** or **Card** (easiest for the mock page)
   - For card: use test number `4111 1111 1111 1111`, any CVV, any future expiry
3. On the **Mock Bank Page** that appears, click the red **"Failure"** button
4. Return to the terminal — the test will detect the webhook within 120 seconds

### Confirming Webhook Receipt

**In the server logs** (uvicorn terminal):
```
INFO:     127.0.0.1:XXXXX - "POST /webhooks/razorpay HTTP/1.1" 200
```

**In the worker output** (if running separately):
```
[orchestrator] classify: [rules, confidence=0.85] insufficient_funds
[orchestrator] policy: retry_sms_tier1
[orchestrator] execute:sms: SMS sent successfully
[orchestrator] outcome: succeeded=True amount_recovered_inr=100.0
```

**In the audit log** (`data/audit_log.jsonl`):
```jsonl
{"ts": "...", "record_id": "evt_...", "stage": "classify", "detail": "..."}
{"ts": "...", "record_id": "evt_...", "stage": "policy", "detail": "..."}
{"ts": "...", "record_id": "evt_...", "stage": "execute:sms", "detail": "..."}
{"ts": "...", "record_id": "evt_...", "stage": "outcome", "detail": "succeeded=True ..."}
```

**In the Razorpay Dashboard:**
- Go to **Webhooks ? Webhook Name ? Logs**
- You should see your endpoint URL with a green `200` response

---

## Skipping the Live Test

The live test automatically skips if any required environment variable is missing:

```bash
pytest tests/test_razorpay_live_integration.py -v
# Output: SKIPPED [1] Razorpay live test skipped: VASOOLI_TUNNEL_URL not set
```

This means CI/CD pipelines run cleanly without credentials.

---

## Running All Tests Together

```bash
# Run only automated tests (safe for CI)
pytest tests/test_webhook_e2e.py tests/test_ingest.py -v

# Run everything including live test (requires tunnel + browser interaction)
pytest tests/ -v -s
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `400 invalid signature` from webhook receiver | Wrong `RAZORPAY_WEBHOOK_SECRET` | Match secret in `.env` and Razorpay dashboard |
| Webhook not arriving | Tunnel URL not in Razorpay dashboard | Add/update webhook URL in dashboard |
| Tunnel domain blocked | Razorpay blocks certain domains | Use `zrok` instead of `ngrok` |
| Test times out after 120s | Failure button not clicked | Redo browser step, click red Failure button |
| `Connection refused` on TUNNEL_URL | Server not running | Start `uvicorn` first |
| `Authentication failed` from Razorpay | Wrong API key or secret | Check `.env` has correct test keys |
