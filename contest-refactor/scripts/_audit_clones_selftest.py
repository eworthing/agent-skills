#!/usr/bin/env python3
"""Self-test: audit_clones.py flags near-duplicate function bodies (byte-identical
and renamed-identifier variants) while staying silent on shallow structural
resemblance that doesn't clear the similarity/size threshold, and degrades
cleanly (empty output, exit 0) on stacks it doesn't parse.

Written in Python, driving the target script as a subprocess — matches this
repo's existing selftest idiom for scripts that need one (see any
`_*_selftest.py` for the general shape: build a temp fixture tree, run the
target script, assert on stdout).

Each fixture below is one function so a failure names exactly which of the
brief's four cases (a)-(d) broke.

Run: python3 scripts/_audit_clones_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

AUDIT = Path(__file__).with_name("audit_clones.py")


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


def _run(root: Path) -> tuple[str, str, int]:
    proc = subprocess.run(
        [sys.executable, str(AUDIT), str(root)],
        capture_output=True,
        text=True,
    )
    return proc.stdout, proc.stderr, proc.returncode


# --- (a) byte-identical function body, duplicated across two files ---------
def case_a_byte_identical(base: Path) -> str | None:
    root = base / "a"
    body = (
        "func computeTotal(items: [Int]) -> Int {\n"
        "    var total = 0\n"
        "    for item in items {\n"
        "        if item > 0 {\n"
        "            total += item\n"
        "        } else {\n"
        "            total -= item\n"
        "        }\n"
        "    }\n"
        "    return total\n"
        "}\n"
    )
    _write(
        root,
        {
            "Sources/ModuleA/Totals.swift": body,
            "Sources/ModuleB/OtherTotals.swift": body,
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "Totals.swift" not in out or "OtherTotals.swift" not in out:
        return f"expected both files in a flagged row\n--- stdout ---\n{out}"
    row = next(line for line in out.splitlines() if "Totals.swift" in line and "|" in line)
    sim = float(row.strip("|").split("|")[-1].strip())
    if sim < 0.99:
        return f"expected similarity at/near 1.0 for byte-identical bodies, got {sim}\nrow: {row}"
    return None


# --- (b) near-identical, only identifiers renamed ---------------------------
def case_b_renamed_identifiers(base: Path) -> str | None:
    root = base / "b"
    _write(
        root,
        {
            "Sources/ModuleA/UserLookup.swift": (
                "func findUser(userID: Int, users: [Int: String]) -> String? {\n"
                "    guard let userID = Optional(userID) else {\n"
                "        return nil\n"
                "    }\n"
                "    if let name = users[userID] {\n"
                "        print(name)\n"
                "        return name\n"
                "    } else {\n"
                "        return nil\n"
                "    }\n"
                "}\n"
            ),
            "Sources/ModuleB/AccountLookup.swift": (
                "func findAccount(accountID: Int, accounts: [Int: String]) -> String? {\n"
                "    guard let accountID = Optional(accountID) else {\n"
                "        return nil\n"
                "    }\n"
                "    if let label = accounts[accountID] {\n"
                "        print(label)\n"
                "        return label\n"
                "    } else {\n"
                "        return nil\n"
                "    }\n"
                "}\n"
            ),
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "UserLookup.swift" not in out or "AccountLookup.swift" not in out:
        return f"expected renamed-identifier pair flagged\n--- stdout ---\n{out}"
    row = next(line for line in out.splitlines() if "UserLookup.swift" in line and "|" in line)
    sim = float(row.strip("|").split("|")[-1].strip())
    if sim < 0.85:
        return f"expected similarity >= 0.85 via ID-normalization, got {sim}\nrow: {row}"
    return None


# --- (c) shallow structural resemblance, genuinely distinct beyond that ----
def case_c_shallow_resemblance_not_flagged(base: Path) -> str | None:
    root = base / "c"
    _write(
        root,
        {
            "Sources/ModuleA/PaymentDispatch.swift": (
                "func chargePayment(method: PaymentMethod) -> Double {\n"
                "    switch method {\n"
                "    case .card:\n"
                "        let fee = 0.029\n"
                "        return 100.0 * (1.0 + fee)\n"
                "    case .wallet:\n"
                "        return 100.0 - 2.5\n"
                "    case .bankTransfer:\n"
                "        let delayDays = 3\n"
                "        return 100.0 - Double(delayDays) * 0.1\n"
                "    }\n"
                "}\n"
            ),
            "Sources/ModuleB/ShippingDispatch.swift": (
                "func estimateShipping(route: ShippingRoute) -> Int {\n"
                "    var days = 0\n"
                "    for leg in route.legs {\n"
                "        days += leg.distanceKM / 500\n"
                "    }\n"
                "    if route.express {\n"
                "        days = max(1, days / 2)\n"
                "    }\n"
                "    return days\n"
                "}\n"
            ),
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "PaymentDispatch.swift" in out and "ShippingDispatch.swift" in out:
        return (
            "shallow structural resemblance across different domains must not "
            f"clear the threshold\n--- stdout ---\n{out}"
        )
    return None


# --- (d) unsupported-stack tree -> empty output, exit 0 --------------------
def case_d_unsupported_stack(base: Path) -> str | None:
    root = base / "d"
    _write(
        root,
        {
            "README.txt": "just some notes\nnothing to see here\n",
            "script.rb": 'def greet(name)\n  puts "hello #{name}"\nend\n',
        },
    )
    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if out.strip() != "":
        return f"expected empty stdout for an unsupported-stack tree\n--- stdout ---\n{out}"
    return None


CASES = [
    (
        "a: byte-identical body duplicated across two files -> ~1.0 similarity",
        case_a_byte_identical,
    ),
    ("b: renamed-identifier clone -> detected via ID-normalization", case_b_renamed_identifiers),
    (
        "c: shallow structural resemblance across domains -> NOT flagged",
        case_c_shallow_resemblance_not_flagged,
    ),
    ("d: unsupported-stack tree -> empty output, exit 0", case_d_unsupported_stack),
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

    print(f"OK: audit_clones — {len(CASES)}/{len(CASES)} fixture case(s) passing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
