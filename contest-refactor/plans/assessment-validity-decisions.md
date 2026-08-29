# Decision Record — Contest-Refactor Schema v6 Assessment Envelope

**Status:** settled. D1–D9 were adjudicated by opencode/glm-5.3 over four rounds
and accepted, stable across three consecutive rounds. D10 was revised every round
and is **decided here on the round-4 basis by owner instruction**, after a fifth
review round timed out twice with no output.

The decisions are folded into
[`assessment-validity-implementation-plan.md`](assessment-validity-implementation-plan.md).
This document is the rationale: options considered, verified facts, and the blast
radius if a call is wrong. Wave 0 of the plan writes the approved set into the
specification before any code lands.

**What this is.** A code-review/refactor-loop skill emits a JSON artifact
(`CURRENT_REVIEW.json`) per loop. An approved specification adds schema version 6:
an `assessment` envelope carrying applicability, coverage, claim ceilings,
provenance, measurements, residuals, pipeline failures, and cost, policed by two
new validation gates (G51 model integrity, G52 eligibility). The design is
deliberately report-only: no certification, no aggregate score.

**Existing machinery these decisions touch.** A closed-vocabulary canon
(`canon/*.toml`) is the single source of truth for every enum and shape rule. A
fixture corpus (102 directories) pairs each "flag" artifact that must FAIL a gate
with a "restraint" artifact that must PASS, and the fixture runner already
asserts that a failing fixture fails for its *cited gate*. A Tier-1 execution
wrapper (`attested_run.py`) runs a command as a true child and appends a ledger
record; gate G47 checks that an artifact's citation resolves to a real record. A
gate G29 requires an artifact's declared `schema_version` to EQUAL a
capability-derived version, looked up in a capability manifest. Artifacts bind
`source_rev` (the reviewed repo) and `skill_rev` (the skill repository revision).

**How to read each entry.** *Verified* facts were established by running code or
reading source, not inferred. *If wrong* states the blast radius.

---

## D1 — Where the pre-handoff validation record attaches

**Question.** The specification requires an artifact to link evidence that strict
validation ran before the completion handoff, and describes hashing the artifact
with `execution_evidence.validation` nulled. Where does that field live?

**Verified constraint.** No such path exists. Today `execution_evidence` is a
single flat object at `loop_result.execution_evidence` holding one citation
(`{event_id, attestation_status}`), documented as `object | null`. Exactly two
fixtures carry a non-null value; both are schema v4.

**Options.** (a) At v6 the field becomes a keyed map,
`{"build": entry|null, "validation": entry|null}`, with the gate reading the flat
shape for v≤5 and the keyed shape for v6. (b) A sibling field
`execution_evidence_validation`. (c) A second top-level evidence surface.

**Decision: (a),** with two conditions:

1. **One owner for the serialization.** The "null the validation entry,
   canonicalize, hash" operation has a single shared implementation used by both
   the wrapper and the validator — the same pattern as D2. Two implementations
   that null or canonicalize differently would compare incomparable bytes.
2. **Migration parity is asserted, not assumed.** The v6 keyed `build` entry is
   policed by exactly the rules the flat v≤5 object carried, and a v6 artifact
   presenting the flat shape fails shape validation. Both get flag fixtures,
   because a shape migration is where a new version silently becomes an escape
   from a rule the old version already enforced.

**If wrong:** the wrapper and the validator hash different things, and the digest
check silently compares incomparable bytes.

---

## D2 — Who owns the derived scope-line rendering

**Question.** Gate G52 requires the user-facing handoff's scope line to equal a
value recomputed from the coverage records, by exact string equality. Who owns
the single implementation?

**Options.** (a) A pure derivation module imported by both the validator and the
report renderer, importing neither. (b) The validator owns it, renderer imports
it. (c) The renderer owns it, validator imports it.

