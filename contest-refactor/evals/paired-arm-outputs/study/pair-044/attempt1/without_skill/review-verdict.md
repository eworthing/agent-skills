# Critic Review — Loop 8, `architecture_quality`

## What the Actor claims

Three open-coded notification call sites (checkout, shipping, account) collapsed behind a single
`NotificationService.send(_:)`. The Actor frames this as pure DRY: "one owner, no duplication,"
suite green at 1,940 tests, and proposes `architecture_quality` → 9.5.

## What I checked instead of taking that at face value

The literal duplication claim is true as far as it goes — three call sites that each built and
dispatched their own message now route through one method. Tests staying green confirms the
*current* behavior didn't regress. Neither of those facts is in dispute.

But `architecture_quality` at a 9.5 bar isn't just "did the duplicate code merge" — it's whether
the resulting shape is the *right* one, and this review was handed the exact piece of evidence
needed to check that: the CONTEXT.md excerpt. It states, as **committed, this-quarter** work, that
notification eligibility, channel selection, retry policy, and audit obligations diverge sharply
by region:

- **EU** — mandatory per-recipient opt-in, plus an audited, retained receipt for every delivery.
- **Region A** — no push infrastructure at all; SMS-only, carrier-specific retry.
- **Region B** — push-first with email fallback (i.e., already multi-channel).

Now look at what the diff actually built:

```swift
protocol NotificationSender {
    func send(_ notification: Notification) async throws
}

struct NotificationService: NotificationSender {
    private let provider: PushProvider
    func send(_ notification: Notification) async throws {
        let formatted = notification.formatted()
        try await provider.deliver(formatted, to: notification.recipient)
    }
}
```

This is a single method, on a single hardcoded `PushProvider` dependency, that throws-or-succeeds
with no return value. Concretely:

- **Region A is impossible to satisfy without a breaking change.** There is no push
  infrastructure in Region A per CONTEXT.md, yet `NotificationService` has exactly one delivery
  path and it's push. There's no channel parameter, no provider-per-channel seam, nothing to
  substitute SMS into.
- **Region B (push + email fallback) has nowhere to hang the fallback.** `send` either delivers
  via the one `PushProvider` or throws. A fallback channel needs to be modeled at this layer, and
  it isn't.
- **EU's audit/receipt requirement has no seam.** `send` returns `Void`. There's no receipt,
  correlation ID, or delivery-result object for an audit trail to attach to — and no eligibility
  check before the send happens (opt-in is a precondition, not a post-hoc log entry).
- **Retry is invisible.** Region A needs a carrier-specific retry policy; nothing in this shape
  suggests where retry would be injected or varied per region.

None of this means the Actor was obligated to *implement* region logic this loop — that's
explicitly Q4 scope, and building it out now would be its own overreach. The problem is narrower
and more serious than "incomplete": the *interface chosen* actively forecloses the very
requirements it was reviewed against. `send(_ notification: Notification) async throws` on a
single concrete `PushProvider` is not a superset that region logic can be layered onto later —
satisfying EU/Region A/Region B will require changing this method's signature and its dependency
shape, i.e., touching every one of the three call sites the Actor just "unified" a second time.
That's the classic false-convergence pattern: today's diff *looks* like consolidation, but it
picks the wrong axis to unify on (formatting/dispatch mechanics) while ignoring the axis that's
actually going to move (region-specific eligibility/channel/retry/audit), so the real duplication
comes right back — this time behind a shared choke point that has to be torn open.

The Actor's report doesn't mention region requirements at all, despite CONTEXT.md being available
context for this review. That's the tell: the "one owner, DRY, 9.5" framing was validated against
current call sites and a green test suite, not against the roadmap the codebase is already
committed to. A green suite here is weak evidence — there are no tests yet for region-specific
behavior because none exists, so "1,940 passed" says nothing about whether this shape survives
contact with Q4.

A secondary, minor point: `NotificationSender` is a protocol with exactly one conformer and no
visible test-double usage in this diff. That's a much smaller concern than the channel/region
issue and wouldn't block on its own — flagging it for completeness, not weighting it heavily.

## Verdict reasoning

Removing the three duplicated call sites is a real, legitimate improvement over open-coded
dispatch and shouldn't be reverted. But the specific claim under review — that this is a 9.5
`architecture_quality` outcome — is not supportable. The abstraction is shaped for a world where
every notification is identical, and CONTEXT.md establishes, as committed near-term work, that
they won't be. Approving this at 9.5 would certify a design that has to be broken open again in
the same quarter, for the same three call sites, to satisfy legally-driven requirements (EU
opt-in/audit) that were knowable at review time. That's not a speculative "might need it someday"
concern subject to YAGNI — it's a dated, contractually committed requirement handed to this review
as evidence, which the Actor's own report never engages with.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "high — chosen abstraction is incompatible with contractually committed, dated requirements (Q4 region-specific eligibility/channel/retry/audit) that were available as review context but unaddressed in the Actor's report", "dimension_scores": {"architecture_quality": 5}, "flagged_smells": ["wrong-axis unification (consolidated dispatch mechanics, ignored the region axis that's actually scheduled to vary)", "hardcoded single-channel dependency (PushProvider) with no channel/provider seam", "no extension point for eligibility/opt-in precondition", "no return value or correlation mechanism to support the EU audited-receipt requirement", "no retry-policy injection point", "self-reported convergence score not checked against available roadmap context", "speculative single-conformer protocol (minor, not blocking)"], "evidence_demanded": ["A design (even unimplemented) showing how send would extend to multi-channel delivery (SMS-only Region A, push+email Region B) without re-touching all three call sites again", "An explicit eligibility/opt-in precondition point in the notification path, given EU opt-in is a legal requirement, not optional", "A delivery-result/receipt type or correlation ID returned from send, or an explicit statement of where the EU audit trail will attach", "Confirmation the Actor consulted CONTEXT.md's Q4 roadmap before proposing this shape, or an explicit rationale for why region logic is deliberately deferred to a follow-up loop with the current interface treated as provisional rather than final"]}
```
