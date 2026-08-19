# Review — Loop 8, `architecture_quality`

## What the diff actually does

The Actor introduces `NotificationService` (conforming to a new `NotificationSender` protocol) as
a single choke point for outbound notifications, and rewires the three call sites (checkout,
shipping, account) to call `notifications.send(_:)` instead of hand-rolling their own
format-and-deliver sequence. Mechanically this is correct: three copies of the same two-line
pattern collapse into one. The test suite (1,940 tests) is reported green, and nothing in the diff
itself looks buggy — `send` formats a `Notification` and hands it to `provider.deliver`.

Taken in isolation, "three identical call sites become one" reads like textbook DRY. The problem is
that it isn't taken in isolation — the CONTEXT.md excerpt attached to this review makes clear that
the sameness this loop is capitalizing on is about to end, on a committed timeline, and the new
abstraction is built as if that were not true.

## Why this doesn't clear `architecture_quality` at 9.5

CONTEXT.md §5 states, as **committed, this-quarter** work: EU notifications need per-recipient
opt-in plus an audited, retained receipt on every delivery; Region A has no push infrastructure at
all and must go out over SMS with a carrier-specific retry policy; Region B is push-first with an
email fallback. Eligibility, channel selection, retry, and audit obligations all vary **per
region**, and that's not speculative — it's the next quarter's committed roadmap, known today.

Against that, look at what `NotificationService.send` actually is:

```swift
struct NotificationService: NotificationSender {
    private let provider: PushProvider
    func send(_ notification: Notification) async throws {
        let formatted = notification.formatted()
        try await provider.deliver(formatted, to: notification.recipient)
    }
}
```

- **It is hard-typed to `PushProvider`.** Region A has "no push infrastructure — SMS only." That
  is not a future edge case the design merely hasn't gotten to yet; it is a documented requirement
  that this exact type signature cannot satisfy. The "one owner" is, today, incapable of serving
  one of the three named regions.
- **There is no channel-selection, eligibility, retry, or audit seam anywhere in the interface.**
  `send` takes a `Notification` and unconditionally delivers it. EU's opt-in check and audited
  receipt, Region A's carrier-specific retry, and Region B's push-then-email fallback would all
  have to be bolted on — almost certainly as branching inside (or wrapping) `send`, which is exactly
  the kind of per-call-site special-casing this loop claims to have eliminated. The duplication
  didn't get designed away; it got deferred to next quarter, at a point where it's harder to
  introduce cleanly because callers already assume a single undifferentiated path.
- **The "sameness" driving this unification is incidental, not essential.** Checkout, shipping, and
  account collapse into one line today only because *all notifications currently behave
  identically* (push, no region logic). That's an accident of the current lack of regionalization,
  not evidence that these call sites are the same kind of thing going forward. Validating a shared
  abstraction against three call sites that all do the identical thing tells you nothing about
  whether the abstraction survives contact with genuinely divergent behavior — and here we already
  know, in writing, that it won't as designed.
- **The green suite is not evidence for the disputed claim.** 1,940 passing tests confirm the
  refactor didn't change behavior for the paths that exist today. None of those tests exercise
  region-specific eligibility, SMS delivery, retry, or audit-receipt behavior, because that code
  doesn't exist yet. "Tests green" is being used in the Actor's report to imply architectural
  soundness, but it only certifies "did not break the status quo" — it says nothing about whether
  the new shape accommodates the committed next step, which is the actual question for
  `architecture_quality`.

None of this makes the diff bad as a narrow, scoped cleanup. Reducing three copies of
format-and-deliver to one is a legitimate, low-risk improvement over open-coded duplication. But
that is a modest, mechanical win — not a 9.5-grade architecture decision. A design graded that high
on `architecture_quality` should demonstrate that its abstraction boundary was chosen with an eye to
the axis along which the domain is known to vary (region/channel here), or at minimum that the
report is honest about the fact that this consolidation is a first step that the known Q4 work will
have to revisit. Instead the report claims "one owner, DRY, no duplication" as a finished, high-grade
result while ignoring a committed requirement that directly contradicts the chosen dependency
(`PushProvider`) and offers no seam for eligibility/retry/audit. That gap between what's claimed and
what the design can actually support is itself the finding: it blocks the 9.5 claim.

## Verdict

Conditional: the mechanical deduplication is fine to keep as a foundation, but it must not be
scored or treated as a finished `architecture_quality` win. Before this can be accepted anywhere
near 9.5, the design needs a channel/region seam (e.g., `Notification` or the send path carrying
enough to select SMS vs. push vs. push+fallback, without `PushProvider` being a hard dependency of
the "single owner"), plus explicit hooks for eligibility and audited-receipt recording. Absent that,
this loop should be treated as "reduced duplication, architecture question still open," not closed
out at 9.5.

```json
{"verdict": "conditional", "blocks_95": true, "blocking_severity": "high — design contradicts a contractually committed, already-documented near-term requirement (Region A cannot use PushProvider at all; EU opt-in/audit and Region B fallback have no seam)", "dimension_scores": {"architecture_quality": 5}, "flagged_smells": ["premature unification of call sites that are only accidentally identical today", "concrete dependency lock-in (PushProvider hard-typed into the 'single owner')", "missing extension seam for a known, committed differentiation axis (region/channel/eligibility/retry/audit)", "green-suite-as-proof (tests certify no regression, not architectural soundness for the disputed claim)", "self-report overclaim relative to attached context"], "evidence_demanded": ["a design for how Region A (SMS-only, no push infra) routes through NotificationService without depending on PushProvider", "an explicit seam for per-region eligibility/opt-in checks prior to delivery (EU requirement)", "an audited, retained receipt mechanism hook for EU deliveries", "a carrier-specific retry policy hook compatible with Region A", "a fallback-channel mechanism for Region B (push-first, email fallback)", "either evidence the abstraction was validated against two divergently-behaving call sites, or an explicit acknowledgment that this is a staged/interim step pending the Q4 region work, not a finished 9.5-grade result"]}
```