**Decision: (a)** — `scripts/_assessment_render.py`. (b) and (c) each make one
consumer depend on the other's whole module for one string. Conceded: this is
closer to "forced by existing structure" than a genuine fork, and is recorded for
completeness rather than because it was contested.

**If wrong:** a heavier import edge, not a correctness failure.

---

## D3 — What the measurement registry contains at version 1

**Question.** Measurements are canon-registered: each `measure` declares its
unit, inclusive scale, and any threshold, and a value outside the registered
scale invalidates the record rather than being clamped. Which measures ship?

**Options.** (a) Exactly the two the specification exemplifies —
`score_mean_abs_gap` (points, 0–10) and `weighted_kappa` (coefficient, −1 to 1),
both threshold-free. (b) A broader set anticipating future measures.

**Decision: (a),** with one condition. The registry's **threshold mechanism**
would otherwise ship unexercised — no registered measure carries a threshold, so
nothing fails for the threshold path. That is the dormant-vocabulary defect
wearing mechanism clothes. The threshold field stays (the specification declares
it), and a self-test exercises the path against a **synthetic, non-canon
registration** so the mechanism is proven without shipping a dormant canon value.

**If wrong:** a legitimate emission is rejected until a canon edit lands. Cheap
and loud, which is the intended direction.

---

## D4 — How the canon loader exposes the new file

**Question.** The shared canon loader reads every `canon/*.toml` into a frozen
dataclass whose fields are flat tuples of strings. The new file is nested. How is
it exposed?

**Options.** (a) Load it into the loader's existing `extra` mapping behind a
typed accessor, validated fail-closed at load. (b) Add first-class dataclass
fields for its parts.

**Decision: (a).** The existing first-class fields are flat enums; this structure
is not, and `extra` already holds the non-enum scalars other files contribute.
Conceded, as with D2: forced by existing structure rather than contested.

**If wrong:** ergonomics only.

---

## D5 — How a version 6 artifact passes the schema-version gate

**Question.** Can a v6 artifact validate at all today?

**Verified constraint — the decisive one.** No. G29 requires `schema_version` to
EQUAL a capability-derived version; the capability function returns only `v4` or
`v5`; the manifest ships with **zero entries**, so every profile derives `4`.
The existing v5 fixtures escape only because G29 is epoch-scoped and the
classifier returns `LEGACY` for an artifact with no `skill_rev` — and
**verified: those fixtures carry no `skill_rev` at all.** A v6 artifact cannot
use that escape, because the specification requires a well-formed `skill_rev` and
treats a missing one as making `valid` impossible.

**Options.** (a) Add a `v6` capability outcome and map the required version
`{v4:4, v5:5, v6:6}`, then record one manifest entry for a reserved fixture-only
provider/model pair. (b) Defer admission and validate the new fixtures
gate-scoped. (c) Introduce a ruleset epoch whose boundary flips the required
version.

**Decision: (a).** (b) is **verified non-functional** — the fixture runner has no
per-fixture gate-scoping execution path; its gate logic is attribution, not
scope. Even if built, (b) would let restraint fixtures pass under a narrowed gate
set production never runs, which is fake corpus evidence. (c) forces v6 on every
post-boundary artifact while the emitter still emits v4.

**Three corrections carried with it:**

1. **The false acceptance text is amended, not merely noted.** The specification
   says "version 5 emission remains the observable default"; that is false
   (derived default is v4; v5 is unreachable with an empty manifest), and
   decision (a) *preserves* the falsity rather than fixing it. The same change
   amends the text to the true invariant: **production pairs derive v4; the
   reserved fixture pair derives v6; no pair derives v5.** Leaving it would push
   a later acceptance run toward adding a v5 manifest entry to make it true —
   contradicting this decision.
2. **The v5 capability branch is now doubly dormant** (no manifest entry, and no
   pair deriving it). Recorded as explicit pre-existing debt, exercised only by
   its existing unit test, and not extended by this work.
