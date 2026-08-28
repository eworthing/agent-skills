# Pre-registration v2 — owner-count wording, full restraint arm

Written 2026-08-28 after `RESULT.md`, before any v2 run started and before the v2
prose edit was applied to the probe environment. Owner-directed retry: "retry with
the owner-count wording plus the full restraint arm."

## What changed from v1, and why

v1's failure mode (T-d1a): "does not leave both standing" was parsed as *leave the
disagreement standing*, so a symptom patch satisfied the collapse limb. v2 replaces
the directional adjective with a structural count an agent cannot reinterpret:
**after the fix, how many code paths own the question?** — and names the T-d1a
failure explicitly: a symptom repair that restores agreement today still leaves the
owner count at two.

## The v2 treatment

Same scratchpad prose copy, byte-identical to shipped `references/` except the SPT
section of `method.md`. v1's two edits are replaced by:

1. Q3 line: *"Does it avoid duplicate layers? Count owners: for each question the
   finding names, how many code paths answer it after the fix? More than one owner
   of the same question — whether the fix added the second owner or left an existing
   pair standing — is a 'no'."*
2. Paragraph **"Q3 counts owners."** after the Q5 paragraph: defines a question
   (a decision callers observe: which layer wins, what "carries" means, resolution
   order); when two sites own the same question (demonstrated drift that is a bug,
   or a documented contract each must satisfy independently); states that a symptom
   repair restoring agreement **still leaves the owner count at two and fails Q3**;
   Q2/Q5 rewiring unchanged from v1 (proven consolidation is not ceremony; the
   closed drift class is the measurable gain); different callers is not a different
   question; guard unchanged — sites answering different questions or that may
   legitimately diverge have owner count one each, collapsing them fails Q4.

The exact diff is archived at `treatment-prose/method.v2.diff`.

## Arms and runs — all six run to completion, no futility stop

v1 skipped the restraint arm when SHIP died early; the owner has now explicitly
ordered the full arm, so **all six runs execute regardless of interim results** —
the restraint data is a deliverable this time, not only a gate.

| Run | Specimen / variant | Role |
| --- | --- | --- |
| V2-d1a, V2-d1b | `config-precedence-duplicate-authority` / `two-owners-drifted` (RED) | primary endpoint ×2 |
| V2-d2 | `auth-unusable-password-policy` / `sentinel-marked-no-credential` | restraint |
| V2-pyd | `pydantic-typing-extra` / `dual-registry-split` | restraint, highest flip risk |
| V2-pyt | `pytest-scope-enum-public-compat` / `enum-with-compat-property` | restraint |
| V2-d6 | `cpython-genexpr-iterability` / `lazy-consistent` | restraint spine |

Sequential sonnet runs; prompts byte-identical to v1's (d1/d2/d6 use the diff-probe
prompt, pyd/pyt the n=3 probe prompt), only probe-directory paths differ. Fresh
pristine variant copies per run. Control remains the 2026-08-27 shipped-prose runs.

## Grading and decision rules — carried from `PREREG.md` verbatim

d1-flip criteria, FLIP definitions per restraint manifest, HARM/VALUE/CHURN labels,
and grading from diffs + executed behaviour + pack oracles are unchanged from v1's
prereg. Decision rule unchanged:

- **SHIP** iff d1 flip 2/2 AND zero FLIPs AND no new HARM.
- **KILL** on any restraint FLIP, regardless of d1.
- **NO-SHIP** otherwise; no third wording iteration inside this measurement.

One attempt per run; an infrastructure death may be relaunched once and noted.

## Added risk, stated up front

v2's paragraph names the symptom-repair failure explicitly. That sentence is aimed
at d1's exact shape, so d1 is even more in-sample than in v1. The restraint arm is
therefore the entire generalization claim: pyd (deliberate near-identical function
pair), pyt (deliberate internal/public type split), d2 (deliberate sentinel scheme),
and d6 (relocation-vs-removal) are where an owner-counting agent could now
over-merge — each pack's deliberate split is exactly a "two sites that look like one
question" trap. A SHIP without those four staying clean would be worthless, which is
why they run unconditionally.
