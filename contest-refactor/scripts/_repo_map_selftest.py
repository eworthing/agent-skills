#!/usr/bin/env python3
"""Self-test: repo_map.py produces correct import-graph candidate evidence and stays
off the score/gate path.

W2.1 repo-map advisory candidate-evidence (Method.md Step 0 / Step 3). Doctrine
boundary (Method.md Meta-Rule 1): promotion_allowed: false — metrics support
judgment; they never decide it.

Assertions:
  1. Every module record carries promotion_allowed: false.
  2. The top-level output carries promotion_allowed: false.
  3. Import edges and fan-in/fan-out values are correct for a known DAG fixture.
  4. Cycles in the import graph are detected.
  5. first_party_file_count is correct (auto-engage threshold reproducibility).
  6. Isolation: adding a repo_map field to an artifact does NOT change any verdict
     from check_g21_scorecard or check_halt_success_gating in validate-artifact.py
     (mirrors _metric_isolation_selftest.py).

No pytest in this repo (pyproject configures only ruff) — standalone _*.py helper.

Run: python3 scripts/_repo_map_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_MAP = Path(__file__).with_name("repo_map.py")
VALIDATOR = Path(__file__).with_name("validate-artifact.py")


def _load_validator():
    spec = importlib.util.spec_from_file_location("_va_rm", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


def _run_map(root: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(REPO_MAP), str(root), "--format", "json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"repo_map.py exited {proc.returncode}: {proc.stderr.strip()}"
        )
    return json.loads(proc.stdout)


def _artifact(score: float, disposition: str | None) -> dict:
    return {
        "state": "HALT_SUCCESS",
        "scorecard": {
            "architecture_quality": {"score": score, "residual_disposition": disposition}
        },
        "findings": [],
    }


def _verdict(va, art: dict) -> list[str]:
    issues = va.check_g21_scorecard(art) + va.check_halt_success_gating(art, None)
    return sorted(f"{i.rule}: {i.message}" for i in issues)


def main() -> int:
    if not REPO_MAP.is_file():
        print(f"FAIL: repo_map.py missing: {REPO_MAP}")
        return 1

    failures: list[str] = []

    # -----------------------------------------------------------------------
    # Fixture A: 3-package DAG (no cycles)
    #
    # billing imports orders and shipping
    # orders imports shipping
    # shipping imports nothing first-party
    #
    # Expected fan-in:  billing=0, orders=1, shipping=2
    # Expected fan-out: billing=2, orders=1, shipping=0
    # Expected edges:   billing->orders, billing->shipping, orders->shipping
    # -----------------------------------------------------------------------
    FIXTURE_DAG = {
        "billing/__init__.py": (
            "from orders import checkout\n"
            "from shipping import tracker\n"
            "\nclass Invoice:\n    pass\n"
        ),
        "orders/__init__.py": (
            "from shipping import tracker\n"
            "\ndef checkout(cart):\n    return cart\n"
        ),
        "shipping/__init__.py": "READY = True\n",
    }

    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "dag"
        _write(root, FIXTURE_DAG)
        try:
            result = _run_map(root)
        except Exception as exc:
            failures.append(f"DAG fixture: repo_map.py failed — {exc}")
        else:
            # 1. Top-level promotion_allowed: false
            if result.get("promotion_allowed") is not False:
                failures.append(
                    f"DAG fixture: top-level promotion_allowed not false "
                    f"(got {result.get('promotion_allowed')!r})"
                )

            # 2. Every module record carries promotion_allowed: false
            for mod in result.get("modules", []):
                if mod.get("promotion_allowed") is not False:
                    failures.append(
                        f"DAG fixture: module {mod.get('module')!r} missing "
                        "promotion_allowed: false"
                    )

            # 3. first_party_file_count (3 files)
            fpc = result.get("first_party_file_count")
            if fpc != 3:
                failures.append(
                    f"DAG fixture: first_party_file_count expected 3, got {fpc!r}"
                )

            # 4. auto_engage must be False for 3 files (threshold is 300)
            ae = result.get("auto_engage")
            if ae is not False:
                failures.append(
                    f"DAG fixture: auto_engage expected False for 3 files, got {ae!r}"
                )

            # 5. Import edges: billing->orders, billing->shipping, orders->shipping
            edges = {(e["from"], e["to"]) for e in result.get("import_edges", [])}
            expected_edges = {
                ("billing", "orders"),
                ("billing", "shipping"),
                ("orders", "shipping"),
            }
            missing = expected_edges - edges
            if missing:
                failures.append(
                    f"DAG fixture: missing import edges {missing}; got {edges}"
                )

            # 6. Fan-in values
            mods_by_name = {m["module"]: m for m in result.get("modules", [])}
            for pkg, expected in {"billing": 0, "orders": 1, "shipping": 2}.items():
                actual = mods_by_name.get(pkg, {}).get("fan_in")
                if actual != expected:
                    failures.append(
                        f"DAG fixture: {pkg!r} fan_in expected {expected}, got {actual!r}"
                    )

            # 7. Fan-out values
            for pkg, expected in {"billing": 2, "orders": 1, "shipping": 0}.items():
                actual = mods_by_name.get(pkg, {}).get("fan_out")
                if actual != expected:
                    failures.append(
                        f"DAG fixture: {pkg!r} fan_out expected {expected}, got {actual!r}"
                    )

            # 8. No cycles in a clean DAG
            if result.get("cycles"):
                failures.append(
                    f"DAG fixture: unexpected cycles {result['cycles']!r}"
                )

            # 9. Public surface: Invoice in billing, checkout in orders, READY in shipping
            expected_surface = {"billing": "Invoice", "orders": "checkout", "shipping": "READY"}
            for pkg, name in expected_surface.items():
                surface = mods_by_name.get(pkg, {}).get("public_surface", [])
                if name not in surface:
                    failures.append(
                        f"DAG fixture: {pkg!r} public_surface missing {name!r}; got {surface!r}"
                    )

    # -----------------------------------------------------------------------
    # Fixture B: cycle (billing <-> reporting) — cycle detection
    # -----------------------------------------------------------------------
    FIXTURE_CYCLE = {
        "billing/__init__.py": "from reporting import audit_log\n",
        "reporting/__init__.py": "from billing import policy\n",
        "api/__init__.py": "from billing import invoice\nfrom reporting import summary\n",
    }

    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "cycle"
        _write(root, FIXTURE_CYCLE)
        try:
            result = _run_map(root)
        except Exception as exc:
            failures.append(f"Cycle fixture: repo_map.py failed — {exc}")
        else:
            cycles = result.get("cycles", [])
            cycle_sets = {frozenset(c) for c in cycles}
            if frozenset({"billing", "reporting"}) not in cycle_sets:
                failures.append(
                    f"Cycle fixture: expected billing<->reporting cycle; got {cycle_sets!r}"
                )
            # Every edge record must carry promotion_allowed: false
            for edge in result.get("import_edges", []):
                if edge.get("promotion_allowed") is not False:
                    failures.append(
                        f"Cycle fixture: edge {edge} missing promotion_allowed: false"
                    )

    # -----------------------------------------------------------------------
    # Isolation test: repo_map field on an artifact must not change any verdict
    # (mirrors _metric_isolation_selftest.py)
    # -----------------------------------------------------------------------
    CASES = [
        ("9.5-accepted (pass)", 9.5, "accepted"),
        ("10-clean (pass)", 10.0, None),
        ("9.4-fail (sub-threshold)", 9.4, "accepted"),
        ("9.5-queued (fail)", 9.5, "queued"),
    ]

    try:
        va = _load_validator()
    except Exception as exc:
        failures.append(f"Isolation: could not load validate-artifact.py — {exc}")
        va = None

    if va is not None:
        for label, score, disp in CASES:
            baseline = _verdict(va, _artifact(score, disp))

            art_with_map = _artifact(score, disp)
            art_with_map["repo_map"] = {
                "promotion_allowed": False,
                "first_party_file_count": 42,
                "auto_engage": False,
                "modules": [],
                "import_edges": [],
                "cycles": [],
            }
            with_map = _verdict(va, art_with_map)

            if with_map != baseline:
                failures.append(
                    f"Isolation ({label}): repo_map field changed verdict\n"
                    f"  no-map: {baseline}\n  with-map: {with_map}"
                )

        # Sanity: the boundary genuinely separates pass from fail (test isn't vacuous)
        if _verdict(va, _artifact(9.5, "accepted")):
            failures.append(
                "Isolation sanity: expected 9.5-accepted to PASS gate (got issues)"
            )
        if not _verdict(va, _artifact(9.4, "accepted")):
            failures.append(
                "Isolation sanity: expected 9.4-accepted to FAIL gate (got none)"
            )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "OK: repo_map — edges/fan-in/fan-out/cycles/public-surface correct, "
        "promotion_allowed: false on every record, auto_engage threshold reproducible, "
        f"gate-isolated ({len(CASES)} boundary case(s) give identical verdict with or "
        "without repo_map field)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
