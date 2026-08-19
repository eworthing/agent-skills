# Item 24 — Coverage Unit, Snapshot, and Resume: Design Note (2026-08-19)

Tranche 5 requires this note before any code: *"Item 24 splits into selection + coverage manifest,
resume/invalidation, and traversal priors — and needs its design note to define the coverage unit,
the snapshot/invalidation model, crash-consistency, and the relationship to `--scope`, `--cap`, and
the registry"* (`docs/review-skill-deep-dive-2026-08-17.md:1234`). No code in this pass.

## 1. The recorded tension, and why it dissolves

`DOMAIN-AWARE-SCANNING-GAP.md` was deferred with evidence on both sides (`deep-dive:708`): levnik
**abandoned** its `domain_mode`/`scan_path` partitioning in the Skills v2 rewrite, center-audit
forbids partitioned traversal by doctrine, and only mhylle keeps it — the one exemplar whose
product is long-running full-repo audit. Two of three point away.

The tension dissolves once the product shapes are compared rather than the mechanisms.
**contest-refactor is not a one-shot traversal.** It is a capped iterative loop over a single
repository, carrying a findings registry across loops, whose unit of work is a backlog item and
whose terminal states are convergence or exhaustion. mhylle partitions because one pass over a
large repo does not fit in one context. We do not have that problem: we have the *opposite* one —
many passes, each cheap, each free to look wherever it likes, and **no record of where any of them
looked**.

So the question item 24 answers is not *"how do I split a traversal and resume it"* — that is
levnik's abandoned design, and adopting it would be the mistake the deferral avoided. It is:

> Across N loops, which first-party source has the Critic **never examined**, and does the handoff
> say so?

That is a **negative-space ledger**, not a traversal partition. The registry already records the
positive space (every finding, with `first_seen_loop`, `last_seen_loop`, and `primary_file`); what
is missing is its complement. Framed that way, alibaba's manifest discipline is importable and
levnik's partitioning is not — which is the reconciliation the deferral was waiting for.

## 2. The coverage unit

**Recommendation: the first-party source file.**

Reuse the filters that already ship and are already shared: `scripts/audit_boundaries.py`'s
`IGNORE_DIRS`, `_is_test_file`, `_is_generated_file`, `_collect_py_files`, `_source_root`. These
are imported directly by `scripts/repo_map.py` rather than mirrored — an established single source
of truth with no drift hazard — and `repo_map.py` already persists `first_party_file_count` "so the
auto-engage decision is reproducible", which is exactly the denominator a coverage ledger needs.

Alternatives considered and rejected:

| Unit | Why not |
|---|---|
| Module / package | Too coarse. A 600-line file inside a "covered" package can be entirely unread, and the coverage claim would be false at the grain users care about. |
| Line span or hunk | Too fine. No loop reads at that grain, and a line-level ledger would need exactly the citation-anchoring machinery that **item 26a was just closed as unwarranted** (`ITEM26-EVIDENCE-ANCHORING-2026-08-19.md`). Building a consumer for machinery we declined to build is backwards. |
| Review-question × file | alibaba's shape, and correct for one-shot diff review. It multiplies the ledger by a lens taxonomy that **item 23 has not defined yet** and cannot define until it has a discriminating corpus. Premature. |

The unit is deliberately *coarser* than the evidence grain. A coverage ledger answers "was this
looked at", not "was this understood" — and conflating the two is how a coverage number becomes a
quality claim it cannot support.

## 3. The blocking prerequisite — FIXED 2026-08-19, and worse than first written

> **Update.** The first draft of this section said `--scope` "is never persisted". Checking the
> premise before building — the discipline item 26a's closure earned the hard way — showed the
> defect was larger: **`--scope` had no defined effect at all.** Fixed the same day; the record
> below is kept because the shape of the miss is the useful part.

**`--scope <dir>` was advertised, recommended, and never read.** It appeared in SKILL.md's
`argument-hint`, in startup.md's "Parse user flags" sentence ("Record for later steps"), and in
`halt-handoff.md:136`, which actively tells users *"Scope down — re-invoke as
`/contest-refactor --scope <dir>`"*. **No step ever read it.** Step 0 step 2 scanned CWD
unconditionally; `source_roots` was never narrowed; nothing recorded the narrowing.

Its one downstream consumer already expected it: `scripts/preflight.py`'s first positional is
documented as `<scope-dir>`, "source/scope directory that must exist before review starts", and its
docstring names "a scope dir that isn't there" as the canonical bad input. The consumer was built
for the flag while the producer ignored it.

A repo-wide audit put the miss in relief: every other advertised flag defines its effect at 3–40
sites; `--scope` had **zero**, its only non-parse mention being the handoff recommending its use.
So a user following the skill's own advice got a whole-repo run and a whole-repo scorecard.

Two consequences, the second larger than item 24:

1. **No coverage number is interpretable.** Coverage is a fraction, and its denominator is exactly
   what `--scope` changes. A ledger built before this is recorded would silently report scoped
   coverage as whole-repo coverage.
2. **Independent of item 24, this is an artifact-honesty defect.** A scoped run emits a scorecard
   and a verdict that read as claims about the repository, and nothing in the artifact discloses
   that only a subdirectory was examined. The HALT_SUCCESS challenger re-derives from the same
   artifact and would inherit the same blind spot, and `halt-handoff.md:136` actively *recommends*
   `--scope <dir>` as a remedy — so the flag sits on a path users are told to take.