3. **The pre-admission run's scope is stated honestly.** Running `--gates G51,G52`
   certifies the two envelope gates only — not general artifact validity, and not
   the other ~49 gates. It is sufficient as *admission* evidence and is not
   evidence that the artifact is otherwise well-formed.

**If wrong:** nothing in the design can be validated end to end. Every other
decision is downstream of this one.

---

## D6 — How the wrapper binds its digest input to the child command

**Question.** The wrapper hashes an artifact then spawns a validator as a child.
What guarantees the child validates the artifact the wrapper hashed?

**Options.** (a) The child command must contain exactly one literal `{input}`
token, which the wrapper substitutes; zero or two occurrences is a usage error
before spawning. (b) Scan the child's arguments for a path equal to the resolved
input and require exactly one match. (c) The wrapper constructs the validator
invocation itself.

**Decision: (a),** with the mechanics pinned: substitution is
**argv-token-level, never string interpolation into a shell command** (a spaced
path split by a shell is precisely the attest-A-validate-B failure); the path is
resolved to a canonical absolute form **before both** hashing and substitution;
and the ledger records the **substituted** command, not the template, so the
record itself proves which path the child received.

**Rationale.** (b) proves only that the path appears *somewhere* in the
arguments — an unrelated option value could match while the validator reads a
different file, and it false-negatives on relative paths and symlinks. (c) is
smaller but puts validator-specific knowledge into a general-purpose wrapper.
Rejecting before spawn rather than degrading after is deliberate: nothing has run
yet, so there is no run to degrade.

**If wrong:** the wrapper attests a digest for artifact A while its child
validated artifact B, and the linkage check passes on mismatched evidence.

---

## D7 — At what grain fixtures pin their expected diagnostic

**Question.** A gate must be proven by a case that fails *for that rule*. At what
grain is that asserted?

**Verified constraint.** The fixture runner **already** enforces gate-grain
attribution. What is missing is sub-rule grain, and one new gate alone carries
roughly fifteen sub-rules.

**Options.** (a) An `expected_diagnostic` field in the fixture metadata,
machine-checked, with the existing gate-grain assertion as the floor.
(b) Rely on gate-grain alone. (c) Assert diagnostics only in the self-test.

**Decision: (a), and MANDATORY rather than optional.** An optional field
reproduces, opt-in, the exact failure it exists to prevent: an author who omits
it falls back to gate grain, and a fixture meant to prove sub-rule X passes
silently because sub-rule Y fired.

**Scope is GATE-KEYED, plus a cohort rule.** The runner rejects **any** fixture
citing G51 or G52 without `expected_diagnostic`, whenever authored — a
cohort-only rule would let a fixture written next quarter quietly reopen the
hole. On top of that, **every fixture this change adds carries the pin whatever
it cites**, because D10's two denial fixtures cite G29 and would otherwise sit at
gate grain, where a denial failing G29 for a *malformed* `skill_rev` would
satisfy the runner while proving nothing. The 102 pre-existing fixtures cite
neither new gate, so none of them changes. The underlying principle, worth
stating because the gate-keyed form obscures it: **diagnostic grain must attach
to the claim under test, not merely to the gate's identity.**

Added with it: **corpus-level accounting** over **every rule this change adds or
modifies** — G29's v6 mapping, the bound read with its dispatch and fail-closed
behavior, D1's shape rules — not only the two new gates. Each such rule is either
attributed by at least one negative case or listed explicitly as a coverage
residual. Permitting a failing case is not the same as accounting for which rules
lack one. One instance the accounting immediately surfaces as missing: nothing
yet proves that **a declared-v6 artifact carrying a non-reserved pair and binding
the entry commit derives v4 and is denied** — admission must be required, not
merely declared.

**If wrong:** the corpus reports coverage it does not have — silently, which is
the failure mode the flag/restraint design exists to prevent.

---

## D8 — What happens when a source reference cannot be verified

