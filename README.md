# Vasooli — a bounded, multi-channel revenue recovery agent for UPI/eNACH rails

> Working name. "Vasooli" = recovery/collection in Hindi. Rename freely.

**Track:** 03 — AI Revenue Recovery
**Built for:** Razorpay AI Buildathon 2026
**One-line pitch:** the enterprise incumbents (Spocto X, Credgenics) already solve the
lending/eNACH side well, for banks and NBFCs who can afford them. Razorpay's own Intelligent
Retry Engine solves one rung of the subscription side. Nobody unifies UPI Autopay
subscriptions, eNACH EMIs, *and* B2B receivables under one lean, audit-first decision layer.
Vasooli is that layer, built directly on Razorpay's own APIs.

**For the full picture:**
- **Why this problem, the numbers, the competitive landscape, before/after scenarios** →
  [`docs/PROBLEM_STATEMENT.md`](docs/PROBLEM_STATEMENT.md)
- **Repo structure, how a record flows through the system, design decisions, deferred
  items, the day-by-day plan** → [`PROJECT_PLAN.md`](PROJECT_PLAN.md)
- **Real Razorpay webhook events this is shaped against** →
  [`docs/razorpay_webhook_events.md`](docs/razorpay_webhook_events.md)

---

## The one thing to say out loud in the pitch

The policy engine that decides retries/escalations is **deterministic, not an LLM call.** An
LLM is used in exactly two places: classifying the ~8% of failures a rule can't confidently
bucket, and generating natural language (WhatsApp copy inside pre-approved template slots,
the Hinglish voice conversation). The LLM never decides *whether* or *how much* money moves.
That's a rules table you can print out and hand to a compliance officer.

```
                    ┌─────────────────────────────────────────────┐
                    │              AUDIT LOG (append-only)         │
                    │   every hop below writes here, with reason   │
                    └───────────────▲───────────────────────────────┘
                                    │
 Razorpay Webhooks   ┌──────────┐   │   ┌───────────────┐   ┌────────────────┐
 payment.failed      │          │   │   │  classify/    │   │  decide/        │
 subscription.pending├─ ingest ─┼───┼──▶│  rules + LLM  ├──▶│  guard clauses  │
 subscription.halted │          │   │   │  fallback     │   │  + rules table  │
 invoice.expired     └──────────┘   │   └───────────────┘   └───────┬────────┘
                                    │                                │
                                    │                     ┌──────────┴──────────┐
                                    │                     ▼                     ▼
                              ┌─────┴─────┐        ┌─────────────┐      ┌─────────────┐
                              │  STOP /   │        │  execute/   │      │   report/   │
                              │  human    │        │  retry ·    │      │  ₹ recovered│
                              │  handoff  │        │  whatsapp · │      │  funnel ·   │
                              │(graceful  │        │  voice ·    │      │  exceptions │
                              │ failure)  │        │  promise    │      │             │
                              └───────────┘        └─────────────┘      └─────────────┘
```

## Quick start

```bash
pip install -r requirements-dev.txt
python scripts/generate_synthetic_data.py
python scripts/run_demo.py
pytest tests/ -v          # 19 tests, all passing
```

Or just `make demo` / `make test`. See `PROJECT_PLAN.md` section 7 for the full command
reference and `Makefile` for shortcuts.

## Bounded rules currently encoded (v0 — tune in `config/`, don't hide)

- **Retry ceiling:** max 3 automated retries after the original attempt, matching NPCI/
  Razorpay's own `subscription.halted` transition point — enforced in
  `decide/guard_clauses.py` as a Python constant, deliberately outside `config/rules_table.yaml`.
- **Consent/DND:** blocks voice escalation unconditionally, checked before the cost gate.
- **Cost gate:** voice only fires when `amount × recovery_probability > cost_per_call`
  (`config/channel_costs.yaml`).
- **Genuinely-dead detection:** `mandate_cancelled_by_user` / `account_closed` never enter
  the retry/escalation ladder — straight to human handoff. This is the scripted "one failure
  handled gracefully" demo moment.

Full detail on all of this, including why each design choice is the way it is, lives in
`PROJECT_PLAN.md`.
