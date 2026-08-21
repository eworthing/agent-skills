# G17 adjudication packet — historical datapoints from the BenchHype post-hoc sweep

Assembled 2026-08-21 from `reports/benchhype-posthoc-sweep-2026-08-21.json` and the cited
commits' artifact blobs (read-only). Each datapoint carries a PROPOSED disposition — check the
box to adopt it or write a different one. Once adjudicated, the tallies feed the G17 promotion
bar; entries are recorded in the register (the behavioral-validation ledger was consolidated
into `docs/contest-refactor-review-register.md` at its deletion).

## Datapoint 1 — `acbcd48db` (2026-05-09, loop 1, schema v2, CONTINUE)

- `what_changed`: "Consolidated board and settings draft save paths through savePendingDraft
  and extended PendingSaveDraft to both draft types."
- `changed_paths`: absent (v2 — the field arrived at v3)
- `interface_test_coverage_path`: **4 fully-populated entries** (AppReducerTests.swift ×2,
  AppReducerTests+SaveAttemptIdentity.swift ×2; all `existing_deepened`,
  `distinguishes_no_op: true`)
- Diagnostic: `[g17-check-blind reason=changed_paths absent or empty (v3+ field) loop=1]`

**PROPOSED — [ ] expected-blind, loop compliant.** The blind is correct behavior (v2 cannot
distinguish "no test changed" from "field absent"), and the loop itself cited coverage fully.
Counts as: applicable ✓, blind (adjudicated-correct) ✓, violation ✗, restraint ✗.

## Datapoint 2 — `2caa30e4b` (2026-05-25, loop 1, schema v3, CONTINUE)

- `what_changed`: "Rewrote docs/core-architecture-primer.md Section 7 (Add-sound import
  workflows) to match current source: consolidated the stale 'three coexisting models'
  framing to two distinct choreography models …"
- `changed_paths`: `['docs/core-architecture-primer.md']` — **docs only, no code**
- `interface_test_coverage_path`: null
- Diagnostic: `[G17] loop 1: what_changed is a deepening refactor and no test file appears…`

**PROPOSED — [ ] FALSE POSITIVE.** The keyword "consolidated" matched prose about rewriting a
primer; no interface was deepened and no test could meaningfully cover a docs rewrite.

**Consequence (owner decision, not changed in this repo yet):** the promotion bar requires
**zero false positives**, so adopting this disposition blocks promotion until the trigger is
refined — e.g. additionally require ≥1 `changed_paths` entry that classifies as a code file
(not docs/markdown). Estimated cost: one condition in
`scripts/_artifact_coverage_citation.py` + a RED/restraint fixture pair + selftest cases;
validator-side only, zero loop-token cost. Alternative: adjudicate as a true-but-trivial
violation and keep the trigger as-is (rejects the refinement, keeps the bar reachable).

## Datapoint 3 — `d19cfd214` (2026-08-16, loop 12, schema v4, HALT_LOOP_CAP)

- `what_changed`: "BulkProgressView.swift: dropped `.task`, `.onDisappear`, `@State
  dispatched`, and the `urls: [URL]` property; AddSoundSheet.swift: `Step.bulkProgress(urls:)`
  is now payload-free, the `onImportAll` gesture now dispatches …"
- `changed_paths`: 2 Swift source files (AddSoundSheet.swift, BulkProgressView.swift); no test
- `interface_test_coverage_path`: null

**PROPOSED — [ ] TRUE violation.** A real interface deepening (payload-free step case,
lifecycle moved to the gesture) committed with no coverage citation.

## Datapoint 4 — `b731a849d` (2026-08-19, loop 2, schema v4, HALT_SUCCESS)

- `what_changed`: "F-011's helper landed at AppReducer+Workflow.swift:248-274; the three
  persist* arms collapsed to one-liner wrappers … ~75 lines of duplicated body → ~12-line
  helper + three ~5-line wrappers …"
- `changed_paths`: `['BenchHypeKit/Sources/BenchHypeApplication/Reducer/AppReducer+Workflow.swift']`
- `interface_test_coverage_path`: null

**PROPOSED — [ ] TRUE violation.** The textbook trigger: helper extraction ("collapsed"), one
non-test source file, no citation — on the terminal artifact of a HALT_SUCCESS run.

## Tally vs the promotion bar (assuming all proposals adopted)

| Bar requirement | After adjudication | Status |
|---|---|---|
| ≥5 applicable runs | 4 (all Swift) | open |
| ≥1 observed true violation | 2 | **met** |
| ≥2 restraint cases | 0 | open |
| ≥2 languages | 1 (Swift) | open — needs a non-Swift run (Python dogfood candidate) |
| zero unadjudicated blind lines | 1 blind, adjudicated-correct if D1 adopted | met on adoption |
| zero false positives | **1 if D2 adopted** | **blocks promotion → trigger decision above** |

Promotion cannot close this cycle regardless of the next run's outcome (single language); the
load-bearing decision in this packet is D2's disposition.
