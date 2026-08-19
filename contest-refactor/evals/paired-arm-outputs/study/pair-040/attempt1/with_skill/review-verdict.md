# Critic Review — Loop 8, `architecture_quality`

## Step 1 — Source inspected

The diff in `scenario.md` is the only current-source evidence available for this loop. It adds:

- `protocol NotificationSender { func send(_ notification: Notification) async throws }`
- `struct NotificationService: NotificationSender` holding `private let provider: PushProvider`, whose `send` does exactly two things: `notification.formatted()` then `try await provider.deliver(formatted, to: notification.recipient)`.
- Three call sites (Checkout shown in full; Shipping/Account described as collapsing the same way) rewritten from open-coded `OrderMessage(...).render()` + direct `pushProvider.deliver(...)` to `try await notifications.send(.orderPlaced(order, buyer))`.

Test evidence: `swift test`, 1,940/1,940 green. Per Meta-Rule 4, a green single-config suite proves the happy path compiles and the existing (uniform) call sites still route through — it says nothing about behavior this module has not yet been asked to perform (region eligibility, channel selection, retry, audit), because no test in the 1,940 exercises that behavior; it doesn't exist yet.

## Authority Map (Method Step 2)

| Concern | Owner | Notes |
|---|---|---|
| Notification dispatch (all flows) | `NotificationService.send(_:)` | Single writer, single call path — genuine consolidation of 3 previously duplicated sites. |
| Delivery channel | `PushProvider` (hardcoded field) | No channel abstraction. Push is the only wire this module can drive. |
| Recipient eligibility / consent | *(no owner)* | Not represented anywhere in the new Interface or Implementation. |
| Delivery audit / receipt | *(no owner)* | Not represented. |
| Retry policy | *(no owner)* | `try await` propagates whatever `PushProvider.deliver` does; no policy layer. |

## Findings (Evidence Chain: Claim → Source → Consequence → Remedy)

### Finding 1 — Primary. The "one owner, one path" claim is already false against committed, current-quarter requirements, and the concrete shape structurally cannot serve one of the three regions.

**Claim:** The Actor's report frames this as a completed unification — "all notifications treated identically" is presented as the resolved end state, not a temporary property of today's feature set. CONTEXT.md §5 states the opposite is committed for this quarter: eligibility, channel selection, retry, and audit obligations **differ per region**, and names three concrete, incompatible shapes (EU: opt-in gate + audited receipt with retention; Region A: SMS-only, no push infrastructure, carrier-specific retry; Region B: push-first with email fallback).

**Source:** `NotificationService.send` (scenario.md diff, new file) has exactly one delivery path: `provider.deliver(formatted, to: notification.recipient)` against a single stored `PushProvider`. There is no channel parameter, no eligibility check, no audit emission, no retry policy hook anywhere in the Interface or Implementation. Cross-referenced against CONTEXT.md §5's Region A line: "no push infrastructure — SMS only."

**Consequence:** This is not a hypothetical future concern to be waved off as speculation — CONTEXT.md marks it "committed, this quarter." Against that fact, three things are true right now about the shape just shipped: (1) Region A traffic is structurally undeliverable through this module as built — there is no non-push channel to route to, so the single-provider design isn't merely "not yet extended," it actively forecloses the only channel Region A can use; (2) EU's legally-required opt-in + audited receipt has zero representation in the Interface, so satisfying it means either editing `NotificationService` in place per-region (reopening exactly the kind of scattered special-casing this loop claims to have eliminated) or re-forking the three call sites apart again; (3) the "one owner, one path" Leverage claim the Actor is scoring 9.5 on is therefore only true for a use case (uniform notifications) that CONTEXT.md says will not exist past this quarter. Depth (small Interface, large Implementation behind it) is being credited for an Interface that is actually *too small* for known, dated, committed requirements — this is `Fake simplification`: shorter code that hides failure behavior (retry), state/consent obligations (EU opt-in), and channel routing that the domain already requires.

