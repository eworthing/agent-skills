# Review — Loop 8, `architecture_quality`

## What the Actor did

The diff replaces three open-coded dispatch sites (checkout, shipping, account) with a single
`NotificationService` that conforms to `NotificationSender` and exposes one `send(_:)` method.
Call sites now read `try await notifications.send(.orderPlaced(order, buyer))` instead of
manually building a message and calling `pushProvider.deliver(...)`. Tests are reported green
(1,940/1,940). Taken purely as "did this remove literal call-site duplication," the answer is
yes — the three call sites no longer each hand-roll formatting and delivery, and they now share
one interface. That part of the claim is real and worth keeping.

## Why this does not clear 9.5

The CONTEXT.md excerpt attached to this review is not background color — it is committed,
in-quarter (Q4) scope, and it describes exactly the axis this refactor just erased:

- **EU** requires per-recipient opt-in eligibility *and* an audited, retained delivery receipt.
- **Region A** has no push infrastructure at all — delivery must go over SMS, with a
  carrier-specific retry policy.
- **Region B** is push-first with an email fallback.

`NotificationService` as written has none of the seams this requires:

1. **Single hardcoded channel.** The struct holds one `private let provider: PushProvider` and
   calls `provider.deliver`. Region A cannot be served by this type at all without changing its
   shape — "no push infrastructure" directly contradicts a push-only delivery path. This isn't a
   hypothetical future need; it's a channel the code cannot currently reach.
2. **No eligibility gate.** `send` unconditionally formats and delivers. There is no point where
   a per-recipient opt-in check could deny or defer delivery, which EU legally requires.
3. **No audit/receipt concept.** `send` returns `Void` (via `throws`, no return value). There is
   nowhere to attach a retained, audited receipt of what was sent, to whom, and when.
4. **No differentiated retry.** Retry policy is not modeled anywhere in `NotificationSender` or
   `NotificationService` — it would have to be invented from scratch, and per the roadmap it
   needs to vary by region (carrier-specific for Region A) rather than be uniform.

This is the classic "wrong abstraction" trap: three call sites that look identical *today* got
collapsed into one concrete path, on the one axis (call-site plumbing) that was genuinely
redundant, while erasing the axis (region: eligibility / channel / retry / audit) that is already
known, documented, and contractually committed to diverge next quarter. The Actor's own report
never mentions the roadmap or any region seam — "one owner, DRY, no duplication" describes the
call sites, not the design's fitness for the work that is already scheduled to land on top of it.

Green tests don't rescue this. 1,940 passing tests demonstrate the refactor preserved *today's*
single-channel, single-region behavior; they say nothing about whether the new shape can absorb
next quarter's committed requirements without another structural rewrite. Given the CONTEXT.md
excerpt was provided specifically for this review, that gap is not speculative YAGNI-territory —
it's a known, near-term, contractually committed collision with the exact shape just built.

The call-site decoupling itself is worth preserving (checkout/shipping/account now depend only on
`NotificationSender.send`, not on formatting/delivery details), so this isn't a case for reverting
the loop wholesale. But certifying `architecture_quality` at 9.5 here would mean signing off on a
design that cannot serve a channel already on the roadmap (Region A/SMS) and has no place to hang
eligibility or audit logic that's legally required (EU) — that's a blocking gap, not a nitpick.

## What I'd need before accepting

- A channel abstraction (protocol, not a concrete `PushProvider` field) so Region A/SMS and
  Region B/push+email-fallback can be added without re-opening `NotificationService`'s shape.
- An explicit seam for eligibility/opt-in checks that can gate or short-circuit `send`, with a
  result type that can represent "not eligible" as distinct from a delivery failure.
- An explicit seam for audit receipt generation + retention, even if just returning a receipt
  value from `send` for now.
- Confirmation (design note or ADR) that this shape was checked against the Q4 roadmap before
  being proposed at 9.5 — right now the report shows no evidence the roadmap was consulted.
- Evidence, beyond "tests green," that scopes what changes when region-specific work lands —
  ideally a short design sketch showing the three regions' flows fit through the new interface
  without further rewrites to the call sites already migrated.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "architecture-invalidating: design cannot serve a contractually committed, in-quarter requirement (Region A has no push channel; EU eligibility/audit obligations have no seam) without further rework", "dimension_scores": {"architecture_quality": 4}, "flagged_smells": ["wrong abstraction axis (unified call-site plumbing while erasing the region axis that is about to diverge)", "single hardcoded implementation behind a protocol built for exactly one need (PushProvider only, no channel abstraction)", "missing extension point for known near-term requirements", "compliance gap: no eligibility/opt-in seam, no audit/receipt seam", "overclaimed completeness: report and proposed score do not address the roadmap context given for review", "tests-green used as proxy for architectural fitness it does not measure"], "evidence_demanded": ["channel abstraction supporting SMS-only and push+email-fallback regions without re-opening NotificationService's shape", "eligibility/opt-in seam with a result distinguishable from delivery failure", "audit receipt + retention seam", "design note/ADR showing this shape was checked against the Q4 roadmap", "a sketch of how EU/Region A/Region B flows fit the new interface without re-touching the already-migrated call sites"]}
```
