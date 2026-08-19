# Item 26a — Computed Evidence Anchoring: Measurement + Closure (2026-08-19)

## Verdict: measured, not warranted

Item 26a would have typed every `evidence[]` citation, resolved it against the source tree at the
revision it was written for, and derived a strength grade from the result. It was planned, peer
reviewed over two rounds (codex `gpt-5.6-sol`, high), and **closed on measurement before any code
was written**.

The gap is real in the abstract: **G3** (`scripts/_artifact_core.py:328`) asserts only that
`evidence[]` is a non-empty list of non-empty strings. Nothing parses a citation, pins its
revision, or types it — precisely Gap 24's diagnosis (`docs/review-skill-deep-dive-2026-08-17.md:1028`).

It is not a defect in practice. Measured across the skill's own dogfood corpus:

| Outcome | Count | Share |
|---|---|---|
| Locator-kind citations (`file_span` 46, `symbol` 1) | 47 | 76% |
| — resolve at their recorded observation sha | **35** | |
| — **fail to resolve** | **0** | **0.0% of locators** |
| — no observation revision recorded (`<pending>`) | 12 | |
| Non-locator evidence, untyped today | 15 | 24% |
| **Total citations** | **62** | |

Corpus: `REVIEW_HISTORY.json` at the repo root — 15 real loops of `/contest-refactor` run against
this repository, the only multi-loop production corpus that exists.

**Zero locator failures.** The plan carried a preregistered enforcement threshold of a 10%
unresolved rate, written before the number was known. The measured rate is 0%, so the rule
this document is honouring is its own: enforcement is unwarranted, and the telemetry that would
measure it would report nothing on the only corpus available.

## The reproduction ladder

Deterministic and registry-only. Re-running it on the same corpus must return
**47 locators / 35 resolved / 0 unresolved / 12 no-revision / 15 non-locator**. A different number
means the ladder below is not the one that was run — the exact failure that produced both
corrections in the next section.

**Revision selection**, for a citation in `loops[N].findings[i]` with `sid = findings[i].stable_id`:

1. `findings_registry.json` entry where `stable_id == sid`; absent → `sha_unavailable`.
2. That entry's occurrence with `loop == N` **and** `status == "open"` **and** a `sha` that is
   present and does not begin with `<` → use it. (23 citations.)
3. Else, if `entry.first_seen_loop == N` and `entry.first_seen_sha` is present and does not begin
   with `<` → use it. (23 citations.)
4. Else → `sha_unavailable`. (16 citations; 12 of them locator-kind.)

**Never `HEAD`, and never a commit search.** Both are covered in Corrections below.

**Classification.** Split the entry at the first ` --`, ` —`, or ` (` and classify the head:

| Pattern | Kind |
|---|---|
| `path:N` or `path:N-M`, all digits | `file_span` |
| `path.ext:identifier` | `symbol` |
| contains `*`, `?`, or `[` | `glob` |
| bare `path.ext` | `file` |
| bare lowercase identifier | `field` |
| anything else | `observation` |

**Resolution** reads blobs with `git show <sha>:<path>` — never the working tree, so a dirty
worktree is irrelevant. `file_span` requires `1 <= start` and `end <= line_count`; `symbol`
requires the identifier to appear in the blob.

The non-locator bucket is reported as a single aggregate (15). Its internal split between `field`,
`glob`, and `observation` is sensitive to the head-split rule — a citation like
`candidate_commit_sha:3e51000` lands in `field` or `observation` depending on how the tail is cut
— and no conclusion here rests on that split, so sub-typing it would be false precision.

## Two corrections, both found by peer review

Recorded because each inflated the case for building, and each is a trap a later author would
re-enter.

### 1. The HEAD fallback (round 1 claimed "24% unresolvable")

