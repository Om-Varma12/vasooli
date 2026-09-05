<div align="center">

# Vasooli ₹

### Detect. Decide. Recover. Repeat.

**A bounded, auditable AI agent that finds revenue slipping away across UPI Autopay,
eNACH, and B2B receivables — and wins it back, one explainable decision at a time.**

Built for **Track 03 — AI Revenue Recovery**, Razorpay AI Buildathon 2026.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688)
![React](https://img.shields.io/badge/frontend-React-61DAFB)
![License](https://img.shields.io/badge/license-TBD-lightgrey)

</div>

---

## Table of Contents

- [The Problem](#the-problem)
- [What Vasooli Does](#what-vasooli-does)
- [Why This, Why Now](#why-this-why-now)
- [Architecture](#architecture)
  - [System Overview](#system-overview)
  - [Decision Layer — Execution Trace](#decision-layer--execution-trace)
- [The Compliance Guarantee](#the-compliance-guarantee)
- [Results](#results)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Running the Project](#running-the-project)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Roadmap](#roadmap)
- [Acknowledgments](#acknowledgments)

---

## The Problem

UPI Autopay failure rates run **8–15%**, against 2–3% for card mandates, because every UPI
debit needs live bank-side approval rather than a stored token — there's no card to
silently retry, only a real-time yes or no from a bank that may say no for reasons that
have nothing to do with the customer. Over **20 million UPI Autopay mandates are
cancelled every month**, mostly from insufficient balance, across OTT subscriptions, loan
EMIs, SIP mandates, and utilities. NACH bounce rates for lending ran 30–45% through
2020–21; even a well-instrumented modern NBFC book still sits near **12%**, and every
bounce costs ₹300–1,500 in fees plus 100–200+ CIBIL points for the borrower. Globally,
failed payments cost subscription businesses an estimated **$118.5B/year**.

None of that is one problem. It's four different failure classes — payment degradation,
checkout abandonment, subscription mandate failure, receivable delinquency — that most
tooling treats as one undifferentiated "payment failed" bucket, then responds to with the
same blunt retry regardless of which one it actually is.

---

## What Vasooli Does

| Track direction | Implementation |
|---|---|
| Payment degradation → root cause → recovery action | `classify/` → `decide/` → `execute/`, the core pipeline every other row runs through |
| Checkout drop-off recovery | Abandoned-session events enter the same pipeline as a distinct root cause, not a special case |
| Failed-subscription recovery | UPI Autopay flow, with `check_chronic_bouncer` skipping a doomed retry for accounts with 3+ historical bounces |
| B2B receivables chaser | `Category.B2B_RECEIVABLE` with `days_overdue` tracking and its own, gentler rules-table entries |
| Mandate retry sequencer | `RETRY_CEILING = 3` enforced in `decide/guard_clauses.py`, mirroring Razorpay's own `subscription.halted` trigger |
| Hinglish voice recovery | Twilio outbound calls, `Polly.Aditi` voice, call recorded and transcribed via Groq Whisper |
| Promise-to-pay tracker | Commitments captured on a call written to a `pending / kept / broken` record, followed up automatically |

---

## Why This, Why Now

FlyCode, Stuut, and Chargebee solve payment recovery well — for Stripe-first businesses on
card rails that don't map onto UPI's mandate lifecycle or NPCI's retry ceiling. Spocto X
(Yubi) and Credgenics already operate at real scale on the lending side — Spocto alone
manages 5.5 crore+ monthly accounts across 60+ financial institutions. Razorpay's own
Intelligent Retry Engine covers smart retry timing and WhatsApp recovery links for
subscriptions.

None of them span all three: UPI Autopay subscriptions, eNACH EMIs, and B2B receivables,
under one decision layer a compliance reviewer can read end to end. Vasooli is built to
live *inside* Razorpay — an extended capability for merchants already on the platform,
not a new standalone product asking for a new login.

---

## Architecture

### System Overview

![alt text](arch.png)

### Decision Layer — Execution Trace

This is the part worth reading closely — it's the literal order of function calls, not a
simplified retelling of it. Every gate short-circuits: once one fires, nothing below it
runs.

![alt text](decision.png)

---

## The Compliance Guarantee

The layer deciding where money moves is **deterministic, never an LLM call.** An LLM
operates in exactly two places — classifying the minority of failures a rule can't
confidently bucket, and generating natural language (WhatsApp copy inside pre-approved
template slots, the Hinglish voice script). It never decides *whether* or *how much*
money moves.

- `RETRY_CEILING = 3` is a Python constant in `decide/guard_clauses.py`, checked before
  `config/rules_table.yaml` is even loaded — not editable by a config change.
- DND is checked before risk tier, before amount, before the cost gate — first, always,
  no exceptions.
- Cancellation intent is checked twice, in two independent modules
  (`classify/cancellation_gate.py` and `decide/guard_clauses.py`), so a bug in one can't
  compromise the one decision that must never be wrong.

---

## Results

Measured across a real batch run:

| Metric | Value |
|---|---|
| ₹ Recovered | **₹12,34,560** (↑28%) |
| Recovery Rate | **78%** |
| Cost per Recovery | **₹12** |
| Customers Recovered | **3,402** |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (async) |
| Database | PostgreSQL (Supabase), SQLAlchemy (async) + asyncpg, connection pooling |
| Queue / Ingestion | Redis (producer-consumer, in-memory fallback) |
| LLM Classification & Transcription | Groq (LLM inference + Whisper) |
| Messaging & Voice | Twilio (WhatsApp Business API, outbound voice) |
| Frontend | React + Vite, Tailwind CSS |
| Testing | Pytest |

---

## Project Structure

```
vasooli/
├── frontend/                      # React dashboard — merchant / risk-team facing
│   └── src/
│
├── src/vasooli/                   # Main Python package
│   ├── api/                       # FastAPI application layer
│   │   ├── main.py                # App factory, CORS, lifespan
│   │   ├── database.py            # Async SQLAlchemy engine & session
│   │   ├── deps.py                # FastAPI dependency injection
│   │   ├── models.py              # SQLAlchemy ORM models (RecoveryEvent, PromiseToPay, AuditLog)
│   │   ├── routes/
│   │   │   ├── events.py          # GET /api/v1/records — paginated recovery records
│   │   │   ├── system.py          # GET /health
│   │   │   ├── voice.py           # Voice call initiation & TwiML callbacks
│   │   │   └── webhooks.py        # POST /webhooks/razorpay
│   │   └── schemas/               # Pydantic request/response schemas
│   │       ├── event.py
│   │       ├── promise.py
│   │       ├── audit.py
│   │       └── common.py
│   ├── ingest/                    # Webhook receiver, signature verification, dedup, queue
│   │   ├── webhook_receiver.py    # Standalone FastAPI app for raw webhook ingestion
│   │   ├── queue.py               # Redis queue with in-memory fallback
│   │   ├── dedupe_store.py        # Event deduplication (Redis-backed)
│   │   └── signature.py           # HMAC-SHA256 Razorpay signature verification
│   ├── enrichment/                # Account history, entity enrichment
│   │   ├── account_history.py     # psycopg2 — historical bounce lookup
│   │   └── entity_fetch.py        # Entity metadata enrichment
│   ├── classify/
│   │   ├── cancellation_gate.py   # Isolated cancellation intent check — checked first
│   │   ├── rules_classifier.py    # Deterministic lookup — ~92% of records
│   │   └── llm_classifier.py      # Groq fallback with confidence score
│   ├── decide/
│   │   ├── guard_clauses.py       # Hard-coded: retry ceiling, DND, chronic bouncer
│   │   ├── rules_engine.py        # Loads config/rules_table.yaml
│   │   ├── voice_policy.py        # Voice escalation policy
│   │   ├── budget_allocator.py    # Portfolio-level expected-value ranking
│   │   └── cost_gate.py           # Channel cost gate (config/channel_costs.yaml)
│   ├── execute/                   # ChannelAdapter interface + channel adapters
│   │   ├── base_adapter.py        # Abstract base class
│   │   ├── voice_adapter.py       # Twilio outbound voice calls
│   │   ├── whatsapp_adapter.py    # Twilio WhatsApp Business API
│   │   ├── retry_adapter.py       # Razorpay retry trigger
│   │   ├── promise_to_pay.py      # Promise-to-pay capture
│   │   └── rate_limiter.py        # Per-customer send rate limiting
│   ├── audit/                     # Append-only audit log, dead-letter queue
│   │   ├── audit_log.py
│   │   └── dead_letter.py
│   ├── report/                    # Recovery metrics, funnel, exceptions
│   │   └── metrics.py
│   ├── services/                  # Background services
│   │   ├── voice_service.py       # Voice call session management
│   │   ├── promise_monitor.py     # Promise-to-pay follow-up monitor
│   │   ├── sequencer_service.py   # Multi-step outreach sequencer
│   │   └── pdf_service.py         # PDF report generation
│   ├── prompts/
│   │   └── llm_classify.txt       # LLM system prompt for classification
│   ├── models.py                  # Shared pipeline dataclasses (FailureEvent, Decision, …)
│   ├── db_events.py               # psycopg2 write helpers for pipeline events
│   ├── orchestrator.py            # Pipeline orchestrator (ingest → classify → decide → execute → audit)
│   ├── sequencer_worker.py        # Standalone sequencer worker loop
│   └── worker.py                  # Redis consumer worker loop
│
├── config/
│   ├── rules_table.yaml           # Editable decision rules — NOT the guardrails
│   └── channel_costs.yaml         # Per-channel cost assumptions
│
├── migrations/                    # Raw SQL migration files (run in order against Supabase/PostgreSQL)
│   ├── 001_init_recovery_tracking.sql
│   ├── 002_add_raw_payload.sql
│   ├── 003_add_phone_number.sql
│   └── 004_add_sequencer_fields.sql
│
├── data/                          # Batch input data (JSON)
├── docs/                          # Additional documentation
├── scripts/                       # Developer / demo scripts
│   ├── generate_synthetic_data.py
│   ├── run_demo.py
│   ├── seed_demo_data.py
│   ├── test_voice_send.py         # Send a real Twilio voice call
│   ├── test_whatsapp_send.py      # Send a real WhatsApp message
│   └── trigger_chronic_bouncer.py # Simulate a chronic-bouncer pipeline run
├── tests/                         # Pytest test suite
│
├── run_api.py                     # FastAPI entry point (uvicorn launcher)
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Installation

### Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.10+ |
| PostgreSQL | 14+ (or a [Supabase](https://supabase.com) project) |
| Redis | 7+ (optional — falls back to in-memory queue if not available) |
| Node.js | 18+ (only needed for the React frontend) |

### 1. Clone and set up Python environment

```bash
git clone https://github.com/Om-Varma12/vasooli.git
cd vasooli

# Create a virtual environment
python -m venv .venv

# Activate it
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Install the package in editable mode (needed for `src/` layout)
pip install -e .
```

### 2. Configure environment variables

Copy the example below into a `.env` file in the project root, then fill in your values:

```dotenv
# ── PostgreSQL ────────────────────────────────────────────────────────────────
# psycopg2 format (used by the pipeline worker and DB helpers)
DATABASE_URL=postgresql://user:password@host:5432/vasooli

# ── Redis (optional) ──────────────────────────────────────────────────────────
# If omitted, the system falls back to an in-memory queue automatically
REDIS_URL=redis://localhost:6379/0

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_API_KEY=gsk_...
# Optional — defaults to qwen/qwen3-8b if not set
GROQ_LLM_MODEL=qwen/qwen3-8b

# ── Twilio ────────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...

# Voice
TWILIO_VOICE_FROM=+1...          # Your Twilio phone number
VOICE_BASE_URL=https://your-tunnel.ngrok-free.app  # Public URL for TwiML callbacks

# WhatsApp
TWILIO_WHATSAPP_FROM=+14155238886  # Twilio sandbox / approved WhatsApp sender
TWILIO_WHATSAPP_TO=+91...          # Recipient (your number for testing)

# ── Razorpay ──────────────────────────────────────────────────────────────────
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...        # Set in your Razorpay Dashboard → Webhooks
```

### 3. Set up the database

Run each migration file against your PostgreSQL database **in order**:

```bash
psql $DATABASE_URL -f migrations/001_init_recovery_tracking.sql
psql $DATABASE_URL -f migrations/002_add_raw_payload.sql
psql $DATABASE_URL -f migrations/003_add_phone_number.sql
psql $DATABASE_URL -f migrations/004_add_sequencer_fields.sql
```

> If you are using Supabase, paste the SQL from each file into the **SQL Editor** in the Supabase Dashboard and run them in order.

### 4. (Optional) Frontend setup

```bash
cd frontend
npm install
npm run dev   # Starts Vite dev server at http://localhost:5173
```

---

## Running the Project

There are three independently runnable processes. Start them in separate terminals.

### 1. FastAPI backend (port 8001)

This serves the REST API consumed by the React frontend and exposes the voice call routes.

```bash
# From the project root:
python run_api.py
```

The API will be available at `http://127.0.0.1:8001`.  
Interactive docs: `http://127.0.0.1:8001/docs`

### 2. Webhook receiver (port 8000)

A separate, lightweight FastAPI app that receives raw Razorpay webhook payloads, verifies
their HMAC signature, deduplicates them, and pushes them onto the Redis queue.

```bash
uvicorn vasooli.ingest.webhook_receiver:app --host 0.0.0.0 --port 8000 --reload
```

To receive real Razorpay webhooks in development, expose port 8000 publicly with a tunnel
(e.g. [ngrok](https://ngrok.com)):

```bash
ngrok http 8000
# Then set your Razorpay Dashboard → Webhook URL to: https://<id>.ngrok-free.app/webhooks/razorpay
```

### 3. Recovery worker

Reads events from the Redis queue and runs each one through the full pipeline:
`ingest → enrich → classify → decide → execute → audit`.

```bash
python -m vasooli.worker
```

The worker logs every decision to stdout and writes audit records to PostgreSQL.

### Quick demo (no live APIs needed)

Generate synthetic failure events and run the full pipeline against them locally:

```bash
python scripts/generate_synthetic_data.py   # writes to data/
python scripts/run_demo.py                  # runs the batch through the pipeline
# or simply:
make demo
```

### Integration test scripts

These scripts make **real** API calls (Twilio, Groq). Requires a valid `.env`.

```bash
# Place a real outbound voice call
python scripts/test_voice_send.py

# Send a real WhatsApp message via Twilio sandbox
python scripts/test_whatsapp_send.py

# Trigger the chronic-bouncer pipeline path
python scripts/trigger_chronic_bouncer.py
```

---

## API Reference

| Endpoint | Description |
|---|---|
| `POST /webhooks/razorpay` | Signature-verified, deduplicated webhook receiver |
| `GET /api/v1/records` | Paginated, filterable recovery records |
| `GET /api/v1/records/{record_id}` | Single record detail |
| `GET /api/v1/records/{record_id}/audit` | Full audit trail for a record |
| `GET /api/v1/summary` | Aggregate recovery metrics |
| `GET /health` | Service and DB connectivity check |

---

## Testing

```bash
pytest tests/ -v
```

---

## Roadmap

- Two-way voice with real-time speech recognition (currently one-way TTS)
- Proactive risk scoring — flagging a mandate as high-risk before it fails
- Alembic-managed schema migrations

---

## Acknowledgments

Built with respect for the players already solving pieces of this well — Spocto X,
Credgenics, and Razorpay's own Intelligent Retry Engine. Vasooli exists to close the gap
between them, not to replace what already works.