**Question.** Evidence references point at file-and-line ranges in a bound
revision. The specification is fail-closed: unresolvable revision, missing path,
or out-of-range line makes the assessment invalid. But the existing
execution-evidence gate uses a non-failing "BLIND" outcome for genuine
environmental inability (no git binary, artifact not inside a work tree).

**Options.** (a) Separate the subjects: the *gate* may report BLIND to say why
verification could not run, but the *artifact* can never derive `valid` when a
required reference went unverified, for any reason. (b) Follow the existing
gate's precedent and let environmental unavailability pass. (c) Fail hard with no
operator signal.

**Decision: (a),** with a case that exercises the **combination**, since that
combination is the whole point: a self-test forces a BLIND environment on an
artifact carrying a required reference and asserts both outcomes at once — BLIND
at the gate, `invalid` for the artifact. Without it the anti-laundering rule is
unproven by this record's own standard.

**Rationale.** (b) means a shallow clone or missing git binary silently converts
unverified evidence into satisfied evidence. (c) destroys diagnosability.

**If wrong:** unverified evidence passes as verified (b), or correct artifacts
are invalid whenever the environment is imperfect (c).

---

## D9 — What identity the new fixtures declare

**Question.** D5's manifest entry admits one provider/model pair to version 6.
Which pair, and what stops that identity from standing in for a real run?

**Verified constraint.** The corpus holds 102 fixture directories but 101
artifacts (`bootstrap-repo` has no artifact file), and **every one of those 101
uses provider `claude_code`**. The provider/model gate accepts three known
providers and requires, when a model's source is `default`, that the model equal
that provider's default — a constraint lifted when the source is `user_flag`.

**Options.** (a) A reserved pair: a known-but-unused provider (`opencode`), both
model sources `user_flag`, a reserved model literal. (b) Reuse the production
pair the corpus already uses. (c) A test-time manifest overlay, leaving the
production manifest empty.

**Decision: (a).** (b) admits the production pair to v6 in the first release,
forcing production loops to emit v6 before the emitter prose exists. (c) is
viable and simpler in one respect — the shipped manifest never mentions test
identities — but it exercises an overlay path production never uses, and leaves
the admission decision unauditable from the repository alone; the in-band entry
is auditable and exercises the real manifest path.

**Guard restated, correcting an overclaim.** An earlier rationale said the guard
is execution-evidence linkage. That holds only for artifacts that *cite*
evidence: most fixtures carry null execution evidence and validate anyway, so
linkage checks nothing there. **The actual guard is admission scope** — the
reserved identity is admitted to nothing of production value — plus the in-band
`evidence` pointer on the manifest entry and a reserved model literal that is
unmistakably non-production.

**If wrong:** production emission is forced early, or a fixture identity is
mistaken for a production capability claim.

---

## D10 — How admission state binds to an artifact

**Question.** Provenance records a `rule_set_sha256` binding the applicable rules
and canon, over a canon-declared bundle. Is the capability manifest — which
records which provider/model pairs are admitted to which schema version — a
member of that bundle? And if not, what binds it?

**Two verified facts that redrew the question:**

1. **`skill_rev` DOES cover the manifest.** It is a git SHA (4–40 hex) resolved
   in the skill's own repository, which contains
   `canon/panel-certification.toml`. The suggestion that `skill_rev` might be
   ruleset-scoped and therefore not cover admission is **false on the facts**.
2. **But validation does not read the bound copy.** The capability lookup reads
   the manifest from the **live working tree**
   (`(root or _DEFAULT_ROOT) / "canon" / "panel-certification.toml"`), never from
   the artifact's `skill_rev`. So the admission decision actually applied is not
   the one the artifact's binding names.

Fact 2 is the real defect, and it is sharper than "nothing binds the manifest":
the manifest *is* bound, and the check ignores the binding. Two artifacts with
identical `skill_rev` and identical digests can be validated under different
admission regimes, and post-rollback replay cannot distinguish "was admitted
then" from "never admitted".

