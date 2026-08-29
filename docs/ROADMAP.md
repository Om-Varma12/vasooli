# Vasooli Development Roadmap

This document tracks the status of every component in the Vasooli pipeline — what's **done**, what's a **stub**, and what's **next**.

Last updated: 2026-08-28

---

## Legend
- ✅ **Done** — Real code, tested, committed
- 🔶 **Stub** — File exists, signatures correct, body is a placeholder
- ❌ **Not started** — Not yet created

---

## 1. Webhook Ingestion & Pre-processing

| Task | Status | File |
|---|---|---|
| FastAPI POST `/webhooks/razorpay` endpoint | ✅ Done | `src/vasooli/ingest/webhook_receiver.py` |
| HMAC-SHA256 Signature Verification | ✅ Done | `src/vasooli/ingest/signature.py` |
| `.env` loading via `python-dotenv` | ✅ Done | `webhook_receiver.py` |
| Idempotency / Deduplication (Redis + in-memory fallback) | ✅ Done | `src/vasooli/ingest/dedupe_store.py` |
| Async Queue (Redis BLPOP + local `queue.Queue` fallback) | ✅ Done | `src/vasooli/ingest/queue.py` |
| Structured JSON transaction logging on every incoming event | ✅ Done | `webhook_receiver.py` |
| Real Razorpay nested payload parsing (not top-level `id`) | ✅ Done | `webhook_receiver.py` |

---

## 2. Background Worker

| Task | Status | File |
|---|---|---|
| ThreadPoolExecutor multi-worker consumer | ✅ Done | `src/vasooli/worker.py` |
| Graceful SIGINT / SIGTERM / SIGBREAK shutdown | ✅ Done | `worker.py` |
| Transient error detection + exponential backoff retries (max 3) | ✅ Done | `worker.py` |
| DLQ routing on exhausted retries | ✅ Done | `worker.py` |
| Worker actually connected to orchestrator pipeline | 🔶 Stub | Worker dequeues but needs to call `orchestrator.run_one()` on real Razorpay dicts |

---

## 3. Enrichment & Context Layer

| Task | Status | File |
|---|---|---|
| Account history table in Supabase Postgres | ✅ Done | `src/vasooli/enrichment/account_history.py` |
| `get_history()` — fetch past bounce count, reasons, channel rates | ✅ Done | `account_history.py` |
| `record_bounce()` — upsert on failure event | ✅ Done | `account_history.py` |
| `record_outcome()` — update attempts/successes per channel | ✅ Done | `account_history.py` |
| Fail-open: DB errors caught, routed to DLQ, pipeline continues | ✅ Done | `account_history.py` |
| Live Entity Fallback Fetch from Razorpay API | 🔶 Stub | `src/vasooli/enrichment/entity_fetch.py` |

---

## 4. Classification Layer

| Task | Status | File |
|---|---|---|
| Cancellation intent gate (Tier 0 — always runs first) | ✅ Done | `src/vasooli/classify/cancellation_gate.py` |
| Deterministic rules classifier (Tier 1 — ~92% of events) | ✅ Done | `src/vasooli/classify/rules_classifier.py` |
| LLM fallback classifier (Tier 2) | 🔶 Stub | `src/vasooli/classify/llm_classifier.py` — `_call_llm()` returns UNKNOWN |
| Low-confidence routing to human review queue | 🔶 Stub | `llm_classifier.py` — logged only, not routed |

---

## 5. Decision / Policy Engine

| Task | Status | File |
|---|---|---|
| Guard clauses: cancellation check + NPCI retry ceiling | ✅ Done | `src/vasooli/decide/guard_clauses.py` |
| Chronic bouncer escalation guard (`past_bounce_count >= 3`) | ✅ Done | `guard_clauses.py` |
| Rules engine (loads `config/rules_table.yaml`) | ✅ Done | `src/vasooli/decide/rules_engine.py` |
| Voice escalation gating (DND → history → risk tier → cost) | ✅ Done | `rules_engine.py` |
| Cost gate (`config/channel_costs.yaml`) | ✅ Done | `src/vasooli/decide/cost_gate.py` |
| Budget-aware portfolio allocator | 🔶 Stub | `src/vasooli/decide/budget_allocator.py` |

---

## 6. Execution Channels

