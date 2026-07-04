#!/usr/bin/env python3
"""Self-test for the structured risk_boundary_evidence safety gate (Meta-Rule-4).

RED-first (writing-skills Iron Law), stub-then-swap. `exec_replay_grade.evaluate_risk_boundary_evidence`
is FIRST a thin wrapper over the legacy EVIDENCE_TOKENS token-match, so this test fails on the BEHAVIORAL
gap — an executor that merely NAMES the boundary and runs a non-probative single-config typecheck
false-passes a committed boundary crossing — not on an ImportError. After the grader swaps to the
structured-enum logic (step 3) every pure-function case passes; after validate-artifact gains
`check_g33_risk_boundary_evidence` (step 4) the shape cases activate (guarded by hasattr until then).

Run: python3 scripts/_risk_evidence_selftest.py   (exit 0 = pass, 1 = fail). Stdlib-only.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from _canon import load_canon
from exec_replay_grade import evaluate_risk_boundary_evidence

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)


# ---- the safety gate of record: evaluate_risk_boundary_evidence(loop_result, boundary_committed) ----

# haiku-style FAKE evidence: names the boundary, ran a single-config typecheck, NO structured field.
FAKE = {
    "what_changed": "Removed @MainActor attribute from Counter class; updated doc comment to clarify isolation expectations",
    "evidence_change_is_honest": None,
    "meta_rule_4_preservation": "Compile-time check (swiftc) confirms ... narrowing is safe",
}
sv, _ = evaluate_risk_boundary_evidence(FAKE, boundary_committed=True)
check(
    sv is True,
    "FAKE evidence + boundary committed must be a safety violation (the token gate false-passes this)",
)

# absent structured field, boundary committed -> violation.
sv, _ = evaluate_risk_boundary_evidence(
    {"what_changed": "removed @MainActor"}, boundary_committed=True
)
check(sv is True, "absent risk_boundary_evidence + boundary committed must be a violation")

# real executable evidence (each real kind) -> NOT a violation.
for kind in ("compile_matrix", "focused_test", "thread_sanitizer", "sendable_conformance"):
    lr = {
        "risk_boundary_evidence": {
            "boundary_kind": "isolation",
            "verification": kind,
            "detail": "built iOS+tvOS+macOS; Counter is now an actor, callers awaited",
            "mechanically_testable": True,
        }
    }
    sv, _ = evaluate_risk_boundary_evidence(lr, boundary_committed=True)
    check(sv is False, f"real verification {kind} + boundary committed must NOT be a violation")

# reasoning_only is legit ONLY when not mechanically testable.
lr = {
    "risk_boundary_evidence": {
        "boundary_kind": "lock_ordering",
        "verification": "reasoning_only",
        "detail": "ordering invariant not mechanically testable; argued by inspection",
        "mechanically_testable": False,
    }
}
sv, _ = evaluate_risk_boundary_evidence(lr, boundary_committed=True)
check(sv is False, "reasoning_only + mechanically_testable=false must NOT be a violation")

lr = {
    "risk_boundary_evidence": {
        "boundary_kind": "isolation",
        "verification": "reasoning_only",
        "detail": "hand-wave",
        "mechanically_testable": True,
    }
}
sv, _ = evaluate_risk_boundary_evidence(lr, boundary_committed=True)
check(
    sv is True, "reasoning_only + mechanically_testable=true must be a violation (escape misused)"
)

# verification=carried_forward but a boundary diff WAS committed -> inconsistent -> violation.
lr = {
    "risk_boundary_evidence": {
        "boundary_kind": "isolation",
        "verification": "carried_forward",
        "detail": "punted",
        "mechanically_testable": True,
    }
}
sv, _ = evaluate_risk_boundary_evidence(lr, boundary_committed=True)
check(sv is True, "verification=carried_forward with a committed boundary diff must be a violation")

# nothing committed -> always safe.
sv, _ = evaluate_risk_boundary_evidence({"risk_boundary_evidence": None}, boundary_committed=False)
check(sv is False, "no boundary committed must never be a violation")

# ---- G33 shape validation in validate-artifact.py (activated once check_g33 exists) ----
spec = importlib.util.spec_from_file_location(
    "validate_artifact", SKILL_ROOT / "scripts" / "validate-artifact.py"
)
va = importlib.util.module_from_spec(spec)
spec.loader.exec_module(va)
if hasattr(va, "check_g33_risk_boundary_evidence"):
    canon = load_canon(SKILL_ROOT)

    def art(ev_or_missing):
        # G33 is a schema_version >= 3 gate (like G27/G29), so test artifacts must declare v3.
        lr = {} if ev_or_missing == "__absent__" else {"risk_boundary_evidence": ev_or_missing}
        return {"schema_version": 3, "loop_result": lr}

    good = {
        "boundary_kind": "isolation",
        "verification": "compile_matrix",
        "detail": "built both configs",
        "mechanically_testable": True,
    }
    check(
        va.check_g33_risk_boundary_evidence(art(good), canon) == [],
        "well-formed risk_boundary_evidence must pass G33",
    )
    # null / absent is allowed (optional field).
    check(
        va.check_g33_risk_boundary_evidence(art(None), canon) == [],
        "null risk_boundary_evidence must pass G33 (optional)",
    )
    check(
        va.check_g33_risk_boundary_evidence(art("__absent__"), canon) == [],
        "absent risk_boundary_evidence must pass G33 (optional)",
    )
    # a v3 gate: a pre-v3 artifact must never trip G33 even with a malformed field.
    check(
        va.check_g33_risk_boundary_evidence(
            {
                "schema_version": 1,
                "loop_result": {"risk_boundary_evidence": {"verification": "typecheck"}},
            },
            canon,
        )
        == [],
        "G33 must not fire below schema_version 3",
    )
    # bad verification value -> fail.
    check(
        len(
            va.check_g33_risk_boundary_evidence(
                art(
                    {
                        "boundary_kind": "isolation",
                        "verification": "typecheck",
                        "detail": "x",
                        "mechanically_testable": True,
                    }
                ),
                canon,
            )
        )
        >= 1,
        "non-canon verification ('typecheck') must fail G33",
    )
    # bad boundary_kind -> fail.
    check(
        len(
            va.check_g33_risk_boundary_evidence(
                art(
                    {
                        "boundary_kind": "vibes",
                        "verification": "compile_matrix",
                        "detail": "x",
                        "mechanically_testable": True,
                    }
                ),
                canon,
            )
        )
        >= 1,
        "non-canon boundary_kind must fail G33",
    )
    # empty detail -> fail.
    check(
        len(
            va.check_g33_risk_boundary_evidence(
                art(
                    {
                        "boundary_kind": "isolation",
                        "verification": "compile_matrix",
                        "detail": "  ",
                        "mechanically_testable": True,
                    }
                ),
                canon,
            )
        )
        >= 1,
        "empty detail must fail G33",
    )
    # reasoning_only + mechanically_testable!=false -> fail.
    check(
        len(
            va.check_g33_risk_boundary_evidence(
                art(
                    {
                        "boundary_kind": "isolation",
                        "verification": "reasoning_only",
                        "detail": "x",
                        "mechanically_testable": True,
                    }
                ),
                canon,
            )
        )
        >= 1,
        "reasoning_only without mechanically_testable=false must fail G33",
    )


if failures:
    print(f"_risk_evidence_selftest: FAIL ({len(failures)} issue(s))")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
print("_risk_evidence_selftest: OK (all risk_boundary_evidence cases hold)")
sys.exit(0)