**Remedy:** Smallest honest fix is not to build out full regional logic now (no friction has been proven for that beyond the roadmap commitment) but to shape the seam so it does not foreclose it: replace the hardcoded `PushProvider` field with a channel/region-resolvable delivery seam (e.g., resolve a `DeliveryChannel` per recipient/region before calling a provider, and give `send` a place to consult eligibility before formatting) — without re-duplicating the three call sites. This keeps the single owner, single path claim honest instead of leaving it accurate only for today's feature set.

### Finding 2 — Secondary. `NotificationSender` is a bare protocol with one production conformer and no behavior-faithful test fake in evidence.

**Claim:** The new seam does not satisfy the Two-Adapter rule and is not justified under the Unified Seam Policy's single-Adapter alternative.

**Source:** `protocol NotificationSender` / `struct NotificationService: NotificationSender` — no second conformer, no fake, appears nowhere in the diff or the Actor's report.

**Consequence:** Per Unified Seam Policy, a single Adapter is only justified if it encodes (i) a policy decision, (ii) failure isolation the deletion test confirms would otherwise spread, or (iii) platform isolation — and the loop_result must cite which. None is cited, and `send` currently encodes no policy: it formats and forwards, nothing more. Under the rubric this is "bare protocol conformance for testability without a behavior-faithful fake" → protocol soup, on its own. This is a smaller finding than Finding 1 and would not by itself block a high score, but it compounds it: the protocol layer is currently pure ceremony around a single concrete struct, while the place that actually needs a seam — channel/region variation — has none.

**Remedy:** Either add a behavior-faithful fake and use it in tests exercising `send`, or drop the protocol and let call sites depend on the concrete `NotificationService` directly until a second real Adapter exists.

## Architectural Tests applied

- **Deletion test:** for today's uniform behavior, deleting `NotificationService` reintroduces duplicated formatting/dispatch at 3 call sites — passes, on the narrow claim that current behavior stays uniform. That claim is what Finding 1 disputes.
- **Two-adapter rule:** fails (Finding 2).
- **Shallow module test:** Interface (`send(_:)`) ≈ Implementation (format + one `deliver` call) — shallow. Acceptable only if the domain is in fact uniform; CONTEXT.md says it will not be, this quarter.
- **Unified Seam Policy:** neither path (a) nor (b) is satisfied or cited.

## Verdict reasoning

The consolidation itself is a real, source-backed improvement over three duplicated call sites — that much of the Actor's report is accurate and shouldn't be discounted. But the 9.5 claim rests on "one owner, one path" as a durable architectural property, and CONTEXT.md — provided as part of this review, not speculative — shows that claim is false against a committed, dated (this-quarter) requirement, with a concrete, nameable failure (Region A has no push infrastructure and this module has no other channel). That is a real ownership/Interface-shape hazard in the module that owns *all* outbound notifications for Checkout, Shipping, and Account — not a local or cosmetic one — but it is not yet an active runtime break (no region-differentiated traffic exists yet), so I anchor it at **Serious deduction** rather than Likely disqualifier, while flagging that it borders the higher anchor if Region A traffic is already flowing through this path. That is enough to block certifying `architecture_quality` at 9.5 this loop.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "Serious deduction", "dimension_scores": {"architecture_quality": 7.0}, "flagged_smells": ["fake simplification", "protocol soup"], "evidence_demanded": ["A concrete extension point (channel/region resolution before delivery, e.g. a DeliveryChannel or per-region policy seam) showing NotificationService will not foreclose Region A's SMS-only requirement or EU's opt-in+audit requirement, both committed this quarter per CONTEXT.md §5", "Citation of which Unified Seam Policy path (a) two-adapter or (b)(i)/(ii)/(iii) justifies NotificationSender as a protocol, or removal of the protocol in favor of the concrete NotificationService", "A behavior-faithful test fake for NotificationSender if the protocol is kept", "Confirmation of whether any Region A recipients currently route through this path today, which would escalate this from a committed near-term gap to a live delivery failure"]}
```
