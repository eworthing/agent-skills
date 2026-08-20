#!/usr/bin/env python3
"""Self-test: G17, indirect coverage citation (_artifact_coverage_citation.py).

Three properties carry this gate, and each is easy to get wrong in a way that
reads as success:

  1. **Test-path classification must not be silently overbroad.** Misclassifying
     a source path as a test SUPPRESSES the diagnostic, and a check that never
     fires cannot be adjudicated later. A false positive gets looked at; a false
     negative is invisible. So the restraint cases here assert that ordinary
     production directories (`ABTesting`, `Testimonial`, `contest-refactor`)
     still FIRE, not merely that test directories stay silent.

  2. **Blindness is an outcome, not a pass.** `changed_paths` arrived at v3 and
     the v2->v3 migration default-fills it to `[]`, so absent evidence is
     indistinguishable from "no test file changed". Reading it as the latter
     fires G17 on every migrated v2 artifact.

  3. **The prose and the code must state one contract.** G17 is specified in
     validation.md AND output-format-json-rules.md; the accepted-kind regex is
     pinned against both by literal containment.

Run: python3 scripts/_g17_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import _artifact_coverage_citation as g17

DEEPENING = "Extracted the three duplicated bodies into one helper."
CITATION = [
    {
        "target_symbol": "persistSettingsChange",
        "target_symbol_kind": "new",
        "distinguishes_no_op": True,
    }
]


def _artifact(changed, what=DEEPENING, citations=None, schema_version=4, loop=2) -> dict:
    return {
        "schema_version": schema_version,
        "loop": loop,
        "loop_result": {
            "what_changed": what,
            "changed_paths": changed,
            "interface_test_coverage_path": citations,
        },
    }


def _run(artifact: dict) -> tuple[list, str]:
    """(returned issues, printed output).

    Classification is asserted through the PRINTED diagnostic, not the return
    value: under REPORT_ONLY the return is always empty, so asserting on it would
    make every case pass vacuously. The return value is checked once, separately,
    to pin the report-only invariant itself.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        real = g17.check_g17_coverage_citation(artifact, None)
    return real, buf.getvalue()


def _fires(artifact: dict) -> bool:
    _, out = _run(artifact)
    return "[G17]" in out


def _blind(artifact: dict) -> bool:
    _, out = _run(artifact)
    return "g17-check-blind" in out