**Shipped, and cheaper than the field this section originally proposed.** Step 0 step 2 now
carries the effect: under `--scope <dir>` the scan is restricted to `<dir>`, so
`discovery.source_roots` records the narrowing and G40 carries it forward every loop, `<dir>` is
the `<scope-dir>` preflight receives, and the Discovery section and any HALT handoff must state
that the scorecard is a claim about `<dir>` rather than the repository. **No new field was needed**
— `source_roots` already records it. The residual distinction (roots *detected* vs roots *imposed
by the user*) has no consumer today and is deliberately not built.

Guarded by `scripts/_flag_effect_selftest.py`: the flag set is **discovered** from SKILL.md's
`argument-hint`, and each flag must have its effect defined at a registered site, counting neither
the advertisement nor the parse list. Advertising a flag without registering where it acts fails;
deleting the operative prose fails. That is the discovery-tripwire shape recommended in
`ITEM3-HARD-RULE-PROPAGATION-2026-08-19.md` for the enumerate-only dispatch audits — applied here
first because the flag list has a machine-readable source and the dispatch-prompt set does not.
Verified in both directions, including a temporary fake flag that the guard rejected.

## 4. Snapshot and invalidation

Follow the rule item 26a's closure established the hard way: **bind to a recorded revision, never
search for one.** A resolver that searches manufactures results — that error survived a round of
peer review twice in one week.

- Every coverage record carries the `sha` it was computed at, taken from the loop's own observation
  revision, never from `HEAD` and never from a commit-subject search.
- **Two identities per unit**, following alibaba: the stable path (`ItemID`) and a content
  fingerprint (`Fingerprint`). Path identity survives edits; the fingerprint is what invalidates.
- A unit whose fingerprint changed since it was examined is **`stale`**, not `covered`. Silence
  about staleness is how a coverage ledger becomes a lie about a repository that has moved on.
- A renamed file is a new `ItemID` with a matching fingerprint — detectable, and reported as such
  rather than resolved automatically, because rename detection is a heuristic and this ledger's
  whole value is that it does not guess.

## 5. Terminal state is derived, never stored

alibaba's rule, adopted in spirit: *"selected … equals the disjoint union of completed, reused,
failed and waived"*, with the terminal state **derived from coverage, never stored**. Here:
`selected == examined ⊎ skipped ⊎ stale ⊎ never_examined`, with disjointness asserted, and every
`skipped` carrying a **typed exclusion reason** rather than free text. A stored terminal flag can
disagree with the parts it summarises; a derived one cannot. This is the same discipline
`_paired_arm_validate.py` applies to attempt states and `_artifact_residual.py` to residual
accounting — house style, not an import.

## 6. Crash consistency

Nothing new is needed. The loop already commits its artifacts once per loop, and the paired-arm
study established git-as-checkpoint as this repo's answer to partial writes: a record exists iff it
is committed, resume reads committed history, uncommitted work does not exist. Coverage entries are
written **in the same commit as the loop's artifacts**, so they inherit atomicity and can never
disagree with the loop record they belong to. No sidecar, no lock file, no completion marker — an
earlier design in this repo tried all three, and peer review found five race and crash holes in
that machinery before it was deleted in favour of git.

## 7. Relationships

- **`--cap N`** — the cap bounds loops, so coverage is *inherently* partial and that is not a
  defect. The ledger's job is to make partiality visible **in the handoff**, which is where
  `halt-handoff.md` already tells the user to scope down or bump the cap. A coverage line there
  turns that advice from a guess into a fact.
- **`--scope`** — narrows the denominator; must be persisted first (§3).
- **The findings registry** — tracks the positive space and joins the ledger on `primary_file`. A
  file carrying a finding is necessarily `examined`, which gives the ledger a free consistency
  check against a record that already exists: every registry `primary_file` must appear as
  `examined` at the loop that recorded it. Worth building before any other consumer, because it is
  a cross-check between two independent records rather than a new claim.
- **Item 23's multi-run recall** — depends on this: prior-run gap targeting needs cross-run state
  keyed to fingerprints (`deep-dive:1233`). Item 24 is upstream of it.

## 8. Slice contract

Per tranche-5's requirement that every slice carry a deterministic acceptance test, a cost ceiling,
a promotion threshold, and a rollback trigger:

| Slice | Acceptance | Ceiling | Promotion | Rollback |
|---|---|---|---|---|
| **A. Give `--scope` an effect** — **DONE 2026-08-19** | `_flag_effect_selftest.py`: every advertised flag has a defined effect at a registered site; a new unregistered flag fails | 1 prose sentence + 1 selftest; **zero loop-path tokens** (`startup.md` is main-agent-only, budget unchanged at 84,115/84,200) | shipped on its own merits (honesty fix) | revert one sentence; no schema, no field, no artifact migration |
| **B. Ledger + derived terminal state** | disjointness asserted; every registry `primary_file` appears `examined` at its loop | one module < 400 LoC, report-only first | the registry cross-check finds ≥1 real inconsistency, or a consumer exists | report-only flag, as `_artifact_transitions.py` |
| **C. Fingerprint invalidation + resume** | a mutated file flips `covered → stale` deterministically | reuse `_fingerprint.py` normalisation | B stable across ≥5 real loops | drop to path-only identity |
| **D. Churn prior + escalate-on-hit** | ordering reproducible from a fixed sha | tech-audit's top-30 heuristic | measured against flat ordering | ordering is advisory; disable |

## 9. Recommendation

**Slice A is done; B–D stay behind a consumer.** Slice A turned out to be a correctness bug rather
than a coverage prerequisite — an advertised flag with no implementation — and it had a reader
today: the challenger, and any human reading a scoped run's scorecard. B–D have no consumer until
item 23's multi-run work exists, and item 23 is itself gated on a discriminating corpus. The lesson from item 26a applies directly: **machinery with no reader is speculative work**,
and this repo has just spent a review cycle proving it.
