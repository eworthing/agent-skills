## Review: Loop 8 — `architecture_quality`

**What the diff actually does.** Three call sites (checkout, shipping, account) that each
hand-rolled "format a message, push it" are collapsed into one `NotificationService.send(_:)`,
backed by a `NotificationSender` protocol and a concrete `provider: PushProvider` field. The
duplication removed is real, and `send()` does two fixed things in a fixed order: format the
notification, then deliver it through a single push channel. Test count (1,940 green) is
consistent with the claim that nothing currently broke — but that's the weakest form of evidence
here, because none of the behavior the next quarter of work depends on exists yet for the suite
to exercise.

**Why this doesn't clear 9.5.** The attached `CONTEXT.md` excerpt isn't background color — it's
a committed, this-quarter (Q4) roadmap item, and it describes exactly the axes this refactor just
erased:

- **EU** requires per-recipient opt-in *before* send, plus an audited, retained delivery receipt.
  `send(_:)` has no eligibility/consent check and no receipt-capture hook — it formats and pushes,
  full stop.
- **Region A** has *no push infrastructure at all* — SMS only, carrier-specific retry. But the
  new abstraction's only dependency is `provider: PushProvider`, a concretely-typed push channel.
  Region A cannot be expressed inside this "single owner, single path" shape without either
  breaking the abstraction or smuggling a region branch inside `send`, which defeats the stated
  point of the refactor ("one owner, one path, no duplication").
- **Region B** needs push-first-with-email-fallback and retry. `send()` is a single
  deliver-and-return call — no channel selection, no fallback, no retry policy seam.

So the refactor didn't just DRY up three copies of the same logic — it collapsed three
independently-extensible call sites into one path that is *coupled to the one dimension* (channel,
eligibility, retry, audit) the domain is contractually committed to diversifying along in the very
next quarter. That's the textbook "wrong abstraction ahead of known divergence" trap: duplication
across three call sites was cheap to later specialize per-region; a single `send()` glued to a
concrete `PushProvider` is not. Whoever picks up the EU/Region A/Region B work will most likely
have to tear this abstraction back apart (or degrade it into a growing if/switch inside `send`),
which is churn this loop created rather than saved.

This is not a speculative "you should have built for a hypothetical future" objection — the
roadmap excerpt is explicit that this is committed, this quarter. A 9.5 `architecture_quality`
claim implies the shape chosen won't need to be re-fought the moment already-known requirements
land; here it very clearly will, and the loop report doesn't engage with the conflict at all —
it frames the change as finished and DRY, full stop.

**What would be fine.** Unifying the dispatch call sites is not itself the problem — the report's
"no duplication" framing is legitimate as far as it goes. The defect is in the specific shape: a
concrete `PushProvider` dependency and an undifferentiated `format → deliver` sequence with no
seam for eligibility gating, channel selection, retry policy, or audit capture. A channel-neutral
delivery abstraction (or a policy/region parameter threaded through `send`) would have captured
the same duplication win without foreclosing Region A or the EU/Region B requirements.

**Verdict rationale.** Given a roadmap conflict this concrete and this immediate, I can't certify
`architecture_quality` at 9.5, and I don't think the claim survives even a generous read — the
coupling to a single push channel is a real defect, not a style nit. Sending back for revision
rather than provisionally approving, since the fix (decoupling from `PushProvider`, adding
per-region seams) changes the shape of the abstraction itself, not just its documentation.

```json
{"verdict": "rejected", "blocks_95": true, "blocking_severity": "high — abstraction concretely coupled to a single channel type, conflicting with a contractually committed, this-quarter requirement (Region A has no push infrastructure); no seam for per-region eligibility/consent, channel selection, retry, or audit", "dimension_scores": {"architecture_quality": 6.0}, "flagged_smells": ["wrong abstraction ahead of known divergence (Sandi Metz: prefer duplication over the wrong abstraction)", "concrete coupling to PushProvider forecloses SMS-only region", "missing extension seams for per-region eligibility/consent gating, channel selection, retry policy, and audit/receipt capture", "loop report claims completion/9.5 without engaging documented roadmap conflict"], "evidence_demanded": ["A design sketch or interface change showing how per-region eligibility/consent gating, channel selection (push/SMS/email), retry policy, and audit/receipt capture attach to send(_:) without re-opening this abstraction", "Replacement of the concrete PushProvider field with a channel-agnostic delivery abstraction (or explicit region/policy parameter) before Region A work begins", "Explicit acknowledgment in the loop report of the CONTEXT.md Q4 roadmap conflict rather than presenting the change as architecturally final", "A concrete plan or stub demonstrating EU's audit-receipt retention and opt-in gating are representable in the new path"]}
```
