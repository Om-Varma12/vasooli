# Vasooli Development Roadmap

This document outlines the remaining tasks, integrations, and architectural components required to transition **Vasooli** from its current mock-demo batch processor state to a production-ready, real-time revenue recovery system.

---

## 1. Webhook Ingestion & Pre-processing
Currently, ingestion is simulated by loading a static JSON batch. The production ingest pipeline requires:

- [ ] **FastAPI Webhook Receiver (`src/vasooli/ingest/webhook_receiver.py`)**
  - Implement a public POST endpoint to listen to Razorpay webhook event payloads.
- [ ] **HMAC Signature Verification (`src/vasooli/ingest/signature.py`)**
  - Validate incoming payloads against Razorpay's signing keys to prevent spoofing.
- [ ] **Idempotency & Deduplication (`src/vasooli/ingest/dedupe_store.py`)**
  - Set up a Redis-backed deduplication store using `SETNX` on the Razorpay `event_id` to guarantee at-most-once processing of redelivered webhooks.
- [ ] **Async Message Queue (`src/vasooli/ingest/queue.py`)**
  - Safely enqueue validated events to an asynchronous message broker (e.g., Celery/RabbitMQ, Redis, or AWS SQS) for consumption.

---

## 2. Enrichment & Context Layer
The decide layer requires historical context to dynamically adjust recovery weights.

- [ ] **Account History Storage (`src/vasooli/enrichment/account_history.py`)**
  - Deploy a datastore (e.g., SQLite or PostgreSQL) to track payment profiles.
- [ ] **Bounce History Tracking**
  - Record the count and reason for previous payment failures per customer mandate.
- [ ] **Live Entity Fallback Fetch (`src/vasooli/enrichment/entity_fetch.py`)**
  - Implement fallback HTTP requests to the Razorpay Subscriptions/Payments APIs to enrich the event payload if webhook metadata is missing.

---

## 3. LLM Classification Wiring
The LLM classification currently returns stubbed values.

- [ ] **API Client Wiring (`src/vasooli/classify/llm_classifier.py`)**
  - Integrate a live client wrapper (e.g., Anthropic Claude or Google Gemini API) to categorize `unclassified_bank_response` codes.
- [ ] **Low-Confidence Review Queue Routing**
  - Route classification results below `CONFIDENCE_THRESHOLD = 0.6` to a manual human review dashboard rather than executing automated triggers.

---

## 4. Real Execution Channels
Execution adapters currently simulate success/failure outputs using random probability logic.

- [ ] **WhatsApp Business API Integration (`src/vasooli/execute/whatsapp_adapter.py`)**
  - Connect Meta’s Cloud API for WhatsApp to deliver template nudges (filling placeholder slots such as amount, merchant name, and payment links).
- [ ] **Outbound Telephony (`src/vasooli/execute/voice_adapter.py`)**
  - Wire up an outbound telephony client (e.g., Twilio, Exotel, or Sarv) to trigger calls.
- [ ] **Speech-to-Text (STT) & Text-to-Speech (TTS)**
  - Integrate services (e.g., Google TTS/STT or Deepgram) to speak to customers in Hinglish and transcribe their spoken responses in real-time.
- [ ] **Promise-to-Pay Database & Cron Scheduler (`src/vasooli/execute/promise_to_pay.py`)**
  - Save customer payment promises ("I will pay tomorrow") into a database table.
  - Implement a recurring scheduler (e.g., Celery Beat or a cron job) to verify if the payment was received by the promised date.

---

## 5. Operations, Infrastructure & Resiliency

- [ ] **Asynchronous Worker Loop (`src/vasooli/worker.py`)**
  - Build the consumer worker process to pull events from the queue, execute the pipeline, and commit entries to the audit logs.
- [ ] **API Rate Limiting (`src/vasooli/execute/rate_limiter.py`)**
  - Build channel-level rate limiters to respect API provider throughput ceilings.
- [ ] **Dead Letter Queue Routing (`src/vasooli/audit/dead_letter.py`)**
  - Wire up error boundaries to route malformed payloads, API timeouts, and unhandled system failures to a Dead Letter Queue (DLQ) for alerting.
