<!-- Split out of DISPLACEMENT-2026-08-21.md on 2026-08-22: the sweep outgrew being a
     section of a token-budget note. That note keeps §10 as a pointer here. -->

# The vacuous-assertion sweep (2026-08-21 → 22)

§8's third finding — a probe that had silently stopped testing anything — is a **class**, not a
one-off, and this skill ships **72** `_*_selftest.py` files. A sweep of all of them was launched and
**died on an account spend limit before producing anything**; it is outstanding work, not a
completed clean bill.

**Method, for whoever picks it up.** A finding must be *proven by mutation*: break the behaviour the
test names, re-run it, and only report it if it still passes. Work on a copy of the tree so parallel
mutation is safe, and restore between mutations. Prioritise by stakes — a vacuous guard on a hard
gate or on redaction matters more than one on a reporting helper. Finding nothing is a good result;
an honest empty report beats a padded one.

**Batch 1 (serial, 2026-08-21) — 5 tested, 1 proven vacuous.** A second real one, in the panel
half of rule #6 exception (d): `_artifact_panel.py:652`'s
`if stable_ids and findings_count in (1, 2) and len(stable_ids) != findings_count:` could be deleted
outright (`if False:`) and **no test in the entire 72-file suite noticed**. The two fixtures the
coupling selftest's own docstring cites as pinning that rule each trip a *different* check first —
one the per-member `finding_stable_id not in findings[]` check, the other the separate `{1,2}` cap —
so the distinct-id comparison itself was never isolated. Closed by one fixture where every other leg
holds (`STABLE_A` present in `findings[]`, `findings_count` 2 inside the cap) so only the count
mismatch can fire; verified to kill the mutation.

Worth noting *how* it hid: not a drifted threshold like the first one, but **two neighbouring checks
that shadow the third**. Every fixture aimed at the rule was absorbed by a cheaper check upstream.
That is a distinct failure mode and a harder one to spot by reading.

**Batch 2 (drift guards) — 6 tested, 0 findings.** `_retired_prose`, `_ref_tree_lint`, `_canon`,
`_flag_effect`, `_schema_compat`, `_transition_table` all killed both mutations. `_retired_prose`
turned out to be self-guarding against the failure predicted for it: renaming its target file fires
*"a rename would silently blind this check"* rather than going quiet. Two judgment calls were made
correctly and are recorded so they are not re-raised as findings: a **paraphrased** (non-verbatim)
reintroduction does slip past `_retired_prose`, but its contract is a literal substring from a named
commit — the same shape as the method.md-heading non-finding above; and `_transition_table`'s
legality check, when disabled, fails five assertions at once, which is the opposite of the shadowing
problem.

