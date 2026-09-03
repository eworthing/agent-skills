#!/usr/bin/env python3
"""Selftest for scripts/grade_site_pass.py (SITE-PASS plan W0). Run directly; exit 0 = pass.
Guards: evidence parsing for `path:a`, `path:a-b`, `path:a,b`; range-intersection hits;
the +/-5 single-line tolerance (boundary in and out); baseline exclusion of rejected sites
the pre-change artifact already touched; roster_gap null without a roster and computed with one.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grade_site_pass as G

P = "Mod/File.swift"
MANIFEST = {
    "scope": "Mod",
    "sites": [
        {
            "fid": 1,
            "verdict": "real",
            "path": P,
            "line_start": 100,
            "line_end": 110,
            "question": "Q1",
        },
        {
            "fid": 2,
            "verdict": "real",
            "path": P,
            "line_start": 200,
            "line_end": 200,
            "question": "Q2",
        },
        {
            "fid": 3,
            "verdict": "real",
            "path": "Mod/Other.swift",
            "line_start": 5,
            "line_end": 9,
            "question": None,
        },
        {
            "fid": 4,
            "verdict": "rejected",
            "path": P,
            "line_start": 300,
            "line_end": 305,
            "question": None,
        },
        {
            "fid": 5,
            "verdict": "rejected",
            "path": P,
            "line_start": 400,
            "line_end": 405,
            "question": None,
        },
    ],
}


def _artifact(evidence: list[str], roster: list[str] | None = None) -> dict:
    art = {"findings": [{"id": "F1", "evidence": evidence}]}
    if roster is not None:
        art["discovery"] = {"site_pass_roster": {"paths": roster, "digest": "x"}}
    return art


def test_parse_evidence_shapes() -> None:
    assert G.parse_evidence(f"{P}:12 (note)") == [(P, 7, 17)]
    assert G.parse_evidence(f"{P}:12-40 (note)") == [(P, 12, 40)]
    assert G.parse_evidence(f"{P}:311,316 (swap)") == [(P, 306, 316), (P, 311, 321)]
    assert G.parse_evidence("no line ref here") == []
    assert G.parse_evidence(f"{P}:40-12") == [(P, 12, 40)], "reversed span normalizes"


def test_intersection_and_tolerance() -> None:
    r = G.grade(_artifact([f"{P}:108-130"]), MANIFEST)
    assert [s["hit"] for s in r["sites"]] == [True, False, False, False, False], r["sites"]
    assert r["sites"][0]["finding_ids"] == ["F1"]
    r = G.grade(_artifact([f"{P}:205"]), MANIFEST)  # single line, 5 away -> hit
    assert r["sites"][1]["hit"] is True
    r = G.grade(_artifact([f"{P}:206"]), MANIFEST)  # 6 away -> miss
    assert r["sites"][1]["hit"] is False
    r = G.grade(
        _artifact([f"{P}:99"]), MANIFEST
    )  # single line, 1 before a range -> hit via tolerance
    assert r["sites"][0]["hit"] is True
    assert r["real_hits"] == 1 and r["real_total"] == 3


def test_restraint_and_baseline_exclusion() -> None:
    art = _artifact([f"{P}:301-302", f"{P}:401"])
    r = G.grade(art, MANIFEST)
    assert r["rejected_hits"] == 2 and r["restraint_failures"] == [4, 5], r
    baseline = _artifact([f"{P}:300-310"])
    r = G.grade(art, MANIFEST, baseline=baseline)
    assert r["exclusion_set"] == [4], r["exclusion_set"]
    assert r["restraint_failures"] == [5], r["restraint_failures"]
    assert r["sites"][3]["excluded"] is True and r["sites"][4]["excluded"] is False


def test_roster_gap() -> None:
    assert G.grade(_artifact([]), MANIFEST)["roster_gap"] is None
    r = G.grade(_artifact([], roster=[P]), MANIFEST)
    assert r["roster_gap"] == ["Mod/Other.swift"], r["roster_gap"]
    r = G.grade(_artifact([], roster=[P, "Mod/Other.swift"]), MANIFEST)
    assert r["roster_gap"] == []


def test_cli_json_and_table() -> None:
    import json
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        a = Path(td) / "a.json"
        m = Path(td) / "m.json"
        a.write_text(json.dumps(_artifact([f"{P}:100"])))
        m.write_text(json.dumps(MANIFEST))
        proc = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).parent / "grade_site_pass.py"),
                str(a),
                str(m),
                "--json",
                "--label",
                "t",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        out = json.loads(proc.stdout)
        assert out["label"] == "t" and out["real_hits"] == 1
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "grade_site_pass.py"), str(a), str(m)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0 and "real 1/3" in proc.stdout, proc.stdout


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print(f"PASS {_name}")
    print("grade_site_pass selftest: OK")
