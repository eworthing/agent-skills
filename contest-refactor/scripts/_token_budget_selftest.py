#!/usr/bin/env python3
"""Self-test for token-budget.py (R2-N1 from peer review).

Asserts that --loaded-set matches the documented Reference Load Matrix in SKILL.md and
the per-loop file set recorded in analysis/contest-refactor/TOKEN-USAGE-AUDIT.md, so a
savings number is never trusted off a tool whose routing has silently drifted.

Run directly: `python3 scripts/_token_budget_selftest.py` (exit 0 = pass). Stdlib-only.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent

spec = importlib.util.spec_from_file_location("token_budget", HERE / "token-budget.py")
tb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tb)

failures: list[str] = []


def check(cond: bool, msg: str):
    if not cond:
        failures.append(msg)


# --- Golden per-step sets (source: SKILL.md "## Reference Load Matrix", rows Step 1 /
# Step 1 emit / Step 2 / Step 3). If SKILL.md's matrix changes, update both it and these.
GOLDEN_APPLE = {
    "step1": [
        "SKILL.md",
        "lens-apple.md",
        "lens-security.md",
        "lens-efficiency.md",
        "method.md",
        "method-critic.md",
        "architecture-rubric.md",
        "architecture-rubric-scoring.md",
    ],
    "step1_emit": [
        "output-format.md",
        "output-format-json.md",
        "output-format-json-rules.md",
        "output-format-markdown.md",
        "validation.md",
    ],
    "step2": ["method.md", "architecture-rubric.md"],
    "step3": [
        "output-format.md",
        "output-format-json-rules.md",
        "output-format-markdown-archive.md",
        "validation.md",
        "implementation-reviewer.md",
        "provider-adapters.md",
    ],
}

for step, golden in GOLDEN_APPLE.items():
    got = tb.loaded_set(step, lens="apple")
    check(got == golden, f"loaded_set({step!r}) = {got}, expected {golden}")

# Generic lens swaps only the stack lens file.
check(
    tb.loaded_set("step1", lens="generic")[1] == "lens-generic.md",
    "generic lens did not swap lens-apple.md -> lens-generic.md in step1",
)

# --- The de-duped "loop" union must equal the 16-file per-loop set the audit documents
# (A1a added output-format-json-rules.md, the emit-time carve-out, at Step 1 emit / Step 3;
# 2026-07-13 promotion added always-included lens-efficiency.md at Step 1).
AUDIT_PER_LOOP = {
    "SKILL.md",
    "lens-apple.md",
    "lens-security.md",
    "lens-efficiency.md",
    "method.md",
    "method-critic.md",
    "architecture-rubric.md",
    "architecture-rubric-scoring.md",
    "output-format.md",
    "output-format-json.md",
    "output-format-json-rules.md",
    "output-format-markdown.md",
    "output-format-markdown-archive.md",
    "validation.md",
    "implementation-reviewer.md",
    "provider-adapters.md",
}
loop_union = set(tb.loaded_set("loop", lens="apple"))
check(
    loop_union == AUDIT_PER_LOOP,
    f"loop union {sorted(loop_union)} != audit per-loop set {sorted(AUDIT_PER_LOOP)}",
)

# --- Every file in every loaded set must actually exist on disk (catches a renamed ref).
for step in ("step1", "step1_emit", "step2", "step3"):
    for name in tb.loaded_set(step, lens="apple"):
        p = (SKILL_DIR / name) if name == "SKILL.md" else (SKILL_DIR / "references" / name)
        check(p.is_file(), f"loaded_set({step!r}) names missing file: {name}")

# --- Unknown step is a hard error, not a silent empty set.
try:
    tb.loaded_set("step99")
    failures.append("loaded_set('step99') did not raise")
except SystemExit:
    pass

# --- Counter is deterministic (same input -> same count); positive on real text.
count_fn, method = tb._make_counter()
s = "Claim -> Source -> Consequence -> Remedy. " * 7
check(count_fn(s) == count_fn(s), "counter is non-deterministic")
check(count_fn(s) > 0, "counter returned non-positive on real text")
check(count_fn("") == 0, "counter on empty string is non-zero")

# --- Budget guard (Lever D). The guard reads SKILL.md's matrix directly, so it closes the
# gap the GOLDEN_* lists above cannot: those duplicate the load table, and both could stay
# green while SKILL.md drifted underneath them.


class _Args:
    lens = "apple"


def _guard() -> int:
    """Run the guard with stdout captured -- the negative cases below print FAIL lines by
    design, and leaking them into a passing self-test's output reads like a real failure."""
    with contextlib.redirect_stdout(io.StringIO()):
        return tb.cmd_check(_Args(), count_fn, method)


check(_guard() == 0, "budget guard fails at HEAD")

# A heuristic tokenizer must refuse to render a verdict, not render a wrong one. The ceilings
# are hand-set from tiktoken counts, so a heuristic count is not comparable to them in either
# direction -- and exit 2 (plumbing: cannot measure) must stay distinguishable from exit 1
# (over budget), or "the tokenizer is missing" silently reads as "the budget is fine".
with contextlib.redirect_stdout(io.StringIO()) as _buf:
    _rc = tb.cmd_check(_Args(), count_fn, "heuristic(max(words/0.75, bytes/4))")
check(_rc == 2, f"a heuristic tokenizer must exit 2 (cannot measure), got {_rc}")
check(
    "CANNOT MEASURE" in _buf.getvalue(),
    "the heuristic refusal must say plainly that it could not measure",
)
check(
    "budget-guard: OK" not in _buf.getvalue(),
    "a heuristic run must never print an OK verdict",
)

# A ceiling must actually bite.
_real = dict(tb.CEILINGS)
try:
    tb.CEILINGS["loop"] = 1
    check(_guard() == 1, "ceiling breach not detected")
finally:
    tb.CEILINGS.clear()
    tb.CEILINGS.update(_real)

# Matrix drift must actually bite: drop a declared divergence and the omission should surface.
_div = dict(tb.DECLARED_DIVERGENCES)
try:
    tb.DECLARED_DIVERGENCES.pop(("step1", "SKILL.md"), None)
    check(_guard() == 1, "undeclared load-table divergence not detected")
finally:
    tb.DECLARED_DIVERGENCES.clear()
    tb.DECLARED_DIVERGENCES.update(_div)

# Every declared divergence must still BE one. A stale exemption silently pre-approves a
# future real drift, which is the failure mode the guard exists to prevent.
# Checked under BOTH lenses: the table is lens-independent, so an entry that diverges
# under either lens (e.g. the stack lens itself) is live.
_matrix = tb._matrix_always()
for (step, name), reason in tb.DECLARED_DIVERGENCES.items():
    if step not in _matrix:
        continue
    declared = _matrix[step]
    live = False
    for _lens in ("apple", "generic"):
        actual = set(tb.loaded_set(step, _lens))
        if name in (actual - declared) or name in (declared - actual):
            live = True
            break
    check(
        live,
        f"stale DECLARED_DIVERGENCES entry ({step}, {name}): no longer a divergence -- remove it",
    )
    check(bool(reason.strip()), f"DECLARED_DIVERGENCES ({step}, {name}) has an empty reason")


if failures:
    print(f"FAIL ({len(failures)}):")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print(f"OK: token-budget self-test passed (counter method: {method})")
sys.exit(0)