**Options.** (a) Exclude the manifest from `rule_set_sha256`, rationale in canon,
and treat the residual as acceptable. (b) Include it in the bundle. (c) Exclude
it, and add a separate provenance field `capability_manifest_sha256`.
(d) Exclude it, and make the capability lookup a **bound read at the artifact's
`skill_rev`** when validating an already-emitted v6 artifact, keeping the live
read for v≤5.

**Decision: (d), with (a)'s exclusion retained.** (b) is decisive to reject — a
routine admission edit would perturb the digest every earlier fixture recorded,
so administration would invalidate unrelated stored evidence and make the
rollback test unreadable. (a) alone leaves fact 2 unaddressed. (c) closes it only
partially and reintroduces (b)'s instability through the back door: if the new
field is recomputed from the live tree, every manifest edit breaks every stored
digest; if recomputed at `skill_rev`, it merely restates a binding that already
exists. (d) closes the hole with **no new field at all** — it makes the admission
decision reproducible from the artifact's own bindings, which is the property
actually wanted — and is version-scoped so no v≤5 artifact is reinterpreted.

**Two residuals, recorded rather than left implicit.** (i) The v≤5 admission path
intentionally still tracks the live manifest; recorded in canon beside the
exclusion rationale so a future v7 does not inherit the live read by silence.
(ii) The **emitter** must read live — the revision it will bind does not exist
yet at emission — while validators bound-read. A manifest change inside the
emission-to-commit window that **alters this pair's derivation** surfaces as a
G29 mismatch; one that does not is irrelevant to this artifact. Universal
detection is NOT claimed.

### Ordering: entry first, reversing an earlier reviewer

Under (d) the fixtures' bound read must find the manifest entry that admits them.
Two exemption-free resolutions exist:

- **Resolution A — entry first.** The manifest entry lands **with the canon
  file**, in the first wave; the fixture corpus lands in a later wave; fixtures
  bind the entry commit. The observation that unlocks this: `skill_rev` binds the
  *ruleset*, not the test data, so the bound commit need not contain the corpus.
  Cost: the entry's `evidence` pointer dangles until the corpus lands, so the
  "no entry cites a corpus that does not yet exist" invariant scopes to release
  tags and `HEAD` rather than to every intermediate commit. **That rescope names
  its enforcement point** — the release acceptance battery resolves every
  manifest entry's `evidence` pointer against the tag, and intermediate wave
  commits are declared explicitly non-replayable for that one check.
- **Resolution B — amendment commit.** Entry and corpus land together; the
  immediately following commit mechanically rewrites the fixtures' `skill_rev` to
  the entry commit. Cost: one scripted commit, plus a transiently non-validating
  intermediate commit that CI and bisect must be told to expect.

**Adopted: Resolution A.** B's transiently non-validating commit collides with a
standing rule of the implementation plan — every wave commit must pass the full
verification battery — whereas A keeps every commit green and pays only with a
release-scoped audit invariant. **This reverses a placement a different model
family required** (codex moved the entry into the corpus task precisely so no
entry could cite a missing corpus). That reviewer was arguing audit hygiene
without the bound read in view; under (d) its placement makes admission
structurally impossible, so the ordering is decided on merit and the audit
invariant is rescoped rather than abandoned.

**Both exemption routes are forbidden, for two independent reasons.** A
**content-keyed** exemption (keyed on the reserved identity) leaks by
construction — any real artifact can declare that identity, which is exactly what
D9's corrected guard concedes. A **harness-keyed** override (a test-only
validator flag) does not leak but leaves the positive bound-read path exercised
by nothing until a production run, which is dormant mechanism.

### Proving the read is actually bound — three tests across two axes

An exhaustive claim must name the dimension along which it is exhaustive; four
unqualified claims in this record's history were later retracted, each marking a
real coverage hole.

