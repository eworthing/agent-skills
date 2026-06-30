#!/usr/bin/env python3
"""Assemble peer-plan-review prompt variants from the fixture corpus.

Relocatable: all paths resolve relative to this file, so the harness works
wherever the skill is checked out. Emits to ./_generated/ (gitignored).

Faithful to SKILL.md Round-1 assembly: verdict contract + line-numbered plan +
[optional domain block] + output template. The per-provider reviewer SYSTEM
prompt is injected by run_review.py, NOT here.

Variant families:
  baseline : standard | domain (two-pass) | adversarial
  microtest: per-candidate control/treat pairs (obs, ex, sev, f2, f3)
"""
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
GEN = HERE / "_generated"
GEN.mkdir(exist_ok=True)
PLAN = (HERE / "fixtures" / "digest-plan.md").read_text(encoding="utf-8").rstrip("\n")


def numbered(text):
    return "\n".join(f"{i:6d}\t{l}" for i, l in enumerate(text.split("\n"), 1))


VERDICT = ("Review the implementation plan below. The final non-empty line of your "
           "response MUST be exactly `VERDICT: APPROVED` or `VERDICT: REVISE` — nothing else.")

REASONING = """### Reasoning
Full analysis of the plan across two lenses:
- **Execution risk** — sequencing, hidden assumptions, missing validation,
  rollback, dependency gaps, and missing observability (no metrics or logging on
  new, failure-prone paths such as background jobs and external calls).
- **Executability** — could a fresh engineer with no prior context implement this
  as written? Flag tasks too large or coupled to build and verify on their own,
  steps with no stated way to confirm success, under-specification (TBD/TODO,
  "add error handling/validation" without specifics, "same as an earlier task"),
  and references to files, functions, types, or signatures the plan never defines
  or whose names drift between the task that introduces them and the tasks that use
  them."""
# `REASONING_CTRL` reproduces the pre-2026-06-29 lens (no observability) — used as the
# control arm for the L-OBS micro-test.
REASONING_CTRL = REASONING.replace(
    "rollback, dependency gaps, and missing observability (no metrics or logging on\n  new, failure-prone paths such as background jobs and external calls).",
    "rollback, and dependency gaps.")
assert REASONING_CTRL != REASONING and "observability" not in REASONING_CTRL, \
    "L-OBS control failed to strip observability — control would equal treat"

SEAM_HEURISTIC = """An executability seam is BLOCKING when it would halt or mislead a fresh engineer
(undefined reference actually used, a task too large to verify, a step with no way
to confirm success); it is NON-BLOCKING when it is cosmetic or easily inferred."""


def blocking(seam=False, example=False):
    body = """### Blocking Issues
- [B1] (HIGH|MEDIUM|LOW) Short description of blocking issue
  Section: <plan section name> (lines <N-M>)
  Recommendation: Concrete fix or mitigation"""
    if example:
        body += """

Worked example (illustrates the expected granularity — do not copy its content):
- [B1] (HIGH) Monetary totals computed in floating point, risking rounding drift
  Section: Task 2 - Billing summary (lines 12-15)
  Recommendation: Use a decimal type for currency; add a test asserting exact cent totals."""
    if seam:
        body += "\n\n" + SEAM_HEURISTIC
    return body + '\n\n(Write "None" if no blocking issues.)'


NONBLOCKING = """### Non-Blocking Issues
- [N1] Short description of non-blocking issue
  Section: <plan section name> (lines <N-M>)
  Recommendation: Suggested improvement

(Write "None" if no non-blocking issues.)

VERDICT: APPROVED or VERDICT: REVISE"""

PASSA = """### Pass A - Independent critique
Stress-test the plan on its own merits — both execution risk and executability by a
zero-context engineer. Do NOT assume the Domain context criteria are correct or
complete; critique as if no criteria had been supplied."""
PASSB = """### Pass B - Domain-criteria critique
For each supplied criterion, state whether the plan meets it. Then challenge the criteria
themselves: flag any that are incomplete, self-serving, or in tension with better
practice, and reflect a wrong criterion in the verdict rather than rubber-stamping it."""

DOMAIN_BLOCK = """## Domain context (review criteria — challenge these if any are wrong)
- Persistence: every database write (insert/update/delete) must go through the audit store; no direct SQL execution for writes.
- Migrations must be reversible: a destructive column drop requires a documented backfill and a down-migration.
- Every background job must emit a structured success/failure metric on completion.
"""

