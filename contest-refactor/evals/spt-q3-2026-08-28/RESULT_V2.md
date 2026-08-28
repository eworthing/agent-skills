# SPT Q3 owner-count clause (v2) — 2/2 primary, 4/4 restraint clean: SHIPPED

Graded against `PREREG_V2.md` from applied diffs, executed repros, bundled suites,
and pack oracle batteries — never agent self-reports. All six pre-registered runs
executed to completion; no futility stop this time.

## Scoreboard

| Run | Outcome | Verified how |
| --- | --- | --- |
| V2-d1a | **flip** — single `_resolve()` owner driven by `ORDER`; symptom patch discarded pre-code "because it fails Q3" | diff; suite 7/7; all 3 pack oracles green |
| V2-d1b | **flip** — single `_carrier()` owner; symptom patch **SPT-REJECTED at Q3**, "failing the owner-count test verbatim" | diff (one membership check left in module); suite 7/7; oracles green |
| V2-d2 | clean — zero production edits; sentinel design defended 10/10; hash proposal SPT-rejected on Meta-Rule 4 | empty production diff; suite 5/5 |
| V2-pyd | clean — both classifier fns and both registries intact; disclosed gap left open; real out-of-frame find applied (`eval` mutates caller's namespace → eval a copy) | per-file diffs; suite 8/8; **full oracle matrix matches declared expectations** |
| V2-pyt | clean — `_span`/`span` split untouched; `__lt__`→`SPANS` is a measured `allowed_findings` entry | diff; suite 8/8 |
| V2-d6 | clean — `lazyselect.py` byte-untouched; two mutation-verified tests added; loop-collapse correctly SPT-rejected | `diff -q`; suite 5/5 |

**Primary endpoint 2/2. FLIPs 0/4. HARM 0/6.** Pre-registered rule → **SHIP**.

Both d1 runs independently produced the graded-correct consolidation *citing the
owner count as the reason*, and V2-d1b did the thing v1 never achieved: it raised
the symptom patch as a candidate and SPT killed it at Q3. The gate now catches the
under-action case the way it already caught the nine over-action cases.

## Borderline noted, not a flip

V2-pyt deleted `value_of()` (zero callers in the checkout). The pack's **hidden**
oracle harness calls it, so the battery crashes on the edited variant — but the
**control run made the identical deletion yesterday** under shipped prose, so it is
not clause-caused, and it is neither a `must_not_find` FLIP nor pre-registered HARM
(bundled suite passes). Two records worth keeping: (a) variant-frozen oracle
batteries cannot grade API-removing diffs — a harness limitation to remember when
reusing packs as diff graders; (b) the loop's altitude on "dead public API in a
library checkout" is inconsistent across symbols in a single run (kept
`span_from_value` for external-caller risk, deleted `value_of`), independent of
this clause.

## What shipped

`references/method.md` SPT section, byte-identical to the measured treatment prose:

- Q3: *"Does it avoid duplicate layers? Count owners: for each question the finding
  names, how many code paths answer it after the fix? More than one owner of the
  same question — whether the fix added the second owner or left an existing pair
  standing — is a 'no'."*
- New paragraph **"Q3 counts owners."** — definition of a question, the two proofs
  of shared ownership (demonstrated drift that is a bug; documented contract each
  site must satisfy independently), the explicit "a symptom repair that restores
  agreement today still leaves the owner count at two and fails Q3", Q2/Q5
  rewiring, different-callers-is-not-different-questions, and the Q4 guard for
  load-bearing duplication.

Verification at ship: token budget within existing headroom (86,075/87,800 apple;
81,953/83,700 generic — no ceiling change needed), 80/80 selftests, validate-repo
OK, 102/102 fixtures, 26/26 packs, ruff clean.

## Honest scope of the claim

d1 is in-sample twice over — the clause was derived from its failure and v2 names
that failure's shape. The generalization evidence is exactly: four deliberate-split
restraint packs stayed clean under owner-counting, once each, one model. The v1
misread (T-d1a routing around "leave both standing") shows wording robustness is
run-sensitive; n=2 on v2's wording is consistent but small. Prose-flow probes, not
the full gate harness. Effect in a real instrumented run remains unobserved.
