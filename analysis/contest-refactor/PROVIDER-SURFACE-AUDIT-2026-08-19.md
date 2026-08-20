# Provider Surface Audit — verified against installed binaries (2026-08-19)

Triggered by a live BenchHype run that reached HALT_SUCCESS at loop 1 under an inline,
self-vetted challenger. Root cause was not the model or the host — it was
`references/provider-adapters.md`, whose per-provider claims were stamped
`verified 2026-05-09` and had drifted. Every claim below was re-checked against the
binary actually installed on this machine.

## Result

| Provider | Detection | Spawn | Read-only enforcement | State |
|---|---|---|---|---|
| `claude_code` | `CLAUDECODE=1` ✅ live | Agent tool, `general-purpose`, `claude-sonnet-5` ✅ | none — prompt-only, and the doc **says so** | sound, unchanged |
| `codex` | `CODEX_HOME` ✅ live | ❌ 3 phantom flags → **exit 2** | ❌ `--deny-tool` phantom → real: `--sandbox read-only` | **fixed** `d165a45` |
| `opencode` | ❌ `OPENCODE_SESSION` never existed | ❌ bare model id invalid | ❌ `--read-only` phantom → real: `permission` config | **fixed** `b76df07`, `d278c6b` |
| `agy` | absent → `unknown` | — | ❌ **none exists** | deliberately unsupported |
| `gemini` | absent → `unknown` | — | ✅ `--approval-mode plan` | EOL 2026-06-18 |

## Why agy is deliberately NOT profiled

Verified on **agy v1.0.16** (peer-plan-review's reference describes v1.0.7): the only
relevant flags are `--dangerously-skip-permissions` (auto-approve everything) and
`--sandbox` (terminal restrictions only — the workspace stays writable). **There is no
read-only mode.**

contest-refactor's reviewer and challenger are contractually read-only: the reviewer
decides commit-or-revert on a diff it must not be able to touch, and the challenger's
whole value is an independent attempt to break a verdict. agy cannot enforce either.

So falling through to `provider: unknown` → inline is **the correct classification**, not
a gap. Adding an agy profile would let it host roles it cannot secure, and the
`spawn_isolation: inline` record plus the preflight warning already tell the user what
they are getting.

**Do not "fix" this by adding a detection row.** The prerequisite is a read-only
mechanism in agy itself. If one ships, the profile is straightforward — until then the
absence is the safety property.

Gemini CLI is past EOL (2026-06-18; this audit is 2026-08-19). Noted only because it
carries `--approval-mode plan`, explicitly "read-only mode" — the exact enforcement its
successor dropped.

## The pattern, and what replaced the date stamps

Three of five providers were wrong or absent, and the failure mode was identical each
time: a `verified <date>` stamp made unchecked assertions read as checked. Two distinct
degradation paths, same destination —

- **opencode ignores unknown flags** → the spawn "succeeds" with the control absent
  (reviewer ran with write allowed while the doc claimed enforcement);
- **codex rejects unknown flags** → the spawn fails and falls back to inline, losing the
  independent challenger.

Both end at a terminal verdict weaker than the schema advertises, and no gate could see
it, because G32 only requires `challenger_model` to be a non-empty string.

The date stamps are now backed by `scripts/_provider_detection_selftest.py`, which pins
the specific flags and mechanisms rather than trusting a date: the phantom flags must not
return, the real enforcement (`--sandbox read-only`, `permission`/`edit: deny`) must stay
named, and the opencode model id must keep its `provider/` prefix. A stale claim now
fails a test instead of aging quietly.

## Related

- `spawn_isolation: inline` at a terminal success is flagged report-only by
  `scripts/_artifact_independence.py` (`28642b0`).
- `preflight.py --provider` warns before dispatch when detection lands on `unknown`.
- Inline-as-a-budget-flag was considered and **rejected**: `TOKEN-USAGE-AUDIT.md:126`
  measures inline as cheaper on input tokens, but the reload is what keeps each Critic
  blind — "caching the prior loop's context cross-loop would defeat the anti-anchoring
  property the whole skill rests on". A Critic that remembers its own prior scorecard is
  anchored to it, and 9.5-convergence becomes self-confirming.
