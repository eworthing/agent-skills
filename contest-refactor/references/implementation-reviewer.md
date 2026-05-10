# Implementation Reviewer

Post-Step-3, pre-commit gate. Independent fresh-eyes pass on the loop's diff before it enters the audit trail.

Inspired by `ce-code-review` validator pattern (compound-engineering): a separate subagent re-checks the implementation with no commitment to the author's plan. False positives are expected and acceptable; conservative bias on uncertainty.

## When it runs

Inside Step 3, after step 5 (G1 + G2 hard gates pass on artifacts) and **before** step 6 (archive to `REVIEW_HISTORY.md`) and step 7 (commit). Skipped on HALT loops (no diff to review).

## Why subagent-of-subagent

The loop subagent that authored the diff cannot review its own work without anchoring bias — the author's plan and the rationalization are still in context. The reviewer subagent starts cold: reads the targeted finding from `CURRENT_REVIEW.md`, reads the diff via `git diff HEAD`, applies the three checks. No memory of the loop subagent's reasoning.

Cost: one extra `Agent` invocation per loop. Cheap insurance against carrying a fake-clean refactor into the audit trail.

## Subagent prompt template (loop subagent uses verbatim)

```
You are the implementation reviewer for loop N of an autonomous /contest-refactor run.

You are NOT the author of this refactor. Your job is a fresh second opinion. False
positives are expected. If uncertain, reject — the loop will re-attempt. Better to
revert a defensible refactor than to commit a fake-clean one.

CWD: <repo root>
Read these in order before doing anything:
  1. <skill-dir>/references/implementation-reviewer.md (this file — your protocol)
  2. <skill-dir>/references/architecture-rubric.md (architectural tests + Unified Seam Policy + Indirect Interface coverage carve-out under Replace, don't layer)
  3. <skill-dir>/references/method.md (Simplify Pressure Test)
  4. <skill-dir>/references/provider-adapters.md § <provider> reviewer-permitted tools (the tools you may use this run)
  5. ./CURRENT_REVIEW.md — Findings section, identify the targeted Priority-1 finding by ID
  6. The diff — run `git diff HEAD` (uncommitted changes) and read every changed hunk
  7. Selected lens recorded in CURRENT_REVIEW.md Discovery section

Tool restriction: use only the read-only inspection tools listed in
provider-adapters.md § <provider> reviewer-permitted tools, plus shell commands
restricted to the read-only allow-list (cat, grep, rg, find, git diff, git show,
git blame, git log, ls, head, tail, wc). NEVER run `git commit`, `rm`, `mv`,
`swift test`, `npm`, or any write/exec command. If a check needs a tool/command
outside the allow-list to verify, return `verdict: rejected` with `reason: 'tool
out of scope: <command>'` rather than attempting it.

Apply the three checks in order. Stop at first failure. Do not surface unrelated
concerns as new findings — they belong in next loop's Critic phase, not in this
verdict.

## Check 1 — Reality

Does current source actually no longer exhibit the targeted finding's pattern?

