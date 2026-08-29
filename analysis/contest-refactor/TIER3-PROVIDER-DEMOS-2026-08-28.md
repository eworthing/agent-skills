# Tier-3 Build Phase — Provider Interception Demos (2026-08-28)

Follows `TIER3-FEASIBILITY-GATE-2026-08-20.md`, whose verdict was GO for the
**automatic-invocation** threat model on one demonstrated interception point
(claude_code `PreToolUse`). That gate named the next step: demonstrate the
remaining providers, **opencode first, because it is the actual production
runner**. This document records what the build phase established.

## Summary

| Provider | Automatic invocation | Commit-draft input | Fail-closed block | Diagnostic round-trip | Status |
| --- | --- | --- | --- | --- | --- |
| claude_code | yes | yes | yes | yes | Demonstrated 2026-08-20 (gate doc) |
| **codex** | **yes** | **yes** | **yes** | **yes** | **Demonstrated 2026-08-28 (below)** |
| opencode | yes (production data) | yes (production data) | **untested** | **untested** | Partial — environment unusable, see below |

## 1. codex `PreToolUse` — all four capabilities demonstrated

Isolated `CODEX_HOME` (the peer-plan-review adapter's proven isolation pattern):
a temp home with only `auth.json` copied and its own `hooks.json`. The user's
global `~/.codex/hooks.json` was not modified — verified after the run, its
`cbm-code-discovery-gate` entry intact. Scratch git repo, one staged file, no
commits. Model `gpt-5.4-mini`, `codex exec` with `--dangerously-bypass-hook-trust`
(the fresh home has no persisted hook trust), 240-second watchdog.

The hook is a stub validator: it appends the raw payload to a JSONL file, probes
several JSON paths for the command string, and on `git commit` writes stderr and
exits 2.

| Capability the validator needs | Evidence |
| --- | --- |
| **Automatic invocation** — fires with zero model cooperation | Hook fired on the session's first `git commit`; the prompt said nothing about hooks or validators |
| **Commit-draft input** — sees the drafted subject before the commit exists | `hook-fired.log`: `INTERCEPTED COMMIT: git commit -m 'demo: hook interception test'` — the exact pre-commit G22 input |
| **Fail-closed blocking** | Exit 2 blocked the call: `git log` reports no commits on `main`, staged change intact (`A file.txt`) |
| **Diagnostic round-trip** | Model's final message: "`git commit …` was blocked by a PreToolUse hook. Reported output: `validator stub: G-stub FAIL on drafted subject; commit blocked (fail-closed demo)`" |

### Finding: codex and claude_code share one payload contract

The captured payload is shape-identical to claude_code's:

```json
{ "session_id": "…", "turn_id": "…", "transcript_path": "…", "cwd": "…",
  "hook_event_name": "PreToolUse", "model": "gpt-5.4-mini",
  "permission_mode": "bypassPermissions", "tool_name": "Bash",
  "tool_input": { "command": "git commit -m 'demo: hook interception test' ." },
  "tool_use_id": "…" }
```

Same `tool_name` value (`Bash`), same `tool_input.command` path, same exit-2 +
stderr block protocol. **One hook implementation serves both providers**, which
reduces the per-provider cost the register priced as separate work. `cwd` and
`permission_mode` arrive free and are directly useful: the former scopes the hook
to a target repo, the latter lets the health check report the session's
permission posture.

Corroboration that this is not demo-only behaviour: the user's machine already
runs a production blocking hook on the same contract —
`~/.codex/hooks/cbm-code-discovery-gate` blocks `Grep|Glob|Read|Search` with
exit 2 and a stderr message.

## 2. opencode — two capabilities established, blocking untested

**Established from production data, not a demo.** The run-kit's observe-only
plugin (`observe-tools.ts`, installed for exactly this purpose) banked 2,870
`tool.execute.before/after` events across real runs:

- **Automatic invocation:** the plugin fired throughout, with no model cooperation.
- **Commit-draft input:** five `git commit` before-events carry the full drafted
  subject, including real BenchHype loop commits — e.g. `loop 1: re-derive
  HALT_SUCCESS — independent challenger held verdict [registry: +0 findings,
  ~0 occurrences]`.
- **Item-14's "uncertain" cell for opencode is closed:** the after-hook *does*
  expose an exit code. `exit` appears in `metadata` on 905 bash events
  (`{"exit": "0"}`).

**Blocking and diagnostic round-trip remain untested.** The plugin type is
`"tool.execute.before"?: (input, output) => Promise<void>` — no return value can
signal a veto, so the only candidate mechanism is **throwing** from the handler.
Three attempts to test it produced no evidence:

1. Harness error — `timeout` is absent on macOS (exit 127); the session never launched.
2. Model `deepseek-v4-flash` returned HTTP 403: China-hosted, requires workspace opt-in.
3. `glm-5.3` hung for **70 minutes with zero bytes written**, and was killed.

4. **Health probe** — a bare `Reply with exactly: OK` prompt, no repo, no
   plugin, 90-second deadline: hung, **zero bytes**, killed (exit 137).

Attempt 3 matches an earlier failure the same day: a peer-review round on the
same provider/model timed out twice at 30 minutes with nothing streamed. Four
independent hangs, the last on a two-word prompt with no plugin and no
repository, indicate the environment — plausibly quota exhaustion presenting as a hang — rather than
anything about the plugin API. **The opencode demonstration is deferred, not
failed**, and remains the register's stated priority because opencode is the
production runner.

## 3. What this changes for the build

- The interception mechanism is now demonstrated on **two of five** providers,
  and the two share one payload contract and one block protocol.
- Per-provider hook work is cheaper than priced for the claude_code/codex pair;
  it is unpriced for opencode until a session can run.
- Nothing here touches the five-phase validator, which remains the expensive half
  (~250–400k on the register's estimate) and the piece that makes the 27
  mechanized gates execute.
- The honest downgrade from Item-14 §4 stands unchanged: this is a
  same-privilege control. It defeats a loop that forgets to invoke the validator;
  it does not defeat a model that edits agent-writable hook config.

## 4. Reproduction

Scratch artifacts were built under a session scratchpad and are not retained.
The codex demo is reproducible from §1: isolated `CODEX_HOME` with `auth.json`
and a `hooks.json` registering a `PreToolUse` hook on matcher `.*`; a stub that
reads stdin, extracts `tool_input.command`, and exits 2 with a stderr message on
`git commit`; a scratch repo with one staged file; `codex exec
--dangerously-bypass-hook-trust`.

## 5. Validator deliverable 1 — the state→gate dimension is already collected

The register's first validator deliverable is "the phase-to-gate matrix and
expected artifact state per phase". Half of it exists as data:
`run-kit/reports/benchhype-posthoc-sweep-2026-08-21.json` holds **82 artifact
states** from BenchHype's real history (May→Aug, 4 runs), each validated by
subprocessing the shipped `validate-artifact.py`, with **24 distinct gates**
firing across them.

Cross-tabulating gate against emitted artifact state shows the mapping is
genuinely sparse — the validator does not need every gate at every phase:

| Gate | Where it fires (artifact state) | Reading |
| --- | --- | --- |
| `G37` | `HALT_STAGNATION`=11, `HALT_LOOP_CAP`=1 | terminal-only |
| `G21-scorecard` | `HALT_SUCCESS`=9, `HALT_SUCCESS_candidate`=9 | success-terminal only |
| `evidence-chain` | `CONTINUE`=12, `HALT_SUCCESS_candidate`=12 | pre-terminal |
| `transition-legality` | `HALT_LOOP_CAP`=8, `CONTINUE`=7, `HALT_STAGNATION`=6 | transition points |
| `G5`, `G18`, `G19` | every state | universal |

State distribution across the 82: `CONTINUE`=32, `HALT_SUCCESS`=18,
`HALT_STAGNATION`=12, none=11, `HALT_SUCCESS_candidate`=6, `HALT_LOOP_CAP`=3.

**Interpretation rule, carried from the sweep itself:** these counts include
EPOCH OBSERVATIONS — a strict failure on an artifact written before a gate
shipped is not a violation by the run. The table therefore maps **applicability
per state**, not defect rates.

### What is still missing

Emitted artifact *state* is not the same axis as validator *phase*
(`step1-post-write | step3-prearchive | postarchive | postchallenge-precommit |
postcommit`). This data supplies the **state→gate** dimension. The
**phase→artifact-availability** dimension is still owed: which files exist at
each phase, and therefore which gates are structurally unrunnable there rather
than failing. `G18` is the worked example — it compares `CURRENT_REVIEW.json`
against `REVIEW_HISTORY.json`, which is not appended until archive, so a
mid-loop `G18` failure is an artifact of phase, not a defect. Deriving that
dimension needs no new runs: the sweep already materializes each state's file
list (`files` per row), which is the raw input.

## 6. The phase dimension — and a correction

Deriving the second dimension from the same sweep (each row records the files
present at that state) produced a result that **falsifies the prediction stated
in §5**, and the correction matters more than the original claim.

§5 predicted that a gate whose input file is absent would *fail* at that phase —
`G18` compares `CURRENT_REVIEW.json` against `REVIEW_HISTORY.json`, so a mid-loop
`G18` failure would be "phase, not defect". Measured across the 82 states:

| | states missing `REVIEW_HISTORY.json` | states with it |
| --- | --- | --- |
| `G18` fires | **0 / 8** | 24 / 65 (37%) |
| distinct gates firing | **1** (`G5` only) | 24 |
| mean issues per state | 3.5 | 5.2 |

`G18` does not fail without its input. **It goes silent.** So do roughly twenty
other gates: on the eight incomplete states, `G5` is the only rule that fires at
all (28 issues), while `G18`, `G19`, `G21-scorecard`, `G32`, `evidence-chain` and
the rest never execute. The validator still exits 1 — but on a single narrow
rule, with most of its battery having quietly not run.

### The design constraint this produces

**A phase with incomplete inputs looks cleaner than a phase with complete ones,
for the wrong reason.** Fewer gates can execute, so fewer issues are reported,
so the artifact appears healthier mid-loop than at terminal. Any five-phase
validator that simply runs the battery per phase inherits this directly.

So the phase configuration cannot be a gate *list* alone. Each phase must declare
which gates are **expected runnable** there, and a gate that produced no finding
because its input was absent must be reported as **skipped-for-phase**, never
folded into a pass. Otherwise the hook reports "clean" at exactly the phases
where it checked least.

This is the same defect class the assessment-validity research documented from a
competitor (losing coverage *raised* the grade) and that schema v6 answers with
derived validity plus missing-critical-coverage invalidation — found here in this
repo's own tooling, by measurement rather than by argument. The two projects want
the same invariant: **absence of a finding is not evidence of compliance unless
the check actually ran.**

### Status of deliverable 1

- **state→gate dimension: collected** (§5), sparse and usable.
- **phase→runnability dimension: derived** (this section) — the mechanism is
  silence, not failure, and it is measured on 82 real states.
- **Still owed:** the per-phase *expected-runnable* declaration itself, which is
  a design decision rather than a measurement, and the skipped-for-phase
  reporting channel in the validator. Both belong to the funded build.
