#!/usr/bin/env python3
"""Selftest for audit_suppressions.py (DD-06). Run directly; exit 0 = pass.

Guards the four properties the detector's usefulness rests on:
  1. a blanket suppression is flagged;
  2. a coded one is NOT (restraint -- `# noqa: F401` on a re-export is idiom);
  3. a rationale, on the line or the line above, silences the hit;
  4. a swallowed CI gate counts only when the step actually checks something.
Mutating any of the four must fail this file.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_suppressions as A


def _repo(files: dict[str, str]) -> Path:
    d = Path(tempfile.mkdtemp(prefix="supp-selftest-"))
    for rel, body in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return d


def _kinds(report: dict, check: str) -> list[dict]:
    return [h for h in report["hits"] if h["check"] == check]


def test_blanket_flagged_coded_not() -> None:
    r = A.audit(
        _repo(
            {
                "a.py": "import os  # noqa\n",
                "b.py": "import os  # noqa: F401\n",
                "c.swift": "// swiftlint:disable\nlet x = 1\n",
                "d.swift": "// swiftlint:disable force_cast\nlet y = 2\n",
            }
        )
    )
    hits = _kinds(r, "reason_free_suppression")
    files = sorted(h["file"] for h in hits)
    assert files == ["a.py", "c.swift"], f"blanket/coded split wrong: {files}"
    assert all(h["scope"] == "blanket" for h in hits), hits
    assert r["counts"]["coded_suppression"] == 2, r["counts"]
    # Coded ones are disclosed, never dropped -- silence about them would be the
    # same defect as `absent` reading as `clean`.
    assert len(r["coded_suppressions"]) == 2, r["coded_suppressions"]


def test_rationale_silences() -> None:
    r = A.audit(
        _repo(
            {
                "trailing.py": "import os  # noqa  keep for the plugin hook\n",
                "above.py": "# re-exported on purpose for the shim\nimport os  # noqa\n",
                "bare.py": "import os  # noqa\n",
            }
        )
    )
    files = sorted(h["file"] for h in _kinds(r, "reason_free_suppression"))
    assert files == ["bare.py"], f"rationale not honoured: {files}"


def test_gate_needs_a_checker() -> None:
    r = A.audit(
        _repo(
            {
                ".github/workflows/ci.yml": (
                    "jobs:\n"
                    "  lint:\n"
                    "    steps:\n"
                    "      - run: ruff check .\n"
                    "        continue-on-error: true\n"
                ),
                ".github/workflows/deploy.yml": (
                    "jobs:\n"
                    "  ship:\n"
                    "    steps:\n"
                    "      - run: rsync -a build/ host:/srv\n"
                    "        continue-on-error: true\n"
                ),
            }
        )
    )
    gates = _kinds(r, "swallowed_gate")
    files = sorted(h["file"] for h in gates)
    assert files == [".github/workflows/ci.yml"], f"checker gating wrong: {files}"


def test_baseline_counted_and_exit_codes() -> None:
    d = _repo({"mypy-baseline.json": '["a.py:1: err", "b.py:2: err"]\n'})
    r = A.audit(d)
    base = _kinds(r, "lint_baseline")
    assert len(base) == 1 and base[0]["entries"] == 2, base
    assert A.main([str(d)]) == 2, "hits must exit 2"
    assert A.main([str(_repo({"clean.py": "import os\n"}))]) == 0, "clean must exit 0"


def test_promotion_never_allowed() -> None:
    # Every hit is a lead for Method Step 3, never a finding (Meta-Rule 1).
    assert A.audit(_repo({"a.py": "import os  # noqa\n"}))["promotion_allowed"] is False


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("audit_suppressions selftest: OK")
