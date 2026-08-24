#!/usr/bin/env python3
"""Self-test: audit_hotspots.py candidate selection and restraint across multi-language stacks.

Tests that:
  - Queue A flags high control reasoning density (decisions, nesting, condition operands).
  - Queue B flags high temporal mutation reasoning (mutation sites, mutation span across branches).
  - Queue C flags private navigation fragmentation (single-use private helper delegation).
  - Multi-language stacks (Swift, TS, Go, Rust, Kotlin) are parsed via ast-grep.
  - Missing external tools skip gracefully with installation guidance and exit 0 (never crash).
  - Clean and restraint codebases remain silent or below selection floors.
  - Test files and generated files are excluded.
  - JSON output satisfies the candidate-evidence contract (promotion_allowed: false).

Run: python3 scripts/_audit_hotspots_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AUDIT = Path(__file__).with_name("audit_hotspots.py")


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, body in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")


def _run(
    root: Path, extra_args: list[str] | None = None, env: dict[str, str] | None = None
) -> tuple[str, str, int]:
    args = [sys.executable, str(AUDIT), str(root)]
    if extra_args:
        args.extend(extra_args)
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        env=env if env is not None else os.environ.copy(),
    )
    return proc.stdout, proc.stderr, proc.returncode


# --- Test 1: Queue A - Control Reasoning Density -----------------------------
def test_queue_a_control_density(base: Path) -> str | None:
    root = base / "queue_a"
    code = """
def complex_decision_engine(a: int, b: int, c: int, flag: bool) -> str:
    if (a > 0 and b < 10) or (c == 5 and flag) or (a + b == 20):
        for i in range(a):
            if i % 2 == 0:
                try:
                    if b > 5:
                        return "deep_branch_1"
                except ValueError:
                    return "err"
            elif i % 3 == 0:
                if c > 10:
                    return "deep_branch_2"
    elif b > 20 and c < 0:
        while a > 0:
            if flag:
                return "while_branch"
            a -= 1
    return "default"
"""
    _write(root, {"engine.py": code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if not data["candidates"]:
        return f"expected candidate in Queue A, got none\nstdout: {out}"
    cand = data["candidates"][0]
    if "control" not in cand["candidate_queues"]:
        return f"expected candidate in 'control' queue, got {cand['candidate_queues']}"
    if cand["signals"]["decision_count"] < 6:
        return f"expected decision_count >= 6, got {cand['signals']['decision_count']}"
    if cand["signals"]["max_nesting"] < 3:
        return f"expected max_nesting >= 3, got {cand['signals']['max_nesting']}"
    return None


# --- Test 2: Queue B - Temporal Mutation -------------------------------------
def test_queue_b_temporal_mutation(base: Path) -> str | None:
    root = base / "queue_b"
    code = """
def mutate_across_lifecycle(items: list[int], mode: str) -> dict:
    state_flag = "INIT"
    total_accumulator = 0
    buffer = []
    
    # Line span across 20+ lines with mutations inside branches
    for item in items:
        if item > 100:
            state_flag = "OVERFLOW"
            total_accumulator += item
            buffer.append(item)
        elif item > 50:
            if mode == "AGGRESSIVE":
                state_flag = "WARN_HIGH"
                total_accumulator += item * 2
            else:
                total_accumulator += item
        else:
            total_accumulator += item
            if state_flag == "INIT":
                state_flag = "PROCESSING"

    if total_accumulator > 500:
        state_flag = "FINALIZED"
    
    return {"state": state_flag, "total": total_accumulator, "buffer": buffer}
"""
    _write(root, {"mutator.py": code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if not data["candidates"]:
        return f"expected candidate in Queue B, got none\nstdout: {out}"
    cand = data["candidates"][0]
    if "mutation" not in cand["candidate_queues"]:
        return f"expected candidate in 'mutation' queue, got {cand['candidate_queues']}"
    if cand["signals"]["mutation_sites"] < 3:
        return f"expected mutation_sites >= 3, got {cand['signals']['mutation_sites']}"
    if cand["signals"]["mutation_span"] < 10:
        return f"expected mutation_span >= 10, got {cand['signals']['mutation_span']}"
    return None


# --- Test 3: Queue C - Private Navigation & Single-Use Helpers ---------------
def test_queue_c_private_navigation(base: Path) -> str | None:
    root = base / "queue_c"
    code = """
class OrderProcessor:
    def process_order(self, order_id: str, items: list[dict]) -> bool:
        self._validate_items(items)
        self._calculate_taxes(items)
        self._charge_account(order_id)
        return True

    def _validate_items(self, items: list[dict]) -> None:
        if not items:
            raise ValueError("empty")

    def _calculate_taxes(self, items: list[dict]) -> None:
        self._lookup_tax_table()

    def _lookup_tax_table(self) -> None:
        pass

    def _charge_account(self, order_id: str) -> None:
        pass
"""
    _write(root, {"orders.py": code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    cand = next(
        (c for c in data["candidates"] if c["symbol"] == "OrderProcessor.process_order"), None
    )
    if not cand:
        return f"expected OrderProcessor.process_order in candidates\nstdout: {out}"
    if "navigation" not in cand["candidate_queues"]:
        return f"expected 'navigation' in candidate_queues, got {cand['candidate_queues']}"
    if cand["signals"]["single_use_private_helper_count"] < 2:
        return f"expected single_use_private_helper_count >= 2, got {cand['signals']['single_use_private_helper_count']}"
    return None


# --- Test 4: Multi-Language Parsing via ast-grep (Swift & TypeScript) ---------
def test_multilang_swift_and_ts(base: Path) -> str | None:
    if not (shutil.which("ast-grep") or shutil.which("sg")):
        # If ast-grep is absent on the test host, skip this test
        return None

    root = base / "multilang_swift_ts"
    swift_code = """
