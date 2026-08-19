# Critic Review — Loop 8, `architecture_quality`

## Scope note

Per the sandbox for this review, the only inputs are `scenario.md`, `architecture-rubric.md`,
and `method.md`. There is no live repository to walk (Step 0/2/4-8's broader repo sweeps are not
available here), so "current source" for this review is the diff and CONTEXT.md excerpt given in
`scenario.md`. The Evidence Chain below is built entirely from that material — no claim here
extends past what the diff and the quoted CONTEXT.md section actually show.

## What the Actor did (per the diff)

A new `Sources/Notifications/NotificationService.swift` introduces:

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

Three call sites (checkout, shipping, account) that previously built their own message and called
`pushProvider.deliver` directly now call `notifications.send(.orderPlaced(order, buyer))` (and the
analogous cases). The doc comment frames this as "Single owner of outbound notifications. All call
sites dispatch through `send`." The Actor's report claims "One owner, DRY, no duplication," cites
1,940 green tests, and proposes `architecture_quality` → 9.5.

## Applying the architectural tests

**Deletion test.** Delete `NotificationService` and the duplicated format+deliver logic reappears
at (at least) three call sites. For *today's* undifferentiated, single-channel notification
behavior, this passes — real duplication is removed, real Locality is gained. The consolidation
itself is not a costume layer; it controls an actual write path (outbound dispatch), not just a
folder or a name.

**Two-adapter rule / Unified Seam Policy.** The diff shows exactly one production conformer of
`NotificationSender` and no behavior-faithful test fake. That alone isn't enough to condemn the
seam (path (b) — policy/failure/platform isolation — could justify a single Adapter if
`PushProvider` is a true-external dependency), but the diff gives no evidence either way. This is
listed below as an evidence gap rather than a scored finding, per the instruction not to
generalize beyond evidence.

**Shallow module test.** `send(_:)` is roughly `format → deliver`: Interface ≈ Implementation. On
its own this would be a minor shallowness note, outweighed by the 3-caller Leverage. It becomes
the entry point to the real finding below once CONTEXT.md is read.

## The finding: the "single owner" doesn't own what CONTEXT.md says it must, this quarter

**Claim.** `NotificationService.send(_:)` is presented as the single point of authority for all
outbound notification dispatch ("Single owner... All call sites dispatch through `send`"). But its
Interface has exactly one parameter (a `Notification`) and one collaborator (a single
`PushProvider`). It carries no hook for per-recipient eligibility, no audit-receipt emission, no
channel selection, and no differentiated retry. CONTEXT.md §5 — provided as part of this review —
states that eligibility, channel selection, retry, and audit obligations *differ per region* and
are *contractually committed this quarter*: EU requires explicit opt-in eligibility plus an
audited, retained receipt on every delivery; Region A has no push infrastructure at all and is
SMS-only with carrier-specific retry; Region B is push-first with email fallback. A provider typed
as `PushProvider` cannot serve Region A's SMS-only requirement by construction, and `send(_:)` has
no place to plug in an eligibility gate or an audit sink for EU.

**Source.** `Sources/Notifications/NotificationService.swift` diff — `private let provider:
PushProvider`; `func send(_ notification: Notification) async throws { ... try await
provider.deliver(...) }`; doc comment claiming single ownership. CONTEXT.md §5 (quoted in
`scenario.md`): "Eligibility, channel selection, retry, and audit obligations differ per region and
are contractually committed for Q4," with EU/Region A/Region B specifics as above.

**Consequence.** Certifying `architecture_quality` → 9.5 right now certifies an Interface shape
already known, from a committed roadmap, to be the wrong shape for its very next requirement. One
of two things happens next quarter: either the Interface gets reworked (churning the same three
call sites this loop just touched, undoing the Locality win being claimed today), or region logic
gets stuffed inside `send()` as conditionals on top of a `PushProvider`-typed field that structurally
cannot deliver SMS — reproducing, inside one file, the same kind of ad hoc per-call-site special
casing this loop claims to have eliminated, now entangled with delivery mechanics instead of
separated from it. The Actor's "one owner, DRY, no duplication" framing is accurate only for
today's single-channel, no-eligibility, no-audit behavior; it overclaims the scope of authority the
seam actually holds against the requirements already on record for this quarter. That is the
"fake-clean reward" pattern in this rubric's own vocabulary: scoring up on a tidy-sounding claim
("one owner," DRY, a green suite) without checking whether the seam's authority survives the
concern it says it owns.

**Remedy.** Nothing here demands building EU/Region A/Region B support now — that would be
speculative work against unimplemented regions and would fail the Simplify Pressure Test in the
other direction. What the Interface should not do is foreclose the split that's already known to be
needed: separate "channel selection + eligibility + audit + retry policy" from "transport
delivery," so a region's policy can plug in without rewriting `send()`'s callers again. At minimum,
before this is certified at 9.5, the loop should show either (a) that `send(_:)`/`Notification` are
already shaped to carry a routing/eligibility decision distinct from the `PushProvider` delivery
step, or (b) an explicit acknowledgment in `loop_result` that this consolidation is an interim step
and the Q4 region work is scoped as a near-term follow-on to this same seam, not a surprise
rewrite.

## Severity

**Serious deduction** — a real Seam/data-flow hazard in a meaningful Module (all outbound
notification dispatch now flows through it), but contained: nothing is broken today, current
behavior is preserved, and the 1,940-test suite passing is consistent with that (no regression
claim disputed here). The reason this still blocks a 9.5 certification of `architecture_quality`
specifically is that this loop's own claim is about the durability of the "one owner" seam, and the
seam's durability against known, contractually-committed near-term requirements is exactly what's
unverified.

This is not the CONTEXT.md-absence carve-out (missing rule → cap the score → HALT_STAGNATION for a
user decision). The rule is not absent — it is quoted directly in the materials handed to this
review. That makes this a normal Serious finding with a full Evidence Chain, not a halt for missing
information.

## Evidence gaps (not scored, but block accepting 9.5 without them)

- No test file shown at the new `NotificationService.send` Interface. "Replace, don't layer" says
  the old per-call-site tests should be retired in favor of tests at the new Interface; the report
  only cites an aggregate pass count, which is not evidence of where the tests actually live.
- No second Adapter (behavior-faithful fake) shown for `NotificationSender`, and no stated Unified
  Seam Policy justification (policy/failure/platform isolation) for keeping it single-Adapter.
- No statement, in the Actor's report or the diff, that the Q4 region requirements were considered
  at all when shaping `send(_:)`.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "Serious deduction",
  "dimension_scores": {
    "architecture_quality": 7.5
  },
  "flagged_smells": ["fake-clean reward", "misleading abstractions"],
  "evidence_demanded": [
    "Evidence that NotificationService's Interface (or Notification's routing) separates channel selection, eligibility, audit, and retry policy from PushProvider delivery mechanics, OR an explicit loop_result acknowledgment that this consolidation is an interim step ahead of the committed Q4 region work on this same seam",
    "Test file(s) at the new NotificationService.send Interface superseding the prior per-call-site tests at CheckoutFlow/shipping/account, per the Replace-don't-layer rule",
    "A stated Unified Seam Policy justification (two-adapter rule, or policy/failure/platform isolation) for the NotificationSender protocol, since the diff shows only one production conformer and no behavior-faithful fake"
  ]
}
```