**Axis 1 — how the read DEGRADES.** Exhaustive at three variants:

| Cheat | Behavior on a pre-entry-revision artifact | Caught by |
| --- | --- | --- |
| Always-live lookup | live manifest has the entry → derives v6 → unexpected pass | case 1 |
| Fallback when the bound read finds nothing | bound read succeeds with zero entries → falls back → v6 | case 1 |
| **Fallback when the bound read ERRORS** | bound read never errors here (the revision resolves, the manifest exists) → behaviorally identical to an honest lookup | **case 2 only** |

- **Case 1 — pre-entry revision denied.** A v6 artifact binding a revision
  earlier than the entry must be DENIED.
- **Case 2 — unresolvable revision denied.** A v6 artifact carrying the reserved
  pair and a **fabricated, well-formed 40-hex `skill_rev` that resolves nowhere
  in any clone** must be DENIED with an operator signal distinguishable from a
  plain derivation mismatch. Two constructions were rejected: a SHA "beyond a
  shallow-clone boundary" resolves fine in a full clone, so the deny would arrive
  as a plain mismatch with no signal and the fixture would fail its own assertion
  for the wrong reason; and a non-git *environment* is not expressible as a
  fixture at all — that form lives in the D8-style environment-forcing self-test.
  A malformed value is equally wrong: it fails format validation before the
  lookup runs.

**Axis 2 — WHO receives the bound read.** Not covered by any fixture, and not
fixable by adding more of them. A lookup could dispatch on **pair identity** — or
any corpus correlate such as the reserved literal or the fixture path layout —
instead of on declared version: bound read for the reserved pair, live read for
everyone else. Every case above still passes, and so does the whole corpus.

The reason is structural: **the manifest's only v6 entry is the reserved pair's,
so the corpus's entire bound-versus-live divergence space is that one pair
between pre- and post-entry revisions.** On that pair the cheat behaves honestly;
everywhere else there is no divergence to detect. Behavioral coverage is bounded
by the divergence space, and this one is degenerate by design. It matters because
the moment the later release records the production entry, production v6
artifacts get live-read admission — verified fact 2 returning silently for
exactly the artifacts that matter, voiding residual (ii)'s loudness promise and
leaving the replay ambiguity that motivated (d) unresolved. It is also the
content-keyed exemption reborn at implementation level: forbidden in the design,
policed by nothing in the code.

- **Case 3 — synthetic-manifest self-test** (the D3 pattern generalized, since a
  degenerate divergence space cannot be tested behaviorally). Against a
  **non-canon** manifest carrying a **non-reserved** pair whose entry exists at a
  bound revision but not in the live tree, assert the bound derivation applies to
  it — proving dispatch is version-keyed and pair-agnostic. Drive the real lookup
  function directly so path-keyed variants are caught too, and exercise two
  divergent revisions **within one process** so a manifest cached across
  artifacts is caught as well.

**If wrong:** under (a) alone, admission regime changes are invisible in the
artifact; under (d) with a content-keyed exemption, real artifacts escape the
bound read silently — the laundering class this design exists to prevent; under
(d) with a live fallback, verified fact 2 returns unannounced.

---

## Review provenance

Adjudicated by opencode/glm-5.3 across four rounds, blocking findings 3 → 1 → 1 →
1, each round's finding new rather than a re-litigation of the last. D1–D9 were
ACCEPTED and unchanged across rounds 2–4. D10 was revised in every round: the
bound read (round 2) replaced a rejected provenance-field proposal; Resolution A
(round 3) replaced two wrong framings of the fixture interaction; case 2 (round
4) covered a degradation variant case 1 structurally could not; case 3 (round 4)
covered a dispatch-scope variant no fixture can reach. A fifth round timed out
twice with no output and was abandoned; D10's final state is therefore reviewed
through round 4 and settled by owner decision.
