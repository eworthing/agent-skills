# Output Format — JSON emit-time rules (loaded at Step 1 emit / Step 3)

Emit-time coherence rules + embedded objects for `CURRENT_REVIEW.json`, carved out of [output-format-json.md](output-format-json.md) so the per-loop **investigation** phase does not carry them resident. The Critic collects evidence against the field schema in [output-format-json.md § Required-field schema](output-format-json.md#required-field-schema-machine-readable); these rules are checked when the artifact is **emitted** (Step 1 emit / Step 3). Loaded per the `SKILL.md` Reference Load Matrix at emit, not at loop start.

## Contents

- [Per-Loop Progress Line Format (schema_version >= 3)](#per-loop-progress-line-format-schema_version--3)
- [halt_handoff object (PR 4, schema_version >= 2)](#halt_handoff-object-pr-4-schema_version--2)
- [re_validation_context object (PR 4, schema_version >= 2)](#re_validation_context-object-pr-4-schema_version--2)
- [Schema validation rules (enforced by the validation hard gates)](#schema-validation-rules-enforced-by-the-validation-hard-gates)

## Per-Loop Progress Line Format (schema_version >= 3)

Every loop dispatch (CONTINUE) and every HALT_* emit prints a single one-line progress summary to the terminal so callers (`/loop`, wrapper agents, log greppers) can track loop activity without parsing the full review. Q8 in [validation.md](validation.md) is the quality-pass check; the format is:

```
loop <N>/<cap> | F<n> <slug> | <dim> <a>→<b> <UP|DOWN|SAME> | tests <green|red|n/a> | reviewer: <approved|rejected|conditional|n/a> | <duration>s
```

Field rules:

- `<N>/<cap>` — `loop` and `loop_cap` from CURRENT_REVIEW.json.
- `F<n>` — `loop_local_id` of the targeted Priority-1 finding for the loop. `n/a` on HALT_SUCCESS / HALT_DRY_RUN.
- `<slug>` — kebab-case finding title, max 40 chars (e.g., "collapse-repository-theater"). Truncate at 40 chars without ellipsis. `none` on HALT_SUCCESS.
- `<dim>` — scorecard short code: `arch` | `tests` | `concur` | `error` | `code` | `ownership` | `coupling` | `depth` | `impl`. Pick the dimension with the largest absolute delta this loop; ties broken alphabetically.
- `<a>→<b>` — prior loop's score → current loop's score (e.g., `8.0→8.5`). `n/a→n/a` when no prior loop exists (loop 1).
- `<UP|DOWN|SAME>` — delta enum from the picked dimension's scorecard entry.
- `<green|red|n/a>` — test status: `green` if Step 1 build/tests passed, `red` if failed (build-failure path), `n/a` for HALT_DRY_RUN (Step 1 ran but no claim emitted).
- `<approved|rejected|conditional|n/a>` — `implementation_review.verdict` from the loop. `n/a` for HALT_DRY_RUN / HALT_SUCCESS / HALT_LOOP_CAP / HALT_STAGNATION (no refactor executed).
- `<duration>` — wall-clock seconds from Step 1 start to Step 3 step 11 commit (or to halt emit, when no commit). Integer.
- `stalled: <dim> <n>` — **optional trailing field.** The dimension with the largest `loops_since_up` (consecutive prior loops with `delta != "UP"`, computed from `REVIEW_HISTORY.json`) when that count is >= 3; omitted otherwise. Ties alphabetical. Derived, never stored — persisting it would buy a recompute-vs-stored integrity gate and nothing else. This is the only place a ratchet becomes visible *during* a 13-28 minute loop, while the run is still interruptible; by the cap handoff it is history.

### Variants

HALT_SUCCESS:
```
loop <N>/<cap> | HALT_SUCCESS | scorecard: <avg_score> | tests green | <duration>s
```

HALT_DRY_RUN:
```
loop <N>/<cap> | HALT_DRY_RUN | plan-only (Step 2) | tests <green|red|n/a> | <duration>s
```

HALT_STAGNATION:
```
loop <N>/<cap> | HALT_STAGNATION/<subtype> | F<n> <slug> | <dim> <a>→<b> SAME | tests <green|red> | <duration>s
```

HALT_LOOP_CAP:
```
loop <N>/<cap> | HALT_LOOP_CAP | F<n> <slug> (carried) | <dim> <a>→<b> <delta> | tests <green|red> | <duration>s
```

### Examples

```
loop 3/10 | F3 collapse-repository-theater | arch 8.0→8.5 UP | tests green | reviewer: approved | 47s
loop 7/10 | HALT_SUCCESS | scorecard: 9.6 | tests green | 38s
loop 1/10 | HALT_DRY_RUN | plan-only (Step 2) | tests green | 12s
loop 4/10 | HALT_STAGNATION/oscillation | F2 splice-workflow-file | arch 8.5→8.5 SAME | tests green | 51s
```

Q8 verifies presence and shape; format violations never block emit.

## halt_handoff object (PR 4, schema_version >= 2)

Replaces the flat `halt_handoff_text` field at schema_version >= 2. Required when `state` ∈ {`HALT_SUCCESS`, `HALT_STAGNATION`, `HALT_LOOP_CAP`, `HALT_DRY_RUN` (v3+), `HALT_EXHAUSTION` (v4+)}; **null on `CONTINUE` and on the non-terminal `HALT_SUCCESS_candidate`** (a pause for the main-agent challenge, not a user-facing halt). Presence enforced by G34; object shape by G35.

```jsonc
"halt_handoff": {
  "state": "HALT_STAGNATION",                                        // optional mirror of top-level state for self-contained validation; default = top-level state when absent
  "halt_subtype": "oscillation",                                     // optional mirror of top-level halt_subtype; default = top-level halt_subtype when absent
  "text": "<full user-facing message per references/halt-handoff.md template, all placeholders resolved>",
  "expected_actions": [
    {
      "action_id": "split-workflow-file",                              // string, kebab-case identifier
      "description": "Split AppReducer+Workflow.swift to clear file_length warning",
      "match_keywords": ["split", "workflow", "AppReducer+Workflow"],  // array of strings; substring match against commit subjects
      "match_paths": ["BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift"],  // array of paths; match against commit's changed files
      "match_kind": "all_of"                                           // enum: all_of | any_of | no_drift_expected
    },
    {
      "action_id": "accept-halt",
      "description": "User accepts current halt; no commits expected",
      "match_keywords": [],
      "match_paths": [],
      "match_kind": "no_drift_expected"
    }
  ],
  "remaining_serious_findings_disposition": [
    // Required at schema_version >= 2 when state == HALT_STAGNATION AND halt_subtype == "oscillation".
    // Every Serious-or-worse finding with status ∈ {open, rejected_attempt} in the registry must appear here
    // with a canonical `disposition` (from canon/retirement-reasons.toml) plus the required sidecar.
    // G30 enforces coverage; the validator rejects HALT_STAGNATION/oscillation when any eligible
    // Serious-or-worse finding is missing or its sidecar is missing.
    { "stable_id": "F-007", "disposition": "unresolvable" },
    { "stable_id": "F-009", "disposition": "user_decision", "user_decision_ref": "ADR-0042" },
    { "stable_id": "F-011", "disposition": "outside_scope", "scope_label": "audio-engine" },
    { "stable_id": "F-013", "disposition": "unverifiable", "reason": "requires hardware test rig not available in scope" },
    { "stable_id": "F-015", "disposition": "superseded", "superseded_by": "F-020" }
  ]
}
```

`match_kind` semantics (the three values are canon — `canon/match-kinds.toml`; domain + coupling enforced by G35):
- `all_of` — match if at least one match_keyword AND at least one match_path hit. **Default when match_paths is non-empty** (rule #18 enforces).
- `any_of` — match if any match_keyword OR any match_path hit. Permitted only when match_paths is empty (keyword-only fallback).
- `no_drift_expected` — match if `git log <halt_sha>..HEAD` returns empty.

The loop subagent emits `halt_handoff.expected_actions[]` from the menu options in halt-handoff.md. Each menu option becomes a HandoffAction with `action_id` derived from the option's verb/object and `match_keywords` / `match_paths` populated from the option's referenced symbols.

### remaining_serious_findings_disposition[] sidecar rules (G30)

Each entry has `stable_id` plus `disposition` (one of the canonical values from `canon/retirement-reasons.toml`) plus a required sidecar field, depending on `disposition`:

- `disposition == "unresolvable"` — no extra sidecar; the registry already carries the `retirement` block (`reason` + `rationale`).
- `disposition == "user_decision"` — `user_decision_ref` non-empty (e.g., `"ADR-0042"`).
- `disposition == "outside_scope"` — `scope_label` non-empty (the scope label that does not cover the finding).
- `disposition == "unverifiable"` — `reason` non-empty (one-line explanation of why the available tools cannot validate the finding's claim).
- `disposition == "superseded"` — `superseded_by` non-empty (the stable_id of the replacement finding).

A missing sidecar where one is required is a G30 failure.

## re_validation_context object (PR 4, schema_version >= 2)

Required when `re_validated_at_sha` is non-null (Step -1 ran a fresh Step-1 critic pass on drift). Null otherwise.

```jsonc
"re_validation_context": {
  "drift_commit_count": 3,                                             // int. count of commits in <halt_sha>..HEAD
  "prior_handoff_actions_taken": [
    {
      "action_id": "split-workflow-file",
      "matched_commit_sha": "c066b0b",
      "commit_subject": "split AppReducer+Workflow.swift by feature",
      "match_kind": "all_of",
      "matched_keywords": ["split", "workflow"],
      "matched_paths": ["BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift"]
    }
  ],
  "expected_actions_unmatched": ["accept-halt"],                       // array of action_ids that did not match any commit (or "no_drift_expected" actions when drift exists)
  "why_halt_persists": "The workflow file split landed cleanly; remaining findings are cosmetic test-name polish, not contest-relevant.",  // one-sentence summary composed by main agent's re-validation pass
  "re_validation_run_by": "main_agent_step_neg_one"                    // enum: main_agent_step_neg_one (canonical) | other-future-routes
}
```


## Schema validation rules (enforced by the validation hard gates)

1. Every Markdown section has a corresponding JSON field. Missing JSON field = hard gate failure.
2. Enum values exactly match the Markdown allowed strings (no synonyms, no abbreviations).
3. `proof` non-empty when `score > 7` OR when `unverifiable_due_to_build_failure == true` (in the build-failure case `proof` is the carry-forward note rather than a structural citation).
4. `residual_blocking_10` non-empty when `9.5 ≤ score < 10`; null when `score == 10`.
5. `dependency_category` non-null when finding is a Coupling & Leakage finding (title or `what_is_wrong` references domain↔framework or domain↔persistence leakage). Allowed values: `in-process` | `local-substitutable` | `remote-owned` | `true-external` (no synonyms; no `remote but owned` or `true external`).
6. `findings` count is 3-5 (or up to 7 if each addition changes verdict/scorecard/backlog). Three exceptions: (a) **empty** allowed when `state == "HALT_SUCCESS"`; (b) **empty** allowed when `state == "HALT_STAGNATION"` AND `halt_subtype == "no_backlog"`; (c) **exactly 1 finding** allowed when the build-failure path is active — detected as `state == "CONTINUE"` AND at least one scorecard entry has `unverifiable_due_to_build_failure == true`. The single finding must be the build-failure finding (`severity: "Likely disqualifier"`, `test_failed: "n/a"`). Rule #19 independently validates converged-terminal residual accounting (no_backlog + cap-empty-backlog). Three v5-panel exceptions, G32-scoped ([output-format-json.md § Schema version 5 changelog](output-format-json.md#schema-version-5-changelog)): (d) **1 or 2** findings — the number of distinct resolved breaks — allowed when `halt_success_challenge.outcome == "broke"` at `schema_version >= 5` AND `state` is `CONTINUE` **or** `HALT_STAGNATION`/`user_decision`; (e) **empty** allowed when `state == "HALT_STAGNATION"` AND `halt_subtype == "verification_blocked"` AND `halt_success_challenge.outcome == "blocked"` at `schema_version >= 5` — the v5-panel condition deliberately keeps this from reaching earlier schema versions or a non-panel `verification_blocked` halt; (f) **exactly 0** findings when `state == "HALT_STAGNATION"`, `halt_subtype == "user_decision"`, AND `halt_success_challenge.outcome == "pending"` at `schema_version >= 5` — not "0 or 1": a permitted 1 would contradict the no-registry-write rule while the registry question is open. The panel-keyed halves of (d)/(e)/(f) are G32-enforced; the state-only converse direction (e.g. a 1-finding CONTINUE without a qualifying v5 panel, or an empty `verification_blocked` outside the v5-panel scope) has no gate — rule #6 remains prose there, and fixtures for it stay deferred.
7. `backlog` presence by `state`:
   - `CONTINUE` → non-empty (1-3 items)
   - `HALT_SUCCESS` → empty
   - `HALT_STAGNATION` → optional; if non-empty, items carry forward as suggestions; `unresolved_reason` must be non-null
   - `HALT_LOOP_CAP` → optional; if non-empty, items name the best next move; `unresolved_reason` must be non-null
8. `loop_result` present iff a refactor was executed this loop (i.e., loop reached Step 3 step 4); absent during HALT loops AND during build-failure path (Step 1 step 2).
9. `adr_conflicts` non-empty implies `adr_reopen_justification` non-null.
10. Verdict string is one of the five exact enum values.
11. `unresolved_reason` non-null when `state` in {`HALT_STAGNATION`, `HALT_LOOP_CAP`, `HALT_EXHAUSTION`}; null otherwise. **Presence enforced by G34.**
12. **9.5 residual disposition**: when `score >= 9.5 AND score < 10`, `residual_disposition` ∈ {`accepted`, `queued`} and `residual_rationale_or_backlog_ref` non-null. When `score == 10` OR `score < 9.5`, both fields are null — and **the converse half is mechanized** by G5 (`check_g5_sub95_residual_fields`): an `accepted` disposition below 9.5 is deferring a residual, not accepting one, and a residual named beside a `10` contradicts G6. The forward half stays a Critic checklist item.
13. **HALT_SUCCESS gating**: when `state == "HALT_SUCCESS"`, every scorecard dimension must satisfy: `score == 10` OR (`score >= 9.5` AND `residual_disposition == "accepted"`). Any `queued` residual blocks HALT_SUCCESS — downgrade to CONTINUE. An `accepted` residual needs no `residual_expires` (a rationale-justified permanent carve-out is a valid HALT_SUCCESS); but if it *carries* a `residual_expires` whose date has passed, that blocks HALT_SUCCESS until the residual is reconsidered.
14. **Build-failure carry-forward**: when any scorecard entry has `unverifiable_due_to_build_failure: true`, gates G4 (score>7 source-backed) and G8 (no score increase without proof) are suspended for that entry. The flag is permitted only on Step 1 step 2 (build-failure path).
15. **Implementation review presence**: `implementation_review` is required when `loop_result` is present (i.e., a refactor was executed); absent when `loop_result` is absent. Final committed `verdict` ∈ {`approved`, `rejected`} — `conditional` is a mid-loop transient state that must be resolved (re-spawn → approved or rejected) before commit. `rounds` ≥ 1; `rounds == 2` only when first reviewer pass returned `conditional`.
16. **Reject ↔ loop_result coherence**: when `implementation_review.verdict == "rejected"`, `loop_result.targeted_finding_status` must equal `"carried_forward"` AND `loop_result.unintended_regression` must equal `implementation_review.reason`. Mismatch = G2 fails.
17. **Halt subtype required**: when `state == "HALT_STAGNATION"`, `halt_subtype` ∈ {`no_progress`, `oscillation`, `user_decision`, `no_backlog`, `verification_blocked`} (the canonical set owned by `canon/halt-subtypes.toml`). Every other state must have `halt_subtype: null`. **Presence (non-null iff HALT_STAGNATION) enforced by G34**; membership (∈ canon) by the schema-enum check.
18. **Halt handoff required**: when `state` ∈ {`HALT_SUCCESS`, `HALT_STAGNATION`, `HALT_LOOP_CAP`, `HALT_DRY_RUN`, `HALT_EXHAUSTION`} (HALT_DRY_RUN at schema_version >= 3 only; HALT_EXHAUSTION at schema_version >= 4 only); **null on `CONTINUE` and on the non-terminal `HALT_SUCCESS_candidate`** (a pause for the main-agent challenge, not a user-facing halt). **Handoff PRESENCE is enforced by G34; the object SHAPE sub-rules below (non-empty `text`, `expected_actions[]` array, per-`HandoffAction` `match_kind ∈ canon` + the path↔kind coupling) are enforced by G35.** (`action_id` / `match_keywords` *content* — kebab-case, non-empty — remains out of scope for G35.)
    - schema_version 1: `halt_handoff_text` non-empty string built from the matching template in `references/halt-handoff.md` with all placeholders resolved.
    - **schema_version >= 2 (PR 4)**: `halt_handoff` object non-null with `text` non-empty AND `expected_actions[]` array (may be empty). Each HandoffAction must satisfy: `match_kind ∈ canon.match_kinds` (`canon/match-kinds.toml`); if `match_paths` is non-empty, `match_kind` must be `all_of`; if `match_paths` is empty, `match_kind` ∈ {`any_of`, `no_drift_expected`}. Null on `CONTINUE` and on the non-terminal `HALT_SUCCESS_candidate`. (Shape enforced by **G35**.)
19. **terminal residual accounting**: when `state ∈ {HALT_STAGNATION, HALT_LOOP_CAP, HALT_EXHAUSTION}` — **at any subtype and with any backlog** — `unresolved_reason` must account for every score `< 9.5`: the source-backed blocker, why it keeps the 9-anchor unmet, and why it cannot be a backlog item or accepted residual. Rejected Cosmetic/ADR/SPT-failing candidates alone do not satisfy this rule when the dimension's 9-anchor is met; those become accepted residuals at 9.5 or disappear into a score of 10. At these terminals **G37** additionally requires each sub-9.5 dimension to be accounted by exactly one of: a `backlog[]` item whose `score_impact` names it, or `residual_blocker_kind: "structural_anchor_unmet"`. A promotion-trigger kind forces promotion to 9.5-accepted; neither account present is a **stranded** dimension. A non-empty backlog does not excuse the audit — it accounts only for the dimensions it names.
20. **user_decision coherence**: when `halt_subtype == "user_decision"`, `open_question_for_user` (in subagent return JSON) and `unresolved_reason` must both be non-null and consistent.
21. **Stable ID presence (PR 1, v2+)**: Every emitted finding (CONTINUE and HALT alike) has both `loop_local_id` (regex `^F\d+$`) and `stable_id` (regex `^F-\d{3,}$`) non-empty. `stable_id` matches an entry in `findings_registry.json` (Method Step 1.5 fuzzy-match) or is a new ID equal to `findings_registry.next_serial - 1` after the loop's increment. Reviewer-rejected loops still emit findings with stable_id; registry occurrence carries `status: "rejected_attempt"`.
22. **Interface test coverage citation (PR 3, v2+)**: When `loop_result.what_changed` contains any keyword from § Deepening Keywords AND diff contains no test file changes, `loop_result.interface_test_coverage_path` must be non-null with at least one entry. Each entry: `target_symbol` non-empty, `target_symbol_kind` matches `^(new|existing_deepened|existing_[a-z_]+_interface)$` (canonical: `new` or `existing_deepened`; role-bearing variants like `existing_bootstrap_interface` accepted when symbol is a stable named-role interface), AND `distinguishes_no_op == true`. Otherwise null.
23. **re_validation_context coherence (PR 4, v2+)**: When `re_validated_at_sha` non-null, `re_validation_context` required with all fields non-null (`drift_commit_count`, `prior_handoff_actions_taken`, `expected_actions_unmatched`, `why_halt_persists`, `re_validation_run_by`). Each `prior_handoff_actions_taken` entry's `match_kind` must equal prior loop's matching action's `match_kind`. `re_validation_run_by == "main_agent_step_neg_one"` (canonical).

24. **HALT_DRY_RUN coherence (v3+)**: when `state == "HALT_DRY_RUN"`, `dry_run == true` AND `halt_subtype == null` AND `halt_handoff` non-null with text from [halt-handoff.md § HALT_DRY_RUN](halt-handoff.md). CURRENT_REVIEW.md contains `## Loop N Plan (dry-run)` with the Step 2 plan. `loop_result` and `implementation_review` absent (no Step 3 work). `backlog` non-empty (plan derives from a Priority-1 finding). G9 backlog purity unaffected.

25. **Retry envelope shape (v3+)**: `implementation_review.retry_count ∈ {1, 2}`. When `retry_count == 1`: `retry_cause == null` AND `retry_attempts[]` has 1 entry. When `retry_count == 2`: `retry_cause ∈ {"timeout", "spawn_error", "malformed_json"}` AND `retry_attempts[]` has 2 entries AND first entry's `outcome` matches `retry_cause`. `reason` MUST NOT mention "after 2 attempts" or transient causes; those live in `retry_cause` / `retry_attempts[]` only. Both attempts fail → `verdict == "rejected"` AND `reason == "reviewer unavailable; manual verification required"` exactly. At v5, the panel **member** retry envelope (not `implementation_review`) extends both enums with `budget_exhausted`; see rule #36.

26. **changed_paths populated (v3+)**: when `loop_result` present, `loop_result.changed_paths[]` non-empty (empty diff = nothing changed and `loop_result` should be absent per rule #8).

27. **test_scope coherence (v3+)**: `discovery.test_scope ∈ {"full", "incremental"}`. `"incremental"` → `discovery.test_filter` non-null non-empty. `"full"` → `discovery.test_filter` null. Per [validation.md G21 extension](validation.md), `state == "HALT_SUCCESS"` requires `discovery.test_scope == "full"` if any prior loop in REVIEW_HISTORY.json had incremental scope.

28. **HALT_SUCCESS challenge (v4+)**: enforced by G32 in [validation.md](validation.md). Rules differ by state and schema_version:
    - **`state == "HALT_SUCCESS"` at schema_version >= 4**: `halt_success_challenge` required non-null; `halt_success_challenge.outcome == "held"`; `halt_success_challenge.challenger_model` non-empty; `halt_success_challenge.attempts` a non-empty list; `halt_success_challenge.binding.run_id` equals top-level `run_id`; `halt_success_challenge.binding.source_rev` equals top-level `source_rev`; `halt_success_challenge.binding.candidate_commit_sha` non-empty. Any miss is a G32 failure.
    - **`state == "HALT_SUCCESS_candidate"` at schema_version >= 4**: `halt_success_challenge` must be `null`; `run_id`, `source_rev`, `candidate_fingerprint` must all be non-null. The candidate is EXEMPT from the challenge requirement — it awaits promotion by the main agent.
    - **schema_version < 4**: G32 does not fire. Legacy v3 `HALT_SUCCESS` without a challenge remains valid.
    - **`state == "HALT_SUCCESS_candidate"`**: obeys the same scorecard / backlog / findings rules as `HALT_SUCCESS` (every dim 10 or 9.5-accepted; empty backlog; empty findings). It is a success claim awaiting challenge, not a downgrade.
    - **`outcome == "broke"` + `state == "HALT_SUCCESS"`**: illegal. Main agent must demote the candidate before emitting terminal `HALT_SUCCESS` (the challenger breaks → demote, not promote).
    - At v5 see rule #36 (panel).

29. **risk_boundary_evidence shape (G33, v3+)**: `loop_result.risk_boundary_evidence` is OPTIONAL (null/absent ⇒ no Meta-Rule-4 risk boundary crossed this loop). When present non-null it is an object: `boundary_kind ∈ {isolation, sendable, conditional_compilation, cross_file_visibility, lock_ordering}`; `verification ∈ {compile_matrix, focused_test, thread_sanitizer, sendable_conformance, reasoning_only, carried_forward}` — there is deliberately NO single-config-typecheck value, because a green single-config compile does not prove an isolation/Sendable/visibility invariant (Meta-Rule 4); `detail` a non-empty string; and `verification == "reasoning_only"` requires `mechanically_testable == false`. G33 checks SHAPE only (the validator has no git diff); the git-grounded safety check — a committed boundary diff must carry a *real* verification — lives in the Layer-5 grader (`exec_replay_grade.py` `evaluate_risk_boundary_evidence`).

30. **state required (G36)**: `state` is a required, non-null field — `state is None` (whether `null` or an absent key) is a hard-gate failure. **Presence enforced by G36**; membership (`state ∈ canon.states`) for a non-null foreign state is the schema-enum check's concern (the two are disjoint). Closes a hole owned by no gate previously: the schema-enum check fires only when `state is not None`, and G34 returns early when `state ∉ canon.states`, so a null/missing `state` passed strict.

31. **backlog score_impact attribution (G39, v4+)**: each `backlog[]` item's `score_impact` is `<canon_dim_id> <signed delta>`, semicolon-joined for a multi-dimension item — `"data_flow +0.5; framework_idioms +0.5"`. Every id must be a `canon/scorecard-dimensions.toml` id **and** present in this loop's `scorecard`. Display labels, trailing prose, unsigned deltas and free text all fail. The field was required-but-unread before v4 and drifted into prose no rule could act on; attribution is what makes a backlog item rankable by the dimension it moves. **Shape only** — whether the projected move is *correct* is the Critic's judgment and stays out of the gate. Fires only when `backlog[]` is non-empty.

32. **discovery persistence (G40, v4+)**: `discovery` is non-null on **every** loop, not only the first, and carries non-empty `source_roots`, `test_command` and `lens`. Step 0 runs once per invocation; each later loop copies the object forward verbatim rather than re-deriving or nulling it, and rewrites it only when Step 0 genuinely re-ran (fresh run, `--reset`, `--purge`) — carrying it forward *faithfully* is this rule's obligation, since G40 checks only presence and shape. The `### Discovery` section in `CURRENT_REVIEW.md` stays first-loop-only: Markdown is the human summary and the archive preserves it; the JSON is the machine handoff. Rationale for the v4 change: [validation.md § G40](validation.md).

33. **cap loop executes (G41, v4+)**: when `state == "HALT_LOOP_CAP"` AND `loop == loop_cap` AND `backlog` is non-empty, `loop_result` is required. The cap gates the next dispatch, not the current loop's execution, so the loop that spends the budget does the work the budget bought. Exempt: `loop > loop_cap` (Step-1 emit, nothing left to run), an empty backlog (Steps 2-3 are legitimately skipped — that terminal is G37's), and `loop < loop_cap` (not policed). A reviewer-rejected cap loop still satisfies this: the revert path writes `loop_result` with `targeted_finding_status: "carried_forward"`.

34. **backlog stable_id (G42, v4+)**: each `backlog[]` item carries `stable_id` matching `^F-\d{3,}$` — the id of the Finding it was derived from. When this loop's `findings[]` is non-empty, that id must be one of them: the backlog is "derived only from Findings + Simplification Check; introduces no new concerns", so an item pointing at nothing is a concern introduced at backlog time. Without this field a backlog item has no identity at all — `priority`, `rank` and (post-G39) `score_impact` say what it *moves* and where it *ranks*, but nothing says *which finding it is*, so no rule can follow one item across loops without regex-scraping "(Finding F-002)" out of the title. Cross-loop questions — how long has this been queued, was it deferred or is it new — are unanswerable until identity is machine-readable.

35. **convergence-pass coverage (G43, v4+, loop >= 4)**: a dimension owed a convergence pass — sub-9.5 with `delta == "SAME"` across this loop and the two prior (Stalled-Dimension Sweep), or `score >= 9.5` with `residual_disposition: "accepted"` (Adversarial Pass) — must be named by a `convergence_pass[]` record or by a `backlog[]` item's `score_impact`. Each record carries a non-empty `surface_walked`; `outcome: "candidate"` carries a `finding_stable_id` resolving in this loop's `findings[]`; `outcome: "clean"` carries a non-empty `clean_rationale`. **From the third consecutive `clean` on a dimension**, the record must also carry `proposed_fix` — `(fix_kind ∈ canon/fix-kinds.toml, target_path, target_symbol)` — whose triple differs from that dimension's triple in the prior loop, plus `spt_question_failed`. Novelty is judged on the triple, never on `note` or `clean_rationale`: free-form wording defeats recurrence detection, so rewording is not a new proposal. Floor `loop >= 4` because loop 1's `delta` is `SAME` by definition.

36. **HALT_SUCCESS panel (G32, v5+)**: at `schema_version >= 5`, `halt_success_challenge` is a panel of 3 staged challengers, not a single challenger — full shape and aggregate/state coupling invariants live in [validation.md § G32](validation.md#hard-gates-must-pass-before-emit) and the v5 object schema in [output-format-json.md § Schema version 5 changelog](output-format-json.md#schema-version-5-changelog). Per-member retry envelope enums: `retry_attempts[].outcome ∈ {ok, timeout, spawn_error, malformed_json, budget_exhausted}`; `retry_cause ∈ {timeout, spawn_error, malformed_json, budget_exhausted}` (`budget_exhausted` is the v5 addition to both, alongside rule #25's `implementation_review` enum). A `budget_exhausted` attempt's verdict is discarded and consumes one retry; `C_max` is a per-**attempt** cap, so a legitimately retried member may approach 2×`C_max` aggregate usage without any accepted attempt violating the envelope.

37. **exhaustion record shape + honesty coupling (G45, v4+)**: `exhaustion` is required non-null iff `state == "HALT_EXHAUSTION"`; null otherwise. When present: an object with exactly `kind`, `detection_mode`, `evidence` — all non-empty strings, `kind`/`detection_mode` ∈ `canon/exhaustion-kinds.toml`. `detection_mode == "preventive_step_budget"` ⟹ `kind == "unknown"` — a preventive checkpoint cannot distinguish context pressure from a spend limit from any other cause. Only `"user_reported"` may claim `"context_pressure"` or `"spend_limit"`. Full handoff template + the three-deaths note: [halt-handoff.md § HALT_EXHAUSTION](halt-handoff.md#halt_exhaustion-schema_version--4).

38. **general remediation fields (G46, v4+)**: `loop_result.finding_family`, `.effort`, and `.repair_revalidation` are required together whenever `loop_result` is present (rule #8's trigger); a queued backlog item carries none of them. `finding_family ∈ canon/remediation-fields.toml finding_families`; `effort ∈ {trivial, small, moderate, large}`; `repair_revalidation` mirrors `risk_boundary_evidence`'s shape (rule #29): `{outcome ∈ canon/remediation-fields.toml repair_revalidation_outcomes, detail <non-empty>, mechanically_testable <bool>, drift_notes}`, `drift_notes` required non-empty for every outcome except `INVARIANT_HOLDS` (one-directional) — full rationale: [validation.md § G46](validation.md#hard-gates-must-pass-before-emit). `disposition` and a widened `fix_kind` are family-conditional and DEFERRED, not part of this rule.

Both CURRENT_REVIEW.md / .json AND `findings_registry.json` AND `REVIEW_HISTORY.json` (v2+) are committed at end of each loop alongside the code change.
