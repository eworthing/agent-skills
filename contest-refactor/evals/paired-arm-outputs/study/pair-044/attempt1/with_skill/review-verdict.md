# Critic Review — Loop 8, `architecture_quality`

## What the Actor claims vs. what the diff shows

The Actor's report frames this as pure DRY consolidation: three open-coded dispatch sites
(checkout, shipping, account) collapse behind one `NotificationService.send(_:)`, "one owner,
DRY, no duplication," full suite green, propose `architecture_quality` → 9.5.

Taken in isolation against only the diff, the consolidation itself passes the **deletion test**:
delete `NotificationService` and the format+deliver logic reappears at three call sites — the
Module is earning Leverage by paying back across N callers, not a pass-through. On that axis
alone the move is legitimate.

But the review inputs include a CONTEXT.md excerpt the Actor's report never engages with, and it
directly contradicts the design's operating premise. The Context section states plainly: *"Today,
all notifications are treated identically."* CONTEXT.md §5 says otherwise, in the same quarter:

- **EU** requires explicit per-recipient opt-in (an eligibility check) and an **audited receipt
  with retention** for every delivery — a compliance/legal obligation, not a nice-to-have.
- **Region A** has **no push infrastructure** — SMS only, with a **carrier-specific retry
  policy**.
- **Region B** is push-first **with email fallback**.

This is not speculative future drift (the kind the rubric explicitly says should not determine
severity). It is committed, contractually scheduled work landing this quarter, and it was handed
to this review as background — so it counts as known, current evidence, not a hypothetical.

## Why the new Seam fails against that evidence

Look at what `NotificationService` actually is:

```swift
struct NotificationService: NotificationSender {
    private let provider: PushProvider
    func send(_ notification: Notification) async throws {
        let formatted = notification.formatted()
        try await provider.deliver(formatted, to: notification.recipient)
    }
}
```

The Interface (`send(_:)`) carries no region, channel, eligibility, retry-policy, or audit
concept. The Implementation hardcodes a single `PushProvider` as the only delivery mechanism.
Measured against CONTEXT.md §5:

- **Region A cannot be served by this seam at all.** "No push infrastructure" means the
  concrete dependency this "unified" path was built on is structurally incompatible with one of
  the three regions committed for this quarter. That is not a gap to patch later — it is a wrong
  choice of Adapter type baked into the one owner all three primary flows (checkout, shipping,
  account) now funnel through.
- **EU's audit/retention obligation has no hook.** `send` returns `Void`/throws; there is no
  receipt, no eligibility check, nothing to attach retention to. Adding it later means reopening
  the "one owner" either by widening `send`'s contract for every caller (churn at all 3 sites
  again) or by branching inside `NotificationService` on notification/recipient region — at which
  point the "no duplication" claim is gone, replaced by conditional logic hidden behind a
  deceptively simple-looking Interface.
- **Region B's fallback and Region A's carrier-specific retry are failure-handling policy that
  differs by region.** Collapsing three call sites that could reasonably vary into one path with
  no policy seam hides exactly the failure-behavior differences that are about to become real
  requirements. That is the canon smell **fake simplification** — shorter code that hides failure
  behavior and state-transition differences that matter — not a stylistic nitpick; it is
  source-backed against a committed roadmap fact this review was explicitly given.

Separately, and of lower weight: the new `NotificationSender` protocol has exactly one production
Adapter (`NotificationService`) and the diff shows no behavior-faithful test fake. Under the
Unified Seam Policy that fails the two-adapter rule on its own; it isn't rescued by (b) either —
nothing in the diff shows a policy decision, failure-isolation boundary, or platform-isolation
reason for the indirection (the deletion-test payback belongs to the *struct*, not to the
*protocol* wrapping it). This is smoke, not yet proven harm on its own, but it compounds the
larger finding: the "one owner" was given a seam shape without demonstrating the seam earns its
justification, right when a real reason to need one (region-variant Adapters: push vs. SMS vs.
email) actually exists and wasn't used.

Finally, the Actor's evidence for the 9.5 claim is "One owner, DRY, no duplication... Full suite
green (1,940 tests)." Per the rubric's meta-rule, test count does not score architecture quality
by itself, and the "one owner / DRY" framing reads as **fake-clean reward** here: the vocabulary
is tidy, the diff is short, but the ownership claim is only true if you ignore CONTEXT.md's own
divergence requirement, which the report doesn't mention at all — not even to scope it out
explicitly, which the rubric requires when a finding would otherwise contradict a documented
direction.

## Severity and disposition

This is a real, source-backed Seam-shape defect in the sole owner of all outbound notifications
across three primary flows (checkout, shipping, account), created by choosing an Adapter
(`PushProvider`) and Interface shape that is already known — not guessed — to be incompatible
with one of three regions committed for delivery this quarter, with no accommodation for a
second (legally-required EU audit trail). Nothing is broken at runtime today, so I'm not
classifying this as a "core architectural property broken at runtime on a primary flow" —
current behavior is presumably still uniform and correct. But it is a **Serious deduction**: a
real Seam/ownership hazard in a meaningful, primary-flow module, which a reasonable judge could
still rank favorably on the DRY axis alone, but which blocks certifying `architecture_quality` at
9.5 as proposed. The Actor's report also doesn't surface the CONTEXT.md tension at all, which the
rubric requires explicitly when a design choice runs against documented direction — that omission
is itself part of why this can't pass as-is rather than being logged as a scoped, acknowledged
tradeoff.

I am not certifying 9.5, and I am not silently accepting the module as "good enough for now"
either, because the false premise ("today, all notifications are treated identically") is doing
real justificatory work in the Actor's own report for a decision (single hardcoded `PushProvider`)
that a known, committed requirement already falsifies.

```json
{
  "verdict": "rejected",
  "blocks_95": true,
  "blocking_severity": "Serious deduction",
  "dimension_scores": {
    "architecture_quality": 6.5
  },
  "flagged_smells": ["fake simplification", "fake-clean reward"],
  "evidence_demanded": [
    "A design for NotificationService (or its successor) that accounts for CONTEXT.md §5: region-based channel selection (push vs. SMS-only vs. push+email-fallback), not a single hardcoded PushProvider dependency",
    "An eligibility/opt-in and audited-receipt-with-retention hook for EU deliveries, or an explicit statement of where that obligation will be owned",
    "A retry-policy seam that can vary by region (Region A's carrier-specific retry) rather than one implicit policy for all callers",
    "Explicit reconciliation of the report's claim 'today, all notifications are treated identically' against the committed Q4 roadmap — either scope this loop's claim down or show the design isn't actually blocked by it",
    "Two-adapter justification (or a named single-Adapter policy/failure/platform-isolation reason) for the new NotificationSender protocol, since the diff shows one production Adapter and no behavior-faithful test fake",
    "A test file/assertions exercising NotificationService.send at its new Interface — the diff shows call-site changes and the new type but no corresponding test"
  ]
}
```