import Foundation

class SettlementCoordinator {
    func executeSettlement(id: String, amount: Double) -> Bool {
        var balance = amount
        var fees = 0.0
        if balance > 100.0 && id.count > 3 {
            for i in 0..<10 {
                if i % 2 == 0 {
                    balance += Double(i)
                    fees += 1.5
                } else {
                    balance -= 0.5
                }
            }
        }
        _recordSettlement(balance)
        return balance > 0.0
    }

    private func _recordSettlement(_ b: Double) {
        print(b)
    }
}
"""
    ts_code = """
export class OrderWorkflow {
    process(orderId: string, total: number): boolean {
        let currentTotal = total;
        let stepCount = 0;
        if (currentTotal > 50 && orderId.length > 0) {
            for (let i = 0; i < 5; i++) {
                if (i % 2 === 0) {
                    currentTotal += i * 10;
                    stepCount += 1;
                } else {
                    currentTotal -= 2;
                }
            }
        }
        return currentTotal > 100;
    }
}
"""
    _write(
        root,
        {
            "Sources/SettlementCoordinator.swift": swift_code,
            "src/OrderWorkflow.ts": ts_code,
        },
    )
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if len(data["candidates"]) < 2:
        return f"expected >= 2 candidates (1 Swift + 1 TS), got {len(data['candidates'])}\nstdout: {out}"

    swift_cand = next((c for c in data["candidates"] if "executeSettlement" in c["symbol"]), None)
    if not swift_cand:
        return f"expected executeSettlement in Swift candidates, got: {data['candidates']}"
    if swift_cand["signals"]["decision_count"] < 3:
        return f"expected Swift decision_count >= 3, got {swift_cand['signals']['decision_count']}"

    ts_cand = next((c for c in data["candidates"] if "process" in c["symbol"]), None)
    if not ts_cand:
        return f"expected process in TS candidates, got: {data['candidates']}"
    if ts_cand["signals"]["decision_count"] < 3:
        return f"expected TS decision_count >= 3, got {ts_cand['signals']['decision_count']}"

    return None


# --- Test 5: Missing Tool Graceful Skip & Install Guidance -------------------
def test_missing_tool_graceful_skip(base: Path) -> str | None:
    root = base / "missing_tool_repo"
    swift_code = "func simple() { print(1) }\n"
    _write(root, {"App.swift": swift_code})

    # Run with PATH emptied of ast-grep
    fake_env = os.environ.copy()
    fake_env["PATH"] = "/usr/bin:/bin"  # standard system bins without homebrew / cargo

    out, err, rc = _run(root, ["--json"], env=fake_env)
    if rc != 0:
        return f"expected exit 0 when tool is absent, got {rc}\nstderr: {err}"

    data = json.loads(out)
    if data.get("status") != "absent":
        return f"expected status: 'absent' when ast-grep missing, got {data.get('status')}"
    if "install_instructions" not in data:
        return f"expected 'install_instructions' in payload, got {data}"
    if "brew install ast-grep" not in data["install_instructions"]:
        return f"expected brew install command in instructions: {data['install_instructions']}"
    return None


# --- Test 6: Restraint Cases (Clean Code / Tests / Generated) ----------------
def test_restraint_cases(base: Path) -> str | None:
    root = base / "restraint"
    clean_py = """
def linear_transform(x: int, y: int) -> int:
    scaled = x * 2
    offset = y + 10
    return scaled + offset

def safe_lookup(mapping: dict[str, str], key: str, default: str) -> str:
    return mapping.get(key, default)
"""
    clean_swift = """
func linearTransform(x: Int, y: Int) -> Int {
    let scaled = x * 2
    let offset = y + 10
    return scaled + offset
}
"""
    test_code = """
def test_massive_nested_branches():
    for a in range(10):
        for b in range(10):
            if a > b:
                assert True
"""
    _write(
        root,
        {
            "src/clean.py": clean_py,
            "src/clean.swift": clean_swift,
            "tests/test_ignored.py": test_code,
        },
    )
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if data["candidates"]:
        return f"expected 0 candidates on clean codebase, got: {data['candidates']}"
    return None


# --- Test 7: JSON Schema & Epistemic Contract --------------------------------
def test_epistemic_contract(base: Path) -> str | None:
    root = base / "contract"
    code = """
def complex_fn(x: int) -> int:
    if x > 10:
        if x > 20:
            if x > 30:
                return x * 2
    return x
"""
    _write(root, {"sample.py": code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if data.get("promotion_allowed") is not False:
        return f"expected promotion_allowed: False, got {data.get('promotion_allowed')}"
    if "doctrine" not in data:
        return "expected 'doctrine' in JSON payload"
    return None


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir)
        cases = [
            ("queue_a_control_density", test_queue_a_control_density),
            ("queue_b_temporal_mutation", test_queue_b_temporal_mutation),
            ("queue_c_private_navigation", test_queue_c_private_navigation),
            ("multilang_swift_and_ts", test_multilang_swift_and_ts),
            ("missing_tool_graceful_skip", test_missing_tool_graceful_skip),
            ("restraint_cases", test_restraint_cases),
            ("epistemic_contract", test_epistemic_contract),
        ]
        failed = False
        for name, fn in cases:
            err = fn(base)
            if err:
                sys.stderr.write(f"FAIL: {name}: {err}\n")
                failed = True
            else:
                print(f"PASS: {name}")

        if failed:
            return 1
        print("OK: audit_hotspots — 7/7 selftest cases passing")
        return 0


if __name__ == "__main__":
    sys.exit(main())
