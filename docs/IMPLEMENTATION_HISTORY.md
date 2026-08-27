# Vasooli: Implementation History & Solved Challenges

This document tracks the core infrastructure, resilience, and scale features implemented in the Vasooli project. It provides a detailed overview of the problems tackled and the engineering solutions applied to make the system production-ready.

---

## 1. Webhook Ingest Layer (Live Event Processing)
**Problem:** The system initially only processed static, offline JSON batch files (`failed_payments_batch.json`). We needed a way to listen for live, real-time events triggered by the payment gateway (Razorpay).
**Solution:**
*   Built a lightweight, asynchronous HTTP server using **FastAPI** (`src/vasooli/ingest/webhook_receiver.py`).
*   Exposed a `POST /webhooks/razorpay` endpoint designed to do almost zero processing so it can immediately return a `200 OK`. This prevents the payment gateway from timing out and assuming our server is down.

## 2. Security & Signature Verification
**Problem:** Webhook endpoints are public. A malicious actor could send a fake payload pretending to be a failed payment, tricking our system into harassing a customer unnecessarily.
**Solution:**
*   Implemented cryptographic signature verification (`src/vasooli/ingest/signature.py`).
*   Uses **HMAC-SHA256** to hash the raw request body against our private secret key.
*   The system compares this hash to the `x-razorpay-signature` header provided by the gateway. If they match, the payload is 100% authentic and untampered.

## 3. Idempotency (Deduplication)
**Problem:** Network unreliability means Razorpay might send the exact same webhook twice (e.g., if our `200 OK` response was lost in transit). We cannot safely run the policy engine and trigger WhatsApp messages twice for the same event.
**Solution:**
*   Built an **Idempotency Store** (`src/vasooli/ingest/dedupe_store.py`) backed by Redis (with an in-memory `set` fallback).
*   Tracks every unique `razorpay_event_id`. If an event ID has already been seen, the system intercepts it at the API layer, immediately returns `200 OK`, and drops it before it reaches the processing queues.

## 4. Producer-Consumer Queue Architecture
**Problem:** Processing a failed payment (classification, decision logic, LLM calls, external API calls) is slow. If the API waits for this to finish before responding to Razorpay, the connection will time out.
**Solution:**
*   Decoupled ingestion from processing using a **Queue** (`src/vasooli/ingest/queue.py`).
*   The FastAPI receiver acts as the **Producer**, pushing validated events onto a Redis List (`RPUSH`).
*   The background worker acts as the **Consumer**. Crucially, it uses **Blocking Pops (`BLPOP`)** instead of infinite while-loops. This puts the worker thread to sleep at the OS level until an event arrives, saving massive amounts of CPU.

## 5. Background Worker Resilience & Concurrency
**Problem:** Processing one event at a time is too slow for scale. Furthermore, if the system is restarted or crashes, we can't afford to lose events currently being processed or crash due to momentary API outages.
**Solution:**
*   **Concurrency:** Upgraded the worker daemon (`src/vasooli/worker.py`) to use a `ThreadPoolExecutor`, allowing it to process multiple webhooks simultaneously.
*   **Graceful Shutdown:** Registered OS Signal Handlers (`SIGINT`, `SIGTERM`, `SIGBREAK`). If the server is restarted, the worker stops pulling new events and waits for the active threads to finish their current tasks before cleanly shutting down.
*   **Transient Error Retries:** Implemented automatic **Exponential Backoff**. If an external API throws a timeout or 500 error, the worker catches it, increments a retry counter, and re-enqueues the event to try again later (e.g., after 2, 4, then 8 seconds).

## 6. Token-Bucket Rate Limiter
**Problem:** External channel providers (like WhatsApp Business API or Exotel telephony) have strict throughput limits (e.g., 60 requests per minute). If we hit them with a sudden burst of 100 messages, they will block or drop our requests. A simple reset counter is flawed because it allows bursts right on the reset boundary.
**Solution:**
*   Implemented a thread-safe **Token-Bucket Rate Limiter** (`src/vasooli/execute/rate_limiter.py`).
*   Tokens refill at a constant, calculated rate (e.g., 1 token per second). Threads must `acquire()` a token before calling an external API.
*   This perfectly smooths out bursts. If the bucket is empty, the system gracefully routes the event to the Dead Letter Queue instead of dropping it silently.

## 7. Dead Letter Queue (DLQ)
**Problem:** Unhandled exceptions, malformed payloads, or exhausted rate limits usually crash batch scripts or result in silently lost data. 
**Solution:**
*   Built a **Dead Letter Queue** (`src/vasooli/audit/dead_letter.py`) as a secure graveyard for failed events.
*   Failed events are written to an atomic, append-only `jsonl` file with deep context (pipeline stage, error message, raw payload, timestamp).
*   Wired the orchestrator to catch per-record crashes during batch processing and route them to the DLQ, ensuring one bad record never aborts an entire batch.
*   Provided a built-in CLI (`python -m vasooli.audit.dead_letter`) to easily filter, read, and inspect failed events for debugging.
