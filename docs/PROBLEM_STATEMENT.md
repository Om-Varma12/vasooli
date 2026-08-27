# The problem Vasooli solves

## 1. Scale

- UPI Autopay: 1.27B+ mandates registered by Nov 2025 (10x growth in under two years),
  850M+ cumulative registrations by March 2026, 95M active mandates, ~4.2 crore
  transactions/month (NPCI data). Subscription economy this feeds is projected at $350B.
- **Lead stat, use this one:** UPI AutoPay failure rates run 8-15%, vs 2-3% for card
  mandates (design-guide estimate, the defensible number). NPCI's own August 2025 data
  showed a single bad month spiking to 55-90% failure, driven by insufficient balances and
  wrong beneficiary details — real, but volatility evidence, not the steady-state baseline.
  Cite 8-15% first; mention the 90% spike only as "and in a bad month, this gets much worse."
  Do not lead with the 90% figure — it invites an easy, credibility-costing pushback from
  anyone who's read the NPCI release. Whatever the true baseline, absolute failure volume is
  enormous: 20M+ UPI Autopay mandates are cancelled every month, mostly due to insufficient
  balance, spanning OTT, loans, investments, utilities.
- NACH/eNACH (lending EMIs, SIPs, insurance): bounce rates historically 30-45%
  (2020-21 data); a well-instrumented modern NBFC book runs closer to 12%. Every bounce
  costs ₹300-1,000 (NACH return fee) + ₹500-1,500 (lender bounce fee) + late interest, and
  can cost a borrower 100-200+ CIBIL points. RBI's Code of Conduct puts soft collection
  (calls/SMS/re-presentation) as the response to the first 1-2 bounces, escalating to a
  recovery agent only after 60-90 days, NPA at 90 days.
- Globally, for scale: failed payments cost subscription businesses an estimated $118.5B/yr;
  involuntary churn is 20-40% of total churn and the cheapest segment to recover.

## 2. What exists and why the gap is narrower than it first looks

Global dunning tools (FlyCode, Stuut, Chargebee, Churn Buster, Redux, Respaid) are a mature,
funded category — real product, real revenue, some even doing autonomous voice outreach and
ERP write-back. Every one of them is Stripe/card-rail-native. India's recurring-payment
stack doesn't map onto "retry a card, update card on file":

- UPI Autopay has no card to update — failures are bank-side real-time approvals, not expired
  plastic.
- NPCI enforces a hard 3-retry ceiling as infrastructure (subscription.halted trigger), not a
  merchant setting.
- eNACH has its own mandate lifecycle: sponsor-bank registration, non-revocable variants for
  lending, RBI-mandated pre-debit notifications.
- EMI collections are RBI-regulated with specific timing/conduct rules.

**But on the lending/eNACH side specifically, this is NOT a greenfield gap — say this
yourself before a judge does.** Spocto X (Yubi) is India's largest end-to-end debt
collections platform powered by agentic AI: 5.5 crore+ monthly accounts managed, 8.9 crore+
borrowers protected from becoming NPAs, 60+ financial institutions as clients across private
banks, PSUs, NBFCs, and fintechs, ₹167 crore annual revenue as of March 2025. It already does
predictive bounce-risk scoring, omnichannel WhatsApp/SMS/voice outreach, and has a
conversational-AI partnership specifically built for complex-language debt resolution in
India — which directly covers the "Hinglish voice" ground on the lending side. Credgenics
does the same category with legal-collections escalation layered on top. These are real,
proven, enterprise-grade competitors, not hypothetical ones.

Razorpay's own core Subscriptions product already has retry logic beyond the newer beta
piece, and PayU ships similar. The "Intelligent Retry Engine" (beta, launched FTX 2026, part
of Intelligent Revenue-Protect, automatic WhatsApp recovery links) is Razorpay's newest
weapon here, not their only one.

**What's actually still real whitespace, stated at the size it deserves:** Spocto and
Credgenics are lending-focused — built for banks/NBFCs, not for the relationship-sensitive
B2B distributor-invoice collections culture, and not spanning UPI Autopay subscription churn
at all. Razorpay solves subscriptions, not lending or B2B receivables. **Nobody is unifying
all three rails — UPI Autopay subscriptions, eNACH EMIs, and B2B receivables — under one
audit-first decision layer a compliance reviewer can actually read.** That's a real, honest,
narrower claim than "nobody's solved this," and it's the one to make.

## 3. What Vasooli is

A decision layer, not a retry engine or a chatbot. For every failed payment / halted mandate
/ overdue invoice: diagnose root cause -> decide via a fixed, inspectable rules table (never
an LLM judgment call on the money decision itself) -> execute across retry/WhatsApp/Hinglish
voice -> track any promise-to-pay -> log every decision to an audit trail in plain language.

## 4. Five before/after situations

1. **OTT subscription, insufficient funds** — today: immediate identical retries burn the
   3-retry ceiling on nothing that changed. Vasooli: smart-timed retry windows, ceiling spent
   deliberately, WhatsApp only once retries are genuinely exhausted.
2. **NBFC EMI, mandate expired** — today: treated like any other bounce, sometimes retried
   pointlessly. Vasooli: classified as not retry-worthy, routes straight to re-authorization
   link, escalates to a Hinglish call explaining the actual problem.
3. **SIP mandate, bank downtime** — today: looks identical to customer-caused failure, causes
   needless customer anxiety. Vasooli: classified as high-probability transient, retried
   quietly, usually no customer contact at all.
4. **B2B wholesale invoice, 45 days overdue** — today: fully manual, promises live in someone's
   WhatsApp/memory, escalation is all-or-nothing. Vasooli: structured promise-to-pay ledger
   with scheduled follow-up, gentler B2B-specific escalation ladder, clean audit trail.
5. **Genuinely cancelled customer** — today: many systems keep retrying/messaging regardless.
   Vasooli: cancellation intent is the first gate checked, before anything else — zero
   retries, zero messages, zero calls, straight to human handoff.

## 5. Mapping to the track's bar

Explainable + bounded actions -> deterministic policy engine, no LLM in the money decision.
Compliant escalation -> retry ceiling is NPCI's real number, not a config default.
Stopping rules -> cancellation-intent gate runs first, unconditionally.
Audit trail -> data/audit_log.jsonl, one line per decision, human-readable.
Measured recovery -> src/vasooli/report/metrics.py, computed from the same probabilities
the decide layer used to decide whether a channel was worth the cost.

## 6. Positioning, one sentence

Not "nobody's solved this." **"The enterprise incumbents solve two-thirds of this well, for
customers who can afford them; we're the lean, cross-rail, audit-first layer for everyone
else."** Say the competitor names yourself before a judge does — Spocto X, Credgenics,
Razorpay's own retry engine — then pivot to the specific, defensible gap: nobody spans all
three rails under one auditable decision layer.
