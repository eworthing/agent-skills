# Critic Review — Loop 8, `architecture_quality`

## Scope note

This review is scoped to the three attached inputs only: `scenario.md` (diff + Actor report),
`architecture-rubric.md`, and `method.md`. No live repository, git history, or other files were
read. The Authority Map (method.md Step 2) and the leaf-module duplication sweep (Step 6) cannot
be produced in full because only a diff excerpt is available, not the full source tree — this
review is bounded to what that diff and the accompanying `CONTEXT.md` excerpt make visible, per
the Evidence Chain (`method.md` § The Evidence Chain): claims are scoped to what current evidence
actually shows, not generalized beyond it.

## Independent re-derivation (per method.md Step 1 — Inspect current code only)

The Actor's report claims: "One owner, DRY, no duplication... Full suite green (1,940 tests).
Proposing `architecture_quality` → 9.5." Per the Anchor-to-source warning, that claim is
re-derived from the diff itself rather than accepted on report.

**What the diff actually does.** A new `NotificationSender` protocol and its sole conformer
`NotificationService` replace three open-coded dispatch sites (checkout, shipping, account) that
each built a message and called `pushProvider.deliver(...)` directly. All three now call
`notifications.send(_:)`. `NotificationService.send` does exactly two things: `notification.formatted()`,
then `provider.deliver(formatted, to: notification.recipient)`, where `provider: PushProvider` is
a single concrete, push-only dependency. This is a real Locality win for *today's* stated
condition — "all notifications are treated identically" — and it does collapse duplicated dispatch
ceremony at three call sites into one. That part of the claim holds.

**Where the claim overreaches.** The task supplies a `CONTEXT.md` excerpt specifically because it
bears on this architectural decision, and the rubric requires using it, not filing it away
(`architecture-rubric.md` § CONTEXT.md / docs/adr Awareness). §5 is not aspirational — it is
"Roadmap (committed, this quarter — Q4)" — and it states plainly that eligibility, channel
selection, retry, and audit obligations **differ per region**: EU requires per-recipient opt-in
plus an audited, retained delivery receipt; Region A has **no push infrastructure at all** (SMS
only, carrier-specific retry); Region B is push-first with email fallback.

Held against that, the shape just shipped is a problem, not a convenience:

- **Claim:** The new seam unifies dispatch around the wrong axis. It collapses the axis that only
  varied cosmetically (order vs. shipping vs. account message bodies) while giving zero purchase
  on the axis CONTEXT.md says will actually diverge next quarter (region: channel, eligibility,
  retry, audit).
- **Source:** `NotificationSender.send(_ notification: Notification) async throws` carries no
  channel, region, eligibility, or audit parameter. `NotificationService` is hard-wired to a
  single concrete `PushProvider` — there is no seam point for SMS or email delivery at all. The
  method body is `format → deliver`; there is no retry policy, no eligibility check, and no
  receipt/audit path anywhere in the Adapter.
- **Consequence:** Region A cannot be served through this seam in any form — it has no push
  infrastructure, and the only Adapter that exists is push-only. EU's audited-receipt-with-retention
  requirement has no attachment point in a `throws`-only, fire-and-forget `send`. This is not a
  hypothetical future concern the rubric tells reviewers to ignore ("unsupported speculation") —
  CONTEXT.md dates it as committed this quarter, which is exactly the kind of concrete,
  document-backed friction the rubric treats as real (`architecture-rubric.md` § CONTEXT.md
  Awareness; `method.md` Meta-Rule 3). A seam built with a name ("`NotificationService`," "one
  owner") that implies general-purpose delivery, but an implementation that is push-only and
  parameterless with respect to the one dimension known to fork immediately, is a **misleading
  abstraction** over a **weak domain model** — the domain concept actually being modeled next
  quarter is "region-scoped delivery policy," and this Interface has no vocabulary for it at all.
  Because the fork is proven (not speculative) and near-term, the Depth/Leverage this loop claims
  ("one Implementation pays back across N call sites") will very likely evaporate within the same
  quarter it was built, when the seam has to be reopened (or forked back apart) to add
  region-conditional channel/eligibility/retry/audit behavior it currently cannot express.
- **Remedy:** Do not certify `architecture_quality` → 9.5 on this shape unqualified. Either (a)
  show the Interface already carries what the region work needs — e.g., a channel/region or
  policy value threaded through `send`, so the upcoming EU/Region A/Region B work extends this
  seam rather than reworking it — or (b) have the Actor explicitly scope this loop's claim
  ("collapsed duplicate push-only dispatch across 3 call sites; region-variant policy is
  out-of-scope, tracked separately") instead of an unqualified 9.5. Neither is present in the
  report as given.

**Secondary, lower-confidence finding — seam justification.** `architecture-rubric.md` §
Architectural Tests #2 and § Unified Seam Policy require a new/restructured Seam to clear one of
two paths: two real Adapters (prod + behavior-faithful test fake), or a single Adapter that
encodes policy/failure-isolation/platform-isolation. The diff shows exactly one Adapter
(`NotificationService`) with no policy, retry, or failure-isolation logic in its body, and no test
fake is visible in the excerpt. On the evidence given, this seam does not visibly clear either
path — it may simply be that the fake exists outside the diff shown, which is why this is flagged
as evidence to demand rather than a confirmed violation, per the Evidence Chain rule to downgrade
an unprovable claim rather than assert it.

## Simplify Pressure Test (method.md § Step 2 gate) on the proposed fix

1. Fixes real ambiguity? Partially — removes duplicated dispatch ceremony for the currently-identical
   treatment, but does not touch (and in fact forecloses) the ambiguity CONTEXT.md says is about to
   matter.
2. Smallest honest fix? For the problem it addresses, yes. For the problem the codebase actually
   has coming (region-variant delivery), it is not a fix at all — it removed the seam points a
   region-aware version would need.
3. Avoids duplicate layers? No behavior-faithful second Adapter is shown; open question, not
   confirmed duplication.
4. Runtime behavior stays honest? Yes for current behavior — nothing here changes what ships today.
5. Product improvement measured against what's declined? The DRY gain at 3 call sites is real but
   modest; against it, the loop declined to leave (or build) any hook for a committed, dated,
   multi-region requirement landing the same quarter. That is a real cost the report does not
   weigh at all — Q5 fails.

## Verdict rationale

This is not a "likely disqualifier" — nothing is broken at runtime today, the stated
all-notifications-identical condition holds, and the suite is green. But it is a real, contained
Seam hazard in a meaningful module: the Interface picked the wrong axis to unify around, given
committed, dated, source-external evidence (CONTEXT.md §5) that the correct axis is about to
matter and this shape gives zero purchase on it. That is a **Serious deduction**, and it blocks
certifying `architecture_quality` at the 9.5 threshold this loop as claimed.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"architecture_quality": 8.0}, "flagged_smells": ["weak domain model", "misleading abstractions"], "evidence_demanded": ["Confirm whether NotificationSender has a behavior-faithful test fake (second Adapter) in the suite, or name which Unified Seam Policy single-Adapter path (policy/failure/platform isolation) NotificationService currently encodes.", "Show where the Interface (Notification / send(_:)) will carry region, channel, eligibility, retry, and audit-receipt data before certifying architecture_quality at 9.5 — or explicitly rescope the claim to 'duplicate push-only call sites collapsed; region-variant policy out of scope this loop.'", "Name the seam that will carry non-push channels for Region A (no push infrastructure) given NotificationService's current hard dependency on a single concrete PushProvider."]}
```
