# Critic Review — Loop 8, `architecture_quality`

## Step 0 — CONTEXT.md awareness

CONTEXT.md §5 is explicit and dated: region-specific notification rules are **committed for this
quarter (Q4)**, not speculative. Three regions diverge on eligibility, channel, retry, and audit:

- **EU** — explicit per-recipient opt-in required; every delivery must produce an audited,
  retained receipt.
- **Region A** — no push infrastructure at all; SMS only, carrier-specific retry.
- **Region B** — push-first with email fallback.

Per the rubric's CONTEXT.md Awareness section, this is read at Step 0 and used as domain
evidence throughout, and a finding that contradicts a committed decision must say so explicitly.
This is not the "context-sufficiency cap" case (that carve-out is for a rule *absent* from
CONTEXT.md) — the rule here is present and detailed. That makes it stronger evidence, not weaker.

## Step 1 — Inspect current code only

Re-deriving from the diff itself, not from the Actor's characterization: `NotificationService`
is a new type with one method, `send(_ notification: Notification) async throws`, whose body is
two calls — `notification.formatted()` then `provider.deliver(formatted, to: notification.recipient)`.
The `provider` field is typed concretely as `PushProvider`:

```
struct NotificationService: NotificationSender {
    private let provider: PushProvider
    func send(_ notification: Notification) async throws { ... }
}
```

Three call sites (checkout, shipping, account) previously each built their own message and called
`pushProvider.deliver` directly; they now call `notifications.send(...)`.

## Step 3 — Architecture review

**Deletion test:** delete `NotificationService` → the format+dispatch pattern reappears at three
call sites verbatim. It earns its keep as a dedup of real, currently-identical duplication. This
part of the consolidation is legitimate and I am not flagging the collapse itself.

**Unified Seam Policy:** a new protocol (`NotificationSender`) was introduced with exactly one
production conformer and no test fake shown in the diff or cited in the report. That leaves path
(b) — single-Adapter policy/failure/platform isolation — as the only justification, specifically
(ii) failure isolation the deletion test confirms would otherwise spread across N callers. That
holds for *today's* uniform behavior. The report never states which of (i)/(ii)/(iii) it's relying
on, which the rubric asks findings to cite explicitly — a minor process gap, not the main issue.

**Depth / Leverage against the stated near-term requirement:** this is the substantive finding.
`Interface ≈ Implementation` here — the interface is two lines deep, and the concrete `PushProvider`
type is baked directly into the sole owner of outbound notification dispatch. Weighed against
CONTEXT.md §5, three concrete problems exist right now in the architecture that was just declared
"done":

1. **Region A cannot be served at all.** `PushProvider` is the only channel `NotificationService`
   knows how to call. Region A has *no push infrastructure* — SMS only. This isn't a missing nice-to-have,
   it's a hard type-level dependency on a channel the region doesn't have.
2. **No seam for eligibility/consent.** EU requires explicit per-recipient opt-in before send.
   `send(_:)` has no eligibility check point — every notification is sent unconditionally.
3. **No seam for audit or retry policy.** EU needs an audited, retained receipt per delivery;
   Region A needs carrier-specific retry. `send(_:)` has exactly one code path with no hook for
   either, and no notion that these vary by recipient/region.

None of this breaks anything *today* — the system currently treats all notifications identically,
so the single path is honest for the current runtime. That keeps this out of "Likely disqualifier"
(nothing is broken at runtime on a primary flow right now). But `architecture_quality` is being
scored to 9.5 on a design that, by the roadmap's own committed timeline, will need its sole
Interface reopened at all three call sites again within the quarter — the exact duplication this
loop just collapsed is at real risk of reappearing, or worse, growing three-way region branches
inside a two-line `send` that was sized for one path. That's a real, contained, evidenced Seam/Depth
problem in a meaningful module — "Serious deduction," not disqualifying, but squarely blocking a
9.5 certification of the architecture as delivered.

## Simplify Pressure Test / Q5

Q1–Q4 pass: the fix removes real ambiguity, is roughly the smallest honest fix for *today's*
uniform case, doesn't duplicate layers, and doesn't hide any current runtime behavior. Q5 is where
it fails as a 9.5 claim: the report frames this as terminal ("One owner, one path... no
duplication") rather than as an interim step, and doesn't name the dimension cost of designing the
Interface without any accommodation for a divergence that isn't hypothetical — it's dated and
contractual. A design that at least kept `provider` behind an abstraction wider than `PushProvider`,
or that threaded a region/channel value through `Notification` even before implementing per-region
logic, would leave room to grow without re-touching the three call sites again. As shipped, the
next quarter's work will almost certainly require re-opening this "one path" at all three sites.

## Step 8 — Tests (secondary observation, not scored — out of this loop's dimension)

The 1,940-green-suite claim is not architecture evidence (rubric: counts are not quality). No new
test targeting `NotificationService.send` directly is cited in the diff or report; the green suite
is consistent with, but doesn't prove, anything about the architecture question above. Not scoring
`test_strategy` here since it isn't the touched dimension this loop, but noting it as something
the Actor's report leans on as if it were architectural proof, which it isn't.

## Verdict

The consolidation itself is real and defensible — I'm not asking for it to be unwound. What blocks
9.5 is that the Actor's report and the diff certify the new `NotificationService` as a finished,
single owner for "all notifications" while CONTEXT.md, provided as part of this same review,
describes contractually-committed per-region divergence in exactly the properties (channel,
eligibility, retry, audit) this Interface has no room for — most concretely, a region with no push
infrastructure at all is bound to a `PushProvider`-typed dependency. That is a source-backed,
CONTEXT.md-grounded Seam/Depth finding in a meaningful module, contained today but not free — it
should cap the dimension below 9.5 pending either a design that leaves room for the committed
divergence, or an explicit acknowledgment that this is an interim step with a named follow-up.

```json
{
  "verdict": "conditional",
  "blocks_95": true,
  "blocking_severity": "Serious deduction",
  "dimension_scores": {"architecture_quality": 7.0},
  "flagged_smells": [],
  "evidence_demanded": [
    "A stated design (even if not yet implemented) for how NotificationService accommodates per-region channel selection, given provider is concretely typed PushProvider and Region A has no push infrastructure (CONTEXT.md §5)",
    "A seam or hook point for per-recipient eligibility/opt-in before send, required for EU",
    "A seam or hook point for per-delivery audited receipt (EU) and carrier-specific retry (Region A), distinct from the current single unconditional dispatch path",
    "Explicit citation of which Unified Seam Policy path ((a) two-adapter or (b)(i)/(ii)/(iii)) justifies the new NotificationSender protocol, since no test fake is shown",
    "If this is intended as an interim step rather than a finished design, explicit documentation of that scope limit and a follow-up backlog item, rather than a 9.5 claim of completion"
  ]
}
```