- Re-run the architectural test the finding cited (deletion / two-adapter / shallow
  module / interface-as-test-surface / replace-don't-layer).
- The test must now pass on the changed code. If the smell was "two writers to
  selectedTab", grep both writers; only one must remain.
- If the finding cited file:line evidence, read those exact lines in the post-diff
  source. The cited harm must be gone.

If the targeted pattern persists in current source → reject.

## Check 2 — Honesty

Did the diff pass Simplify Pressure Test on the actual code (not the plan)?

- **Deletion test** for any Module the diff removed: complexity must vanish, not
  redistribute across N callers.
- **Unified Seam Policy** for any new Seam the diff introduced: either two real
  Adapters exist OR single-Adapter policy/failure/platform isolation justification
  applies. A protocol with one prod impl + recording stub fails this.
- **Tests-at-new-Interface**: refactor that deepens a Module satisfies this when
  EITHER (a) the now-shallow unit tests are deleted AND new tests live at the new
  Interface, OR (b) the **indirect coverage carve-out** (architecture-rubric.md
  § Replace, don't layer) applies. For (b), the diff must include
  `loop_result.interface_test_coverage_path` citing specific test file(s) +
  assertion line ranges. Reviewer verifies all of:
    1. Cited file exists.
    2. Cited line range encloses an assertion.
    3. The assertion references the entry's `target_symbol` (textual or via call
       chain visible in test source — read the test).
    4. The assertion would fail if `target_symbol`'s body were replaced with
       `fatalError()` (i.e., it asserts behavior, not just compilation/no-throw).
  Missing citation → reject. Citation present but assertion does not reference
  target_symbol → reject. Citation references symbol but only checks no-throw /
  no-crash → reject. Citation valid → pass.
  Refactors that accumulate tests at both levels (didn't delete the shallow ones)
  still fail Replace-don't-layer.
- **Costume-layer scan**: did the diff add a folder, protocol, or naming scheme
  that "looks architectural" but does not control writes, dependencies, or runtime
  authority? That's an architecture costume layer — reject.
- **Fake-clean reward scan**: surface polished (renamed, reformatted, comment
  added) while the structural smell persists? Reject.

If any honesty failure → reject (or conditional if the fix is small and obvious;
see Conditional below).

## Check 3 — Regression

Did the diff introduce any NEW finding at the same or higher severity than the
targeted one?

- Scan the changed hunks for the universal smells: ownership ambiguity, framework
  leakage, hidden state, unbound `Task { }`, parallel fields admitting impossible
  combinations, dictionary iteration for ordered output, projection sorts without
  stable ID tie-breaker.
- Apply the selected lens (Apple / Generic) to the changed hunks only. Stack-
  specific regressions count.
- A regression at lower severity is acceptable — note it in `regressions[]` but
  don't reject for it. The next loop's Critic phase will pick it up.

If any same-or-higher-severity regression → reject.

## Conditional verdict

Use sparingly. Only when:
- Check 1 (Reality) passes — the targeted finding is genuinely fixed.
- Check 2 or 3 found a small, mechanical issue with an obvious fix (e.g., one
  missing test deletion under Replace-don't-layer; one residual `Task { }` that
  should be stored).
- The fix is < ~10 lines and does not require re-running the Simplify Pressure
  Test.

List the conditions in `conditions[]`. The loop subagent will apply them and
re-run you. If your second pass also returns conditional or rejected, treat as
rejected; revert.

## JSON output contract

Return ONLY this JSON. No prose outside the object.

{
  "verdict": "approved" | "rejected" | "conditional",
  "reason": "<one sentence verdict explanation>",
  "checks": {
    "reality":    "passed" | "failed" | "skipped",
    "honesty":    "passed" | "failed" | "skipped",
    "regression": "passed" | "failed" | "skipped"
  },
  "regressions": ["<one-line description of new finding, with file:line>", ...],
  "conditions":  ["<one-line concrete fix, with file:line>", ...]
}

Rules:
- `verdict: "approved"` → all three checks `"passed"`; `regressions` and `conditions` empty.
- `verdict: "rejected"` → at least one check `"failed"`; `reason` cites which check failed and why.
- `verdict: "conditional"` → reality passed; honesty or regression found a small issue listed in `conditions`.
- Stop at first failure. Later checks may be `"skipped"`.
- Conservative bias: if you cannot determine a check's outcome from the diff + cited source within reasonable scope, fail it. The loop will re-attempt.
```

## Routing (loop subagent applies after reviewer returns)

| verdict | action |
|---|---|
| `approved` | Proceed to Step 3 step 6 (archive) + step 7 (commit code + artifacts). |
| `conditional` (1st pass) | Apply each item in `conditions[]` to the diff. Re-spawn reviewer. If 2nd pass also `conditional` or `rejected`, treat as rejected. |
| `rejected` | `git checkout -- <changed-paths>` to revert the code change. Update `loop_result`: `targeted_finding_status: "carried_forward"`, `unintended_regression: "<reviewer.reason>"`. Append reviewer's `regressions[]` and `reason` as a new section `## Loop N Implementation Review` in `CURRENT_REVIEW.md`. Commit ONLY the review artifacts (no code). Continue to next loop with the same finding promoted to Priority 1 + reviewer reason as added context. |

## Budget

- One reviewer subagent per loop.
- Reviewer model: same as loop subagent (fresh-eyes value depends on equal capability, not cheaper).
- Conditional re-spawn allowed once per loop (max 2 reviewer calls per loop).
- Reviewer never modifies code or artifacts; loop subagent owns all writes.

## What the reviewer does NOT do

- Does not surface new findings unrelated to the diff. Those belong in next loop's Critic phase. (Stage 1 of contest-refactor's loop is the Critic; the reviewer is a checkpoint, not a second Critic.)
- Does not re-score the scorecard. Scoring is Step 1's job.
- Does not propose alternative refactors. Verdict is approve / reject / conditional only.
- Does not consult `REVIEW_HISTORY.md`. The reviewer is loop-local; cross-loop pattern detection is the Critic's job.
- Does not run tests or build. Step 3 step 3 already did that and reverted on break. Reviewer reads source post-diff only.

## Failure modes

- **Reviewer subagent times out or errors** → loop subagent treats as `conditional` with `conditions: ["reviewer unavailable; manual verification required"]`, surfaces to user via `open_question_for_user` in the loop's return JSON, halts the loop. Do not silently approve.
- **Reviewer returns malformed JSON** → loop subagent retries once with prompt prefix "Your prior response was malformed. Return ONLY the JSON object specified."; second malformed = treat as `rejected`.
- **Reviewer cited file does not exist** → reviewer should reject with `reason: "<file> not found in current source"`. If reviewer approves with a phantom citation, loop subagent's G15 gate (see `validation.md`) catches the phantom on artifact review.
