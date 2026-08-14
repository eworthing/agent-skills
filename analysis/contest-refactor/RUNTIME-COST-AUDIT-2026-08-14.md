# Runtime-Cost Audit — why contest-refactor runs got slow and expensive

**Date**: 2026-08-14 (**rev 3** — corrected after two peer-review rounds)
**Snapshot**: repo HEAD `c6b8175`
**Peer review**: codex `gpt-5.6-sol` effort `xhigh`. Round 1 → `REVISE` (6 blocking); round 2 → `REVISE` (5 blocking, narrowed; all rev-2 arithmetic independently reproduced by the reviewer). Every correction below was re-verified against the repo before adoption — including two places where the reviewer's own figures did not reconcile. See [Review corrections](#review-corrections).
**Extends**: [TOKEN-USAGE-AUDIT.md](TOKEN-USAGE-AUDIT.md) (2026-06-26), whose Lever 4 is **partly executed** (A3 Move A `432f138`, Move B `b33e7ec`).
**Status**: findings validated. **G43 fix and Lever E shipped 2026-08-14** (see [Shipped](#shipped)); Levers A / B / C / D / F remain proposed.

---

## Accounting model (stated once, used throughout)

All token figures are **de-duplicated unique loads per loop**, matching `loaded_set("loop")` in `scripts/token-budget.py:80`, which collapses files appearing in several steps via `seen.setdefault`. A file listed at both Step 1 emit and Step 3 is therefore counted **once** per loop.

This matters: rev 1 claimed a saving of "10,475 × 2 loads" against a baseline that already counted one load, double-counting the headline by 2×. **Physical reads may exceed unique loads; if a future analysis counts physical reads, it must re-baseline the denominator too.** Reviewer-sidecar costs are a *separate population* and are never expressed as a percentage of the loop-reference projection.

**Unique loads are a proxy, not billed cost — and not a bound in either direction.** Actual billing follows `cost ≈ per-message resident context × messages` ([TOKEN-USAGE-AUDIT.md:292](TOKEN-USAGE-AUDIT.md)): each loop subagent is a 28–85-message conversation re-billing its context every message, and references average ~25% of per-message context across ~241 loop messages ([:311](TOKEN-USAGE-AUDIT.md)).

That does **not** make the percentages below lower bounds. The files Levers A and E touch are **deliberately deferred**: `SKILL.md:132` instructs that the emit-time references are *"not read until step 5 (emit); do not pre-load them during this investigation, to keep the per-message context lean."* `validation.md` therefore rides only post-emit messages, fewer than the average reference. The billed denominator also includes target-source context and output, which the 852,247 figure excludes.

**Treat 3.7% / 7.3% / 10.0% strictly as gross unique-instruction deltas with no upper- or lower-bound interpretation**, pending a per-route model of read ordinal and subsequent-message residency. *(Rev 3 called them lower bounds — an overcorrection to round 2's finding that trims multiply. Both the "orthogonal" framing of rev 2 and the "lower bound" framing of rev 3 were wrong.)*

```
per-loop fixed instruction reload :    84,197 tok   (unique loads, apple lens)
SKILL.md trigger extra            :    10,277 tok
RUN TOTAL projection (10 loops)   :   852,247 tok
```

Instruction text only — before target-source reads, reviewer sidecars, or output. The 2026-06-26 measurement was **61,100 tok/loop**: **+38% in six weeks**.

---

## Method (reproducible)

| Claim | Command |
|---|---|
| per-loop / per-run figures | `python3 scripts/token-budget.py --project --loops 10 --json -` (assert `method == "tiktoken/cl100k_base"`) |
| per-step load sets | `for s in step1 step1_emit step2 step3 loop; do python3 scripts/token-budget.py --loaded-set "$s"; done` |
| growth | `git ls-tree -r --long <sha> -- contest-refactor/{SKILL.md,references,canon}` |
| mechanized gate set | `grep -oE 'def check_g[0-9]+\w*' scripts/_artifact*.py scripts/validate-artifact.py`, cross-checked against driver calls |
| gate-prose split | split `validation.md` on `^- \[ \] \*\*G\d+`, tiktoken each section |
| validator behaviour | `python3 scripts/validate-artifact.py evals/fixtures/<f> --mode strict` |
| full harness | `python3 scripts/validate-fixtures.py evals/fixtures` (80 fixtures — the positional arg is required) |
| self-test sweep | `rc=0; for f in scripts/*_selftest.py; do python3 "$f" >/dev/null || { echo "FAIL $f"; rc=1; }; done; exit $rc` — 38 files, all must exit 0 |

**Working directory.** Every command above except the `git ls-tree` row runs from `contest-refactor/` (prefix with `cd contest-refactor &&`). The `git ls-tree -- contest-refactor/...` command runs from the repository root.

**Tokenizer hard-gate required.** `token-budget.py` silently falls back to a byte/word heuristic when tiktoken is unimportable — in a restricted environment the same command returned `89,690 / 907,566` while exiting 0. Any figure quoted from it must be confirmed via `--json` with `method == "tiktoken/cl100k_base"`. Adding `--require-tiktoken` is a prerequisite to calling these numbers reproducible.

---

## Finding 1 — growth is monotonic, but the rev-1 wording was wrong

Runtime-loaded surface (`SKILL.md` + `references/` + `canon/`):

| Snapshot | Bytes |
|---|---:|
| 45 days ago (`b3ed848`) | 389,642 |
| 30 days ago | 433,385 |
| 7 days ago | 484,626 |
| **HEAD** | **511,474** |

Of the HEAD total, **17,432 bytes is `canon/` — TOML data read by validators, not by the model.** Reasoning-context bytes are ~494,042. `canon/` growth is nearly free at runtime and should not be conflated with prose growth.

File-level change over the window: **22 grew, 16 unchanged, 5 added, 0 shrank.** Commits touching *this surface*: **44** (91 covers all of `contest-refactor/`).

The accurate claim is **"nothing shrank"**, not "everything grew" — and a deletion pass does exist: `0d2c986` was genuinely net-negative (+66 / −121). What is missing is not the will to delete but a **standing ceiling** that would force it.

## Finding 2 — mechanized ≠ covered: a clause-level partition

`validate-artifact.py` defines and wires 22 `check_g*` functions; all are called by the driver.

Rev 1 partitioned by **function name** and concluded 20 gates were "fully mechanized" (10,475 tok). That partition is too coarse. Probing artifacts that violate gate *prose* while the checker reports no issue shows the Python is materially narrower for **nine** gates:

| Gate | Prose obligation the checker does not cover | Tok |
|---|---|---:|
| G21 | scorecard-only; dry-run/empty paths unprobed | 718 |
| G37 | both-accounts case | 654 |
| G28 | cannot prove per-transition writes, fsync, or process-start freshness | 516 |
| G19 | missing `skill_rev` | 501 |
| G40 | docstring: *"Presence and shape only — deliberately NOT compared against a prior loop's discovery… Carrying the object forward faithfully is rule #32's obligation, not the gate's"* | 464 |
| G27 | omits the build-flake half | 434 |
| G38 | narrower than prose | 424 |
| G22 | inspects existing git history; **cannot validate a pending commit subject**, and skips entirely without project config | 339 |
| G31 | no-snapshot / bogus-hash case | 176 |
| | **Total that must stay on the read path** | **4,226** |

Corrected partition of `validation.md` (16,385 tok, 43 sections):

| Category | Tok | Gates |
|---|---:|---:|
| Candidate for carve (pending clause audit) | **6,249** | 11 — G18 G30 G32 G33 G34 G35 G36 G39 G41 G42 G43 |
| Materially narrower than prose — **stays** | 4,226 | 9 |
| Self-declared partial (G5, G16) — **stays** | 773 | 2 |
| Judgment-only — **stays** | 4,637 | 21 |
| Preamble/other | 500 | — |

`validate-artifact.py` is **not invoked anywhere in the runtime protocol** — it appears only in SKILL.md's "See Also" (line 291). That remains the core waste. But the recoverable prose is **6,249 tok/loop, not 10,475**, and the 11 survivors still need a clause-by-clause audit with negative fixtures before any is reclassified as mechanical.

## Finding 3 — the validator's diagnostics are more actionable than the prose

```
FAIL [G37] HALT_LOOP_CAP dimension 'data_flow' score=8.5 < 9.5 is unaccounted:
  no backlog[] item's score_impact names it ... file it to the backlog, tag the
  structural blocker, or promote to 9.5-accepted
```

Gate, field, actual value, remedy — instance-specific where the prose is generic. `strict` → exit 1 on failure, 0 on clean; `advisory` → always 0. This is why the direction is right even though the prize is smaller than rev 1 claimed.

## Finding 4 — the validator cannot be called as rev 1 proposed

Rev 1 said "add `validate-artifact.py --mode strict` at Step 1 emit and Step 3." **Step 1 is impossible as written.** `check_g18_review_history_append` (`_artifact_history.py:268`) requires `len(loops) == current_review.loop`, but history is appended at **Step 3 sub-step 9** (`SKILL.md:211`). A normal pre-Step-3 state yields:

```
FAIL [G18] REVIEW_HISTORY.json has 1 loops[] entries; current_review.loop == 2 requires exactly 2 entries
FAIL [G18] REVIEW_HISTORY.json.loops[-1] must equal CURRENT_REVIEW.json verbatim
```

G22 has the mirror problem: it reads existing git history and cannot validate a **pending** commit subject before `git commit`.

**A fourth gap: main-owned challenge transitions.** After the loop commits the candidate (`halt_success_challenge: null`), **main** mutates and commits again on each outcome (`SKILL.md:140`): **held** → record challenge, promote to terminal `HALT_SUCCESS`, commit; **broke** → commit a CONTINUE transition; **unavailable** → commit `HALT_STAGNATION`/`verification_blocked`. A `postcommit` phase would detect malformed G32/G34/G35 state only *after* the terminal commit is already in history. **G32 alone is 1,218 tok — 19% of Lever A's scope — and lives entirely inside this uncovered transition.**

**Prerequisite:** a phase-aware validator with **five** phases — `step1-post-write | step3-prearchive | postarchive | postchallenge-precommit | postcommit` — each declaring its applicable gate set, plus commit-draft input for G22 and for every main-owned transition commit (held / broke / unavailable / v5 panel aggregate). Each phase needs negative fixtures and a defined failure-recovery route. Without this there is no valid insertion point.

## Finding 5 — wall-clock: sequential chain, with parallel exceptions

Per 10-loop run, **conditional on every loop reaching Step 3**:

- 10 loop subagents (cold context, full reference reload)
- 10–20 implementation-reviewer subagents (≤2/loop; 90 s timeout, 180 s on transient retry)
- 1 challenger, **or** a v5 staged panel where member 1 runs first and **members 2–3 launch in parallel** on a `held` verdict (`halt-verifier.md:70`)

The loop→reviewer chain is sequential; the panel tail and optional helpers are not. HALT/dry-run loops skip the reviewer, so the ≈21–31 figure is an upper bound, not a constant.

## Finding 6 — G43 is the largest gate and may never have run

Largest gate section (1,777 tok — **28.4% of Lever A's scope**). From loop 4, a dimension answering `clean` three loops running must carry a structurally novel `proposed_fix`. Rationale cites 55 production loops and a real decay pattern; it deliberately prevents early convergence, which is a legitimate cost and an owner tradeoff.

**But it is not a reliable baseline for current behavior.** `SKILL.md:133` instructs "run hard gates (**full G1–G42** as applicable per loop type)" and `SKILL.md:236` repeats "Hard gates **G1–G42** … apply across all halt paths" — while `canon/validation-gates.toml` declares **G43**, added 2026-08-06 (`9346822`). Since `validate-artifact.py` is never invoked at runtime either, **G43 is currently outside the instructed range and effectively ambiguous or skipped.**

This is a live defect independent of any cost work, and it is a precondition for Lever A: 28.4% of the carve's value is a gate whose present enforcement is unverified, so "the validator preserves enforcement" cannot be claimed for it.

**Fix**: make the range canon-derived (or say "all gates"), pin it with a `validate-repo.py` check that the instructed range matches `canon/validation-gates.toml`, and re-baseline G43's behavior before crediting it in any carve.

## Finding 7 — RESOLVED: per-message rebilling is already measured

This needed no new instrumentation. The prior audit measured it on a real 4-loop run (Codex-validated) and the numbers settle every open question here.

**Cost ≈ per-message resident context × messages.** Each loop is a 28–85-message subagent re-billing its full ~250k context every message. One run: ~241 unique assistant messages, 289 tool calls (148 Bash, 90 Read), ~5.3M *fresh* tokens. Cache hit rate is 93.9% — **caching already works; it is not the leak.**

Ranked by measured impact ([TOKEN-USAGE-AUDIT.md § Findings](TOKEN-USAGE-AUDIT.md)):

| # | Lever | Measured weight |
|---|---|---|
| 1 | **Fewer assistant messages per loop subagent** | 20% fewer messages ≈ 20% off the 82.6%-of-cost input side |
| 2 | **Read→extract→drop instead of holding files resident** | 90 Reads pulled ~336k tok of source; 27–50 KB files re-bill every subsequent message |
| 3 | Broad reference/context trims | references are ~25% of per-message context; worth ~10%+ |
| 4 | Cross-loop re-reads | ~5.0M cache-write (36% of cost) re-reading the same source each loop; bounded by blind-critic independence |

Loop subagents are **66.8%** of cost-weighted total (~70% of all cache-read); reviewer sidecars are 3.6%.

**What this means for the levers here.** E (shipped) and A sit on axis 3 — the right axis, modestly weighted. B sits on the 3.6% sidecar and is dead. The unexploited leverage is axes 1–2, which are **behavioral** (how the loop reads and how often it messages), not structural (what the skill file contains). No document edit reaches them; they are a change to loop conduct.

---

## Second pass — hypotheses checked and rejected

| Hypothesis | Verdict |
|---|---|
| Narrative "production motivation" prose bloats references | **No** — 542 tok across 10 sentences. My paragraph-level first estimate (12,105) was 22× overstated. |
| Cross-file duplication | **No** — Lever 2, declined at ~0.1–0.3% |
| Concision rewriting of loop prose | **No** — Lever 3, ~1% for a 90–126-run sweep |
| Quadratic history re-read | **No** — tail-2 loops + compact registry, O(1) in loop count |
| `evals/` (359 MB) costs run tokens | **No** — tier-3, never in reasoning context |
| Description summarizes workflow (SDO risk) | **Minor** — leads with rubric mechanics; low impact, slash-invoked |

**"Just trim the prose" is measurably wrong.** The cost is structural — what loads, how often, and how many messages rebill it.

---

## Shipped

Both landed with the full harness green (`validate-repo` OK, 80 fixtures, 38 self-tests, eval-skill 92% unchanged) and were measured **net of the pointer lines each added** — gross deletion minus add-back, per round-2 N1.

**1. G43 range fix + freshness pin.** `SKILL.md:133,236` instructed "full G1–G42" while canon declared G43, leaving the largest gate (1,777 tok) outside the range the loop is told to run. Both sites now say *"every gate in `canon/validation-gates.toml`"* — canon-derived, so it cannot go stale again. Pinned by a new `check_gate_range_freshness` in `validate-repo.py`, which fails any hardcoded `G1–G<n>` whose upper bound ≠ canon's highest. **RED/GREEN verified**: reintroducing the original text reproduces `[gate-range-freshness] SKILL.md: stale gate range 'G1-G42' but canon declares G43 as highest`.

**2. Lever E — provenance carve.** All 43 `*Source:*` citations moved verbatim from `validation.md` to a new cold `references/validation-sources.md`, keyed by gate id. No normative clause moved; no rule reworded. Load-path proof: the new file returns **0 occurrences in every load set** (`step1`, `step1_emit`, `step2`, `step3`, `loop`).

| | Before | After | Net |
|---|---:|---:|---:|
| `validation.md` | 16,385 | 13,209 | −3,176 |
| per-loop fixed reload | 84,197 | **81,124** | **−3,073** |
| run projection (10 loops) | 852,247 | **821,580** | **−30,667 (3.6%)** |

The per-loop net (−3,073) is smaller than the gross carve (−3,176) because a discoverability pointer was added to `validation.md` and to SKILL.md's See Also. Per the accounting model, 3.6% is a **gross unique-instruction delta, not a billed-cost saving**.

## Ranked levers

Risk-adjusted. All savings are **unique-load proxy** tokens over a 10-loop run against the 852,247 projection — lower bounds; billed value is larger because the removed text rides ~241 messages (Finding 7). All are **gross deletions**: net savings are lower by the hot-path pointer, validator invocation commands, and failure-routing prose each lever must add back, and must be recomputed from the final diff.

| | Change | Saving | % | Risk |
|---|---|---:|---:|---|
| **E** | Move the 43 `*Source:*` provenance lines to a cold reference; **retain every normative clause** | 31,760 | 3.7% | **Low** — no rule becomes reactive |
| **A** | Carve the 11 audited-clean gates' prose to `validation-mechanized.md`, routed on validator failure; requires phase-aware validator + `validate-repo.py` update | ≤62,490 | ≤7.3% | **Medium** |
| ~~**D**~~ | ~~CI ceiling on per-loop reload~~ — **shipped** as `token-budget.py --check` | prevents recurrence | — | — |
| **F** | Fewer assistant messages + read→extract→drop inside loop subagents | **the largest measured lever** | — | Behavioral |
| ~~**B**~~ | ~~Reviewer reference-trim~~ — **killed**: measured at **<0.1% of real cost** | — | — | — |

**A + E = 84,960 tok (10.0% proxy)** — *not* 94,250: **929 tokens of provenance lines sit inside the 11 gates A already carves**, and are counted once.

**Phase applicability of Lever A's 6,249 tok** (by each gate's own label — this corrects rev 2, which wrongly called Step 3 "the phase the change most affects"):

| Phase | Gates | Tok | Share |
|---|---|---:|---:|
| Step-1 pre-emit | G30 G33 G34 G35 G36 G39 G42 G43 | 4,377 | 70% |
| Main-owned terminal challenge | G32 | 1,218 | 19% |
| Step-3 / pre-commit | G18 G41 | 654 | 10% |

The dominant phase is **Step-1 pre-emit**, which a dry-run *does* reach. The genuinely untested phases are the **main-owned challenge transitions** (Finding 4) — not Step 3 generally. *(Round 2 reported a "7 sections / 4,791 tok Step-1-only" split; that subset is `G30 G32 G34 G35 G36 G42 G43`, which includes the main-owned G32 and excludes the pre-emit G33/G39, so it does not reconcile with the gates' own labels. Its directional point — Step-1 dominates — is correct and adopted.)*

### Lever A is an enforcement-routing change, not a verbatim carve

Rev 1 called A "byte-identical to A1a/A2/A3." **That analogy is wrong.** A1a kept its carved file on the emit/Step-3 matrix; A3 kept rules loaded by the Critic while excluding a *different consumer*. Both relocated text that stayed proactively loaded for its consumer. Lever A instead converts **proactive instruction into failure-only recovery** — a behavior and enforcement change. Risk is **Medium**, not Low.

Scope A must include, or it is not shippable:

1. **Phase-aware validator** (Finding 4) with per-phase applicable-gate sets and commit-draft validation.
2. **`validate-repo.py` updates** — it hard-codes `validation.md` for G30/G31 presence (`:196`), the G3 Evidence-Chain cross-reference (`:214`), and gate sequencing (`:263`). A carve breaks the repo's hard validation contract unless these operate over **both** normative files.
3. **`token-budget.py` load-set goldens + `_token_budget_selftest.py`** updated.
4. **Clause-level coverage matrix** for the 11 candidates, with negative fixtures proving each clause is enforced before its prose leaves the read path.
5. **Behavioral experiment, pre-registered.** The control is **current proactive prose**, paired against carve-plus-validator as treatment (a no-guidance arm is optional calibration only — it answers a different question). ≥5 reps per arm across CONTINUE, dry-run, cap, stagnation, success-candidate, reviewer-reject, malformed-artifact, **and the three challenger transitions** (held / broke / unavailable). Pass criteria fixed in advance: first-pass artifact validity, correction count to reach valid, final routing equivalence, diff/commit equivalence, validator-failure rate, cost, and wall-clock.
6. **Rollback criteria** and telemetry on validator-failure frequency.
7. **G43 re-baseline first** (Finding 6) — 28.4% of the scope is a gate whose current enforcement is unverified.

### Lever D — shipped (was: needs one source of truth)

As specified it would not catch what it exists to catch. `token-budget.py` and `_token_budget_selftest.py` **each hardcode their own copy of the per-step load lists**; neither derives them from `SKILL.md`'s Reference Load Matrix. Both can stay green while the matrix drifts — the exact failure mode the ceiling is meant to prevent. `token-budget.py:58` also carries a stale comment claiming the conditional `halt-handoff.md` is "counted" at Step-1 emit, while the adjacent list omits it — so the script's own documentation disagrees with its data.

**Shipped** as `token-budget.py --check`, which parses SKILL.md's Load Matrix directly rather than trusting either hardcoded copy. Two guards, deliberately independent so neither is derived from the data it polices:

- **Ceilings** — hand-set numbers (`loop` 82,000; `skill_md` 10,600). Growth past them fails, forcing a deliberate bump with a stated reason.
- **`DECLARED_DIVERGENCES`** — every intentional difference between the code's load table and the matrix, each with a reason. Any *undeclared* difference fails, so the table cannot drift from the instructions it models. A conditional file becoming unconditional surfaces here, which is why no separate conditional ceiling was needed.

`--require-tiktoken` exits 2 rather than reporting heuristic numbers as measured (round-3 N6).

Self-tested including negative cases: ceiling breach, undeclared divergence, and a **stale-exemption check** — an entry that is no longer a divergence fails, since a dead exemption silently pre-approves a future real drift. That check caught a bad entry in the table on its first run.

### Lever B is killed, not deferred

Not "needs re-audit" — **measured and immaterial**. The empirical run puts all three reviewer sidecars at **3.6% of cost-weighted total**, and trimming only their `method.md`/`architecture-rubric.md` reads moves **<0.1% of real cost** ([TOKEN-USAGE-AUDIT.md § Findings 5](TOKEN-USAGE-AUDIT.md)). The Step-0 audit agents alone cost more than every reviewer combined. The 55–110k projection was real arithmetic against the wrong denominator: a rounding error on a ~5.3M-fresh-token run. Do not revisit.

### Lever C withdrawn

Rev 3 listed "default `--cap` 10 → 5" as a lever. It is not one: `--cap N` is already a user flag, so nothing is unlocked by moving the default, and the empirical run states plainly that **"loop count was not the problem this run (4 loops, clean convergence)."** Lowering the default would truncate runs for users who never pass the flag, buying nothing. Withdrawn.

---

## Review corrections

### Round 1 (rev 1 → rev 2)

| ID | Correction | Verified by |
|---|---|---|
| B1 | 9 gates materially narrower than prose; carve scope 10,475 → 6,249 tok | `check_g40` docstring; per-gate tiktoken = 4,226 exactly |
| B2 | Saving double-counted; single accounting model adopted | `token-budget.py:80` `seen.setdefault` |
| B3 | Step-1 strict call impossible; phase-aware validator required | `_artifact_history.py:268` vs `SKILL.md:211` |
| B4 | A reclassified Low → Medium, enforcement-routing | precedent comparison |
| B5 | Lever B baseline stale; unquantified pending re-audit | `432f138`, `b33e7ec` |
| B6 | `validate-repo.py` updates added to scope | `validate-repo.py:46,196,214,263` |
| N1 | 22 grew / 16 unchanged / 5 added / 0 shrank; 44 commits; `0d2c986` deletion pass | git |
| N2 | `canon/` (17,432 B) separated from reasoning-context bytes | `cat canon/* \| wc -c` |
| N3 | Finding 7 added — per-message rebilling, 241 messages | TOKEN-USAGE-AUDIT.md |
| N4 | Spawn count qualified; v5 members 2–3 parallel | `halt-verifier.md:70` |
| N5 | Lever E added, ranked above A on risk | 43 lines / 3,176 tok |
| N6 | Tokenizer hard-gate requirement added | heuristic fallback reproduced |
| N7 | 38 self-tests (not 12); 80 fixtures confirmed | `ls scripts/*_selftest.py` |

### Round 2 (rev 2 → rev 3)

Reviewer independently reproduced every rev-2 figure: 6,249 / 4,226 / 3,176 / 929 overlap / 84,960, plus growth, canon size, commit counts, 80 fixtures, 38 self-tests.

| ID | Correction | Verified by |
|---|---|---|
| B1 | Fifth validator phase `postchallenge-precommit` added for main-owned held/broke/unavailable + v5 panel transitions; G32 (1,218 tok, 19% of scope) lives entirely there | `SKILL.md:140` |
| B2 | G43 is outside the instructed gate range and may never have run; re-baseline is a precondition for Lever A | `SKILL.md:133,236` say "G1–G42"; `canon/validation-gates.toml` declares G43 |
| B3 | **Finding 7 inverted.** References ride ~241 messages, so trims *multiply* rather than compete with message-count work; percentages relabelled unique-load proxies | [TOKEN-USAGE-AUDIT.md:292,311](TOKEN-USAGE-AUDIT.md) |
| B4 | Paired control = current prose (not no-guidance); pre-registered criteria; challenger transitions added. Phase applicability corrected: **4,377 pre-emit / 1,218 terminal / 654 Step-3** — rev 2's "Step 3 is most affected" retracted | per-gate labels in `validation.md` |
| B5 | Lever D re-scoped to a manifest-derived single source of truth + separate fixed/conditional ceilings | `token-budget.py` and `_token_budget_selftest.py` each hardcode the step lists |
| N1 | Savings relabelled gross deletions / upper bounds pending final diff | — |
| N2 | Working directories stated in Method | — |
| N3 | Executable self-test sweep command given | — |

**Not adopted as stated:** round 2's "7 sections / 4,791 tok are Step-1-only". That subset (`G30 G32 G34 G35 G36 G42 G43`) includes the main-owned G32 and omits the pre-emit G33/G39, so it does not reconcile with the gates' own phase labels. The directional claim — Step-1 pre-emit dominates — is correct and adopted with the label-derived split above.

---

## Open risks

1. **Billed savings remain unsized for the shipped work.** Finding 7 gives the cost model and the ranking, but no per-run measurement was taken before/after Lever E. The 3.6% figure stays a gross unique-instruction delta.
2. **The 11 candidate gates are unaudited at clause level.** 6,249 tok is a ceiling; the true figure is lower by however much of those clauses the Python doesn't reach.
3. **n=0 on Lever A's live behaviour**, and its main risk — that the model writes sloppier artifacts knowing a validator will catch them — is behavioral, requiring the 5+ rep experiment, not a static audit.
4. **Loop-count distribution unmeasured.** 10 loops is a cap, not an observed mean; runs of 15 are referenced in gate rationales.
6. **G43's current enforcement is unverified** — 28.4% of Lever A's scope rests on a gate outside the instructed range (Finding 6).

---

## Recommendation

**Shipped:** the G43 fix, Lever E, and Lever D. **Withdrawn:** Lever C (a flag that already exists). **Killed:** Lever B (<0.1% of real cost).

**Do next, in order:**

1. **Lever F — the largest measured lever, and the only untouched one.** Axes 1–2 of Finding 7: fewer assistant messages per loop subagent, and read→extract→drop instead of holding 27–50 KB source files resident across a whole loop. Loop subagents are 66.8% of cost-weighted total. This is a change to how the loop *conducts* itself, so it belongs in `method.md` / lens read-discipline, not in another carve — and per repo convention it needs a micro-test against a control before shipping.
2. **Lever A — only if F leaves it worth the scope.** Three reviews shrank its value while growing its prerequisites; on the measured cost model it sits on axis 3, the same modestly-weighted axis as the E carve that just shipped for 3.6%. The five-phase validator, gate × phase × state matrix, and pre-registered experiment are a large bill for that axis. Default to not doing it.
