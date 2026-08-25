#!/usr/bin/env python3
"""Selftest for G48 (run_id identity discipline, REPORT-ONLY).

Subprocesses the SHIPPED validate-artifact.py against temp-dir artifacts — never a
reimplementation (the item-16 acceptance rule, _g47_selftest.py precedent). Assertions
are on the [g48-run-id] stdout diagnostics plus a standing guard that NO G48 Issue ever
reaches the --json sidecar (the REPORT_ONLY contract: diagnostics print on detection for
every epoch; enforcement waits on the module's written promotion bar). A synthetic
minimal artifact legitimately fails unrelated gates (G18/G19...), which is not what this
test measures.

Stability contract under test: a non-null run_id must not change across consecutive
loop numbers; post-reset stalled numbering (1,2,1,2) is a run boundary, not a violation;
null -> non-null mid-run minting is legal.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
VALIDATOR = SCRIPTS / "validate-artifact.py"

GOOD = "run-2026-08-21-0123456789abcdef0123456789abcdef"
GOOD2 = "run-2026-08-21-fedcba9876543210fedcba9876543210"
BAD = "loop-2-302837137"
REV = "2b81c10"  # any 4-40 hex short sha classifies CURRENT


def _run(td: Path, review: dict, loops: list[dict] | None = None) -> tuple[list[str], str]:
    (td / "CURRENT_REVIEW.json").write_text(json.dumps(review, indent=1) + "\n")
    history = td / "REVIEW_HISTORY.json"
    if loops is not None:
        history.write_text(json.dumps({"schema_version": 3, "loops": loops}, indent=1) + "\n")
    elif history.exists():
        history.unlink()
    sidecar = td / "_issues.json"
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), str(td), "--mode", "strict", "--json", str(sidecar)],
        capture_output=True,
        text=True,
    )
    payload = json.loads(sidecar.read_text())
    g48 = [i["message"] for i in payload.get("issues", []) if i.get("rule") == "G48"]
    diags = "\n".join(ln for ln in proc.stdout.splitlines() if ln.startswith("[g48-run-id"))
    return g48, diags


def _review(rid, rev=REV, schema=4, loop=2) -> dict:
    r = {"schema_version": schema, "loop": loop, "run_id": rid, "state": "CONTINUE"}
    if rev is not None:
        r["skill_rev"] = rev
    return r


def main() -> int:
    failures: list[str] = []
    issue_leaks: list[str] = []

    def case(name: str, review: dict, loops=None) -> str:
        with tempfile.TemporaryDirectory(prefix="g48-selftest-") as td_s:
            g48, diags = _run(Path(td_s), review, loops=loops)
        if g48:
            issue_leaks.append(f"{name}: {g48}")
        return diags

    # 1. Conformant id, current epoch: no diagnostic.
    diags = case("conformant/current", _review(GOOD))
    if diags:
        failures.append(f"conformant/current must print nothing, got {diags!r}")

    # 2. Bad format, current epoch: format diagnostic prints.
    diags = case("bad/current", _review(BAD))
    if "does not match" not in diags:
        failures.append(f"bad-format/current must print the format diagnostic, got {diags!r}")

    # 3. Bad format, LEGACY (no skill_rev): diagnostic still prints (epoch-independent).
    diags = case("bad/legacy", _review(BAD, rev=None))
    if "does not match" not in diags:
        failures.append(f"bad-format/legacy must still print the diagnostic, got {diags!r}")

    # 4. Null run_id: silent (minting is the loop's job; G32 owns terminal non-null).
    diags = case("null-rid", _review(None))
    if diags:
        failures.append(f"null-run_id must be silent, got {diags!r}")

    # 4c. Restraint: a fully-minted history stays silent.
    hist_ok = [
        {"loop": 1, "run_id": GOOD, "schema_version": 4},
        {"loop": 2, "run_id": GOOD, "schema_version": 4},
    ]
    diags = case("history-all-minted", _review(GOOD), loops=hist_ok)
    if diags:
        failures.append(f"a fully-minted history must be silent, got {diags!r}")

    # 5. Bad format at schema_version 3: silent (run_id is a v4+ field).
    diags = case("schema-3", _review(BAD, schema=3))
    if diags:
        failures.append(f"schema-3 must be silent, got {diags!r}")

    # 6. Stability: consecutive loops with a non-null id change -> diagnostic.
    loops = [
        {"schema_version": 4, "loop": 1, "run_id": GOOD},
        {"schema_version": 4, "loop": 2, "run_id": GOOD2},
    ]
    diags = case("rid-change", _review(GOOD2), loops=loops)
    if "changed within a run" not in diags:
        failures.append(
            f"consecutive-loop id change must print stability diagnostic, got {diags!r}"
        )

    # 6b. Non-null -> null across consecutive loops is also a change.
    loops = [
        {"schema_version": 4, "loop": 1, "run_id": GOOD},
        {"schema_version": 4, "loop": 2, "run_id": None},
    ]
    diags = case("rid-dropped", _review(None), loops=loops)
    if "changed within a run" not in diags:
        failures.append(f"non-null->null across consecutive loops must print, got {diags!r}")

    # 7. null -> non-null mid-run minting is legal.
    loops = [
        {"schema_version": 4, "loop": 1, "run_id": None},
        {"schema_version": 4, "loop": 2, "run_id": GOOD},
    ]
    diags = case("mid-run-mint", _review(GOOD), loops=loops)
    # This case guards the STABILITY check specifically: a null predecessor is not an id
    # *change*, so stability must stay quiet. It is not a claim that the null itself is fine.
    # Since 2026-08-23 the mint happens at Step 1 sub-step 5, in the same pass that writes the
    # artifact, so a history entry can no longer legitimately be null and the missing-mint
    # sub-check SHOULD fire here. Asserting plain silence would have re-hidden the exact
    # failure that ran live on BenchHype (loop 1 null, loops 2-6 conformant, G48 silent).
    if "changed within a run" in diags:
        failures.append(f"a mid-run mint must not trip the stability check, got {diags!r}")
    if "did not fire" not in diags:
        failures.append(
            f"a history entry with a null run_id must print the missing-mint diagnostic, got {diags!r}"
        )

    # 8. Post-reset stalled numbering (1,2,1,2), different id per segment: run boundary,
    #    not a violation (reset restarts numbering at 1 -> no consecutive pair spans it).
    loops = [
        {"schema_version": 4, "loop": 1, "run_id": GOOD},
        {"schema_version": 4, "loop": 2, "run_id": GOOD},
        {"schema_version": 4, "loop": 1, "run_id": GOOD2},
        {"schema_version": 4, "loop": 2, "run_id": GOOD2},
    ]
    diags = case("post-reset", _review(GOOD2), loops=loops)
    if diags:
        failures.append(f"post-reset segments must be silent, got {diags!r}")

    # 9. Historic pre-mint loop from an OLD, already-closed run must stay silent -- only
    #    entries in the CURRENT run are diagnosed (retro #5). Both entries carry `loop: 1`
    #    because a `--reset` restarts numbering; the LAST such entry marks the current run's
    #    start, so the old run's null run_id (before it) must not resurface on every validate.
    loops = [
        {"schema_version": 4, "loop": 1, "run_id": None},  # OLD run: pre-mint, already closed
        {"schema_version": 4, "loop": 1, "run_id": GOOD2},  # reset boundary -> new run starts clean
    ]
    diags = case("historic-null-old-run", _review(GOOD2, loop=1), loops=loops)
    if diags:
        failures.append(f"a null run_id from a closed prior run must stay silent, got {diags!r}")

    # REPORT_ONLY guard: across every case above, no G48 Issue may ever have surfaced.
    if issue_leaks:
        failures.append(f"REPORT_ONLY violated — G48 Issues surfaced: {issue_leaks}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: G48 — report-only diagnostics RED/GREEN on both epochs, reset boundaries respected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
