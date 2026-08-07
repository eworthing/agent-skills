# Plan — Recommendation 1: certification cannot rest on one pass

**Status:** revised across 10 peer-review rounds in two sessions (codex `gpt-5.6-sol`, effort `xhigh`), both run to their round cap, plus a final consistency pass. **Delivery step 1 (v5 reader) is implemented** — `scripts/_artifact_panel.py` (G32 moved out of `_artifact_halt.py` and extended for v5), `_g32_panel_selftest.py` (49 cases), and 20 fixtures (see § Fixtures — as built). **Step 2 (behavioral gate) is implemented and was run live twice on 2026-08-07** — `scripts/_panel_gate_adapter.py` + 18-case selftest, evidence in `evals/panel_gate_results.json`. Run 1 **FAILED** restraint (3/6 members over-flagged; port-seam-split axis); after the challenger prompt gained the **relocation bar** and `C_max` was re-derived, run 2 **PASSED both scenarios** (flag 3/3 broke, restraint 9/9 held) — see § Pre-enforcement gate — as run. **Step 3 (emitter + routing prose + capability manifest) is implemented, 2026-08-07** — `canon/panel-certification.toml` (default-deny, **zero entries recorded**), `scripts/_panel_capability.py` (+18-case selftest), and the routing prose across 12 files — see § Step 3 — as built. All three delivery steps are done; what remains blocked is **recording a capability entry**, not the machinery: the in-session Agent profile cannot stop a member before it crosses `C_max` and does not natively report usage (plan § Cost), and step 3's `halt-verifier.md` edits moved the current digest to `sha256:a79723a9…`, so recording an entry needs an enforcement-capable transport (or an explicit owner amendment to stop-before-crossing) **plus** a fresh gate PASS at the then-current digest. Until then every profile emits v4 — the fail-closed design working as specified.
**Review state:** session 1 settled the design — Tier 1 only, `schema_version` 5, fixed N=3, staged launch, no fixture migration. Session 2 (fresh context) recorded the core certification design as sound from its round 4 on, with remaining findings characterised as "narrow state-machine and schema contradictions rather than missing architectural work." Its final round's fixes (panel-checkpoint resume row above rows 7/7b/8; G32 narrowed to digest *shape*) plus a subsequent self-review pass — which moved panel-checkpoint creation to **panel spawn** so mid-panel member verdicts have somewhere durable to live, added the `normalization` field to the member schema, deduplicated the fixture tables, and swept stale cross-references — have **not** been peer-reviewed.

**Known pattern worth flagging to an implementer:** three separate times this plan assigned G32 a *temporal* invariant it cannot check (`candidate_binding` equality, then its immutability, then `protocol_digest` copy-forward). G32 is a stateless single-artifact validator. Any cross-artifact or across-time guarantee belongs to routing/resume logic with behavioral tests. Expect to re-apply that rule during implementation.
**Source of the requirement:** [`evals/scorecard-coupling/README.md § What this layer licenses`](../evals/scorecard-coupling/README.md), recommendation 1, derived from Layer 6 attempt 5.
**Scope:** Tier 1 (adversarial panel) at `schema_version` 5. Tier 2 (per-dimension panel scoring) and Tier 3 (guard band) are deferred behind measurement gates defined below.

**What this does not do.** Recommendation 1 remains **open at the numeric cut-score level.** Three binary challengers reduce the risk that a single adversarial check misses a defect; they do not add a second scorer. The per-dimension ≥ 9.5 claim still comes from exactly one rater. This is defense-in-depth on the *verdict*, not implementation of the measured recommendation — that is Tier 2, and Tier 2 is gated on recommendation 2.

## What the measurement does and does not license

| quantity | value |
|---|---|
| single-rater SEM (blind) | 0.283 |
| 95% band | ± 0.56 |
| score needed to clear a 9.5 cut by more than measurement error, one rater | **≥ 10.06** — above the scale maximum |
| blind scores ever reaching 9.5, across 81 | 0 |

**Licensed:** G21 certifies `HALT_SUCCESS` per dimension at ≥ 9.5, and a single Critic pass cannot resolve a 9.5 cut at a 0.5-granular scale. A rater would need to observe ≥ 10.06 to clear the cut by more than its own measurement error, which the scale cannot express.

**Not licensed, and deliberately absent from this plan's justification:**

- The ICC-derived panel reliabilities (0.374 blind, 0.802 primed) and the ±0.32 band are properties of the **mean** of three scorecards. They say nothing about a **median** rule and nothing at all about a binary `held`/`broke` verdict. Tier 1 is justified as **adversarial redundancy**, not as scorecard reliability.
- The "0 of 81" figure spans two corpora and several skill revisions. It is evidence that blind absolute level runs low; it is not a population certainty that blind scoring would block everything.

## What certification rests on today

1. The **loop Critic** (one rater) emits `HALT_SUCCESS_candidate` with all nine dimensions ≥ 9.5.
2. Main spawns **one challenger** ([`halt-verifier.md`](../references/halt-verifier.md)) which tries to *break* the verdict and returns a binary `held` / `broke`. It does **not** re-score. It fires at most once per terminal attempt ([`halt-verifier.md:27`](../references/halt-verifier.md)).
3. `held` → promote to terminal `HALT_SUCCESS`. G32 gates the emit.

This plan addresses one thing: **one binary check is not enough evidence to bless a terminal state.**

---

## What ships: Tier 1 at `schema_version` 5

A panel of **exactly 3** challengers, launched **staged**, aggregated **asymmetrically**. Each member does what today's single challenger does — same prompt, same inputs, same `held`/`broke` semantics, same per-member arm diversity. Members are independent: no cross-member coordination, and no member sees another's result.

### Staged launch (one, then two)

1. Launch **member 1**. A **structurally valid break** demotes immediately; members 2 and 3 are never launched.
2. Member 1 exhausting its retry envelope routes `verification_blocked`; members 2 and 3 are never launched.
3. Only on member 1 `held` do **members 2 and 3 launch in parallel**.

This preserves three independent holds behind every certification while paying for one call on early-failure paths.

**Stage-2 join.** Once members 2 and 3 are running, main **awaits both through their real retry envelopes** and persists their actual outcomes. There is no cancellation: a joined member either finishes or exhausts its envelope, and a cancelled-sibling pseudo-outcome would be an invented state that no envelope produces. Routing then applies the precedence table to the completed set of three.

### Routing precedence

Evaluated top-down; first match wins. Precedence matters because more than one row can apply at once.

| # | condition | aggregate | outcome |
|---|---|---|---|
| 0 | any member's break hits an **ambiguous registry match** | `pending` | `HALT_STAGNATION` subtype `user_decision`, `open_question_for_user` non-null |
| 1 | any member returned a **structurally valid** `broke`, **and** the fix needs a CLAUDE-md Stop/Ask decision | `broke` | `HALT_STAGNATION` subtype `user_decision`, `open_question_for_user` non-null |
| 2 | any member returned a **structurally valid** `broke` | `broke` | demote — CONTINUE with the finding as Priority 1 (as today) |
| 3 | fewer than 3 members returned a usable verdict after the retry envelope | `blocked` | `HALT_STAGNATION` subtype `verification_blocked` |
| 4 | all 3 returned `held` | `held` | promote to terminal `HALT_SUCCESS` |

