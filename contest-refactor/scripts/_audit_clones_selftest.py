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

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

AUDIT = Path(__file__).with_name("audit_clones.py")


def _load_audit_module():
    """Import audit_clones.py by path so fixtures can call its internal
    tokenizer/fingerprint/jaccard stages directly, instead of eyeballing
    similarity from source text (the CLI never prints sub-threshold scores)."""
    spec = importlib.util.spec_from_file_location("audit_clones", AUDIT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["audit_clones"] = module  # dataclass decorator needs this registered first
    spec.loader.exec_module(module)
    return module


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


# --- (c) genuine near-miss: shared guard-clause preamble, diverges after ---
# Both bodies open with the *identical* five-guard validation preamble (a
# realistic copy-paste-then-diverge shape) but each ends with distinct logic.
# Measured against this repo's real _normalize_tokens/_fingerprint/_jaccard
# pipeline this pair scores ~0.615 similarity: well below the 0.85 threshold,
# but nowhere near 0 — a substantial-overlap-that-still-falls-short case,
# not something that would pass at any threshold regardless of value.
def case_c_shallow_resemblance_not_flagged(base: Path) -> str | None:
    root = base / "c"
    shared_preamble = (
        "    guard let amount = order.amount, amount > 0 else {\n"
        "        return 0.0\n"
        "    }\n"
        "    guard order.customer.isActive else {\n"
        "        return 0.0\n"
        "    }\n"
        "    guard !order.region.isEmpty else {\n"
        "        return 0.0\n"
        "    }\n"
        "    guard order.currency.isValid else {\n"
        "        return 0.0\n"
        "    }\n"
        "    guard order.items.count > 0 else {\n"
        "        return 0.0\n"
        "    }\n"
        "    for discount in order.discounts {\n"
        "        print(discount)\n"
        "    }\n"
    )
    payment_text = (
        "func chargePayment(order: Order) -> Double {\n" + shared_preamble + "    let fee = 0.029\n"
        "    return amount * (1.0 + fee)\n"
        "}\n"
    )
    shipping_text = (
        "func estimateShipping(order: Order) -> Int {\n" + shared_preamble + "    var days = 0\n"
        "    return days\n"
        "}\n"
    )
    _write(
        root,
        {
            "Sources/ModuleA/PaymentDispatch.swift": payment_text,
            "Sources/ModuleB/ShippingDispatch.swift": shipping_text,
        },
    )

    # Empirically verify the pair is a genuine near-miss — substantial shared
    # structure, not the ~0.0 similarity a switch-dispatcher-vs-loop pair would
    # produce regardless of threshold — by driving the target's own
    # extraction/fingerprint/jaccard stages directly (not eyeballing source).
    audit = _load_audit_module()
    payment_body = audit._extract_swift_kotlin_functions(
        Path("PaymentDispatch.swift"), payment_text
    )[0]
    shipping_body = audit._extract_swift_kotlin_functions(
        Path("ShippingDispatch.swift"), shipping_text
    )[0]
    payment_fp = audit._fingerprint(audit._normalize_tokens(payment_body.text))
    shipping_fp = audit._fingerprint(audit._normalize_tokens(shipping_body.text))
    sim = audit._jaccard(payment_fp, shipping_fp)
    if not (0.3 <= sim < 0.85):
        return (
            f"expected a genuine near-miss (0.3 <= similarity < 0.85), got {sim} — "
            "either the shared preamble collapsed to no overlap (0.0, no evidence "
            "the 0.85 cutoff specifically matters) or the pair drifted at/above "
            "the reporting threshold"
        )

    out, err, rc = _run(root)
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    if "PaymentDispatch.swift" in out and "ShippingDispatch.swift" in out:
        return (
            "a near-miss (shared preamble, diverging tail) below the 0.85 "
            f"threshold must not be flagged\n--- stdout ---\n{out}"
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


# --- (e) PYTHON support exists at all -------------------------------------
# Every other fixture is Swift. The Python extractor could return [] for all
# input -- i.e. Python clone detection simply not existing -- and this suite
# stayed green, because nothing ever fed it Python.
def case_e_python_clone(base: Path) -> str | None:
    root = base / "e"
    body = (
        "    total = 0\n"
        "    for row in rows:\n"
        "        if row.get('active'):\n"
        "            total += row['amount']\n"
        "        else:\n"
        "            total -= row['penalty']\n"
        "    normalized = total / max(len(rows), 1)\n"
        "    return round(normalized, 2)\n"
    )
    root.mkdir(parents=True, exist_ok=True)
    (root / "alpha.py").write_text(f"def settle(rows):\n{body}", encoding="utf-8")
    (root / "beta.py").write_text(f"def reconcile(rows):\n{body}", encoding="utf-8")
    out, err, rc = _run(root)
    if rc not in (0, 1):
        return f"unexpected exit {rc}: {err.strip()}"
    if "alpha.py" not in out or "beta.py" not in out:
        return (
            "duplicated Python function body not reported -- the Python extractor "
            f"is unproven; output was: {out.strip()[:200]!r}"
        )
    return None


# --- (f) the size floor is real -------------------------------------------
# `_MIN_LINES` could be set to 0 and nothing noticed, so trivially short
# duplicate bodies were never proven excluded. The body below is deliberately
# sized to STRADDLE the floor: it is reported when the floor is 0 and silent at
# the shipped floor of 8. A shorter body does not work -- a 2-line duplicate is
# excluded by a different gate regardless of `_MIN_LINES`, so a fixture that
# small passes either way and proves nothing.
def case_f_below_size_floor(base: Path) -> str | None:
    root = base / "f"
    root.mkdir(parents=True, exist_ok=True)
    body = "".join(f"    x{i} = rows[{i}] * {i} + 1\n" for i in range(1, 6)) + "    return x1\n"
    (root / "one.py").write_text(f"def alpha(rows):\n{body}", encoding="utf-8")
    (root / "two.py").write_text(f"def beta(rows):\n{body}", encoding="utf-8")
    out, err, rc = _run(root)
    if rc not in (0, 1):
        return f"unexpected exit {rc}: {err.strip()}"
    if "one.py" in out and "two.py" in out:
        return (
            "a 6-line duplicate was reported below the 8-line floor; _MIN_LINES is "
            "not enforced, so every short accessor pair becomes a finding"
        )
    return None


CASES = [
    (
        "a: byte-identical body duplicated across two files -> ~1.0 similarity",
        case_a_byte_identical,
    ),
    ("b: renamed-identifier clone -> detected via ID-normalization", case_b_renamed_identifiers),
    ("e: duplicated PYTHON body -> Python extractor actually runs", case_e_python_clone),
    ("f: 2-line duplicate -> excluded by the _MIN_LINES size floor", case_f_below_size_floor),
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