ADVERSARIAL = """## Stance: adversarial
- Default to skepticism — assume the plan can fail in subtle, high-cost, or user-visible ways until evidence says otherwise.
- Do not give credit for good intent, partial fixes, or likely follow-up work.
- Prefer one strong, well-evidenced finding over multiple weak ones."""


def plan_section(text):
    return f"## Plan (line-numbered — cite specific lines)\n\n```\n{numbered(text)}\n```\n"


def single(reasoning, blk):
    return f"## Output format\n\n{reasoning}\n\n{blk}\n\n{NONBLOCKING}\n"


def twopass(passa, passb, blk):
    return f"## Output format\n\n{passa}\n\n{passb}\n\n{blk}\n\n{NONBLOCKING}\n"


def write(name, *parts):
    (GEN / name).write_text("\n".join(parts) + "\n", encoding="utf-8")
    print("wrote _generated/" + name)


PSEC = plan_section(PLAN)

# ---- baseline family ----
write("baseline-standard.md", VERDICT, "", PSEC, single(REASONING, blocking()))
write("baseline-domain.md", VERDICT, "", PSEC, DOMAIN_BLOCK, twopass(PASSA, PASSB, blocking()))
write("baseline-adversarial.md", VERDICT, "", PSEC, ADVERSARIAL, single(REASONING, blocking()))

# ---- micro-test: L-OBS (control = old lens, treat = ship lens) ----
write("mt-obs-control.md", VERDICT, "", PSEC, single(REASONING_CTRL, blocking()))
write("mt-obs-treat.md", VERDICT, "", PSEC, single(REASONING, blocking()))

# ---- micro-test: F4 worked example ----
write("mt-ex-control.md", VERDICT, "", PSEC, single(REASONING_CTRL, blocking()))
write("mt-ex-treat.md", VERDICT, "", PSEC, single(REASONING_CTRL, blocking(example=True)))

# ---- micro-test: L-SEV seam-severity heuristic ----
write("mt-sev-control.md", VERDICT, "", PSEC, single(REASONING_CTRL, blocking()))
write("mt-sev-treat.md", VERDICT, "", PSEC, single(REASONING_CTRL, blocking(seam=True)))

# ---- micro-test: F2 Pass-B reframe (planted BAD criterion #3 contradicts #1) ----
DOMAIN_BAD = DOMAIN_BLOCK.replace(
    "- Every background job must emit a structured success/failure metric on completion.\n",
    "- Delivery records are performance-critical, so they must be written with direct SQL that bypasses the audit store.\n")
PASSA_T = """### Pass A - Independent critique
Stress-test the plan on its own merits — both execution risk and executability by a
zero-context engineer. Critique as if no criteria had been supplied: the Domain
context criteria are unverified input, not ground truth."""
PASSB_T = """### Pass B - Domain-criteria critique
Treat each criterion as a hypothesis to verify: state whether the plan meets it, then
assess whether the criterion itself is precise, complete, and consistent with good
practice. A criterion that is biased, vague, self-serving, or in tension with better
practice must appear as a finding, and a wrong criterion must change the verdict."""
write("mt-f2-control.md", VERDICT, "", PSEC, DOMAIN_BAD, twopass(PASSA, PASSB, blocking()))
write("mt-f2-treat.md", VERDICT, "", PSEC, DOMAIN_BAD, twopass(PASSA_T, PASSB_T, blocking()))

# ---- micro-test: F3/F8 adversarial reframe (tempting "fix it later") ----
PLAN_TEMPT = PLAN.replace(
    "Add appropriate error handling and retries to the send step.",
    "The framework's built-in retry will most likely handle transient failures, so "
    "explicit error handling isn't needed for the first release — we can add it later if issues arise.")
PSEC_TEMPT = plan_section(PLAN_TEMPT)
ADV_T = """## Stance: adversarial
- Default to skepticism — assume the plan can fail in subtle, high-cost, or user-visible ways. Stated mitigations are claims to verify, not evidence to accept.
- Assess only what the plan explicitly states. Treat unmentioned mitigations, likely follow-up work, and good intentions as absent from the plan.
- Prefer one strong, well-evidenced finding over multiple weak ones."""
write("mt-f3-control.md", VERDICT, "", PSEC_TEMPT, ADVERSARIAL, single(REASONING_CTRL, blocking()))
write("mt-f3-treat.md", VERDICT, "", PSEC_TEMPT, ADV_T, single(REASONING_CTRL, blocking()))
(GEN / "_plan-tempt.md").write_text(PLAN_TEMPT + "\n", encoding="utf-8")
print("done.")