**Row 0 sits above the ordinary break rows deliberately.** An ambiguous match is not a "structurally valid `broke`" — no `stable_id` was resolved — so without its own row it would fall through to row 2 and land on CONTINUE, where raw `break_evidence` is forbidden. It must also outrank a *valid* sibling break: a run that cannot tell which existing finding this is must ask before it writes to the registry, regardless of what another member found. The sibling's valid break is still persisted and is re-resolved after the user answers.

Rows 1–2 outrank row 3: **a valid break beats another member's unavailability.** A break is positive evidence and does not become less true because a sibling timed out. Row 1 preserves the existing Stop/Ask branch at [`halt-verifier.md:105`](../references/halt-verifier.md), which the single-challenger contract already has and which a panel must not silently drop.

A `broke` is **structurally valid** only if, after normalization, it carries a resolved `finding_stable_id` and an `spt` record whose `result` is `"passed"` with a non-empty rationale (both defined below). A break that is still malformed after the member's retry envelope is **normalized to `outcome: "unavailable"`** with `retry_cause: "malformed_json"` — it never persists as a schema-invalid `broke`, and it therefore counts toward row 3, not rows 1–2. Otherwise a garbled response becomes a free demotion.

**Why asymmetric.** A `held` is the *absence* of evidence, and absence from one rater is weak — that is the whole finding. A `broke` carries positive evidence. Majority-voting on breaks would let a real defect be outvoted, inverting the gate's purpose.

---

## Deferred, with reasons

### Tier 2 — per-member per-dimension scorecards. Deferred behind measurement.

Not shipped, and **no divergence threshold ships**. The draft proposed `1.96 × SEM`; that multiplier is derived for the **mean** of three and cannot govern a **median**-of-three comparison.

Before Tier 2 can gate certification, in order:

1. **Offline, zero token cost:** replay the raw six-rater matrices already in the Layer 6 archive to bootstrap the distribution of median-of-three differences.
2. **Then, and only then:** replicate paired blind/primed panels on multiple current-revision corpora with an external calibration set (recommendation 2). Derive a one-sided empirical threshold for `candidate score − blind median`, treating **panels**, not dimensions, as the independent observations.

Also corrected from the draft: Tier 2b would **not** produce a blind/primed pair "for free". A pair requires an explicit post-prime rescore, which is additional cost, and terminal-derived data is opportunistic and selection-biased — not a substitute for dedicated Layer-6 calibration probes.

### Tier 3 — guard band on the candidate score. Deferred.

A guard band requires an observed **≥ 10.06** from one rater. Unreachable by construction. It becomes meaningful only **if** recommendation 2 shrinks SEM. Recorded here so the next reader does not re-derive it.

---

## Work items

### Schema — `schema_version` 5

**Why a new version rather than widening v4.** Panel certification changes both the shape *and the meaning* of `halt_success_challenge`. Gating at v5 preserves v4's single-challenger contract, leaves every existing artifact valid, and avoids retroactively invalidating committed runs. Nothing in the codebase pins a maximum `schema_version`, so v5 is additive.

```jsonc
{
  "required_panel_size": 3,               // int, fixed at 3 in v5
  "outcome": "held",                      // aggregate: held | broke | blocked | pending
  "protocol_digest": "sha256:…",          // stamped at panel creation; what resume/rollback compares
  "candidate_binding": {                  // immutable; present on EVERY path
    "run_id": "…",
    "source_rev": "…",
    "candidate_commit_sha": "…",
    "candidate_fingerprint": "…"          // v4+ field, reused
  },
  "panel": [                              // ordered; member 1 is the staged first launch
    {
      "member_index": 1,                  // 1-based, matches launch order
      "challenger_model": "…",
      "outcome": "held",                  // held | broke | unavailable
      "attempts": [ /* {arm, target, what_tried, why_failed} — as today */ ],
      "break_evidence": null,             // required non-null iff outcome == "broke"
                                          // NORMALIZED form: { finding_stable_id, spt: {result, rationale} }
                                          // (the raw challenger returns a different shape — see below)
      "normalization": null,              // null | "pending_user_decision" | "deferred_by_pending_registry_decision"
                                          // non-null ONLY under aggregate outcome "pending" (raw break_evidence)
      "reason": "…",
      "retry_count": 1,                   // int ∈ {1, 2} — mirrors rule #25 exactly
      "retry_cause": null,                // null | "timeout" | "spawn_error" | "malformed_json"
                                          //      | "budget_exhausted"  (v5 addition)
                                          // non-null iff retry_count == 2
      "retry_attempts": [                 // length == retry_count
        { "attempt": 1, "outcome": "ok", "error": null, "duration_ms": 7250 }
      ],
      "token_usage": {                    // aggregate across ALL transport attempts
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0
      }
    }
    // members 2 and 3 present only if member 1 held
  ]
}
```

Four shape decisions worth stating, because the existing schema cannot carry the claim on its own:

- **The retry envelope is rule #25's shape plus exactly one v5-specific value.** `retry_count` / `retry_cause` / `retry_attempts[]` take the shape rule #25 already defines for `implementation_review` ([`output-format-json.md:328–330`](../references/output-format-json.md)) — `error`, `duration_ms`, `length == retry_count`, "first entry's `outcome` matches `retry_cause`" — and **extend both enums with `budget_exhausted`**, giving `{ok, timeout, spawn_error, malformed_json, budget_exhausted}` for `retry_attempts[].outcome` and `{timeout, spawn_error, malformed_json, budget_exhausted}` for `retry_cause`. The extension is not optional: the session budget below produces exhaustion records, and a "reused verbatim" envelope would make every one of them schema-invalid. Row 3 of the precedence table turns on envelope exhaustion, so the record must prove it.
- **The break contract has two stages, and only the second is validated.** A challenger cannot mint a valid `finding_stable_id` — registry matching and allocation happen in main. So:

  | stage | shape | produced by |
  |---|---|---|
  | **raw** | `break_evidence: { finding: <unnumbered Evidence Chain>, spt: { result: "passed", rationale: <non-empty> } }` | the challenger |
  | **normalized** | `break_evidence: { finding_stable_id, spt: { result, rationale } }` | main, after registry-match or allocation and writing the top-level `findings[]` entry |

  **G32 and the grading adapter validate only the normalized record.** The raw record cannot contain a stable ID yet, so applying G32 to it directly would be a category error. This also reuses the existing finding validation rather than inventing a parallel format.

  **The raw `finding` payload carries every required top-level Finding field except the main-assigned ones** — a `findings[]` entry minus **both** `stable_id` *and* `loop_local_id`. `loop_local_id` is `"F<n>"`, fresh per loop and **ordered by Priority** ([`output-format-json.md:186`](../references/output-format-json.md)), so it cannot be assigned until every break is collected and ordered. Normalization is not a shape conversion; it is a multi-artifact transaction, specified below.