| Task | Status | File |
|---|---|---|
| Token-bucket Rate Limiter (per-channel, thread-safe) | ✅ Done | `src/vasooli/execute/rate_limiter.py` |
| Retry adapter (mocked outcome) | ✅ Done | `src/vasooli/execute/retry_adapter.py` |
| WhatsApp adapter (template message built, mocked send) | 🔶 Stub | `src/vasooli/execute/whatsapp_adapter.py` |
| Real WhatsApp Business API send (Meta Cloud API) | ❌ Not started | `whatsapp_adapter.py` needs wiring |
| Voice adapter (mocked Hinglish transcript) | 🔶 Stub | `src/vasooli/execute/voice_adapter.py` |
| Real outbound telephony (Twilio / Exotel + STT/TTS) | ❌ Not started | `voice_adapter.py` needs wiring |
| Promise-to-pay DB ledger + follow-up cron | 🔶 Stub | `src/vasooli/execute/promise_to_pay.py` |
| Human handoff adapter | ✅ Done | `promise_to_pay.py` — `HumanHandoffAdapter` |

---

## 7. Audit & Observability

| Task | Status | File |
|---|---|---|
| Append-only audit log (JSONL, one line per decision) | ✅ Done | `src/vasooli/audit/audit_log.py` |
| Dead Letter Queue — write / read / CLI | ✅ Done | `src/vasooli/audit/dead_letter.py` |
| DLQ wired into orchestrator per-record errors | ✅ Done | `src/vasooli/orchestrator.py` |
| DLQ wired into rate limiter overflow | ✅ Done | `src/vasooli/execute/__init__.py` |
| DLQ wired into account history DB errors | ✅ Done | `account_history.py` |

---

## 8. Reporting

| Task | Status | File |
|---|---|---|
| `build_report()` / `print_report()` aggregation | ✅ Done | `src/vasooli/report/metrics.py` |

---

## 9. Testing

| Suite | Tests | Status |
|---|---|---|
| Ingest layer integration tests | 28 | ✅ |
| Rate limiter + DLQ tests | 14 | ✅ |
| Account history live Supabase tests | 4 | ✅ |
| Classify / decide / orchestrator / config unit tests | ~19 | ✅ |
| **Total** | **46+** | ✅ All passing |

---

## 🎯 Next Steps (Priority Order)

### Priority 1 — Close the end-to-end loop: webhook → orchestrator
> Real Razorpay events land in the queue but **never flow through classify → decide → execute**. The worker must convert the raw webhook dict into a `FailureEvent` and call `orchestrator.run_one()`.

**File:** `src/vasooli/worker.py` — wire dequeued Razorpay payload → `FailureEvent` → `run_one()`

### Priority 2 — Entity Fetch Enrichment
> Webhook payloads are often incomplete. Need to call Razorpay's `payment.fetch(id)` API to fill in missing fields before classification runs.

**File:** `src/vasooli/enrichment/entity_fetch.py` — implement using `razorpay` SDK + `.env` keys

### Priority 3 — LLM Classifier
> ~8% of events hit `unclassified_bank_response` and fall through to `UNKNOWN`. Need real Gemini/Claude call.

**File:** `src/vasooli/classify/llm_classifier.py` — replace `_call_llm()` stub body

### Priority 4 — Real WhatsApp sends
> Template is built. Just needs Meta Cloud API credentials wired in.

**File:** `src/vasooli/execute/whatsapp_adapter.py`

### Priority 5 — Promise-to-Pay DB ledger
> Voice calls capture promises. Need a Supabase table and a daily cron check.

**File:** `src/vasooli/execute/promise_to_pay.py` + new Supabase table

---

## System Architecture Status

```
[Razorpay] → POST /webhooks/razorpay  ✅
                     ↓
         [Signature verify]            ✅
                     ↓
          [Dedup store]                ✅
                     ↓
             [Queue]                   ✅
                     ↓
    ┌───────────────────────────┐
    │  worker.py (consumer)     │  ⚠️  Runs separately: needs webhook→FailureEvent bridge
    └───────────────────────────┘
                     ↓
  [entity_fetch enrichment]            🔶 stub
                     ↓
  [account_history enrichment]         ✅
                     ↓
         [classify]                    ✅  (LLM tier = stub 🔶)
                     ↓
          [decide]                     ✅
                     ↓
         [execute]                     ✅  (channels = mocked 🔶)
                     ↓
    [audit_log + DLQ]                  ✅
```
