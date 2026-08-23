#!/usr/bin/env python3
"""G48 — run_id identity discipline (format + cross-loop stability). REPORT-ONLY.

The lifecycle (SKILL.md Step 3 sub-step 3): a null ``run_id`` is minted
``run-<UTC yyyy-mm-dd>-<uuid4().hex>`` at the start of sub-step 3 — every loop,
wrapped or not — then carried unchanged; only ``--reset``/``--purge`` starts a
new run. Observed failure shape (BenchHype, 2026-08-19): a run minted a fresh
id per loop (``run-2026-08-20-001`` at loop 1, ``loop-2-302837137`` at loop 2),
which made ``coverage_ledger.split_runs`` see one run per loop and blinded the
transitions checker.

Two sub-checks:

- FORMAT: a non-null top-level ``run_id`` on a v4+ artifact must match
  ``^run-\\d{4}-\\d{2}-\\d{2}-[0-9a-f]{32}$``.
- STABILITY: within ``REVIEW_HISTORY.loops``, an adjacent pair with
  ``loop_b == loop_a + 1`` (consecutive ascending numbering = the same-run
  signal; ``--reset`` restarts numbering at 1, so reset boundaries never form
  consecutive pairs) must not change or drop a non-null run_id.
  null -> non-null is legal (mid-run minting under a pre-lift skill rev).

Deliberate disagreement with ``coverage_ledger.split_runs``: split_runs treats
a non-null run_id change as a run boundary even at contiguous ascending
numbering — conservative on purpose, so the transitions checker never
manufactures a false transition-violation across what might be a real boundary.
G48 flags exactly that shape as the identity-discipline defect itself:
contiguous numbering says same-run, the id says new-run, and the contradiction
is the violation.

Why REPORT_ONLY and not epoch-scoped (item 30, measured 2026-08-21): the
CURRENT epoch classifies on ``skill_rev`` presence alone, and the very run that
motivated this gate already emitted ``skill_rev`` (``4fe8cdf``) — under an
epoch-scoped Issue its committed terminal artifact fails retroactively even
though the mint/format rule shipped AFTER that run. The binary LEGACY/CURRENT
boundary is too coarse for a requirement this new. Promotion bar (report-only
is permanent by default unless the bar is written down — the G17 lesson):
graduate to an Issue only when BOTH (a) an epoch boundary exists that provably
post-dates this gate's ship — e.g. a third ``EPOCHS`` entry classified by a
skill-repo ancestor check on ``skill_rev``, or a marker only the post-G48 skill
emits — so no artifact produced before 2026-08-21 can classify into it; and
(b) M2 (run-kit PREDECLARATION) observes at least one instrumented run PASS
under the lifted mint prose, with every diagnostic adjudicated and zero false
positives.
"""

from __future__ import annotations

import re
from itertools import pairwise

from _artifact_core import Issue

REPORT_ONLY = True
RUN_ID_RE = re.compile(r"^run-\d{4}-\d{2}-\d{2}-[0-9a-f]{32}$")


def check_g48_run_identity(current_review, review_history) -> list[Issue]:
    if not isinstance(current_review, dict):
        return []
    loop = current_review.get("loop")
    fired: list[str] = []

    rid = current_review.get("run_id")
    schema = current_review.get("schema_version")
    if (
        isinstance(schema, int)
        and schema >= 4
        and rid is not None
        and not (isinstance(rid, str) and RUN_ID_RE.match(rid))
    ):
        fired.append(
            f"run_id={rid!r} does not match run-<UTC yyyy-mm-dd>-<uuid4().hex> "
            f"(SKILL.md Step 3 sub-step 3 minting rule)"
        )

    loops = review_history.get("loops") if isinstance(review_history, dict) else None
    if isinstance(loops, list):
        entries = [e for e in loops if isinstance(e, dict)]
        for a, b in pairwise(entries):
            la, lb = a.get("loop"), b.get("loop")
            if not (isinstance(la, int) and isinstance(lb, int) and lb == la + 1):
                continue  # non-consecutive numbering: reset boundary or malformed — not a same-run pair
            ra, rb = a.get("run_id"), b.get("run_id")
            if ra is not None and rb != ra:
                fired.append(
                    f"run_id changed within a run: loop {la} carried {ra!r}, loop {lb} carries "
                    f"{rb!r} (consecutive numbering = same run; the id names the run, not the loop)"
                )

        # MISSING MINT: a loop that reached the history append without an id. The two checks
        # above are both blind to it -- FORMAT skips null via `rid is not None`, and STABILITY
        # only fires on a non-null predecessor, since null -> non-null is the legal mid-run
        # mint. Together they meant a run where the mint never fired was invisible here until
        # G32 caught it at HALT_SUCCESS_candidate, and invisible forever on a run that never
        # reached it. Observed live 2026-08-23: loop 1 appended with run_id None while loops
        # 2-6 carried one conformant id, and G48 printed nothing.
        for e in entries:
            if (
                isinstance(e.get("schema_version"), int)
                and e["schema_version"] >= 4
                and not e.get("run_id")
            ):
                fired.append(
                    f"loop {e.get('loop')!r} was appended to REVIEW_HISTORY with run_id="
                    f"{e.get('run_id')!r} — the mint (SKILL.md Step 1 sub-step 5) did not fire "
                    f"before the history append"
                )

    for msg in fired:
        print(f"[g48-run-id loop={loop} {msg}]")
    return []  # REPORT_ONLY: diagnostics only, never an Issue — see the promotion bar above