- **SPT is recorded as a pass, not borrowed from the rejection enum.** An earlier draft of this plan reused `spt_question_failed ∈ {"Q1".."Q5", "structural_gate"}`, which is **semantically inverted**: that field is defined as "which SPT question *rejected* it" ([`output-format-json.md:274`](../references/output-format-json.md)), and any "no" downgrades the fix ([`method.md:106`](../references/method.md)). Treating a non-null value as proof of passage would let an invalid break demote certification. Break evidence therefore carries `spt: { result: "passed", rationale: <non-empty> }` and does **not** use `spt_question_failed`, which remains correct only for rejected convergence candidates.
- **`candidate_binding` is hoisted to the aggregate and is immutable.** Panel records persist on non-promoting paths, but the top-level `run_id` / `source_rev` / `candidate_fingerprint` fields are required non-null only on `HALT_SUCCESS_candidate` and `HALT_SUCCESS` ([`output-format-json-rules.md:191`](../references/output-format-json-rules.md)). On a CONTINUE or `HALT_STAGNATION` transition those top-level fields are gone, so `candidate_binding` must be **copied into the panel record at panel-creation time**.

  These are two different guarantees, and an earlier revision conflated them by asking G32 to enforce an equality it has no persisted comparison source for. Resolved explicitly:

  | path | what G32 validates | what enforces the rest |
  |---|---|---|
  | `HALT_SUCCESS` | shape **and** equality — top-level `run_id` / `source_rev` / `candidate_fingerprint` are retained, so G32 compares directly | G32 |
  | CONTINUE / `HALT_STAGNATION` | **shape only** | routing/resume logic, covered by behavioral tests |

  G32 is a stateless validator of one artifact. On non-promoting paths it has no comparison source, so it can check neither equality **nor immutability** — an earlier revision of this plan still claimed immutability, which is the same error one step removed. Creation-time equality and copy-forward immutability are enforced in routing and resume logic and proved by behavioral tests. The alternative — persisting a separate candidate snapshot purely so a validator can re-derive equality — adds an artifact to satisfy a gate rather than a requirement, and is rejected.

G32 must enforce at v5:

