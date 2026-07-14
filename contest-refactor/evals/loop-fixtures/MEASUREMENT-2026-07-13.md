# Layer-4 measurement — lens-efficiency.md always-included promotion (2026-07-13)

RED→GREEN loop-replay measurement for the promotion of `lens-efficiency.md` from
opt-in (`--force-lens efficiency`) to always-included, plus the new D3/D4 detectors.
Precedent format: [`evals/repo-map-fixtures/MEASUREMENT-2026-06-30.md`](../repo-map-fixtures/MEASUREMENT-2026-06-30.md).

## Question

Does the promotion close a real detection gap? Concretely: does a full
contest-refactor loop **miss** an efficiency defect before the promotion (efficiency
ignore-listed) and **catch** it after (efficiency lens always loaded), without
over-flagging a matched near-miss control?

## Method

- **Vehicle:** the committed Layer-4 harness. `loop_replay_materialize.py` copies a
  fixture `codebase/` into a throwaway git repo; a host-dispatched loop runs the
  verbatim `references/trust-model.md` § Loop Isolation template; `loop_replay_grade.py`
  grades the emitted `CURRENT_REVIEW.json`.
- **Model:** default loop model (`claude-sonnet-4-6` tier), n=1 per arm.
- **Blind dispatch:** the loop's prompt carried only the CWD (materialized workdir) and
  the verbatim template — never `smell`, `primary_file`, expected status, or remedy.
  The Step-0 Discovery section in each `CURRENT_REVIEW.md` was host-written from the
  materialized repository's observable files only. Materializer stdout (which prints the
  planted smell) was redirected to a log the prompt never included.
- **RED vs GREEN skill state:** RED read the **pre-promotion** skill from a detached
  worktree at merge commit `26297a4` (where `lens-efficiency.md` is opt-in and not
  loaded by default). GREEN read the **promoted** skill at `27e5071` (always-included).
  The fixture `codebase/` was byte-identical across arms.

## Results

### D1 — recomputed-derived-1 (targeted dimension: `simplicity`)  → MEASURED

| Arm | Skill commit | Loop commit | Findings | Grader | Outcome |
|---|---|---|---|---|---|
| RED  | `26297a4` (opt-in) | `e43b781` | 0 (verdict "Strong contender", `simplicity`=10, `HALT_SUCCESS_candidate`) | FAIL (no finding cites `primary_file`) | **miss** |
| GREEN | `27e5071` (always-on) | `1c2ea2a` | 1 — F1 "render() recomputes statistics three times per call", **Noticeable weakness**, `simplicity` | PASS (all required invariants) | **catch** |

- **Detection lift:** the pre-promotion loop rated the fixture a perfect `simplicity`=10
  and found nothing — the D1 recomputed-derived-value pattern was entirely out of scope
  (efficiency ignore-listed). The promoted loop flagged it as Priority-1, fixed it
  subtractively (evaluate `statistics` once in `render()`), kept output byte-identical,
  and passed `swift test` 7/7.
