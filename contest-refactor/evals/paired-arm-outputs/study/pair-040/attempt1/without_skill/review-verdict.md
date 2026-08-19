# Review — Loop 8 (`architecture_quality`)

## What the diff actually does

The Actor collapses three open-coded dispatch sites (checkout, shipping, account) behind a new
`NotificationService`, reached through a `NotificationSender` protocol with a single method:

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

Call sites shrink from "build a message, call a provider directly" to `notifications.send(.orderPlaced(...))`.
That's a legitimate reduction of duplicated formatting/dispatch boilerplate, and the 1,940-test
green run is real evidence the behavior-preserving part of the refactor didn't break anything that
already has coverage. Taken purely as "did three near-identical blocks become one," this is sound
work.

## What the diff ignores

The CONTEXT.md excerpt attached to this review states, as **committed, this-quarter (Q4)** scope,
that notification behavior is about to become region-dependent along four axes simultaneously:

- **EU**: requires a per-recipient eligibility/opt-in check *before* delivery, plus an audited,
  retained receipt *for every delivery*.
- **Region A**: has no push infrastructure at all — delivery must go over SMS, with a
  carrier-specific retry policy.
- **Region B**: push-first with an email fallback (i.e., more than one channel per notification).

None of these are speculative — they're described as contractually committed for this quarter.
Now look at what the new architecture actually gives a future implementer to hang that logic on:

1. **Channel is hardcoded, not selected.** `NotificationService` holds a single concrete
   `PushProvider` and calls `provider.deliver(...)` unconditionally. There's no notion of "which
   channel for this recipient" anywhere in the type. Region A (no push infra) and Region B
   (push + email fallback) both require channel selection that this shape has no seam for — every
   call site would need to route around `NotificationService`, or `NotificationService` would need
   to be substantially rewritten, not extended.
2. **No eligibility gate.** `send` unconditionally formats and delivers. EU's opt-in requirement
   needs an eligibility check *before* dispatch, ideally one that can also reject/short-circuit. The
   signature (`func send(_ notification: Notification) async throws`) has nowhere to plug that in
   except by mutating the one shared method for everyone — which then has to special-case a region
   that doesn't apply to every caller.
3. **No audit/receipt path.** EU requires an audited receipt with retention per delivery. `send`
   returns nothing and there's no hook for persisting a receipt; that's a second cross-cutting
   concern with no seam.
4. **No retry policy variation.** Region A needs carrier-specific retry. `provider.deliver` is a
   single call with whatever retry behavior `PushProvider` has baked in (and Region A can't even use
   `PushProvider`, since there's no push infra there).

Put together, "one owner, one path" is being sold as the finished shape, but the one path it
converges on is exactly the path the business has already committed to diverging on next quarter,
along four separate dimensions. This isn't a case of premature abstraction in the "extra interface
nobody asked for" sense — the `NotificationSender` protocol currently has exactly one conformer, and
its single-method signature isn't shaped to carry region, channel, eligibility, or audit
information, so it can't be the seam that absorbs the coming work without a rewrite of the
interface itself, not just its implementation. Merging three sites that formatted and sent similarly
was fine when "similarly" meant "identically forever." CONTEXT.md establishes that it doesn't.

It's also notable that the Actor's report doesn't mention the roadmap at all — the self-assessment
of "DRY, no duplication, → 9.5" appears to have been made without weighing whether the resulting
shape survives contact with already-known, already-committed near-term requirements. That's a gap
in the evaluation itself, not just in the code.

## Is this actually a problem, or is it fine to defer?

Deferring region logic until the region work lands would be reasonable if the current refactor were
neutral with respect to it — i.e., if it left the three call sites easy to re-diverge later. It
doesn't: it has now funneled all three flows through one non-parameterized method backed by one
concrete provider type, which is a *harder* starting point for injecting per-region channel
selection than three independent call sites would have been (each of which could have taken a
region-aware path independently without touching a shared abstraction). Centralization is the
right instinct only if the seam is placed where the actual variance will occur; here it's placed
one layer too high, over a delivery mechanism that's about to stop being singular.

## Verdict

The deduplication itself doesn't need to be reverted — it's a reasonable intermediate step. But
"architecture_quality → 9.5" is not supportable on this evidence: a 9.5 claim on this dimension
should mean the shape holds up against known near-term requirements, and here it demonstrably
doesn't, on all four committed axes. Green tests don't help — nothing in the current suite exercises
region routing, eligibility, retry, or audit, because none of that exists yet, so "1,940 passed"
certifies behavior preservation, not fitness for what's coming.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "Blocking",
  "dimension_scores": {"architecture_quality": 6},
  "flagged_smells": [
    "premature convergence: three call sites merged onto a single non-extensible path right before contractually-committed per-region divergence",
    "hardcoded concrete dependency on PushProvider with no channel-selection seam (breaks SMS-only and push+email-fallback regions)",
    "missing cross-cutting seams for eligibility/opt-in gate and audited/retained receipts (EU requirement)",
    "no retry-policy injection point (Region A carrier-specific retry)",
    "single-conformer protocol whose method signature is too thin to serve as the region-policy seam it would need to be",
    "actor's self-assessment doesn't address the attached roadmap context at all"
  ],
  "evidence_demanded": [
    "a channel-selection mechanism replacing the hardcoded PushProvider field, covering SMS-only and push+email-fallback delivery",
    "an eligibility/opt-in gate that can run before dispatch without special-casing every caller",
    "an audit/receipt persistence path with retention, invoked per delivery",
    "an injectable or region-aware retry policy point",
    "either proof the current shape already accommodates the above, or an explicit downgrade of the proposed score with a follow-up loop scoped to the region-policy seam before re-claiming 9.5"
  ]
}
```
