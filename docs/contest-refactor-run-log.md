# `contest-refactor` run log

Chronological record of `contest-refactor` production runs and root-caused incidents, appended to
as they happen — newest sections at the end. Split out of
[`contest-refactor-review-register.md`](contest-refactor-review-register.md) on 2026-08-25: that
document holds the skill's standing findings, coverage snapshot, ponytail/duplication audits, and
cost-ranked work order; this document holds only the dated run-by-run record.

## Execution log — fleet run 2026-08-20 (post-approval)

The owner directed execution of the agent-executable work order (panel decision: **retain**;
scope: everything agent-executable). Sonnet subagents implemented under disjoint file ownership;
every reported claim was re-verified by the orchestrator before commit. Landed:

| Item | Commit | Closure level |
|---|---|---|
| Ponytail 3 — dead-code deletion | `831f901` | Done |
| D4 step 0–1 — adjudication + cross-apply | `7d6f4b8` | Done; record in [D4] below |
| D5 — `_canon_selftest.py` | `acd0bfd` | Done: 16/16 exit sites + committed golden |
| D1 — `load_canon` refactor | `4fee1c1` | Done: equivalence-gated port, 338→247 lines |
| P1 — 9.5-residual enforcement | `ab44c63` | Closed at validator+fixture level |
| P1 ×2 — loop ownership | `3906fb2` | Closed at spec level; **keyed probe PASS** (sweep #5 2026-08-20, ledger section) |
| G29 prose + [I3] | `62d5a71` | Prose half of the emission P2 + both I3 gaps closed; **keyed probe PASS** (sweep #5: emitted v4) |
| Item 14 — execution-evidence ledger (Tier 1) | this commit | Wrapper + wtree + G47 + canon + 3 fixtures + 4 selftests; ceilings bumped (87,500/83,400/12,400); Step-3 section sha re-pinned |
| D2 — `_selftest_lib` | `ac839c5` | Done: 14-file incantation factored, zero call-site changes |
| P2 — aspirational fixtures | `13c947c` | Closed: sub-rule mapping + self-correcting exemption |
| [I1] — ruleset-epoch classifier | `60e1294` | Shipped: dogfood artifact 10→0 strict issues; G43/G46 scoped |
| Independence + transitions + [I2] + G29 enforcement | `d46360b` | All four flips real, epoch-scoped; validator-side |
| Ponytail 2 — history materialization | `4d4f6ae` | Done: 86/97 fixtures, −15,174 lines; 4 explicit-by-design |
| Backlog 8 — strictness post-filter | — | **NO-GO recorded** (`bceff1b`): blocked on item 6 + owner axis decision |

**Fleet complete.** Everything agent-executable from the work order is landed or dispositioned. Still open by design: the Tier-3 hook project (feasibility gate **PASSED — GO** 2026-08-20; build awaits owner pricing), the run-gated tier (next instrumented production run), the G17 flip (run bar 0/5), the audit rev-3 re-review (**done 2026-08-20**: round-4 codex REVISE, five confirmed findings recorded in the audit-consolidation section), D3 (next new gate), and the live-promotion halves of the enforcement flips (Tier-3). Behavioral sweep #5 (2026-08-20) closed the ownership and G29-emission keyed probes — both PASS; only the run-gated `--scope` probe remains (ledger section).

Side effects recorded: `evals/reviewer_baseline.json` prompt pin re-pinned (seventh
staleness-log entry — this edit widens the reviewer's input surface, the closest yet to
re-measure trigger (b)); `check_g28` split into `scripts/_artifact_snapshots.py`
(`_artifact_history.py` 799→650, G19 left at its selftest-pinned line); token ceilings bumped
proactive-margin (loop_apple 86,200 / loop_generic 82,100 / skill_md 12,200).

## Run kit — 2026-08-21 (pre-run instrumentation, all off-loop-path)

The owner directed building the instrumented-run kit ("do these", 2026-08-21). Shipped under
`analysis/contest-refactor/run-kit/` — nothing touches the loop path, so the tranche being
measured is unchanged:

| Tool | Purpose | Validated against |
|---|---|---|
| `posthoc_gate_sweep.py` | phase-to-gate matrix from artifact history (subprocesses the shipped validator) | full BenchHype history (May→Aug, 4 runs) |
| `coverage_citations.py` | item-24 decision data: real citation coverage vs inventory | same corpus |
| `cost_accounting.py` | opencode sqlite (db-backed ≥1.18) cost/resident accounting, read-only | the Aug-19 run's 6 sessions |
| `observe-tools.ts` | observe-only opencode plugin (`tool.execute.before/after` → JSONL); never blocks | scratch opencode session, PASS |
| `PREDECLARATION.md` | D4 predeclaration: M1–M8 measurement definitions + launch checklist | — |

Banked findings from validating the kit (reports committed under `run-kit/reports/`):

- **run_id lifecycle violation in the Aug-19 run (new)**: `run_id` minted per loop
  (`loop-2-302837137`, loop 1 null) — wrong format, wrong lifecycle — the direct cause of the
  `transition-check-blind` lines. Predeclared as M2, a PASS/FAIL probe the next run answers for
  free.
- **G17 historical datapoints (Swift, adjudication pending)**: 3 applicable loop-events, all
  violations (no citation), 0 restraint, 1 expected-blind (v2-era `changed_paths` absent). The
  ≥2-languages promotion bar cannot close on the next run (Swift again).
- **Item-24 justification data**: coverage is heavily uneven across all runs — see
  [`contest-refactor-detection-domains.md`](contest-refactor-detection-domains.md) row 24 for the
  figure and interpretation.
- **Cost baseline (M6)**: Aug-19 run = $9.30, 500 assistant messages, 92.6M resident tokens
  (parent + 2 loop executors + 2 challengers, `opencode-go/minimax-m3`).
- **Item-14 uncertain cell resolved by observation**: opencode `tool.execute.after` metadata is
  `{output, exit, truncated}` — a raw exit code IS present. Both `.opencode/plugin/` and
  `plugins/` load (install in exactly one).
- **Phase-to-gate matrix (Tier-3 input)**: 30+ artifact states validated under the current gate
  set; top strict rules G5x91, G46x45, G19x34, G18x26; 42 `transition-violation` diagnostics.
  Strict failures on pre-epoch artifacts are epoch observations, not violations.

The queued wrapper-adoption keyed probe's production datapoint is now predeclared as M3
(observation only, n=1, no adoption-rate claim).

## run_id discipline + G17 adjudication packet — 2026-08-21

Owner-approved plan (peer review explicitly skipped by owner choice; design verified by an
exploration pass + an independent plan-agent breakage pass). Landed `0667642`:

- **Mint-rule prose lift (M2 root cause)**: SKILL.md sub-step 3's `run-<UTC date>-<uuid4 hex>`
  minting rule was scoped to the wrapped-run conditional — unpinned repos had NO minting
  instruction, so loops improvised at terminal. Now unconditional; the wrapper references the
  top-level run_id. output-format-json.md field spec + example aligned.
- **G48 (run_id format + cross-loop stability) — shipped REPORT-ONLY, a deviation from the
  approved plan recorded honestly**: the plan predicted the BenchHype terminal artifact would
  classify LEGACY ("no retroactive invalidation"); verification falsified that — the Aug-19 run
  already emitted `skill_rev` (`4fe8cdf`), so a CURRENT-epoch Issue retroactively fails its
  committed HALT_SUCCESS artifact (exactly the item-30 class). The binary LEGACY/CURRENT
  boundary is too coarse for a requirement this new. Promotion bar written in
  `_artifact_run_identity.py`: (a) a post-G48 epoch boundary (e.g. third `EPOCHS` entry via a
  skill-repo ancestor check on skill_rev), AND (b) M2 observed PASS on ≥1 instrumented run,
  zero false diagnostics. Diagnostics (`[g48-run-id …]`) print for every epoch — the sweep and
  M2 read those.
- Sweep bonus finding: the Aug-19 run's loop-1 FINAL history entry carried `run-2026-08-20-001`
  (not null as the mid-loop commit suggested) and the two loops ran under different skill revs
  (`5936630` → `4fe8cdf`) — live mid-development dogfooding; both G48 sub-checks fire on it as
  diagnostics.
- Fixture hygiene: `halt-terminal-held` and `independence-missing` (both CURRENT-epoch) repaired
  from the non-conformant `run-2026-06-21-001` to a conformant id; g48 flag/restraint pair added
  (corpus 100 → 102); Step-3 section sha re-pinned; ceilings 87,800/83,700/12,500.
- **G17 adjudication packet** (`analysis/contest-refactor/run-kit/G17-ADJUDICATION-2026-08-21.md`):
  4 datapoints with proposed dispositions — 2 TRUE violations (Aug-16 loop 12, Aug-19 loop 2),
  1 expected-blind-loop-compliant (May-9, which actually cited a 4-entry coverage path), and
  1 proposed **FALSE POSITIVE** (May-25 docs-only loop; keyword "consolidated" matched primer
  prose). D2's disposition is load-bearing: adopting FP blocks promotion until a
  code-file-in-changed_paths trigger refinement (costed in the packet, owner decision).

## Instrumented run #5 — 2026-08-23 (spend-limit death at loop 1)

Launched under opencode (`opencode-go/minimax-m3`) on BenchHype, `--reset --scope BenchHypeKit`,
with the pin, observer, and clean tree all verified live beforehand. The weekly usage cap killed
it 4m12s in (13:08:30 → 13:12:42Z), before Step 1 ever emitted — **no `CURRENT_REVIEW.json` was
written**. Per the house rule, spend-limit death is not a MISS: this run says nothing about
detection quality. It did produce one real defect and one confirmed measurement.

- **[P1] The verify-trust pin is unreachable by the loop — FIXED this commit.** The operator
  pinned `./scripts/run_local_gate.sh --quick`; the loop ran `--targeted`, invoked
  `attested_run.py` **zero** times, and created no attestation ledger. Observer events 18–20 show
  the mechanism: the loop read `scripts/run_local_gate.sh`, grepped `TARGETED|QUICK|FULL`, and
  *chose a verify command by inspection*, then passed `--targeted` to `preflight.py` and ran it
  bare. Root cause is prose, not code: SKILL.md sub-step 3 gated the wrapper on the command
  "being pinned" without ever instructing the loop to **read** the store and learn which command
  that is, so Discovery's own choice silently won. The store matches on exact string + sha256, so
  a same-script-different-flag near-miss fails closed and unnoticed. Fix: sub-step 3 now reads the
  store and runs the pinned string verbatim in place of Discovery's choice, and names the
  near-miss trap. +60 tokens, `budget-guard: OK`, no ceiling bump.
- **M8 — CONFIRMED at run scale.** opencode's `tool.execute.after` metadata is
  `{output, exit, truncated}` and the raw exit code is present on all 20 bash after-hooks. The
  item-14 uncertain cell is now observed on a live run rather than the scratch test. Detail for
  any consumer: `exit` arrives as a **string** (`"0"`), and the `read` tool carries no exit at all.
- **M3 — FAILED**, as a direct consequence of the P1 above; G47's three attestation flags still
  have no live exercise. **M2, M4, M7, M1, M5 — unmeasured** (no loop artifact was ever written).
- **M6 — $0.19, 29 messages, 2.23M resident tokens** (baseline for the series: Aug-19's $9.30 /
  500 msgs / 92.6M). The command mismatch cost twice: no attestation, and `--targeted` (app build
  + change-mapped UI tests) instead of the cheap pinned `--quick`, still running when the cap hit.
- **Behavior worth an owner call, not yet adjudicated**: at event 4 — ~30s in, inside Step 0,
  before any plan existed — the loop ran `git add skills-lock.json && git commit` against the
  target repo (BenchHype `5d85cc14`). It tidied a dirty file on its own initiative. Whether
  preflight housekeeping may commit outside the refactor mandate is undecided.
- **Owed**: the Layer-5 K=5 execution-grain re-measure that the Step-3 sha re-pin normally
  demands. The executor prompt sha is unchanged and the clause governs *which* verify command is
  invoked rather than the apply/revert grain the invariants measure, so the banked Arm-A results
  are carried forward as **provisional** (recorded in `exec_replay_baseline.json`
  `measurement_notes`).

## Provider detection was dead on both providers — 2026-08-23

Surfaced by the codex operator mid-run, one turn after the run-#5 pin fix. Detection had
**never** successfully fired on either provider we have telemetry for, and the consequence each
time was a terminal `HALT_SUCCESS` resting on a challenge the Critic administered to itself.

- **Root cause is duplication, not a bad predicate.** The rules lived in two files.
  `provider-adapters.md` got the 2026-08-19 `OPENCODE_SESSION` fix; `resume-detection.md` kept
  the dead copy — and Step 0.5 reads `resume-detection.md`, so the stale copy is the one that
  ran. `_provider_detection_selftest.py` read only `provider-adapters.md`, so it could not see
  the disagreement it existed to prevent. Step 0.5 is now a pointer; the table is the single
  source of truth.
- **Codex predicate keyed on a path override.** `CODEX_HOME` overrides `~/.codex` (peer-plan-review
  `references/codex.md:73`) and is unset on a default install — verified unset in a plain shell.
  A live codex session exports `CODEX_SESSION_ID` / `CODEX_THREAD_ID` instead (operator-captured
  env, 2026-08-23). Detection now reads those; `CODEX_HOME` survives only in `$SKILL_DIR`
  resolution. Principle recorded in the doc: **detection reads session-scoped variables; config
  and path overrides never detect.**
- **Provider variables leak across sessions** — the live codex env carried
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` and `GEMINI_CLI_IDE_*`. `CLAUDECODE` therefore stays an
  exact `=1` match and must never be loosened to a `CLAUDE_CODE_*` prefix; the rationale is now
  in the file so a future edit cannot make that mistake innocently. Negative control run in a
  Claude Code session: no `CODEX_*` / `OPENCODE_*` variables present (only `PATH` matched, which
  is exactly the binary-presence ambiguity the rule already refuses to consult).
- **Two new selftest guards, both RED-tested before landing**: (3) `resume-detection.md` may not
  name `CLAUDECODE` / `CODEX_` / `OPENCODE_` at all — pointer only; (4) the Detection **table
  rows** may not key on `CODEX_HOME` and must name a session-scoped codex variable. Guard 4
  scans rows rather than prose for the reason the `--read-only` guard already documents: the
  corrected section names `CODEX_HOME` in the negative, and a substring test cannot tell a
  rationale from a trigger.
- **Cost**: both edited files are Step -1 main-only (the per-loop half was split into
  `provider-adapters-reviewer.md` on 2026-08-21), so this is ×1 per invocation, not per loop.
  Per-loop ceilings unmoved; `budget-guard: OK`.
- **Still unvalidated — do not treat as fixed**: the opencode predicate. `OPENCODE_*` prefix was
  chosen in 2026-08-19 from a scan of strings *referenced in the binary*, which is not the same
  as variables *exported to the tool environment*. Last run's opencode session still resolved to
  `unknown`, and that is equally explained by the stale-file bug fixed here. Next opencode run
  must capture `env | grep -i opencode` as its first action before any claim is made.

## Codex model + per-role reasoning effort — 2026-08-23

Owner-directed, arising from the provider-detection work the same day.

- **Reasoning effort was floating, and that was a silent cost and correctness leak.** No spawn
  passed an effort flag, so every codex subagent inherited `model_reasoning_effort` from the
  operator's `~/.codex/config.toml` — set to `xhigh` there for interactive chat, not for
  autonomous loops. Two machines could produce the same artifact from a `low` Critic and an
  `xhigh` Critic with nothing recording the difference: `CURRENT_REVIEW.json` has `loop_model`
  and `loop_model_source` but **no effort field at all**. Effort is now pinned per role on the
  command line.
- **Per-role tiers (owner-set, not measured)**: loop subagent (Actor + Critic) `high`;
  implementation reviewer `xhigh`; HALT_SUCCESS challenger `xhigh` (inherits the reviewer
  profile); helper sidecars `medium`. The loop tier is an explicit compromise — the owner chose
  `high` over `medium` because the Critic writes the scorecard and judges Meta-Rule-4 risk
  boundaries. **No effort-tier experiment has ever been run**; this is a judgment call recorded
  as one, and it is the obvious candidate for the next paired-arm study.
- **Codex model refreshed**: default `gpt-5.4-mini` → `gpt-5.6-luna`; flagship upgrade target
  `gpt-5.5` → `gpt-5.6-sol`. The `gpt-5.6` family (`gpt-5.6`, `-luna`, `-pro`, `-sol`, `-terra`)
  was verified against **codex-cli 0.149.0's own strings**, not taken on trust — peer-plan-review's
  model list (dated 2026-07-14) predates `luna` and would have rejected it. Updated in lockstep:
  both spawn profiles, the helper tier, the prose defaults, `_artifact_core.py`, and
  `_model_catalog_selftest.py`'s REQUIRED/DEFAULTS_PRESENT tuples.
- **Guard 5 in `_provider_detection_selftest.py`, RED-tested before landing**: every `codex exec`
  line in either adapter file must carry `model_reasoning_effort=`. This is the same failure
  shape as the verify-trust pin and the dead detection predicate — an invisible environment
  dependency the loop does not know it has — so it gets a guard rather than a note.
- Cost: `provider-adapters-reviewer.md` is in the per-loop set, so +43 tokens per loop;
  `provider-adapters.md` is Step -1 main-only. `budget-guard: OK`, no ceiling bump.

## Instrumented run #6 — 2026-08-23 (codex; first run with working provider detection)

**Correction, same day:** this run was NOT terminal when the fixes below were written. A `ps`
pattern that matched `codex exec` but not the bare `codex` binary showed zero processes, and the
artifact was read at `HALT_SUCCESS_candidate`; the run was in fact still live and later reverted
to `CONTINUE` at loop 6. **The skill prose was therefore edited mid-run** — the contamination the
run-kit exists to prevent. Loops 1–6 completed before those edits and their measurements below
stand; anything the run produced afterwards read a different skill than loops 1–6 did and is not
comparable. Recorded here rather than quietly fixed, because a preregistered run whose instrument
changed mid-flight is exactly the thing a register has to say out loud. The `HALT_SUCCESS_candidate`
→ `CONTINUE` reversion was **not** caused by that interference, as first suspected — it was the
challenger breaking the candidate, which is the system working. Killed by the operator at loop 7
after 10 commits across loops 1–6.

Observed at loop 6 of a cap of 10. **The first run in this project's
telemetry where provider detection ever fired**: `provider: "codex"`, `spawn_isolation:
"subagent"`, `loop_model`/`reviewer_model` `gpt-5.6-luna` from `default`, `skill_rev 871a1d5`.

### Measured

- **M2 — partial FAIL, narrowly.** Loops 2–6 carry one identical conformant
  `run-2026-08-23-0f376c5995434c319cd03de4302b95cc`; loop 1 carries null. Format and cross-loop
  stability both pass; only the first loop misses. Fixed below.
- **M3 — FAIL, six for six.** No `attested_run.py` invocation, no attestation ledger,
  `execution_evidence` null on every loop, `--targeted` executing rather than the pinned
  `--quick`. Root cause found and fixed below.
- **M4 — first live emission.** `findings_carried_from_prior_loops: ["F-018 resolved in loop 6"]`.
- **The challenger ran, and it worked — three times.** An earlier entry in this section claimed
  it never spawned. That was wrong, read off a null `halt_success_challenge` without checking the
  commit log. The target repo's history shows `loop N: record challenger break` at **loops 4, 5
  and 6**: each time the loop emitted `HALT_SUCCESS_candidate`, the independent challenger broke
  it, and the loop correctly demoted to `CONTINUE` and opened a finding — F-017 (an Apple Music
  bulk selection re-routable into a library import via stale progress state), F-018 (an accepted
  test-strategy residual that ignored the untested bulk route), F-019 (a library route test
  accepting an unrelated snapshot as proof of session start). The field reads null because a
  demoted candidate clears it; the break is recorded in the commit and the resulting finding.
  This is the first run with a genuinely independent challenger, and it stopped three 9.5+
  success claims that would otherwise have stood.
- **F-019 is a live Tier-1 blind case.** "Test accepts an unrelated snapshot as proof" is exactly
  test-oracle trust — Tier-1 item 1 in
  [`contest-refactor-detection-domains.md`](contest-refactor-detection-domains.md). Found by the
  challenger rather than the lens, which is itself the argument that the lens is blind to it.
  Worth banking as criterion-1 evidence for that candidate.
- **Run-kit gap: `cost_accounting.py` cannot see codex runs.** It reads opencode's session store,
  so M6 returned only the dead opencode session from earlier that day. Codex sessions live under
  `$CODEX_HOME/sessions/` (default `~/.codex/sessions/`). M6 is unmeasurable for codex runs until
  the tool learns that store.

### Fixed

1. **Test-command precedence — the M3 root cause.** Three sources could supply a test command
   (Step 0 Discovery's own inspection, `.contest-refactor.toml` `defaults.test_command`, the
   human-pinned verify-trust store) and no document stated their order. `project-config.md
   § Resolution order` owns precedence and did not mention the store at all; its authority was
   asserted only at its point of use, at the tail of SKILL.md sub-step 3 — where it lost to a
   value Discovery had already committed. The store is now tier 0 in the resolution order, Step 0
   reads it **before** detecting anything, and sub-step 3 simply runs `discovery.test_command`.
   Command and pin now match by construction, which retires the near-miss trap rather than
   warning about it. Also resolved a contradiction in the same file: `test_command`'s inline
   comment called it a fallback while § Resolution order made it an override.
2. **The mint moved to where the artifact is written.** `run_id` is now minted at **Step 1
   sub-step 5**, in the same pass that writes `CURRENT_REVIEW.json`, instead of Step 3 sub-step 3.
   No artifact can be written without an id, so the first-loop miss is gone by construction
   rather than by a louder instruction. Field spec at `output-format-json.md:192` moved with it.
   Note what this supersedes: the 2026-08-21 prose lift that made the mint *unconditional* was
   correct and still did not fix loop 1 — the defect was write-ordering, not reachability.
3. **G48 can now see a missing mint.** Its FORMAT check was guarded by `rid is not None` and its
   STABILITY check only fired on a non-null predecessor, so a run where the mint never happened
   was invisible until G32 caught it at `HALT_SUCCESS_candidate` — and invisible forever on a run
   that never got there. A malformed id fired; a missing one did not. New third sub-check: a
   v4+ history entry appended with a null/empty `run_id` prints a diagnostic. **Verified against
   the real BenchHype artifact**, where it now reports loop 1. Selftest case 7 was narrowed
   rather than deleted — its genuine guard is that a mid-run mint must not trip the *stability*
   check, and asserting plain silence would have re-hidden exactly this failure.

### Pattern across runs #5 and #6

Four defects in two days share one shape: **a rule stated only at its point of use, losing to a
value already committed elsewhere.** The verify-trust pin (Step 3, beaten by Discovery), the
detection predicates (two files, the stale one read), the reasoning effort (stated nowhere,
inherited from the operator's chat config), and the mint (correct and unconditional, beaten by
write order). In every case the prose was right. What held each time was a selftest guard, not a
better sentence — which is why fix 3 above matters more than fixes 1 and 2: without it, neither
of them is measurable on the next run.

## Instrumented run #7 — 2026-08-24 (opencode; hotspot-v2 remediation audit)

BenchHype was re-run with `--reset --scope BenchHypeKit` under opencode
`opencode-go/minimax-m3`. The terminal artifact records skill revision `8156df3`, run id
`run-2026-08-24-7f7088f7f7194dc2819c7d243631c1e9`, candidate commit `0e4f31cd`, and terminal
commit `8c5bf1d7`. This section validates the operator's post-run issue report against those two
commits, the opencode log (`run=b013c251`), and the current skill rather than adopting the
report's causal explanations.

### What the run proved

- **Hotspot persistence works.** A fresh `audit_hotspots.py BenchHypeKit --json` document is
  decoded-equal to terminal `discovery.hotspot_scan`, and the current preflight accepts the pair.
  The record retained six Swift candidates with queue counts `2/2/2`; this closes the earlier
  hand-reconstruction failure for the persisted payload itself.
- **The reset-history repair holds.** `REVIEW_HISTORY.json` has the canonical top-level
  `loops[]`, its tail equals `CURRENT_REVIEW.json`, the current run/loop appears once, and strict
  validation accepts G18. `git show ee2b1292:REVIEW_HISTORY.json` proves the pre-run file already
  had that shape.
- **The independent challenge did useful work.** It corrected five factual claims: 11 concrete
  executor types rather than protocols, eight stored `EditingState` slots (a ninth `var` is
  computed), twelve `AppState` slices, 194 `inout AppState` matches across 32 files (scoped to
  `Sources/`; repo-wide including `Tests/` the count is 209 across 41), and `.walkoutFromLive` as
  the fourth `PendingCueBinding` case. The current source confirms each count/name.
- **The architecture verdict was not broken.** None of the validated protocol defects below is
  evidence of a new Serious-or-worse BenchHype architecture finding. This audit is about whether
  the skill can substantiate that verdict reproducibly.

### Claim-by-claim validation

| Reported issue | Verdict | Evidence and disposition |
|---|---|---|
| Step-0 preflight/artifact circular dependency | **Observed friction; causal claim rejected** | The run invoked preflight before creating `CURRENT_REVIEW.json`, then retried twice. Current `startup.md:41-52` explicitly orders scanner → persist exact object → preflight. That is a two-phase write, not a cycle. Improve the missing-file diagnostic and provide one deterministic discovery-bootstrap command; do not weaken the equality gate. |
| G40 lens list vs string | **Confirmed contract contradiction** | `startup.md:37` says to record the full loaded list; `output-format-json.md:214-224` and `_artifact_core.py:493-533` require `lens` to be one string. Keep `lens: "Apple"|"Generic"`; the always-loaded security/efficiency lenses are ruleset-derived and need no duplicate array today. |
| G19 `loop_model_source` | **Confirmed attribution defect, different fix** | No `--loop-model` or `--reviewer-model` user flag selected minimax. The native opencode task records `model=undefined` and inherits the parent model, so `inherited` is the honest source, not `user_flag`. `provider-adapters.md:172-185` omits `inherited` while `_artifact_history.py:309-470` accepts it. Add an explicit source decision table and record the loop and challenger roles separately. |
| Candidate fingerprint must be recomputed manually | **Confirmed helper gap; report overstates sensitivity** | `candidate_fingerprint.py:19-56` hashes only lens, source roots, selected scorecard fields, and findings; it does not hash every artifact field. Its direct CLI only runs a self-test (`:133-134`), forcing ad-hoc import snippets. Add `compute`, `verify`, and atomic `write` modes. |
| G18 archive equality / legacy `runs[]` migration | **Execution mistake, not current data drift** | Before this run, commit `ee2b1292` already had top-level `loops[]`. The run itself invented `runs[].loops[]`, added `archived_at`, and wrote an order-unstable dedup script — in uncommitted working-tree states only: both committed histories (`0e4f31cd`, `8c5bf1d7`) are clean (top-level `loops[]`, 13 entries, no `archived_at`), so the mistake narrative rests on the operator's report, not committed evidence. `coverage_ledger.py:174-202` reads only top-level `loops[]`; it does not tolerate the alleged legacy shape. Replace model-authored archive mutation with one helper implementing `output-format-state-schemas.md:192,326-341`. |
| G32 attempt target requires a bare dimension | **Confirmed docs/diagnostic sharp edge** | `_artifact_panel.py:44-71` uses exact membership in `{simplicity, domain_modeling}`. `halt-verifier.md:103-110` gives the correct exact example, but the surrounding schema calls target `<dimension|finding>`. State the enum at the field definition and tell the agent to put descriptive detail in `what_tried`. |
| Challenger found factual miscounts | **Confirmed and corrected, but exposed a stronger binding defect** | Candidate `0e4f31cd` fingerprinted `fp-sha256-c61b...`; after the corrections, terminal `8c5bf1d7` fingerprints `fp-sha256-035e...`. G32 v4 checks the terminal fingerprint's internal validity but does not bind `halt_success_challenge` to the candidate fingerprint (`_artifact_panel.py:74-215`). The promoted artifact therefore is not the exact candidate that was challenged. |
| `F-NEW` fails G42 / unclear id with no finding | **Real malformed commits; wrong gate and wrong proposed remedy** | Both new commits contain `stable_id F-NEW`. G42 governs backlog items and does nothing when the backlog is empty (`_artifact_core.py:591-657`); G22 owns commit subjects. Minting F-022 would fabricate a finding. G22 needs explicit no-finding candidate/promotion subject forms, and its commit check must not silently skip a repo-root artifact merely because `.contest-refactor.toml` is absent (`_artifact_history.py:473-540`). |
| No terminal HALT_SUCCESS template | **Rejected** | The exact template already exists at `halt-handoff.md:93-134`. The run improvised because the main promotion transition did not reload/use it. Add a co-located anchor from the held-transition instruction; do not create another template. |
| Inline mode is expensive | **Outcome confirmed; stated cause unproven** | Step 1 ran in the primary opencode session, but no `opencode run` subprocess attempt appears in the log. The artifact nevertheless says `spawn_isolation: "subagent"`, disabling the inline G20 path on false metadata. Cost is real; “subprocess unavailable” was never tested. |
| Opencode provider adapter mismatch | **Confirmed** | The adapter documents only `opencode run` (`provider-adapters.md:76-87`), while the host exposed a native task type `general`. The run first tried invalid `general-purpose`, then used `general` for the challenger. Add the native task path and its exact role/model attribution; keep subprocess as the fallback. |
| Hotspot scan `partial` with no failure list | **Confirmed symptom; root cause found** | Of 609 discovered Swift files, 201 were called failed. `ast-grep` returns exit 1 with valid JSON `[]` when a file contains no `function_declaration`; `_ast_grep_matches` treats every nonzero as failure (`audit_hotspots.py:711-736`). Also, case-sensitive `IGNORE_DIRS` skips `tests` but not SwiftPM `Tests` (`:52-80`), leaking 32 test files — only 32 of the tree's 789 because the separate filename filter `_is_test_file` (`:137-152`) catches suffix-named files; the leakers are extension-suffixed names like `PlaybackReducerTests+AdmissionStatus.swift` (577 `Sources/` + 32 = the 609 discovered). The failures are not `.build` artifacts: `.build` is explicitly ignored. |
| Two commits for one loop | **Expected design** | Candidate durability followed by independently challenged promotion intentionally makes two commits (`SKILL.md:140`). Rename “commit per loop” prose to “commit each durable transition”; do not collapse the commits. |

### Additional defects the retrospective missed

1. **G32 binds the wrong architecture payload.** The challenger reviewed candidate fingerprint
   `c61b...`; main changed fingerprint-bearing residual fields and promoted fingerprint `035e...`.
   Add `binding.candidate_fingerprint`, require equality with the live terminal fingerprint, and
   route any fingerprint-changing correction to a new candidate plus a fresh challenge. Merely
   recomputing the hash is not certification.
2. **Hotspot triage was incomplete.** `method.md:85-86` requires every retained candidate to end
   as `confirm`, `contextualize`, or `dismiss`; Builder Notes say “5 of 6 candidates inspected.”
   G49 validates the scanner record, not its consumption. Persist a structured triage row keyed by
   candidate path+symbol and block candidate emission until its key set equals the scanner roster.
3. **Swift coverage status is false.** Exit-1/no-match is normal ast-grep behavior, so the run's
   `partial` label overstates missing coverage by at least 201 files. Fix this before adding a
   failure-path payload. For genuine failures, emit bounded stderr diagnostics (reason counts + a
   small path sample); avoid expanding the six-field persisted object until a consumer needs it.
4. **Isolation/model provenance is false.** The loop ran inline while the artifact says
   `subagent`; the task inherited minimax while the artifact says `user_flag`. G19 validates
   self-consistency, not runtime truth. The spawn adapter must return the metadata that the
   artifact records rather than asking the model to infer it afterwards.
5. **Both terminal-path commit subjects are invalid and the validator missed them.** G22's commit
   sub-check runs only when project config is present. BenchHype has no `.contest-refactor.toml`,
   so strict validation returned zero Issues while HEAD still contains `F-NEW`.

### Ranked remediation work order

#### P0 — verdict/provenance integrity

1. **Bind G32 to the challenged fingerprint.** Add v4 `binding.candidate_fingerprint`; reject a
   terminal fingerprint that differs. Factual corrections that touch the canonical payload emit a
   corrected candidate and re-challenge. Add one selftest based on the `c61b... → 035e...` drift.
2. **Ship the native opencode adapter.** Prefer host Task `general` when available, otherwise try
   documented `opencode run`, then record an honest inline fallback. The adapter returns
   `{model, model_source, isolation}` for loop/reviewer/challenger roles. Test that
   `general-purpose` never appears in the opencode path and that inline execution records
   `spawn_isolation: inline`.
3. **Correct Swift scan accounting.** Treat ast-grep exit 1 plus decoded `[]` as successful
   no-match, compare ignored directory names case-insensitively, and add fixtures for an enum-only
   Swift file, a function-bearing Swift file, and `Tests/` — the `Tests/` fixture must use an
   extension-suffixed filename (`FooTests+Bar.swift`), since suffix-named test files are already
   caught by `_is_test_file` and would pass the fix on the wrong mechanism. Acceptance on
   unchanged BenchHypeKit: zero false failures and no test-tree discoveries.
4. **Fix no-finding transition commits.** Extend G22 with explicit candidate/promotion forms that
   carry no fake finding id, validate repo-root artifacts even without project config, and add
   pre-commit subject validation so a malformed draft cannot land first and be diagnosed later.

#### P1 — deterministic artifact operations

5. **Mechanize complete hotspot consumption.** Add structured per-candidate triage and a gate whose
   equality check fails the observed 5/6 case. Keep dispositions evidence-only; a `confirm` still
   needs the canonical Finding Evidence Chain.
6. **Replace hand-edited archive/fingerprint steps.** One stdlib archive helper owns append-vs-last
   replacement and parsed-dict equality; extend the existing fingerprint script with artifact
   CLI modes. These are separate narrow helpers, not an omnibus state machine.
7. **Align small contracts.** Make `discovery.lens` explicitly scalar, document the four model
   source values and selection rules, make G32 target enums exact at the schema site, and link the
   held transition directly to the existing HALT_SUCCESS handoff template.

#### P2 — diagnostics and wording

8. Improve preflight's missing-artifact error to name the required scanner → persist → preflight
   order. If the same ordering miss recurs after that, add a minimal discovery-bootstrap helper;
   do not build the proposed all-in-one Step-0 helper pre-emptively.
9. For genuine ast-grep errors, print failure reason counts and a bounded path sample to stderr.
10. Replace “one commit per loop” with “one commit per durable transition” wherever the former
    phrase appears.

### Completion criteria

- A replay of this exact run cannot promote after changing the candidate fingerprint.
- The opencode loop uses native `general` or records an attempted subprocess/inline fallback; the
  artifact's isolation and model-source fields match the observed path.
- BenchHypeKit's Swift scan excludes `Tests/`, treats no-match files as scanned, persists the raw
  scanner object unchanged, and requires six triage rows for six retained candidates.
- Candidate and promotion commits with no finding pass the new G22 form without minting a registry
  id; `F-NEW` fails before commit.
- G18 history remains top-level `loops[]`, one current-run entry per loop, with tail parsed-dict
  equal to `CURRENT_REVIEW.json` after candidate emission and promotion.
- Focused selftests are red on the five observed failures before their fixes, then green; the full
  `validate-repo.py`, validator selftests, fixture corpus, and Ruff gates remain green.

### Remediation landed — 2026-08-25

All ten work-order items shipped across five sequential sonnet waves, each independently verified
before the next dispatched. Commits: `152d8a3` (fingerprint CLI compute/verify/write), `44b4c03` +
`32dce1c` (G32 `binding.candidate_fingerprint`, epoch `G32_FINGERPRINT_BINDING` keyed to the
prose commit — the two-commit epoch shape G49 established), `c2d095f` + `c0de3e3` (scan
accounting + case-insensitive ignore dirs), `57878a1` (opencode three-tier adapter + four-value
model-source table, prose-guarded by selftest), `982620c` (G22 no-finding subject forms,
repo-root skip-bug fix, `check_commit_subject.py` pre-commit checker), `7ffd502` + `41bca16`
(G50 hotspot-triage completeness, epoch `HOTSPOT_TRIAGE`), `d8963d6` (`archive_history.py`
helper, lens-scalar/G32-target/HALT-template alignments, preflight ordering diagnostic).

Completion criteria were replayed against the **real** terminal artifact (`8c5bf1d7` payload,
skill_rev bumped to the remediated revision): the c61b→035e drift and a missing binding
fingerprint each fire G32, a matching binding passes; the observed 5-of-6 triage case and a
missing triage block each fire G50, 6-of-6 passes. BenchHypeKit rescans `577/577/0, ok` with
`Sources/BenchHypePersistence/Migrations/` restored to coverage and zero `Tests/` leakage; the
widened G22 run against BenchHype's actual log now emits the Issue it originally missed;
`check_commit_subject.py` rejects the literal F-NEW subject and accepts the no-finding form.

Found during remediation, disposition noted:
- **Fixed (`c0de3e3`):** the prescribed case-insensitive ignore-dir comparison initially
  swallowed Swift's hand-written `Sources/**/Migrations/` via the Django-oriented `migrations`
  entry — one real production file lost from coverage. `migrations` is now exact-lowercase-only,
  fixture-guarded both directions.
- **Parked (pre-existing, one file):** `_is_test_file`'s `spec.swift` suffix heuristic
  false-positives real domain types — BenchHypeKit's `Sources/BenchHypeDomain/Values/PlaybackSpec.swift`
  is invisible to the hotspot scanner. Not introduced by this work; fix would trade against
  Quick/Nimble spec exclusion outside `Tests/` trees.
- **Parked (pre-existing):** `_exec_replay_selftest.py` and `_paired_arm_selftest.py` were
  already red before the waves (frozen SKILL.md/method.md prose hashes drifted under earlier
  edits). Every wave verified their failure output byte-identical before/after. They need one
  deliberate re-pin pass once prose settles.
- **Accepted residual:** BenchHype's two historic F-NEW commits remain in its log; a future
  multi-loop run whose G22 window reaches depth 3–4 will correctly flag them — the gate working
  on genuinely malformed history, not a false positive.

### Run-2 follow-through — multi-root discovery + residual scheduling (2026-08-25)

The first unscoped run (`0c6d65e1`→`9e09fd08`, HALT_SUCCESS) exposed two design defects the
remediation waves could not have caught: **unscoped runs silently narrowed to one source root**
(startup.md's own example named `BenchHypeKit/Sources/` — dogfooding contamination — and every
mechanical evidence step took a single root; the run scanned only that subtree while presenting a
repo-level verdict), and **9.5-accepted residual work was never scheduled** (the HALT_SUCCESS
handoff said "won't be revisited unless you ask" and nothing downstream read it). A validated
10-issue operator retrospective from the same run added five confirmed frictions. All fixed across
five verified sonnet phases:

- `e286f1e` — `_fs_filters.py` filter SSOT (+ hidden-dir rule; retro #2's ledger garbage traced to
  three divergent filter copies). `audit_boundaries.py` deliberately left non-shim: its consumer
  `audit_suppressions.py` reads its filters directly and a swap would silently change a
  multi-language scan — documented in-file.
- `c1c4d76` — ledger hardening (`missing_root` typed accounting, absolute-root typed rejection)
  + the universe-derived `source_roots()` enumerator and `--list-source-roots` CLI. On BenchHype:
  `BenchHype`, `BenchHypeKit/Sources`, `scripts`, `tools` — the app target the old contract never
  saw.
- `a95cbf8` — the behavior flip, one commit: scanners run at the **repo root** (repo-relative
  candidate paths, fixing the coordinate split with the citation ledger), `--scope` filters the
  discovery walk, and preflight gains three tripwires (source_roots normalization,
  silent-narrowing vs the enumerator, candidate-path coordinates). Run-2's real artifact fires all
  three retroactively — the exact defect class can no longer pass Step 0.
- `f9ec65f` — residual work docket (owner decision: docket + forced next-run intake; the
  `--attack-residuals` flag considered and not chosen). At promotion, main writes
  `docs/audits/contest-refactor-residuals-<run_id>.md` (Tier-4 marker line, one row per accepted
  residual, supersedes chain), riding the promotion commit; the next run's existing
  prior-audit adopt-or-falsify machinery makes every row disqualifying-if-unexamined. Zero new
  gates, zero schema change.
- `b3e9fe9` — retro fixes: challenger prose now mandates the `new_finding` diversity-arm shape
  up front (#1/#8, validator unchanged); `archive_history.py` owns the REVIEW_HISTORY.md divider
  half and the promotion flow archives-before-validating (#3/#4, G18 flicker dead); G22
  structurally validates `--- HALT_SUCCESS <verb> (UTC …) ---` dividers (all three real historic
  variants pass; timestamp-less and capitalized forms fail); G48's missing-mint note is scoped to
  the current run (#5); method.md pins Q9 humility re-derivation (#6).

End-to-end at close: G22 on BenchHype's real archive = 0 issues; scanner at BenchHype repo root =
606 discovered / 0 failed, all paths repo-relative; enumerator exact; battery green throughout
(the two pre-existing frozen-hash failures byte-identical at every phase). Expected on the next
unscoped run: four declared roots, per-root coverage disclosure in the handoff, and — if it ends
HALT_SUCCESS with accepted residuals — the first committed residual docket, which the run after
it must adjudicate row-by-row.

Parked from this pass: `.sh` in the coverage SOURCE_EXTS (declined v1 — would shift every repo's
denominator); a `per_root_cited` ledger field (handoff currently composes it from `sets.cited`);
compound-test-dir helper leakage (`FooUITests/Support.swift`) tracked with the `spec.swift`
false-positive; the frozen-hash re-pin pass still owed.

## Live run #8 — 2026-08-25 (claude_code; multi-root first light + two live incidents)

First unscoped run on the d13bba4 skill, under Claude Code (`spawn_isolation: subagent`,
loop_model `claude-opus-5` via `user_flag`, run id `run-2026-08-25-4a5d0312…`). The multi-root
fix worked on first contact: four declared roots (`BenchHype`, `BenchHypeKit/Sources`, `scripts`,
`tools`), repo-root scan 606 discovered / 0 failed, a `scripts/uitest_lanes.py` candidate in the
top six, and loop 3's cluster sweep re-graded F-024 from Cosmetic to Noticeable (unjustified
`public` at 7 sites across 4 modules — a finding structurally invisible to every prior
single-root run). The `run_id: None` first-write anomaly self-resolved on a later emit pass.
Section written mid-run, when fixes below were PENDING. The run has since terminated: Incident 2's
three fixes shipped in the nine-wave remediation below (`3d36866`); Incident 1's three items remain
open — see the outcomes subsection for what did and did not land.

### Incident 1 — loop-2 ordering fusion (edit before emit, checkpoint skipped)

Loop 2 edited source before the Step-1 emit and never wrote `LOOP_STATE.json` (confessed in
`adadd935` after the operator's mid-loop correction; the validated commit `52873259` was kept
rather than re-derived byte-identically). Root cause: **backlog-seeded certainty** — loop 2's
finding was literally loop 1's backlog item, so the agent treated Steps 1–2 as already done and
batched artifact writes at commit time. Loop 1 (no backlog, real discovery) ordered correctly;
loop 3 (post-correction) also complied — emit 08:38 before edits 08:40, checkpoint with all 8
`pre_step3_blob_shas` matching the dirty set 1:1. Detection gap: **ordering evidence is
self-erasing** — every gate validates committed state, wrong-order and right-order loops commit
byte-identical output, and `LOOP_STATE.json` is deleted at sub-step 11.f on success, so no
post-hoc witness exists. Items: (a) persist a minimal checkpoint witness into the artifact or
history entry a gate can check; (b) Step-1 prose: a backlog entry is not a completed Step 1 —
emit before touching code even when the fix is known; (c) the mid-gap tripwire (source modified
while the artifact still reads loop N−1) stays a candidate, checkable only at next-validate.

### Incident 2 — executor stall cascade (three stalls, root-caused, fixed in-run)

All three stalls clustered at the test-gate boundary and had one mechanism, proven from the
subagent transcripts. **Cause A:** executors end their turn to "wait for a completion
notification" from a backgrounded watcher of the multi-minute gate — in-process teammate
subagents are never re-woken by background-task completion, so waiting equals permanent idle
(`contest-loop-3` 08:47: backgrounded `pgrep` watcher, "I'll wait…", dead; `contest-loop-3b`
08:54: foreground wait auto-backgrounded at the 120 s Bash ceiling, same death; loop 2's
late-report was the quiet variant). Same class as the PPR 2-minute-ceiling lesson. **Cause B:**
fencing a stalled executor never killed its process tree, so gate runs piled up — three
concurrent `run_local_gate.sh` trees (a 15 m 51 s orphaned `--targeted` still driving
`xcodebuild`, a fenced `--quick` chain, and the live inline gate) contending for `.build`/
DerivedData, slowing every successive gate and poisoning its evidence. In-run remediation by the
operator session: all three trees killed (one needed a second pass — the group kill re-parented
`run_local_gate.sh` into a new PGID, the exact kill-tree failure PPR hardening documented), its
own contaminated gate deliberately discarded, single-flight re-run inline; working tree survived
byte-for-byte per the checkpoint. Fixes owed to `provider-adapters.md` claude_code guidance:
(a) an executor must never end its turn awaiting a background notification — poll with repeated
short foreground checks, or run gates where wake-on-completion works (inline/main); (b) fencing
rule — kill the replaced executor's process tree (PGID + re-parent sweep) before spawning the
successor; (c) single-flight gate guard — check for a running gate before starting one, using a
bracket-anchored pattern (`pgrep -f '[r]un_local_gate'`): a bare `pgrep -f` matches the checking
shell's own command line and self-reports a false positive (BenchHype `cli-corrections.md`
Rule 7 documents that exact trap).

**Status: SHIPPED (`3d36866`)** — W4 landed the async-join recipe, the spawn precondition /
single-writer lease, kill-tree fencing with a re-parent sweep, and the bracket-anchored
single-flight guard, closing (a)-(c) above.

### Cleared during the run

The app-target coverage risk on loop 3's visibility narrowing was checked empirically: all 8
narrowed declaration names grepped against `BenchHype/`, `tools/`, `scripts/` — zero Swift
references (one shell-script name hit in `run_sim_snapshots.sh`, not compiled code). The
`--quick`-doesn't-build-the-app gap itself remains real and belongs in the handoff's coverage
disclosure.

### Remediation outcomes — nine-wave plan (2026-08-25)

The two-cause diagnosis above (async-join stall, fencing-without-kill-tree) became a nine-wave
plan (`/Users/pl/.claude/plans/lets-plan-the-fix-robust-avalanche.md`), executed by sequential
Sonnet subagents with the main session verifying rather than editing. All nine waves landed.

| Wave | Commit | Outcome |
|---|---|---|
| W1 | `e252a6a` | Re-pinned `skill_step3_section_sha256`; third carry-note. Healed a pre-existing RED. |
| W2 | `6eabb7c` | Paired-arm provenance: new top-level `material_hashes_frozen_at` (`d4d203e…`) verifies a completed study against its freeze commit instead of live disk; `prereg_sha256` proven byte-stable before and after. Healed the second pre-existing RED. |
| W3 | `5f74abc` | `validate-artifact.py --gates` selector (post-filter of `run_checks()` by `Issue.rule`; unknown id → exit 2). Known limit: G1/G2 are prose-only, so selecting them is vacuous. |
| W4 | `3d36866` | claude_code adapter hardening: async-join recipe, spawn precondition/single-writer lease, kill-tree fencing with re-parent sweep, bracket-anchored single-flight guard; helper-count re-derivation rule. |
| W5 | `259ecce` | Step-0 seed field set, `--reset` now deletes `CURRENT_REVIEW.md`, discovery dotted-path wording, pin-is-a-floor rule, `working_tree_dirty_paths` emission retired. |
| W6 | `1609cd6` | Schema truth-ups + `execution_evidence_skip_reason` prose half; `CONTRACT_REJECTED` named on the rejected row. |
| — | `083f6b3` | G47 two-branch clarification + the item-14 micro-test record in the behavioral ledger. |
| W7 | `7b6498f` | Step-3 sub-step-0 clean-tree assertion, skip-reason tail, G47 ordering fixed in both SKILL.md and validation.md together, judge-provenance occurrence stamps; `skill_md` ceiling 12,500 → 13,000 (measured 12,514, margin 486); fourth exec-replay carry-note. |
| W7.5 | `1bd372b` | Re-pinned `reviewer_prompt_sha256` after W6's prose edit; staleness recorded. |
| W8 | `a6dc71d` | G47 null branch enforced, epoch-scoped: new ruleset epoch `attestation_skip` at rev `1609cd6` (the two-commit prose-then-gate shape). Plus an unconditional shape rule — a skip reason alongside non-null evidence is always an Issue. |

**Item 14's diff-derived hard gate was measured and declined — restraint, not a gap.** The
proposed Honesty-check cue for a null `risk_boundary_evidence` on isolation/visibility diffs was
micro-tested against a no-guidance control: 20 `spawn_agent` calls, five reps per arm per fixture.
The control already caught the risk-bearing case 5/5 (rejected at Regression); the treatment
produced 5/5 non-approved but split routing in only 2/5, adding zero correctness lift, with zero
false positives on the benign arm. Per the micro-test rule the cue was not shipped — the existing
Regression risk-boundary check remains the single source for this family. Full record:
`contest-refactor/docs/behavioral-validation-ledger.md`. This continues the project's established
measured-restraint pattern; file it alongside the other levers that measured flat and were parked.

**A generalizable process defect surfaced along the way.** W6 edited
`references/implementation-reviewer.md` and shipped with `_reviewer_baseline_selftest.py` RED,
because that wave's verification battery only ran the selftests it believed it had touched. The
red sat on `main` until a later wave swept the whole `scripts/_*_selftest.py` set and found it.
The rule this yields: frozen-hash selftests pin files by content hash, so a prose edit anywhere
can break one that has nothing to do with the edited feature — every wave's verification battery
must sweep *all* `_*_selftest.py` files, never a curated subset believed relevant.

**Parked, with sharper reasons than when the plan was written:**

- Item-14 hard gate (diff-derived G33) — no longer "awaiting a false-positive rate": measured,
  zero lift over control.
- A2 gate on `checkpoint_started_at` — report-only field shipped; a gate needs an epoch and buys
  little until a wrong-order incident recurs with the witness present.
- `--stage` presets — `--gates` covers every call site (YAGNI).
- Exec-replay K=5 re-measure — now four carry-notes deep (W1 and W7 each added one), well past
  the manifest's own two-carries trigger. This is the most overdue item on the board.
- Registry cross-run judge gate — stamps only; no gate keys on them in v1.

**End state.** Both previously-red frozen-hash selftests healed (W1, W2). A full independent
sweep at `a6dc71d` verified 79 selftests, 102 fixtures, `validate-repo.py`, and `ruff` all green.