**A latent version of the class, worth knowing about.** `_schema_compat_selftest.py` reads a dogfood
artifact at `REPO_ROOT/CURRENT_REVIEW.json` — one level *above* the skill dir. It exists today, so
the test exercises its real path. If it were ever removed the test would fall to its skip branch and
still exit 0. It does announce the skip in its output (*"dogfood artifact absent; retroactive check
skipped"*), which is the repo's own `absent != clean` discipline honoured — but a runner that reads
only exit codes would see full coverage. Not a defect today; a thing to not be surprised by.

**Batch 3 (HALT/terminal gates) — 6 tested, 0 findings.** `_g17`, `_halt_tail`, `_g37`, `_g41`,
`_g45_exhaustion`, `_risk_evidence` all hold. Three results worth keeping:

- **`_g17` is the best-engineered test in the repo on this axis** and took three mutations, all
  killed hard. It asserts on *printed diagnostics* rather than the `REPORT_ONLY` return value
  specifically to avoid a vacuous pass, and every malformed-citation fixture perturbs exactly one
  field so a broken check cannot hide behind a neighbour — the anti-shadowing discipline, already
  applied, before anyone went looking for it. This matters beyond the sweep: G17 is a **[P1]** item
  with a live adjudication packet, and its guard being sound is a precondition for that packet
  meaning anything.
- **`_risk_evidence` (G33) verifiably closed the bug it was written for.** The historical
  free-text token-match false-pass was reconstructed and dies on exactly the FAKE-evidence case
  whose docstring names it. A guard written to close a vacuous check, confirmed to have done so.
- **`_halt_tail`'s three per-field blocks do not shadow each other** — isolating the null-otherwise
  half of rule #18 killed exactly one case and nothing else.

**Bearing on the displacement analysis.** §5 refused to move this bundle off the unconditional load
path partly because none of these gates has a script backstop. That argument assumed the gates were
soundly tested; the assumption now has evidence behind it rather than being taken on trust.

**Batch 4 (isolation guards + dispatch gates) — 6 tested, 1 proven vacuous.**
`_g14_dispatch_selftest.py` verified G14's presence in `trust-model.md` with
`count(G14_RULE) >= 2`. The file carries **three** copies — canonical § Hard Rule, loop-subagent
template, helper-forwarding clause — so `>= 2` pinned **none** of them: deleting any single copy
leaves two and passed. Its own comment argued for the threshold ("the canonical definition is a
fixed point this test doesn't need to pin separately"), which is precisely the reasoning that made
it vacuous. Both surviving deletions are the regression **backlog item 3 exists to prevent**, one
level down: a dispatch boundary silently losing the payload-is-not-instruction rule. Replaced with
per-site window checks anchored on the text introducing each copy; all three deletions now killed.

**Same shape as batch 1, and that is now a pattern worth naming.** Both findings were an
**aggregate standing in for per-item verification** — a `{1,2}` count of stable_ids, a `>= 2` count
of rule copies. A count cannot say *which* items survived, and which survived is always the
question. Any assertion of the form `count(X) >= N` over a set whose members are individually
load-bearing should be read as suspect on sight.

**The isolation guards are genuinely proven, not merely undisturbed.** `_metric_isolation` and
`_strictness_isolation` were tested by *violating* the isolation — routing `loop_metrics` and
`strictness` into `check_g21_scorecard` / `check_halt_success_gating` — and both caught it
immediately, including a message-text-only leak in the strictness case. That matters: Meta-Rule 1
("metrics support judgment; they never decide it") rests on the first of those.

**Batch 5 (targeted by shape) — 6 tested, 1 proven vacuous, and it is the most consequential of
the four.** Batch 5 was selected by grepping the remaining files for count-style aggregate
assertions, on the theory that two of three findings shared that shape. The finding it produced was
a *different* shape, which is worth noting about targeting heuristics.

`grade_structural.py`'s `_eval_check` — the deterministic per-assertion evaluator that scores real
reviewer submissions against `evals/evals.json` — had **zero RED-path coverage**. Every scenario
fixture drove it through cases that pass. Replacing its entire body with `return True, ""` left
`_grade_structural_selftest.py` green *and* **all 72 selftests in the repo green**. An always-pass
evaluator reports 100% for every candidate on every scenario using these ops, invisibly.

Closed with one True and one False case per op (`eq`, `in`, `any_lt`, `contains_any`,
`excludes_all`, `nonempty`) plus the absent-dimension case, asserted directly against
`_eval_check`. The True cases exist so an operator inversion cannot pass by flipping both. Verified
against three mutations — whole-body always-pass, `any_lt` neutralised, `excludes_all` inverted —
all now killed.

**Third distinct shape.** Batch 1 was two checks shadowing a third; batches 1 and 4 were aggregates
standing in for per-item verification; this is **an entire computation with only GREEN fixtures**.
The common thread across all four is not a code smell but a *fixture-design* failure: in every case
the mechanism was fine and the coverage claim was hollow. Reading the tests suggested coverage in
all four.

**Batch 6 (ranked by logic-per-test) — 6 tested, 9 findings across 5 files.** By far the
highest-yield batch, and the prior is why: after four findings the common thread was a **hollow
fixture set**, not a code smell, so the batch was picked by how large each module is relative to its
selftest rather than by topic or code pattern.

**Fixed this pass (the three with the widest blast radius):**

- **`audit_boundaries.py` — the two filters masked each other.** Disabling `_is_test_file` entirely
  passed, because `IGNORE_DIRS`' `tests` entry caught the files anyway; separately emptying
  `IGNORE_DIRS` also passed, because the filename check caught them back. Each filter was unproven
  while the pair looked covered — the batch-1 shadowing shape again, now between two *filters*
  rather than two checks. This one has **three consumers**: `repo_map.py` and `audit_suppressions.py`
  both import these as a single source of truth. Closed by asserting each filter directly.
- **`preflight.py` — the `--provider unknown` warning had zero coverage** and could be deleted
  outright. It exists because of a documented production incident (an inline self-vet reaching
  HALT_SUCCESS off a stale detection rule with no subagent spawn). A guard installed after a real
  incident is precisely the one that must not be able to vanish quietly. Closed by asserting the
  warning fires and names the HALT_SUCCESS risk.

**Confirmed, reproduced, and now FIXED** — each verified against the mutation that exposed it:

| Site | Mutation that survived | Fix |
| --- | --- | --- |
| `audit_clones.py` | `_MIN_LINES = 8` → `0`; the Python extractor returning `[]` — all four fixtures were Swift-only, so Python clone support was untested end to end | two fixtures: a duplicated Python body, and a **6-line** duplicate that must stay silent below the 8-line floor |
| `repo_map.py` | `auto_engage` threshold pushed out by 100k — the `>300 files` True branch `method.md` relies on was never exercised | a fixture that writes 301 modules and asserts `auto_engage is True`, plus a pin on the documented 300 constant |
| `render_report.py` | residual/disposition rendering and the markdown findings section can both be emptied | **still open** — lowest stakes of the three (report rendering, no gate depends on it) |

**A vacuous test written while fixing vacuous tests.** The first size-floor fixture used a *2-line*
duplicate and passed at both `_MIN_LINES = 8` and `_MIN_LINES = 0` — a second gate excludes bodies
that short regardless of the floor, so the fixture could not discriminate and proved nothing. Caught
by running the mutation rather than trusting the new test. The shipped fixture is sized to
**straddle** the floor: reported at 0, silent at 8. Writing a test that cannot fail is evidently
easy to do even while hunting for tests that cannot fail.

**One correction to my own verification.** My `_public_names` mutation inserted a bare `pass` at the
top of the function, which changes nothing — a dead mutation that proves nothing either way, the
same trap the sweep agent caught itself in on `_g37` and `_ruleset_epoch`. That finding is
**unverified**, not confirmed, and is excluded from the table above.

**`_attested_run_selftest.py` is the most rigorously tested file found in the sweep** — signal
death, stream-flood deadlock, shlex round-trip, trust pin, four distinct failure exit codes,
home-isolation proof. A deliberate hunt for an uncovered branch came up empty.

**Batch 7 (last ratio-ranked three + gate guards on a polarity prior) — 6 tested, 4 findings, all
fixed.** Group A produced one each:

- **`paired_arm_grade.py`** fires `grader_uncertain` / `no_cited_span` twice over — once on the
  grade object's own `semantic_grade`, once per assertion. Only the per-assertion pair was covered,
  so the **top-level block could be deleted outright** with the suite green: a grader returning
  `uncertain` overall, or citing a span absent from the candidate text, went unflagged. Closed with
  three direct assertions including a restraint case.
- **`audit_metric_trend.py`** documents that only the *latest* transition may alarm, but every
  fixture was exactly two loops long, making "last two points" indistinguishable from "any
  consecutive pair". Closed with a three-loop fixture whose old regression has since recovered.
- **`audit_cochange.py`**'s noise-commit filter and >8-file mass-change cap both had zero coverage:
  no fixture had a noise-worded subject or a bulk commit. Closed with pairs that co-change *only*
  inside filtered commits and must therefore stay unreported.

**Group B was a genuine negative, and that is the useful part.** The prior was fixture *polarity* —
a gate guard with only RED cases cannot catch an always-fire mutation, one with only GREEN cannot
catch a never-fire mutation. G5, G39 and G43 were each mutated **both** ways and all six mutations
died. The polarity gap is not the failure mode for the gate guards; the hollow-fixture-set shape
found in modules does not transfer to them.

**Batch 8 (gate preconditions + replay harnesses) — 6 tested, 4 findings.** The stopping condition
set before this batch was *"if the gate guards come back clean, call the sweep done"*. They did not.

- **`_priority_replay_selftest.py` reported `OK` on a genuinely empty corpus** — and printed
  *"0 fixture(s)"* in its own success line. Every check lives inside a loop over
  `on_disk & registered` or is gated on a named fixture, so emptying both the manifest list and the
  fixture directory left nothing to iterate and exit 0. This is `absent != clean` — the rule
  `tool_runner.py` already applies to a tool that never ran — inside the test suite itself. Fixed
  with the guard `_exec_replay_selftest.py` already carried; that file was verified sound on the
  identical probe.
- **G28's `schema_version >= 3` floor was never exercised**: all 18 cases reuse one module constant
  pinned at 4. Fixed with v1/v2 silence cases plus a v4 control.
- **G46** covers its schema floor and `drift_notes` coupling well, but its helper hardcodes a valid
  `skill_rev`, so epoch scoping is unproven *in that file*. The same mutation **is** caught by
  `_ruleset_epoch_selftest.py`, so the system is guarded — recorded as a locality gap, not a hole.
- **G19**'s isolation assertion filters with `"skill_rev" not in i.message`, a substring match on
  freeform text, so a real coupling bug whose message happens to contain that word is silently
  excluded. The isolation itself holds — a reworded control mutation is caught — only the filter is
  fragile.

### Harness defect found in my own verification, and it matters for every result above

Verifying G28 produced a contradiction: the code plainly returns early below `schema_version` 3, yet
the gate fired at v1. The cause was **stale `.pyc` files written by my own mutation runs**. `python3
-B` prevents *writing* bytecode, not *reading* it, so a `__pycache__` entry compiled from a mutated
source survived the restore and kept executing. Disassembly settled it: the loaded function compared
against `0`, the constant from the mutation, while the file on disk read `3`.

Every mutation verdict in this sweep taken immediately after a restore was therefore suspect. All
seven shipped fixes were **re-verified with `__pycache__` cleared before and after each mutation**,
and all seven mutations still die — the fixes are sound and only that one reading was corrupted. But
the general lesson is the sweep's own subject turned on itself: *a verification harness can report a
result that has nothing to do with the code under test*, which is exactly what a vacuous assertion
does. Clear the bytecode cache around every mutation.

**Batch 9 (the corpus-consuming family) — 6 tested, 1 finding, and it closed the class.**
`_principal_baseline_selftest.py` had the identical hole `_priority_replay` had: no guard, so every
check is a no-op loop and an emptied corpus reports `OK … 0 scenario(s)`.

**Two hits on one template was enough to stop testing file-by-file and enumerate the class instead.**
A scan for selftests that both iterate a corpus directory and read a manifest list found exactly
five, split cleanly by family:

| Family | Guarded? |
| --- | --- |
| `_exec_replay`, `_loop_replay`, `_priority_replay` | **yes** — the replay template carries `if not entries` / `if not fixture_dirs` |
| `_advisory_baseline`, `_principal_baseline` | **no** — the baseline template never had it |

Both baselines now carry the guard. `_advisory_baseline` is the interesting half: it *does* fail an
emptied corpus today, but via a separate `evals.json` no-orphan check catching the stale references
— **the save is redundancy, not this contract**, and it moves if that check ever does. The guard is
stated locally so the file no longer depends on a neighbour to be sound.

That is the difference between fixing two files and closing a class: the enumeration cost one grep
and proved there is no third instance.

**The recheck came back clean.** Both Python-module verdicts re-tested under full cache discipline
(the batch-8 G46 epoch gap, the batch-6 `render_report` residual rendering) stand unchanged, so the
stale-bytecode defect corrupted exactly one reading — the G28 one that exposed it.

**Batch 10 (contracts + gate preconditions) — 6 tested, 2 findings, both fixed.**

- **`_handoff_shape_selftest.py`**: G35's `isinstance(match_paths, list)` check had no fixture at
  all — every case routes through an `act()` helper that always passes a real list, so deleting the
  check left the file green. A bare string is the realistic wrong value (hand-authored JSON writing
  `"src/a.py"` for `["src/a.py"]`), and a string *is* iterable, so the downstream coupling checks
  would have treated it as a sequence of characters. Closed with string and dict cases plus a
  restraint case.
- **`_g22_status_selftest.py`**: the v1 and v2 subject regexes carry **independent copies** of the
  same status alternation, and only the v2 copy was ever tested against garbage. v1 is what
  distinguishes *"legacy subject in a v2+ artifact"* from *"malformed"*, so a permissive v1 silently
  reclassifies malformed subjects into the tolerant branch. Closed with a v1 garbage case and a
  suffix-strictness case.

`_artifact_review_contract_selftest.py` is called out as **the most symmetric file in the sweep** —
every valid-value case has an adjacent invalid one, every CURRENT-epoch case a mirrored
LEGACY-tolerance case.

### A fourth dead mutation, and the reason it is the sweep's biggest integrity risk

Mutating `_g42`'s schema floor by text substitution silently landed in **`_g39`'s** code instead:
the two functions share byte-identical preamble text, so `.replace(old, new, 1)` hit the first match
in the file rather than the intended one. Caught by invoking the checker directly and seeing an
empty issue list where the docstring promised a hit.

That is now four dead mutations across this sweep — two caught by the agent (`_g37`,
`_ruleset_epoch`), two by me (`_public_names`, the 2-line clone fixture) — plus the stale-bytecode
defect, which is a *separate* axis. **A dead mutation and a vacuous assertion are the same failure
wearing different clothes**: an instrument that reports a result unrelated to the thing it names.
The sweep's own tooling produced that failure five times while hunting it, which is the strongest
argument in this document for why mutation testing has to verify its own mutations.

**Batch 11 (final) — 6 tested, 2 findings, both fixed.**

- **`audit-enum-interpretation.sh`**: the `count >= 2` outside-home threshold had no negative
  fixture — both flag cases use exactly 2 sites. Lowering it to `>= 1` passed. A single outside-home
  interpretation is the common benign shape, so flagging it would make the audit noise on every real
  codebase. Closed with a one-site restraint fixture.
- **`_wtree.py`**: `BOOKKEEPING_PATHS` holds six entries but only `CURRENT_REVIEW.json` was ever
  exercised, so shrinking the set to that one entry passed — and both fingerprint entry points share
  the constant, so the gap hit both. Concretely: `REVIEW_HISTORY.json`, `findings_registry.json` or
  `LOOP_STATE.json` churning on a normal loop would have registered as **source drift**.

**My first fix for `_wtree` was itself vacuous, and it is the cleanest example in this document.**
It looped over `BOOKKEEPING_PATHS` asserting each entry is excluded — so a mutation *shrinking* the
constant shrank the loop too, and the test still passed. An oracle derived from the implementation
it is meant to check: exactly the DD-01 tautological-oracle shape, written by me, in a fix for a
vacuous test, during a sweep for vacuous tests. Caught only because the mutation was re-run against
the new test. The shipped version writes the expected six names out **literally**, so the test knows
what belongs there independently of the code.

**The file-split self-check came back clean.** `_provider_detection_selftest.py` was edited earlier
the same day when the reviewer profile moved to `provider-adapters-reviewer.md`; mutating the moved
content (codex `--sandbox read-only`, opencode `edit: deny`) is still caught through the two-file
read. The relocation did not blind the guard.

**Final coverage — 68 of 72; 23 proven vacuous, 21 fixed, 3 recorded, 1 withdrawn.** The four
untested are two written and mutation-tested the same day (`_audit_suppressions`,
`_audit_public_compat`) and two that are repo-root dependent and mislead in a copied tree
(`_coverage_ledger`, `_reviewer_baseline`).


| Selftest | Mutation applied | Result |
| --- | --- | --- |
| `_g44_selftest.py` (credential quarantine) | `hits.append` → no-op; `_CREDENTIAL_PATTERNS` → empty | both **killed** |
| `_redaction_dispatch_selftest.py` | redaction rule inverted (`never the value` → `always the value`) | **killed** |
| `_token_budget_selftest.py` | — | **proven vacuous**; fixed in §8 |
| `_tool_runner_selftest.py`, `_g47`, `_g48`, `_g32_panel` | two each (batch 1) | all **killed** |
| `_g32_panel_coupling_selftest.py` | dedup-count comparison → `if False:` | **SURVIVED** — fixed by an isolating fixture |

One near-miss worth recording so it is not re-raised: renaming method.md's *"Credential redaction."*
heading **survives** `_redaction_dispatch_selftest.py`. That is **not** a vacuous assertion — the
test's contract is that the redaction *rule* is forwarded verbatim into dispatch prompts, and
inverting the rule is caught. A heading is not the rule. Reporting it would be the false positive
the method above exists to prevent.

## What this sweep taught

Eleven batches, sixty-plus selftests, mutation-tested by hand against a scratch copy. This is the final form of that record — written for whoever runs a sweep like this on a different repo next, not as a recap of what got found here.

- **Rank files by logic-per-test before anything else.** The single highest-yield move in the whole sweep was computing module-lines-vs-selftest-lines for every candidate and working down that list — one batch, chosen purely by that ratio, produced nine confirmed findings, more than any other batch combined. It costs one `wc -l` per file pair. Do this first, and only reach for a cleverer prior once it's exhausted.
- **A keyword or shape-based prior is a search radius, not a diagnosis — verify what the file actually does before trusting the label that put it in front of you.** A grep built to find aggregates standing in for per-item checks surfaced a file whose real defect was an evaluator with zero passing-only coverage, a different shape entirely. A batch grouped as "consumes a fixture corpus" turned out to contain two files that touch no filesystem corpus at all. The prior is still worth running — it puts you in front of the right files disproportionately often — but expect the defect you find to not match the reason you went looking.
- **When a defect turns out to live in a copy-pasted template, stop going file-by-file and enumerate the whole class immediately.** Two files with the identical missing-guard hole ("this check runs only over a non-empty corpus, so a genuinely empty one silently reports success") were built from the same manifest-plus-directory shape. Finding the second one cost a whole extra batch of file-by-file testing; a single grep for every selftest matching that shape would have found both — and proved there wasn't a third — in minutes. The moment a fix pattern repeats, go looking for its siblings before moving on.
- **A dead mutation and a vacuous assertion are the same failure wearing different clothes: an instrument reporting a result unrelated to the thing it names.** This sweep's own tooling produced that failure at least six times, on both sides of the exercise — a mutation that didn't actually change observable behavior for the fixture under test; a text-substitution that silently patched the wrong function because two functions shared identical boilerplate; a string "deletion" whose replacement still contained the original substring; stale bytecode executing old behavior after a clean-looking source restore. None of these announced themselves — every one looked, at first glance, like a normal result. The only defense that worked every time: before crediting a "survived," directly invoke the mutated code on the exact fixture and confirm the output changed, and confirm the diff landed inside the function you meant to touch, not a neighbor with the same preamble.
- **Environment state is a separate risk axis from mutation design, and it will not announce itself either.** A `.pyc` compiled from mutated source can outlive the restore that undid the source, and produce a flat contradiction days later with no proximate cause visible. Clear compiled-artifact caches before every mutation is applied, before every test run, and again after every restore — from the first batch of a sweep, not adopted retroactively after a scare.
- **"Required" and "applies only when" are claims, not facts, until both sides have a fixture.** This shape recurred at every altitude a schema can have: a contract field that's asserted present but never asserted *required* by deleting it; a gate's stated `schema_version` floor with every fixture hardcoded above it; a set of six excluded paths with fixture coverage on one; a regex's value alternation copied into a second file and negative-tested in only the first. None of these looked incomplete from the test's own summary line — each one read as thorough until a fixture was built for the specific missing side. Enumerate a contract's stated preconditions explicitly and check both sides of each one; don't infer coverage from a test file's confidence in its own docstring.
- **A fully negative batch is a redirect, not a null result — report it with the same weight as a finding.** One batch that killed every mutation, on every gate, testing specifically whether guards fire in both directions, told the next batch to stop hunting that shape and start hunting unstated preconditions instead — and that pivot is what made the following batches productive. A sweep compounds only if its negative space gets written down as explicitly as its positive space; otherwise the next person (or the next session) re-runs the same probe that already came back clean.
- **When an edit relocates content a guard depends on, re-test the guard against the new location before trusting the move was safe.** A file split that moved a section into a sibling document is exactly the moment an existing check silently starts validating an empty half of what it used to cover. The fix is cheap — mutate the specific content that moved and confirm the guard still fires — but it has to be done deliberately; a passing test after a refactor is not evidence the refactor was safe, only that nobody has looked yet.
