#!/usr/bin/env python3
"""Self-test: audit-enum-interpretation.sh flags enums interpreted (switch/==/!=
against their cases) from outside their home module/file, and stays silent on
the false-positive classes the tiered attribution logic is designed to dodge.

Deliberate exception to this repo's "Bash helpers don't get selftests" norm
(see audit-naming.sh, audit-churn.sh, audit-public-surface.sh — none of those
get one): a peer-review round decided the precision-sensitive tiered
attribution here (qualified vs. unqualified, ambiguous-case gating, home
resolution across nested SPM layouts) warranted one. Do not add selftests for
the other Bash helpers off the back of this file existing.

Written in Python, driving the Bash script as a subprocess — matches this
repo's existing selftest idiom for scripts that need one (see any
`_*_selftest.py` for the general shape: build a temp fixture tree, run the
target script, assert on stdout).

Each fixture below is one function so a failure names exactly which of the
brief's seven cases (a)-(g) broke.

Run: python3 scripts/_audit_enum_interpretation_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

AUDIT = Path(__file__).with_name("audit-enum-interpretation.sh")


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


def _run(root: Path) -> tuple[str, str, int]:
    proc = subprocess.run(
        ["bash", str(AUDIT), str(root)],
        capture_output=True,
        text=True,
    )
    return proc.stdout, proc.stderr, proc.returncode


# --- (a) qualified Enum.case at 2 outside-home sites -> Tier 1 row ----------
def case_a_qualified_outside_home(base: Path) -> str | None:
    root = base / "a"
    _write(
        root,
        {
            "Package/Sources/ModuleA/Kind.swift": (
                "public enum Kind {\n    case one\n    case two\n}\n"
            ),
            "Package/Sources/ModuleB/Consumer.swift": (
                "func f(k: Kind) -> Bool {\n"
                "    if k == Kind.one { return true }\n"
                "    switch k {\n"
                "    case Kind.two: return false\n"
                "    default: return false\n"
                "    }\n"
                "}\n"
            ),
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "| Kind |" not in out:
        return f"expected a flagged row for Kind\n--- stdout ---\n{out}"
    row = next(line for line in out.splitlines() if line.startswith("| Kind |"))
    if "1 (qualified)" not in row:
        return f"expected Tier 1 (qualified) row for Kind, got: {row}"
    if "| 2 |" not in row:
        return f"expected outside-site count 2 for Kind, got: {row}"
    return None


# --- (b) unqualified == .uniqueCase at 2 outside-home sites -> Tier 2 row ---
def case_b_unqualified_unique_case(base: Path) -> str | None:
    root = base / "b"
    _write(
        root,
        {
            "Package/Sources/ModuleA/Flavor.swift": (
                "public enum Flavor {\n    case uniqueCaseName\n    case other\n}\n"
            ),
            "Package/Sources/ModuleB/User1.swift": (
                "func f1(x: Flavor) -> Bool {\n    return x == .uniqueCaseName\n}\n"
            ),
            "Package/Sources/ModuleB/User2.swift": (
                "func f2(x: Flavor) -> Bool {\n"
                "    switch x {\n"
                "    case .uniqueCaseName: return true\n"
                "    default: return false\n"
                "    }\n"
                "}\n"
            ),
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "| Flavor |" not in out:
        return f"expected a flagged row for Flavor\n--- stdout ---\n{out}"
    row = next(line for line in out.splitlines() if line.startswith("| Flavor |"))
    if "2 (unqualified)" not in row:
        return f"expected Tier 2 (unqualified) row for Flavor, got: {row}"
    if "| 2 |" not in row:
        return f"expected outside-site count 2 for Flavor, got: {row}"
    return None


# --- (c) ambiguous case shared by two enums -> NOT attributed to either ----
def case_c_ambiguous_case_not_attributed(base: Path) -> str | None:
    root = base / "c"
    _write(
        root,
        {
            "Package/Sources/ModuleA/EnumOne.swift": (
                "public enum EnumOne {\n    case active\n    case inactive\n}\n"
            ),
            "Package/Sources/ModuleA/EnumTwo.swift": (
                "public enum EnumTwo {\n    case active\n    case dormant\n}\n"
            ),
            "Package/Sources/ModuleB/User.swift": (
                "func g1(flag: Bool) {\n    if flag == .active {}\n}\n"
                "func g2(flag: Bool) {\n    if flag == .active {}\n}\n"
            ),
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "| EnumOne |" in out or "| EnumTwo |" in out:
        return f"ambiguous case '.active' must not attribute to either enum\n--- stdout ---\n{out}"
    return None


# --- (d) CodingKeys + case-less namespace enum -> excluded entirely --------
def case_d_excluded_from_inventory(base: Path) -> str | None:
    root = base / "d"
    _write(
        root,
        {
            "Package/Sources/ModuleA/Model.swift": (
                "enum CodingKeys: String, CodingKey {\n    case id\n    case name\n}\n"
                "\n"
                "enum Namespace {\n    static let x = 1\n    static func f() {}\n}\n"
            ),
            "Package/Sources/ModuleB/User.swift": (
                "func f() {\n"
                "    if true == CodingKeys.id.hashValue > 0 {}\n"
                "    _ = Namespace.x\n"
                "    _ = Namespace.x\n"
                "}\n"
            ),
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "CodingKeys" in out or "Namespace" in out:
        return f"CodingKeys/namespace enum must never appear in output\n--- stdout ---\n{out}"
    return None


# --- (e) interpreted only from inside its own home -> NOT flagged ----------
def case_e_inside_home_not_flagged(base: Path) -> str | None:
    root = base / "e"
    _write(
        root,
        {
            "Sources/ModuleA/Widget.swift": (
                "public enum Widget {\n    case small\n    case large\n}\n"
            ),
            "Sources/ModuleA/User.swift": (
                "func f(w: Widget) -> Bool {\n"
                "    if w == Widget.small { return true }\n"
                "    switch w {\n"
                "    case Widget.large: return false\n"
                "    default: return false\n"
                "    }\n"
                "}\n"
            ),
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "| Widget |" in out:
        return f"in-home-only interpretation must not be flagged\n--- stdout ---\n{out}"
    return None


# --- (f) non-Swift tree -> empty table, exit 0 ------------------------------
def case_f_non_swift_unsupported(base: Path) -> str | None:
    root = base / "f"
    _write(root, {"main.py": "print('hi')\n", "lib/util.py": "X = 1\n"})
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if out.strip() != "":
        return f"expected empty stdout for non-Swift tree\n--- stdout ---\n{out}"
    return None


# --- (g) nested ROOT/Package/Sources/ModuleA + ModuleB -> homes resolve ----
def case_g_nested_module_layout(base: Path) -> str | None:
    root = base / "g"
    _write(
        root,
        {
            "Package/Sources/ModuleA/Status.swift": (
                "public enum Status {\n    case idle\n    case running\n}\n"
            ),
            "Package/Sources/ModuleB/Consumer.swift": (
                "func f(s: Status) -> Bool {\n"
                "    if s == Status.idle { return true }\n"
                "    switch s {\n"
                "    case Status.running: return false\n"
                "    default: return false\n"
                "    }\n"
                "}\n"
            ),
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "| Status |" not in out:
        return f"expected cross-module site flagged for Status\n--- stdout ---\n{out}"
    row = next(line for line in out.splitlines() if line.startswith("| Status |"))
    cols = [c.strip() for c in row.strip("|").split("|")]
    # enum | home | tier | outside-site count | sites
    if cols[1] != "ModuleA":
        return f"expected home 'ModuleA' (two-level nested Sources resolution), got: {row}"
    return None


CASES = [
    ("a: qualified Enum.case outside home -> Tier 1", case_a_qualified_outside_home),
    ("b: unqualified unique case outside home -> Tier 2", case_b_unqualified_unique_case),
    ("c: ambiguous case not attributed to either enum", case_c_ambiguous_case_not_attributed),
    ("d: CodingKeys + namespace enum excluded from inventory", case_d_excluded_from_inventory),
    ("e: inside-home-only interpretation not flagged", case_e_inside_home_not_flagged),
    ("f: non-Swift tree degrades to empty table, exit 0", case_f_non_swift_unsupported),
    ("g: nested Sources/ModuleA+ModuleB home resolution", case_g_nested_module_layout),
]


def main() -> int:
    if not AUDIT.is_file():
        print(f"FAIL: audit script missing: {AUDIT}")
        return 1

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        for label, fn in CASES:
            failure = fn(base)
            if failure is not None:
                failures.append(f"{label}: {failure}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(f"OK: audit-enum-interpretation — {len(CASES)}/{len(CASES)} fixture case(s) passing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