- `required_panel_size == 3`; `panel` length consistent with the staged rule (1 entry when member 1 broke or was unavailable; otherwise 3); `member_index` values exactly `1..len` in order.
- Aggregate `outcome` agrees with the precedence table applied to the member records — aggregate `held` with any member `broke` is a violation — and aggregate/state coupling holds (`held`↔`HALT_SUCCESS`, `broke`↔CONTINUE or `user_decision`, `blocked`↔`verification_blocked`, `pending`↔`user_decision`).
- Member records well-formed at **every** index, not just the first; per-member arm diversity; `break_evidence` non-null iff `outcome == "broke"` — in **normalized** form (`finding_stable_id` resolving in this loop's `findings[]`, `spt.result == "passed"`, non-empty rationale) on every route **except aggregate `pending`**, where raw form is required under `normalization: "pending_user_decision"` (the ambiguous member) or `"deferred_by_pending_registry_decision"` (its valid siblings) and the SPT record is validated the same way. `normalization` null everywhere else.
- Retry envelope shape per rule #25 **plus `budget_exhausted`** in both enums, applied per member.
- `candidate_binding` **shape** on every path; **equality** against the live candidate only on `HALT_SUCCESS` (see the table above).
- `token_usage` non-negative with `total_tokens == input_tokens + output_tokens`.

### Break normalization — the transaction

A break does not merely rewrite `break_evidence`. It spans the registry, `CURRENT_REVIEW`, `REVIEW_HISTORY`, the panel, and the backlog.

**Collect before assigning.** Gather every break from the completed panel and order them by `member_index` *first*. Only then assign IDs — `loop_local_id` is Priority-ordered, so per-break assignment as results arrive would produce a different artifact depending on completion order.

1. **Resolve every break against the evolving staged registry**, per Method Step 1.5, in `member_index` order. Match → reuse `stable_id`. Miss → reserve `F-{next_serial}` and increment, so `stable_id == next_serial - 1` as rule #21 requires. The registry is *staged*, so a second break that matches the first's newly reserved entry resolves to it rather than allocating a duplicate.
2. **Deduplicate by `stable_id`.** Two members can report the same defect; that is one finding, not two.
3. **Order the distinct findings** by Priority, lowest `member_index` first.
4. **Assign `loop_local_id`** across that ordered set.
5. **Append one occurrence per distinct `stable_id`** — `{loop: N, loop_local_id, status: "open"}`. This must follow step 4: the occurrence stub *contains* `loop_local_id`, so appending it during resolution would write an ID that does not exist yet.
6. **Write `findings[]`**, one entry per distinct resolved break.
7. **Write backlog items**, each carrying `stable_id` per G42; the Priority-1 item is the first in the ordered set.
8. **Rewrite `break_evidence`** to normalized form on each member record; members that deduplicated to a shared `stable_id` all reference it.
9. **Mirror into `REVIEW_HISTORY.json.loops[-1]`** (G18 parsed-dict equality).

**Replay safety reuses the existing idempotency rules but needs a container that does not exist yet.** Queue the registry mutations as `registry_pending_writes[]` entries with `idempotency_key`, flushed exactly as Step 3 step 10 does — key checked against `findings_registry.json.entries[].occurrences[].idempotency_key`, replay skipping entries already present ([`output-format-state-schemas.md:38,78`](../references/output-format-state-schemas.md)).

But those entries live in `LOOP_STATE.json`, and **`LOOP_STATE.json` is already gone by the time the panel runs.** It is deleted at step 11.f when the loop completes ([`resume-detection.md:129,146`](../references/resume-detection.md)), and the challenger only runs *after* the candidate review is committed ([`halt-verifier.md:25`](../references/halt-verifier.md)). Citing the Step-3 flush algorithm alone therefore buys nothing: the transaction is main-owned and has no durable checkpoint.

This plan adds a **panel phase to `LOOP_STATE.json`**, created at **panel spawn** (member 1 launch), not at normalization time. It stamps the `protocol_digest` at creation, appends each member's record as that member completes, and transitions to a normalization sub-phase — holding the staged panel and its `registry_pending_writes[]` — *before* the first review, history, or registry write. Creation must be at spawn, not at normalization: the partial-panel resume rule below reuses "durable `held` member records," and a checkpoint that only appears at normalization would leave mid-panel member verdicts with nowhere durable to live. Resume reuses the existing archive-dedup, registry-idempotency, and `commit_attempted_sha` rules unchanged.

**The new resume row must precede rows 7, 7b, *and* 8 — not merely row 8.** All three would misfire, and which one depends only on how far the transition write got:

| existing row | fires when | what it would wrongly do |
|---|---|---|
| 7 | `LOOP_STATE` present + `CONTINUE` | route to ordinary §Resume-from-LOOP_STATE, treating the panel checkpoint as a mid-Step-3 interrupt |
| 7b | `HALT_SUCCESS_candidate` | **re-spawn the entire panel**, discarding verdicts already paid for |
| 8 | `LOOP_STATE` present + terminal `HALT_*` | delete the checkpoint as leftover post-halt state |

The phase-keyed row therefore sits after general checkpoint-integrity checks and **before all state-based rows**, and must resume correctly whether `CURRENT_REVIEW` still reads `HALT_SUCCESS_candidate`, has reached CONTINUE, or has reached a terminal `HALT_*`. Test interruption at three points: before the transition write, after it, and after commit but before checkpoint deletion.

**Two distinct stage-2 breaks** both resolve and both appear in `findings[]`; ordering by `member_index` decides which takes Priority 1. They are not coalesced into one finding — two real defects are two findings.

**Ambiguous registry match.** Step 1.5 already routes this to `HALT_STAGNATION`/`user_decision` with `open_question_for_user` ([`method.md:49`](../references/method.md)); retrying the challenger cannot resolve main-side ambiguity. Such a member has **no resolved `stable_id`**, so it must not be persisted as a normalized `broke`.

**When row 0 fires, *every* break in the panel stays raw — not just the ambiguous one.** A mixed state is unrepresentable: a valid sibling break could be neither normalized (no finding was written, because no registry write happens while the question is open) nor left raw (it had no permitted marker). One policy, applied to the whole panel:

| member | `break_evidence` form | marker |
|---|---|---|
| the ambiguous break | raw | `pending_user_decision` |
| any other valid break in the same panel | raw | `deferred_by_pending_registry_decision` |

- **Every** raw finding must still be *complete* (all required Finding fields except the two main-assigned IDs) with its SPT recording `result: "passed"` — ambiguity is about *which* existing finding this is, not about whether the break is valid.
- **Aggregate:** `outcome: "pending"` (precedence row 0). `findings[]` is **exactly empty**, and no registry mutation is flushed.
- **G32** accepts raw `break_evidence` under either marker **only** when aggregate `outcome == "pending"`, `state == "HALT_STAGNATION"`, `halt_subtype == "user_decision"`, and `open_question_for_user` is non-null. It validates both raw payloads and their passed SPT records. Raw form anywhere else is a violation.
- **Resume after the user answers:** the user selects an existing `stable_id` or authorizes a new allocation. Resume re-enters normalization at step 1 and normalizes **every** break in the panel — the deferred siblings included — carrying the persisted raw evidence forward. The panel is **not** re-run: the members already returned their verdicts, and only the registry question was open.

This path therefore carries **exactly zero** findings — see rule #6 exception (f).

**Rule #6 must be amended — this is a hard blocker on the demotion paths, not a detail.** [`output-format-json-rules.md:156`](../references/output-format-json-rules.md) requires `findings` count 3–5 (up to 7), allowing empty only for (a) `HALT_SUCCESS` and (b) `HALT_STAGNATION` + `no_backlog`. As designed, **every** panel demotion path emits an invalid artifact: a CONTINUE-after-`broke` carries one or two findings, a `verification_blocked` carries **zero**, and a `pending` registry question carries **zero**. Add three exceptions:

- **(d)** **1 or 2** findings allowed — the number of distinct resolved breaks — when `halt_success_challenge.outcome == "broke"` at v5 AND `state` is either `CONTINUE` **or** `HALT_STAGNATION`/`user_decision`. Two members can break distinctly, and the Stop/Ask route carries the same finding count as the CONTINUE route; an exception scoped to one finding on one state would invalidate both.
- **(e)** empty allowed when `state == "HALT_STAGNATION"` AND `halt_subtype == "verification_blocked"` **AND `halt_success_challenge.outcome == "blocked"` at v5** — no member returned a usable verdict, so there is nothing to report. The v5-panel condition is deliberate: without it this silently becomes a general `verification_blocked` semantic change reaching earlier schema versions, which is a larger claim than this plan measures.

- **(f)** **exactly 0** findings when `state == "HALT_STAGNATION"`, `halt_subtype == "user_decision"`, and `halt_success_challenge.outcome == "pending"` at v5 — the registry question is open, so nothing has been written. Not "0 or 1": permitting one would contradict the no-registry-write rule above, and a prior loop's finding belongs to that loop's artifact, not this one's `findings[]`.

All three exceptions are conditioned on the **panel fields**, not on state alone, and all need fixtures — positive and negative. Missing this reconciliation would have shipped a gate whose own failure paths cannot validate.

**Records must be durable on the non-promoting paths.** v4 requires `halt_success_challenge: null` on `HALT_STAGNATION`, so a partial panel currently has nowhere to live. At v5, an auditable panel record is permitted on CONTINUE-after-`broke`, on `HALT_STAGNATION`/`user_decision`, and on `HALT_STAGNATION`/`verification_blocked`. Without this, the failure paths are unobservable.

### Version transition, enablement, and delivery sequence

Add [`output-format-migrations.md`](../references/output-format-migrations.md) to the work — it already owns the moved v3 changelog and is the right home for the v4→v5 note.

Transition rules: a persisted **v4** candidate finishes under the legacy single-challenger contract; **v5** artifacts use panels; mixed-version `REVIEW_HISTORY` remains legal. No artifact is rewritten in place.

**Enablement is a default-deny provider-adapter capability, not global prose.** Add a `panel_certification` capability manifest to [`provider-adapters.md`](../references/provider-adapters.md), keyed by **provider + exact model + `protocol_digest`**. Runtime emits v5 **only** when the current digest matches a recorded pass for that exact provider and model. Missing, stale-digest, unknown-model, or rolled-back entries emit **v4**. Without this, the moment the routing prose goes global, unmeasured profiles emit v5 too — and a pass recorded against an older challenger prompt would keep authorizing a protocol nobody measured.

**`protocol_digest` is one canonical value with one algorithm** — not the loosely-named "prompt hash" / "protocol hash" an earlier revision used interchangeably. It is `sha256` over these inputs, concatenated in this exact order, each length-prefixed:

1. `halt-verifier.md` (the challenger prompt) — full file bytes
2. the panel routing-precedence table and staged-launch rules
3. the break-normalization transaction steps
4. the v5 `halt_success_challenge` schema block
5. the gate thresholds (panel count, per-panel break requirement, restraint all-hold requirement)
6. `C_max` for the profile
7. **the challenger spawn profile and tool allow-list** for that provider
8. **the budget-enforcement configuration and the adapter implementing it**
9. **the gate scenario and assertion definitions** (`evals.json` #21/#22 entries and their scenario files)
10. **the grading adapter** (`scripts/_panel_gate_adapter.py`)

Inputs 7–10 exist because provider/model identity does **not** version them: changing the spawn command, the tool permissions, the turn topology, the enforcement adapter, the scenario assertions, or the grading logic can change results while leaving inputs 1–6 untouched. A digest over an under-specified input set is the staleness hole wearing a hash.

**One shared digest function** computes this for both gate evidence and runtime lookup, so the two cannot drift independently. Any behavior-affecting change invalidates every recorded pass; a mismatch — or any input that cannot be read — falls back to v4.

Deterministic tests required for: measured profile, unmeasured profile, stale digest, model override, `unknown` provider, and rollback.

Deliver in three steps, in this order:

1. **v5 reader** — backward-compatible: parses and validates v5 panels, emits nothing v5.
2. **Behavioral gate** — below. Runs the v5 prompt and harness **before** the capability is switched on for any profile.
3. **v5 emitter + routing prose**, gated per profile by the capability entry.

**Rollback** clears the capability while retaining the step-1 reader so v5 artifacts stay readable. A failed v5 panel must **never** be reinterpreted as a v4 success.

**Authorization to *create* a panel is separate from handling one that already exists.** The capability governs creation only; a persisted partial v5 panel encountered after rollback or protocol invalidation still needs a defined route, and "cannot emit v5" plus "partial v5 panels resume as v5" would otherwise contradict:

The panel record stamps `protocol_digest` at creation (see the schema above) — without it there is nothing for resume to compare, and an earlier revision referenced a digest the panel never stored. The two routes are **disjoint**, keyed on whether the stored protocol is still *executable*, not on whether new panels are authorized:

| condition on the persisted panel | route |
|---|---|
| stored `protocol_digest` matches the current digest **and** its inputs are all readable | **finish it under v5** — the members already ran, and abandoning paid-for verdicts is worse than completing them. This holds even when the capability has been revoked: revocation disables *creating* panels, not *completing* one already paid for. |
| stored digest is stale, unreadable, or explicitly unsupported | **launch no further members**; fail closed to `HALT_STAGNATION`/`verification_blocked`, recording the persisted panel, and route to a fresh v4 Critic candidate |

**G32 validates the digest's shape only.** Copy-forward immutability is a temporal invariant across artifacts, and G32 is a stateless single-artifact validator — assigning it that check is the same error this plan already corrected twice, once for `candidate_binding` equality and once for its immutability. Stamping at creation, retaining the original in the panel checkpoint, and enforcing exact copy-forward all belong to routing/resume logic, with behavioral tests. **The resume router — not G32 — compares the stored digest against the currently executable protocol.**

Hard protocol disablement is recorded **separately from the creation-capability entry**, as an explicit unsupported-digest list. Rollback behavior is then deterministic rather than inferred: a digest on that list routes to the fresh v4 Critic path even if it would otherwise still be executable. Rollback-resume and stale-digest-resume both need tests.

### Fixtures

**No existing fixture is migrated.** Every v2–v4 fixture is left byte-unchanged. The draft's claim that eight fixtures need a panel added was wrong: `halt-success-bad` is v2 and `incremental-then-halt-success` is v3, and G32 does not fire below v4 ([`_artifact_halt.py:157,161`](../scripts/_artifact_halt.py)). Of the six v4 terminal fixtures, five deliberately encode one G32 defect each and `halt-terminal-no-challenge` must remain challenge-less — a mechanical panel-add would destroy the coverage they exist to provide.

New v5 fixtures:

| fixture | expectation |
|---|---|
| unanimous 3× `held` | pass |
| panel of 2 | fail |
| aggregate `held` with a member `broke` | fail |
| malformed **non-first** member record | fail |
| `broke` with `break_evidence: null` | fail |
| `broke` whose `finding_stable_id` does not resolve | fail |
| `broke` with `spt.result != "passed"` or an empty rationale | fail |
| `broke` persisted in raw form outside the aggregate-`pending` route | fail |
| member normalized to `unavailable` after a malformed break → `verification_blocked` | pass |
| valid `broke` → CONTINUE, panel recorded | pass |
| valid `broke` needing Stop/Ask → `user_decision`, panel recorded | pass |
| partial panel → `verification_blocked`, panel recorded | pass |

Mirror **only new or changed** fixture artifacts into `REVIEW_HISTORY.json.loops[-1]` — G18 requires parsed-dict equality, and untouched fixtures need no mirror.

Plus boundary fixtures for the three rule #6 amendments and the pending-route policy, **positive and negative**:

| fixture | expectation |
|---|---|
| CONTINUE-after-`broke`, 1 finding, qualifying v5 panel | pass |
| `user_decision`-after-`broke`, 1 finding, qualifying v5 panel | pass |
| two distinct stage-2 breaks → 2 findings | pass |
| `verification_blocked` with empty `findings`, aggregate `blocked` at v5 | pass |
| 1-finding CONTINUE **without** a qualifying v5 panel | fail — **deferred, see below** |
| empty `verification_blocked` outside the v5-panel scope | fail — **deferred, see below** |
| ambiguous match: raw `break_evidence` under `pending_user_decision` at `user_decision` | pass |
| one ambiguous break + one otherwise-valid sibling: both raw, distinct markers, `findings[]` empty | pass |
| normalized sibling under aggregate `pending` | fail |
| non-empty `findings[]` under aggregate `pending` | fail |

Remaining coverage goes in `_g32_panel_selftest.py`: per-member binding, per-member arm diversity, the v4/v5 version boundary, `required_panel_size` mismatch, `member_index` gaps and reordering, retry-envelope shape per rule #25 plus `budget_exhausted`, aggregate/state coupling, `token_usage` arithmetic, two **distinct** stage-2 breaks ordered deterministically by `member_index` (two findings, not one), two members **deduplicating** to one `stable_id` (one finding, one occurrence), first-attempt `budget_exhausted` followed by success, two-attempt exhaustion normalizing to `unavailable`, ambiguous registry match routing to row 0, rollback-resume, stale-digest-resume, and routing precedence (pending-beats-break, break-beats-unavailable, Stop/Ask-beats-CONTINUE).

**Partial-panel resume needs behavioral coverage, not just shape checks:** unchanged-candidate reuse; drift forcing a fresh Critic; a stage-1 `unavailable` resuming into stage 2; and a decisive one-member break **not** being mistaken for unresolved partial work.

**As built (step 1, implementation-time deviations):**

- **The two state-only rule #6 fail fixtures are deferred to step 3.** Rule #6's finding counts are prose-only — no gate enforces them — and `validate-fixtures.py` requires a fail fixture to actually fail (`aspirational = true` waives only the rule-id assertion, not the failure itself). Only the **panel-keyed** halves of exceptions (d)/(f) are G32-enforceable, and those shipped: aggregate `broke` → findings count ∈ {1,2} matching distinct referenced break ids; aggregate `pending` → findings exactly empty. The state-only direction needs rule #6 itself to gain a gate, which is not this plan's scope.
- **20 fixtures shipped, not 22:** 12 core (`panel-*`) + 8 boundary (`panel-rule6-*`, `panel-pending-*`). Names differ cosmetically from the tables above.
- **`open_question_for_user` had no script enforcement anywhere** (discovered while building the pending fixtures). G32's pending branch now enforces it as the fourth leg of the raw-acceptance condition; the general non-null-iff-`user_decision` rule remains prose (G34/G36 territory, untouched here).
- The staged-length rule is enforced **biconditionally** (1 entry ⇒ member 1 broke/unavailable; 3 entries ⇒ member 1 held). A first draft checked only the first direction on the theory that the converse was an execution fact — it is not; member 1's outcome is in the artifact.

### Code

`check_g32_halt_success_challenge` spans [`_artifact_halt.py:138–364`](../scripts/_artifact_halt.py) (~227 lines) in a 693/800-line module. Panel validation cannot land there.

**Move the G32 block into a new `scripts/_artifact_panel.py`**, mirroring the G37 → `_artifact_residual.py` split done earlier this session. This requires updating the import/wiring in `validate-artifact.py`, and both resulting modules must pass `check_module_size.py`. Do not reach for `# WAIVER: module-size`.

Extend **G32** rather than adding G44 — same rule, same concern, and splitting one rule across two IDs violates the disjointness discipline stated in G35's and G36's bodies.

### Prose and canon

- [`halt-verifier.md`](../references/halt-verifier.md) — staged spawn, stage-2 join, routing-precedence table, asymmetric hold/break rule, structural-validity and normalization rules. The "Spawn" and "Outcome routing" sections both change.
- [`trust-model.md:103`](../references/trust-model.md) — singular-challenger routing.
- [`resume-detection.md:30`](../references/resume-detection.md) — row 7b re-enters the challenge; at v5 it must re-enter the **panel**. Plus the **new phase-keyed row** (`LOOP_STATE.phase == "panel_normalization"`) ordered after checkpoint-integrity checks and **before all state-based rows 7 / 7b / 8** — see § Break normalization for why each of those three misfires on a panel checkpoint.
- [`provider-adapters.md:146`](../references/provider-adapters.md) — challenger-spawn profile, staged 1-then-2 spawn, the `unknown`-provider inline path, and the new `panel_certification` capability entry.
- [`validation.md`](../references/validation.md) G32 body; `canon/validation-gates.toml` G32 title.
- [`output-format-json.md`](../references/output-format-json.md) — new § Schema version 5 changelog + the v5 `halt_success_challenge` block; new rule in `output-format-json-rules.md`, **plus the rule #6 amendment (exceptions (d), (e), and (f))**.
- [`output-format-migrations.md`](../references/output-format-migrations.md) — v4→v5 transition note.
- [`halt-handoff.md`](../references/halt-handoff.md) — `verification_blocked` wording for a partial panel.
- [`evals/README.md`](../evals/README.md) — add the missing `halt-challenge-flag` (#21) / `halt-challenge-restraint` (#22) row to the flag/restraint table. They exist in `evals/evals.json` but are absent from the table, which is how this plan's earlier draft came to point the gate at the wrong corpus.
- `SKILL.md` Step 1 Routing, the `HALT_SUCCESS_candidate` branch.

**Partial-panel resume.** On resume with a persisted partial panel: first check the stored `protocol_digest` per the rollback table in § Version transition (a stale or unsupported digest launches nothing). Then, if `source_rev` and `candidate_fingerprint` are **unchanged**, reuse the durable `held` member records from the panel checkpoint and rerun only the unresolved staged work. On **drift**, do not launch another panel — the candidate itself is stale, so route through the existing fresh-Critic drift path to obtain a new candidate first, consistent with the recurrence key at [`halt-verifier.md:135`](../references/halt-verifier.md). A panel is only ever run against a current candidate, under a protocol that is still executable.

---

## Cost

Let `F` = fresh panel executions, `U` = resumed panel executions, `nᵤ ≤ N` members launched by resume `u`, `N = 3`, `R = 2` (max transport attempts per member), `S` = blind-scoring tokens per member attempt, `C` = challenge tokens per member attempt including source and candidate input plus output, and `C_max` a per-attempt **upper bound** on `C`.

**`C_max` requires a new adapter-enforced session budget — provider limits do not supply one.** A challenger is not one model request. It reuses the reviewer-spawn profile ([`provider-adapters.md:146`](../references/provider-adapters.md)) with `read` / `grep` / `glob` and a read-only shell allow-list, so a member invocation is an **agentic session of unbounded model and tool turns**, and `provider-adapters.md` defines no token or turn budget today. A per-request context/output limit therefore bounds a single turn, not the session — so deriving `C_max` from provider limits bounds nothing.

This plan adds a **per-member session budget** enforced by the adapter across every model and tool turn. `C_max` is a **cumulative token cap per transport attempt** — tokens, not turns, because the formulas multiply it against token counts and a turn cap is not dimensionally interchangeable with token consumption. An adapter that enforces turn-based limits derives its token ceiling as `turn_cap × per_turn_hard_limit`.

**Exhaustion is its own cause, not a timeout.** Add `budget_exhausted` to the member `retry_cause` enum. Crossing the cap discards any truncated verdict and consumes **one** retry; only exhausting the full envelope (`R = 2`) normalizes to `outcome: "unavailable"`. Recording exhaustion as `timeout` would make the audit record say the provider was slow when in fact the work was too expensive — two different operational problems with different fixes.

**A profile that cannot enforce the cap and report complete usage stays on v4.** The guarantee requires stopping *before* crossing the ceiling while still reporting exact usage; a provider that surfaces usage only after an unbounded session cannot supply it, and no capability entry may be recorded for it. Without all of this the panel has no cost ceiling and every formula below is decorative.

For **heterogeneous** profiles the gate cost is `36 · Σₚ C_max,p`, not `36 · P · C_max` — the latter is correct only if `C_max` is explicitly the maximum across all profiles. The gate's **observed** maximum `C` is recorded and reported separately; measuring traffic establishes what a pass actually costs, never a mathematical bound.

**Panel-token worst case:** `tokens_max = R·(S + C_max) × (N·F + Σᵤ nᵤ)`
**Tier 1 as shipped** (`S = 0`): `tokens_max ≤ 6·C_max·(F + U)`
**Actual staged spend per fresh execution:** `r₁C + held₁ × (r₂C + r₃C)`, each `r ∈ {1,2}`

**Only `F` is bounded by the loop cap.** `U` is not — repeated user-triggered resumes can add panel executions without a fresh terminal attempt. The proven per-resume bound is `nᵤ ≤ N`; partial-panel reuse often makes it smaller, but a resume that begins with member 1 unavailable can still launch all three, so `nᵤ ≤ N` is the only bound this plan claims.

**One-time gate spend:** `gate_tokens_max = 36 · Σₚ C_max,p` — 2 scenarios × 3 panels × `N` = 3 members × `R` = 2 attempts, summed over measured profiles. This is paid **once per profile-and-protocol revision**, not once per profile forever: changing the challenger prompt or the panel protocol invalidates the recorded pass (see the capability manifest) and the gate must be re-run.

**"Once per run" is false** — the challenge fires once per *fresh terminal attempt*, and after a break plus a source fix the changed `source_rev` makes the next candidate panel-eligible again. Fixing `N = 3` rather than exposing `--panel N` is what keeps `F`'s term bounded; a configurable panel size would add unbounded spend plus a `startup.md` surface change for no evidenced benefit.

`C` is **not yet measured**. It is measured from the behavioral-gate runs below — those already execute real panels, so no separate representative run is needed. The draft's ~250k figure came from a lean scoring harness that omitted ~33k protocol tokens per pass and was handed build/test results rather than producing them; it is not a valid `C`. `token_usage` is `{input_tokens, output_tokens, total_tokens}`, **aggregated across every transport attempt** for that member, not the successful attempt alone. When Tier 2 eventually ships, it restores `S` in the same formula.

## Pre-enforcement gate

v5 must **not** be enabled on the strength of passing selftests. The instrument has no positive control — **no documented production positive control exists**, so "nothing certifies" is currently indistinguishable from "the instrument is too strict."

**Corpus.** The two dedicated challenger scenarios in [`evals/evals.json`](../evals/evals.json): **#21 `halt-challenge-flag`** and **#22 `halt-challenge-restraint`**. These are purpose-built for exactly this instrument — the flag case hides three independent writers to `selectedTab` behind an all-9.5 self-audit, and the restraint case requires the challenger to hold rather than manufacture a finding on file length alone. The general flag/restraint pairs in the README table are reviewer-judgment scenarios, most of which are not HALT-candidate challenges; running all 35 would be both wrong in kind and ~17× the cost.

**Grading adapter** (required work, not an assumption) — `scripts/_panel_gate_adapter.py`, writing results to `evals/panel_gate_results.json`, whose entries carry `{provider, model, skill_rev, protocol_digest, scenario, panel_index, raw_member_responses[], normalized_member_records[], enforced_C_max, observed_usage, exhaustion_cause, structural_pass, semantic_pass}`. `raw_member_responses[]` is retained **alongside** the normalized records, not in place of them — normalization is lossy, and a pass that cannot be re-graded from raw evidence cannot be audited. That file is the evidence a capability manifest entry points at.

Those scenarios emit `verdict ∈ {approved, rejected, conditional}`, not `held`/`broke`. The adapter:

- **Input:** the raw v5 member record returned by the challenger under the real v5 prompt, **then normalized** exactly as main would (registry-match or allocate the finding, write it, rewrite `break_evidence` to its normalized form). The adapter grades the normalized record, never the raw one — the raw record has no `finding_stable_id` yet and would fail G32 by construction.
- **Structural grading:** reuse G32 member validation on the normalized record. Malformed or unavailable output is a **failure**, never a neutral result.
- **Semantic grading:** map `broke` ↔ scenario verdict `rejected`, and `held` ↔ `approved` or `conditional`; then apply the scenarios' existing `[discriminating]` and `[restraint]` assertions unchanged.

**Thresholds:**

- Three independent staged panels per scenario.
- `halt-challenge-restraint`: all nine member verdicts `held` (3 panels × 3 members).
- `halt-challenge-flag`: **each of the three panels individually** must contain a structurally valid `broke` — not merely one break somewhere across the three.

Any failure blocks the `panel_certification` capability for that profile.

**Reproducibility.** Pin and record provider, model, skill revision, `protocol_digest`, raw member responses, enforced `C_max`, observed usage, and grading results for every gate run. **Enablement is scoped to the provider/model profiles actually measured**, enforced by the capability entry — an untested profile is not covered by another profile's gate pass.

**Repository checks**, all required: the new `_g32_panel_selftest.py`; every existing `_*_selftest.py`; `validate-artifact.py`; `validate-fixtures.py evals/fixtures/`; `validate-repo.py`; `check_module_size.py`; `ruff check` + `ruff format --check` at the pinned `0.15.6`; `eval-skill.py contest-refactor`.

### Pre-enforcement gate — as run (step 2, 2026-08-07)

**Profile:** `claude_code` / `claude-sonnet-5` (in-session Agent tool, alias `sonnet`; prompt-level read-only; verdicts delivered over the session mailbox). **skill_rev** `4a081da`; **protocol_digest** `sha256:df8e90bc42fc494f04c7b53bc3f1e411fa4aa760ce268d1b0ca3be705ea86aec`. Staged launch honored: every flag panel and two restraint panels ended at member 1 (break); only restraint panel 2 reached stage 2. Evidence with all raw member responses embedded: [`evals/panel_gate_results.json`](../evals/panel_gate_results.json).

| scenario | panels | structural | semantic | outcome |
|---|---|---|---|---|
| `halt-challenge-flag` (#21) | 3 | 3/3 pass | 3/3 pass — every panel broke at member 1, naming all three `selectedTab` writers, severity Likely disqualifier | **discriminates** |
| `halt-challenge-restraint` (#22) | 3 | 3/3 pass | 0/3 — panels went broke / broke-at-aggregate / broke; 3 of 6 members manufactured a break | **over-flags** |

**Gate verdict: FAIL — no `panel_certification` capability entry may be recorded.** The instrument has a positive control (the flag scenario proves it can break a hollow residual) but fails restraint: under the asymmetric one-break-demotes rule, this profile would wrongly demote a legitimate `HALT_SUCCESS`. The correlated over-flag axis is the **port-seam split**: two members broke by proposing a `CatalogPort`/`TransportPort` adapter split (plus one poll/timeout-extraction break), while the two holding members rejected *the same split* as an SPT Q2/Q3 relocation failure. Challenger-prompt hardening against seam-split manufacture, then a re-gate, is the unblock path for step 3.

**First measured `C` (per member, aggregated across the one transport attempt each; input counts fresh + cache-creation + cache-read tokens):**

| member | input | output | total | duration |
|---|---|---|---|---|
| flag p1 m1 | 544,712 | 11,523 | 556,235 | 144 s |
| flag p2 m1 | 455,847 | 12,568 | 468,415 | 185 s |
| flag p3 m1 | 437,774 | 18,016 | 455,790 | 178 s |
| restraint p1 m1 | 327,756 | 7,373 | 335,129 | 258 s |
| restraint p2 m1 | 768,193 | 24,896 | 793,089 | 307 s |
| restraint p2 m2 | 609,172 | 21,939 | 631,111 | 242 s |
| restraint p2 m3 | 324,547 | 15,476 | 340,023 | 165 s |
| restraint p3 m1 | 346,298 | 21,042 | 367,340 | 249 s |

Observed max `C` = **793k**; ~85% of every member's input is **cache reads** (the agentic loop re-presenting its own context each turn), with fresh+cache-creation+output typically 55k–125k. The naive `C_max = 150_000` was exceeded by **every** member under the raw-throughput metric, so all six panels also carry `budget_violation` — which is why the flag scenario's gate line reads FAIL despite 3/3 semantic passes. **Cost-model follow-up:** `C_max` needs a principled, cache-aware re-derivation (raw throughput, weighted-billing, or fresh-only — pick one and re-state § Cost in that unit) before any re-gate; the current figure was a pre-measurement guess and the gate exists to replace it.

**Profile limitations recorded (each alone blocks a capability entry, independent of the restraint failure):** budget enforcement is `post_hoc_discard` — the in-session Agent tool cannot stop a member *before* it crosses the ceiling, which § Cost requires; and `token_usage` is not reported by the transport itself (recovered post-hoc from session transcripts, deduplicated by message id). A capability-bearing profile needs a transport with preemptive budget enforcement and native usage reporting.

**Re-run under the hardened prompt (same day).** After the run-1 restraint failure, [`halt-verifier.md`](../references/halt-verifier.md) gained the **decomposition relocation bar** (a split breaks the verdict only if it names what it *deletes*; a seam in the type system is not implementation-level evidence; the bar shields no factually-false residual), mirrored verbatim into the gate member prompt, and `C_max` was re-derived to **1.2M raw-throughput tokens per transport attempt** (stated unit above; the naive 150k was ~5× low). Protocol commit `20bcf00`, digest `sha256:c0e09086…`. Result — **gate PASS**: flag 3/3 panels broke at member 1 (severity Likely disqualifier, SPT rationales explicitly clearing the relocation bar); restraint **9/9 member holds** across 3 full staged panels, with run-1's two manufactured attacks (port-seam split, poll/timeout extraction) attempted and *rejected* by multiple run-2 members citing the bar. Per-attempt usage ran 272k–996k (input+output) except one outlier: restraint p1 m3's attempt 1 hit **1.40M** — inflated by transport-protocol flailing (test messages + resends), not challenge work — was **discarded as `budget_exhausted` per § Cost, consuming one retry**; its attempt 2 held at 273k. That was the first live exercise of the `budget_exhausted` envelope and exposed a grading bug, fixed and covered by selftest: the audit compared the member's *aggregate* usage to `C_max`, but `C_max` is per **attempt** — a legitimately-retried member can approach 2×`C_max` aggregate (observed: 1.67M) without any accepted attempt violating. The instrument now has both a positive control and demonstrated restraint on this profile; only the enforcement-mode limitations below keep the capability unrecordable.

**As-built deviations (step 2):** the adapter owns the shared digest function; inputs 2–4 are verbatim plan prose frozen as module constants, so a scoped `RUF001` per-file ignore was added in `pyproject.toml` (rewording to satisfy the linter would change what the digest hashes). Input 10 is the adapter's own bytes — editing it invalidates every recorded pass by design, and **step 3's prose edits to `halt-verifier.md` (input 1) will likewise invalidate this run's digest; the gate re-runs against the frozen protocol before any capability entry is recorded** (the harness is now one `grade` command plus member spawns). Member verdict delivery in this harness arrived via the session mailbox, twice double-JSON-encoded and twice fence/prose-wrapped; `extract_member_json` tolerates all observed shapes and the raw texts are retained verbatim for re-grading. Gate-scope normalization allocates every break against a fresh registry (no cross-member dedup — Method Step 1.5 needs a real registry and is out of gate scope).

### Step 3 — as built (2026-08-07)

**Shipped:** the `panel_certification` capability manifest, the v5 emitter routing prose, and the partial-panel resume router — with **zero capability entries recorded**, exactly the default-deny design. Every profile emits v4 today; the machinery is live, the capability is not.

- `canon/panel-certification.toml` — manifest SSOT (`entries = []`, `unsupported_digests = []`), entry shape documented for when a recordable profile exists.
- `scripts/_panel_capability.py` — `emit_check` (v5/v4 decision: unknown-provider / no-entry / unsupported / stale / match) + `resume_route` (the § Version transition rollback table plus the § Prose-and-canon partial-panel rules, as a deterministic decision function), both calling the step-2 adapter's `compute_protocol_digest` — the one-shared-function requirement holds. CLI `check` / `resume` are what the routing prose invokes. 18-case selftest covers the six plan-required capability cases and nine resume routes.
- Routing prose landed across `halt-verifier.md` (Panel launch + v5 aggregate routing), `trust-model.md`, `resume-detection.md` (new row **6b**, keyed on `LOOP_STATE.phase == "halt_success_panel"`, ordered before rows 7/7b/8; row 7b scoped to the no-panel-checkpoint case), `provider-adapters.md` (§ panel_certification capability manifest), `validation.md` G32 v5 body + `canon/validation-gates.toml` title, `output-format-json.md` (§ Schema version 5 changelog + the v5 schema block), `output-format-json-rules.md` (rule #6 exceptions (d)/(e)/(f), rule #25 note, new rule #36), `output-format-migrations.md` (v4 → 5), `halt-handoff.md` (`verification_blocked` panel wording), `output-format-state-schemas.md` (LOOP_STATE panel phase, additive optional `phase` field at its own schema_version 1), and `SKILL.md` Step 1 routing.

**As-built deviations (step 3):**

- **The manifest is a canon TOML, not prose-embedded state.** The plan said "add a capability manifest to provider-adapters.md"; as built, provider-adapters.md documents the mechanism and `canon/panel-certification.toml` holds the data — matching the repo's canon-SSOT pattern and making the required deterministic tests possible at all (prose is not machine-checkable).
- **A ninth resume route, `resume_stage1`, was added beyond the plan's tables:** the panel checkpoint is created at member-1 *launch*, so an interrupt before member 1 delivers leaves zero durable member records — a legitimate, resumable state the plan's routes did not name. Fail-closing it (the shape-checker's default) would burn a resumable candidate to `verification_blocked`; the correct reading of "rerun only the unresolved staged work" is to relaunch member 1. Selftest-pinned.
- **Digest invalidation, as predicted:** the `halt-verifier.md` edits moved the current digest from run-2's `sha256:c0e09086…` to `sha256:a79723a9…`. No entry was recorded against either — recording still requires an enforcement-capable transport (or an owner amendment to § Cost's stop-before-crossing requirement) **and** a fresh gate PASS at the then-current digest.
- **The two state-only rule #6 fail fixtures stay deferred** (carried from step 1): rule #6's state-only direction has no enforcing gate, and `validate-fixtures.py` requires a fail fixture to actually fail. Rule #6's text now says so explicitly. Giving rule #6 a gate remains out of this plan's scope.
- **The three normalization-interruption points** (before the `sub_phase` transition write, after it, after commit but before checkpoint deletion) are covered by the router's deterministic tests (`resume_stage2`/`complete_normalization` + the reused registry-idempotency and archive-dedup rules make post-commit replay safe); a full loop-replay behavioral harness for them was not built — the router is the decidable core, and replay fixtures would exercise the same decision table through a costlier medium.

## Risk register

- Introducing a schema version is the larger conceptual change, but it removes the draft's biggest work item — fixture churn drops from "8 migrations plus history mirrors" to 12 new v5 fixtures plus 10 boundary fixtures (rule #6 + pending policy).
- **The rule #6 amendment is the highest-risk item.** It widens a rule every state passes through, to unblock three paths this plan creates. A too-broad exception would let genuinely under-populated artifacts validate; all three are therefore conditioned on the panel fields, not on state alone.
- The per-member session budget is new adapter machinery, not a constant — nothing in `provider-adapters.md` bounds an agentic member invocation today.
- The grading adapter is new work the draft did not account for; the challenger scenarios do not speak the v5 member vocabulary. Scoped to two scenarios, it is small.
- The break-evidence flow adds a main-side step (registry-match or allocate, write the finding, then store the ID) that did not exist in the single-challenger path.
- Module split forced by the 800-line cap; `_artifact_history.py` already sits at 794 and is untouched pre-existing debt.
- Staged launch makes panel cost data-dependent, so observed spend varies run to run. The formula bounds it; recorded `token_usage` measures it.
- Resumed panel executions (`U`) are not loop-cap bounded; the only claimed bound is `nᵤ ≤ N`.
- Arm diversity per member triples the duplication sweep. Cheap, but worth naming.
- **Run ledger (was flagged unsubstantiated across rounds 3–5; now cited as far as the archive allows).** The four runs are named in [`evals/scorecard-coupling/README.md`](../evals/scorecard-coupling/README.md): **Run A**, **Run B**, **Run C**, **Run S**, across two corpora — `steamgriddb` (C#) for A/B/C and `agent-skills` (Python) for S. Run B ran **10** loops and Run C **15**, from the combined history's loop numbering `[1..10, 1..15]` (README:199). "55 production loops" is corroborated independently at [`validation.md:242`](../references/validation.md) and [`method-critic.md:106`](../references/method-critic.md).

  **Still not recorded:** per-run loop counts for A and S (they sum to 30 by subtraction, but the archive does not split them), and **no run's terminal state is recorded anywhere**. So "no run has ever reached terminal `HALT_SUCCESS`" remains an *inference from the absence of any such record*, not a positive finding. This plan therefore does not lean on it: the pre-enforcement gate exists precisely because the instrument has no documented positive control, and that argument does not weaken if one of the four runs turns out to have certified.
