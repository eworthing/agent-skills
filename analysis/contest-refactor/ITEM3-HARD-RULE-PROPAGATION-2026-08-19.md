# Item 3 — Hard-Rule Propagation at Dispatch Boundaries: Check Result (2026-08-19)

## Verdict: shipped. Item 25 is unblocked.

Backlog item 3 reads *"Verify hard-rule propagation at every dispatch boundary (challenger first),
generated from one canonical source"* — `Medium-High` value, `Low` cost, status "Check first". It
is listed as the open prerequisite on **item 25** (tool-grounded substrate), alongside items 1 and
18.

The check is done. **Both hard rules already propagate verbatim to every production dispatch
boundary, and both are pinned by a selftest.** No code was needed.

## The boundaries

Four production dispatch sites exist. There is no separate Step-3 executor dispatch — Step 3 runs
inside the loop subagent — and the challenger's prompt source is the whole of `halt-verifier.md`
(`references/provider-adapters.md:147`), which the dormant v5 panel members reuse.

| # | Boundary | Prompt source | G14 | Redaction |
|---|---|---|---|---|
| 1 | Loop subagent (Critic/Actor) | `trust-model.md` § Subagent prompt template | ✅ | via mandatory `method.md` load |
| 2 | Helpers spawned by the loop subagent | `trust-model.md` helper-forwarding clause | ✅ | via parent |
| 3 | Implementation reviewer | `implementation-reviewer.md` | ✅ | ✅ |
| 4 | HALT_SUCCESS challenger (+ v5 panel) | `halt-verifier.md` | ✅ | ✅ |

Both selftests pass:

```
$ python3 scripts/_g14_dispatch_selftest.py
OK: G14 payload-as-evidence rule present verbatim at all 4 dispatch sites
$ python3 scripts/_redaction_dispatch_selftest.py
OK: credential-redaction rule present verbatim at all 3 dispatch sites
```

The two audits that produced this state are already documented in the selftests' own docstrings:
G14 was absent from **3 of 4** boundaries (reachable only through a fragile
prompt → SKILL.md → `validation.md:64` chain), and the redaction rule was absent from the two
boundaries that read raw payload without reliably loading `method.md`. The loop subagent needs no
forwarded redaction copy because it reads `method.md` whole and mandatory at Step 1.

## What the backlog row asked for that is *not* done

**"Generated from one canonical source."** The rules are **copied** verbatim and pinned
byte-identical by a selftest constant, not generated. That closes the drift failure mode — a copy
that diverges from the canonical text fails the test — and it is the cheaper mechanism. Nothing
further is warranted here.

## Residual gap (recorded, not built)

**Both selftests enumerate their sites; neither discovers them.** `_g14_dispatch_selftest.py` names
three files, `_redaction_dispatch_selftest.py` names three. A newly added dispatch boundary would
carry neither hard rule, and **neither test would fail**. The audit is a snapshot, not an invariant.

Two files already demonstrate the shape, both carrying neither rule:

- `evals/exec_step3_executor_prompt.md` — the pinned Layer-5 executor dispatch template
- `evals/paired_arm_dispatch_envelope.md` — the paired-arm study's arm dispatch

**Neither is a live exposure.** Both are eval-harness dispatches that run against repo-controlled
fixture codebases, not against user payload. They are recorded because they are exactly the class
of file that becomes an exposure if promoted toward production, and because they show the
enumeration gap is not hypothetical.

**Recommended closure, when a fifth boundary is next added** (not now — no boundary is pending):
a discovery tripwire rather than a longer list. Pin the *set* of prompt-bearing files: discover
candidates by marker (a "prompt template" heading, or a `prompt:` key in
`provider-adapters.md`), and fail when a discovered file is absent from the registered set. That
converts "enumerated sites" into "enumerated sites plus an alarm on new ones", which is the
property the audit actually wants and the one it currently lacks.

## Consequence for item 25

Item 25 (tool-grounded substrate + per-language rules) depends explicitly on items **1, 3, and 18**
(`deep-dive:1018`). All three are now in place:

- **Item 1** — credential redaction: prose rule (Layer 1, `_redaction_dispatch_selftest.py`) plus
  the mechanical **G44** quarantine gate (`scripts/_artifact_credentials.py`).
- **Item 3** — this check.
- **Item 18** — the ingress provenance envelope at `--incidents`
  (`scripts/_ingress_envelope_selftest.py`, `output-format-state-schemas.md:293`).

**Item 25 is unblocked.** Its remaining prerequisite is its own decomposition — a bounded tool
runner with defined behaviour for absent, version-incompatible, timed-out, and partially
successful tools, plus per-language rule packs scoped to the languages the eval corpus actually
exercises (`deep-dive:1237`).

One boundary carries forward into that work unchanged, and the enumeration gap above sharpens it:
a tool runner is **a new dispatch-adjacent surface** that ingests attacker-influenceable text — a
secret scanner's raw output *contains the secrets it found*. Item 25's design note must place that
surface under both hard rules explicitly rather than inheriting them by proximity, since nothing
mechanical would notice if it did not.