- **Restraint held:** in the GREEN arm the loop explicitly recognized `UnitFormatter`
  (the fixture's near-miss control — a stored O(1) read, not a recomputed derivation) as
  the intended negative control and left it untouched. Zero over-flags.
- **Corroboration:** an earlier probe against a pre-dedup version of this fixture
  (pre-promotion, no efficiency lens) independently reached the same RED behavior —
  it did not flag the D1 pattern, explicitly citing the Ignore-list — while surfacing a
  since-fixed self-inflicted duplication (see fixture-hardening note below).

### D2 / D3 / D4 — sequential-io-1, startup-blocking-1, closure-retention-1  → NOT MEASURED (deferred)

Fixtures are built, hardened to pristine-except-the-planted-defect, and green under
`swift test` (each with a tested near-miss restraint control), but their RED→GREEN loop
quads were **not** run this session. They remain `baseline_unmeasured` in
`loop_replay_baseline.json`. Reason: each full contest-refactor loop costs ~200–300k
tokens and ~13–28 minutes; an account monthly spend limit was hit mid-session; and
reaching a clean, grader-consistent pair for D1 alone consumed several loops of
fixture-cleanliness iteration (below). D1 is the representative pair; the remaining three
follow the identical protocol.

**To complete them** (per detector `<id>` ∈ {sequential-io-1, startup-blocking-1, closure-retention-1}):

```
SP=<scratchpad>
# RED (pre-promotion skill): worktree at the last opt-in commit, e.g. 26297a4
git worktree add --detach "$SP/skill-pre-promotion" 26297a4
python3 contest-refactor/scripts/loop_replay_materialize.py <id> "$SP/lr-<id>-red" >"$SP/<id>-red.log" 2>&1
#   host-write CURRENT_REVIEW.md Discovery (lenses WITHOUT efficiency) from the materialized files
#   dispatch ONE loop reading the worktree's contest-refactor/SKILL.md; then:
python3 contest-refactor/scripts/loop_replay_grade.py <id> "$SP/lr-<id>-red"   # expect FAIL = miss
# GREEN (promoted skill = current HEAD): materialize fresh, Discovery lenses INCLUDING efficiency,
#   dispatch one loop reading the working-tree SKILL.md; then grade — expect PASS = catch.
```

Record each arm in `loop_replay_baseline.json` under `baseline_observed.arms.{red,green}`
and flip the fixture to `measured` (schema in the manifest `prereg.arm_schema`).

## Fixture-hardening note (why D1 took several loops)

The first RED probe against `recomputed-derived-1` exposed that the fixtures were not
pristine: the loop's Priority-1 finding was an unintended `peak = 0.0` correctness bug
(wrong on all-negative samples), and separately a "no public interface" finding and a
redundant guard — none of them the planted efficiency defect. Because the grader
identifies the planted finding as the highest-severity finding citing `primary_file` and
cannot tell a correctness finding from an efficiency one, those competing findings would
have false-GREENed the RED arm. The fixtures were hardened to pristine-except-the-planted-defect
(correct code, public API exercised by a thin executable driver so it is neither
"no public interface" nor "unused public", exhaustive tests so no mutation-gap finding
competes, one tested near-miss restraint control). A second probe then surfaced a
self-inflicted duplicate `format` helper in the near-miss control, which was removed. The
D1 pair above is on the resulting final fixture.

## Conclusion

For D1, the promotion produces the intended, grader-verified detection lift — a clean
miss→catch across the opt-in→always-on boundary — with the matched near-miss control
correctly left alone. n=1 (windowed, not statistical). D2/D3/D4 fixtures are ready and
the procedure is above; their quads are deferred to a follow-up run.

## Caveats

- n=1 per cell. This is windowed evidence (does the mechanism fire), not a rate.
- RED and GREEN differ only in the skill commit (opt-in vs always-on); the fixture is
  byte-identical, so the delta isolates the promotion.
- The blind dispatch prevents smell leakage into the loop, but the fixture author
  necessarily knows the answer; the measured subject is the loop, which saw only the
  codebase and host-derived Discovery.

---

## Addendum — D2/D3/D4 arm session (2026-07-13, later same day)

Follow-up session executing the deferred quads. Loop model this session:
`claude-sonnet-5` (the host `sonnet` tier now resolves there; the D1 pair above
recorded `claude-sonnet-4-6`). Within-pair model consistency is what the delta
needs; cross-fixture tiers now differ and are recorded per arm.

### Completed RED arms (graded, artifacts in session scratchpad)

| Fixture | RED skill | Loop commit | Outcome | Grader |
|---|---|---|---|---|
| startup-blocking-1 | `26297a4` (pre-promotion) | `23da7ea` | **miss** — declined the five sequential startup reads, explicitly citing the unloaded efficiency lens; only a Cosmetic finding cites `primary_file` | FAIL on severity-floor only (clean miss signature) |
| closure-retention-1 | `26297a4` (pre-promotion) | `72183cd` | **CATCH** — F1 "Serious deduction" retention leak, fixed with `[weak self]`, restraint held on `cropFrames` | OK (all invariants) |

**closure-retention-1 falsifies its own red_baseline note** ("no other lens
surfaces it"): the base critic catches closure-capture retention as a
state-management defect without any efficiency lens. There is no detection gap
for D4 on this fixture — a RED→GREEN lift is unmeasurable here. Options for the
owner: (a) record the pair as measured-no-gap once a GREEN arm confirms
lens-loaded behavior + restraint, or (b) rebuild the fixture with a subtler
retention shape the base rubric genuinely ignores.

### sequential-io-1: two probes, no clean arm yet

- **Probe 1 (pilot)**: loop missed the planted D2 exactly as predicted (explicitly
  cited the unloaded lens) but the grader **false-GREENed** the arm — a competing
  Serious cancellation-ownership finding cited the same `primary_file` and
  satisfied every invariant. The D1 fixture-hardening failure mode, reproduced.
  → hardening round 1 (`c2bc49a`): cancellation ownership + static
  `collectPages` + duplicate-id pin, plus equivalent hardening for the other two
  fixtures.
- **Probe 2 (RED v2)**: executor died on a connection drop mid-emit and was
  resumed via a host message — the resumed segment ran on the **session model**
  (`claude-fable-5`, recorded honestly as `user_flag`), contaminating the arm.
  Lesson: **never resume a measurement arm; re-dispatch fresh.** The probe also
  surfaced two more competing findings introduced/missed by round 1 (untested
  `collectPages` cancellation check at exactly the Noticeable floor; unused
  `import Foundation`) → hardening round 2 (`223c51e`, lifting the probe's own
  mutation-verified test verbatim).
- **RED v3** (fresh, against `223c51e` fixture): killed by the account monthly
  spend limit before Step 1 completed. No artifact.

### Infrastructure fixed mid-session

- `aef867e`: G19 canon staleness — `provider-adapters.md` + `validate-artifact.py`
  pinned `claude-sonnet-4-6` as the claude_code default while the runtime tier is
  `claude-sonnet-5`. Honest executors failed strict validation; a gate-pleasing
  artifact (canonical string, wrong model) passed. Backwards incentive, fixed.

### Remaining to complete the quads (blocked on spend limit)

All GREEN arms + sequential-io-1 RED v3 died mid-run (no artifacts). Before
paying for full loops, consider [DETECTION-PROBE.md](DETECTION-PROBE.md) — the
detection question costs ~25–40k tokens/rep at Tier 1 or ~100k/arm at Tier 2,
vs ~300k/arm for the full-loop procedure below, which remains the release-gate
(Tier 3) evidence. Procedure unchanged from § "To complete them" above, with
these amendments:

1. sequential-io-1 arms must run against fixture state `223c51e` or later
   (both arms byte-identical — the GREEN probe that ran against round-1 state
   is void).
2. Record `model` per arm as the executor's true runtime model; expect
   `claude-sonnet-5`.
3. On executor death: re-dispatch fresh (same workdir re-materialized);
   never resume.

### Status

The three fixtures targeted this session (sequential-io-1, startup-blocking-1,
closure-retention-1) remain `baseline_unmeasured` in `loop_replay_baseline.json`
— no complete RED+GREEN pair at a single fixture state; `recomputed-derived-1`
(D1) stays `measured` from the earlier session above. The two completed RED arms above are durable evidence for the next
session via this table and the graded invariant output recorded at commit time.
(Their raw artifact directories lived in the session scratchpad and were lost
to a temp-dir cleanup later the same day; the dispatching session's task
transcripts retain the loops' full output if reconstruction is ever needed.)