The first prototype resolved against `HEAD` when no observation revision was recorded — the exact
fallback the plan's own text forbade. It covered **56% of the corpus**. Files split or moved since
then read as broken citations while being perfectly valid: `scripts/validate-artifact.py:143-2255`
is a real loop-9 citation, valid at its own revision, and 10× out of range at `HEAD` because the
file was later split from ~2,300 lines into the `_artifact_*.py` modules and now runs to 226.

### 2. Commit-subject grep is not an identity (round 2 claimed "the revision sources disagree 5/5")

They do not disagree. The second prototype recovered a revision by `git log --grep '^loop N:'` and
taking the parent of the matching commit. **Every loop has more than one commit with that
subject** — a candidate-recording commit and a later demotion or final commit — and the prototype
selected the wrong one. Against the correct commit the registry sha equals the parent in all five
loops where both sources exist:

| Loop | Final commit | Parent | Registry `open` sha |
|---|---|---|---|
| 1 | `bc95c5e` | `3d220c5` | `3d220c5` |
| 4 | `d936e65` | `3e51000` | `3e51000` |
| 6 | `b33ccc0` | `6c80090` | `6c80090` |
| 10 | `d30fd42` | `b483d55` | `b483d55` |
| 14 | `be014c4` | `1677db4` | `1677db4` |

The registry and git agree exactly. There is no revision ambiguity to resolve, and the ladder
above therefore needs no git search at all.

**The generalisable rule, which outlives this item:** a resolver that *searches* for a revision
manufactures findings. Any future evidence work binds to a recorded sha or reports `unavailable`.
Both corrections were the same error wearing different clothes — guessing a revision when none was
recorded — and it survived one round of review before being caught.

## What survives as real, and why neither justifies code yet

1. **12 of 62 citations (19%) have no recorded observation revision.** `status: resolved`
   occurrences store the literal `<pending>` because the resolution commit does not exist when the
   occurrence is written, and for a finding first seen and resolved in the same loop no other
   record carries the observation sha. The registry schema
   (`references/output-format-state-schemas.md:225-232`) defines four different meanings for
   occurrence `sha` by status, only one of which is the observation revision.
2. **24% of evidence is not a locator** and is indistinguishable from one today. Citing
   `candidate_commit_sha` is legitimate when the artifact schema is what is under review; a glob is
   legitimate evidence about a file set. A naive `path:line` gate would have been roughly 11/13
   false-positive on this bucket — the reason the plan reached for a typed grammar rather than a
   stricter parser.

Neither has a consumer. Nothing reads a typed citation, and nothing reads an observation revision.
Building either now is speculative work against an imagined reader.

## Reopening trigger (preregistered)

Rebuild the corpus and reconsider when **either**:

- the unresolved locator rate exceeds **10%**, or
- a consumer for typed evidence exists — most likely **item 23's lenses**, which cannot emit
  findings under an untyped Source contract, per the tranche-5 ordering that puts item 26's output
  contract before any new lens emits production findings (`deep-dive:1244`).

## Collision check

- **Item 6 (confidence)** — untouched. Evidence strength was to be per-link and derived; confidence
  is finding-level and still an open three-way comparison.
- **Item 27 (disproof)** — untouched. Its verdict answers "is this finding real"; anchoring answers
  "does this citation point at real bytes".
- **Item 28 (remediation)** — untouched; `repair_revalidation` shipped as G46 and concerns the fix,
  not the evidence.
- **Grade `A`.** The plan would have derived it from
  `loop_result.risk_boundary_evidence.verification`. Peer review was right to kill this: that field
  is model-authored, loop-scoped, and attached to no particular evidence link. Item 14's design
  (`ITEM14-HOST-ATTESTATION-DESIGN-2026-08-18.md`) already established that no harness here offers
  an attestation boundary, so grading it `A` would have reintroduced exactly the self-reporting the
  item exists to replace. If strength grading is ever revived, `A` requires a citation-level
  execution record carrying item 14's attestation-or-downgrade status.

## Cost

Two peer-review rounds and read-only analysis. No code, no schema, no canon, no loop-path tokens.
The per-loop reload budget (84,115 / 84,200) is untouched.