def main() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    # --- 1. the trigger ----------------------------------------------------
    check(_fires(_artifact(["src/Widget.cs"])), "deepening + no test file + no citation must fire")
    check(
        not _fires(_artifact(["src/Widget.cs"], citations=CITATION)),
        "a well-formed citation must satisfy the gate",
    )
    check(
        not _fires(_artifact(["src/Widget.cs"], what="Renamed a local variable.")),
        "no deepening keyword -> silent",
    )
    check(
        not _fires(_artifact(["src/Widget.cs"], schema_version=1)),
        "below the v2 floor -> silent",
    )

    # --- 2. test-path restraint: these must stay SILENT --------------------
    for p in (
        "AppReducerWorkflowCoverageTests.swift",
        "Tests/Support.swift",
        "tests/conftest.py",
        "__tests__/helpers.ts",
        "BenchHype/BenchHypeUITests/UITestSupport.swift",
        "BenchHype/BenchHypeMacUITests/MacUITestSupport.swift",
        "test_ledger.py",
    ):
        check(not _fires(_artifact([p])), f"{p!r} is a test file; G17 must stay silent")

    # --- 3. overbreadth: these must still FIRE -----------------------------
    # A substring rule (`"Test" in seg`) matches ABTesting and Testimonial, and a
    # lowercase one matches `contest-refactor` -- this repo's own directory name.
    # Suppressing the diagnostic is the unrecoverable direction, so these are
    # asserted as must-fire rather than left to the classifier's discretion.
    for p in (
        "Sources/ABTesting/Experiment.swift",
        "Sources/Testimonial/Renderer.swift",
        "contest-refactor/scripts/tool_runner.py",
        "Sources/LatestSnapshot/Store.swift",
        "src/ContestEntry/Model.cs",
    ):
        check(
            _fires(_artifact([p])),
            f"{p!r} is a SOURCE path; G17 must fire (a silent miss is invisible)",
        )

    # --- 4. blindness ------------------------------------------------------
    for changed, why in (
        (None, "absent"),
        ([], "empty (the v2->v3 default-fill)"),
        ("src/Widget.cs", "not a list"),
        ([None], "null element"),
        ([""], "empty-string element"),
        ([{"path": "x"}], "dict element"),
        (["."], "'.' -> PurePosixPath('.').parts is ()"),
        (["/"], "'/' names no file"),
        ([".."], "'..' names no file"),
        (["Tests/"], "trailing separator: directory, not a file"),
        (["src/"], "trailing separator: directory, not a file"),
    ):
        check(_blind(_artifact(changed)), f"changed_paths {why} must be BLIND, not a pass")
        check(
            not _fires(_artifact(changed)),
            f"changed_paths {why} must not also report a violation",
        )

    check(
        not _blind(_artifact(["src/Widget.cs"])),
        "a complete artifact must not be reported blind",
    )
    check(
        g17.deepening_keywords("no keyword section here") == (),
        "an unparseable keyword block must yield no keywords (-> blind)",
    )
    check(
        "collapsed" in g17.deepening_keywords() and "extracted" in g17.deepening_keywords(),
        f"the canonical keyword list failed to parse: {g17.deepening_keywords()}",
    )

    # ...and an unreadable source must make the CHECK blind, not fall back to a
    # hardcoded list. A fallback silently re-copies the vocabulary the schema doc
    # says must never be duplicated, and the copy then cannot drift-fail.
    real_doc = g17._SCHEMA_DOC
    try:
        g17._SCHEMA_DOC = SKILL_ROOT / "references" / "does-not-exist.md"
        check(
            _blind(_artifact(["src/Widget.cs"])),
            "an unreadable keyword source must make the check BLIND, never fall back to a copy",
        )
        check(
            not _fires(_artifact(["src/Widget.cs"])),
            "an unreadable keyword source must not report a violation it could not derive",
        )
    finally:
        g17._SCHEMA_DOC = real_doc

    # --- 5. malformed citations -------------------------------------------
    for bad, why in (
        (
            [{"target_symbol": "", "target_symbol_kind": "new", "distinguishes_no_op": True}],
            "empty target_symbol",
        ),
        (
            [{"target_symbol": "x", "target_symbol_kind": "made_up", "distinguishes_no_op": True}],
            "bad kind",
        ),
        (
            [{"target_symbol": "x", "target_symbol_kind": "new", "distinguishes_no_op": False}],
            "no-op not distinguished",
        ),
        ([{"target_symbol": "x", "target_symbol_kind": "new"}], "distinguishes_no_op absent"),
        (["not-an-object"], "non-object entry"),
    ):
        check(
            _fires(_artifact(["src/Widget.cs"], citations=bad)),
            f"malformed citation ({why}) must fire",
        )

    # The role-bearing variant is the contract decision made when the three
    # shipped specs were aligned; assert it rather than leave it to the regex.
    check(
        not _fires(
            _artifact(
                ["src/Widget.cs"],
                citations=[
                    {
                        "target_symbol": "Bootstrap",
                        "target_symbol_kind": "existing_bootstrap_interface",
                        "distinguishes_no_op": True,
                    }
                ],
            )
        ),
        "role-bearing target_symbol_kind must be accepted (output-format-json-rules.md rule 22)",
    )

    # --- 6. report-only holds ---------------------------------------------
    issues, out = _run(_artifact(["src/Widget.cs"]))
    check("[G17]" in out, "guard assumption: this artifact should have printed a violation")
    check(
        g17.REPORT_ONLY and issues == [],
        f"REPORT_ONLY is set, so the check must return no Issue even when it printed: {issues}",
    )

    # --- 7. one contract, stated in prose and code -------------------------
    for rel in ("references/validation.md", "references/output-format-json-rules.md"):
        text = (SKILL_ROOT / rel).read_text(encoding="utf-8")
        check(
            g17.ACCEPTED_KIND_RE.strip("^$") in text,
            f"{rel} must state the same accepted-kind contract as the code "
            f"({g17.ACCEPTED_KIND_RE}) -- a mechanical G17 that disagrees with the "
            "manual G17 checklist leaves the numbered rule internally inconsistent",
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: G17 — trigger, test-path restraint both directions, blind-not-pass on v2/malformed "
        "paths, citation shape, report-only holds, one contract in prose and code"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
