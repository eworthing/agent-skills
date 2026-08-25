#!/usr/bin/env python3
# WAIVER: module-size — one flat case-per-scenario selftest mirroring the single-file
#   scanner it exercises (audit_hotspots.py carries the same waiver); splitting would
#   scatter fixtures away from the scanner behavior they pin down.
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
import tomllib
from pathlib import Path

AUDIT = Path(__file__).with_name("audit_hotspots.py")
SKILL_ROOT = Path(__file__).resolve().parents[1]
SCAN_KEYS = {
    "schema_version",
    "status",
    "coverage",
    "promotion_allowed",
    "candidates",
    "queue_counts",
}


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
    if set(data) != SCAN_KEYS:
        return f"expected canonical persisted keys, got {sorted(data)}"
    if "brew install ast-grep" not in err:
        return f"expected install guidance on stderr, got {err!r}"
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
    if set(data) != SCAN_KEYS:
        return f"expected exact G49-compatible keys, got {sorted(data)}"
    return None


def test_python_ast_scope_and_expressions(base: Path) -> str | None:
    root = base / "python_ast_scope"
    code = """
def _if_ready(value):
    return bool(value)

def _while_ready(value):
    return bool(value)

def _match_ready(value):
    return bool(value)

def _expr_ready(value):
    return bool(value)

def _item_ready(value):
    return bool(value)

def analyze(values):
    if _if_ready(values):
        pass
    while _while_ready(values):
        break
    match values:
        case list() if _match_ready(values):
            pass
    result = 1 if _expr_ready(values) else 0
    filtered = [item for item in values if _item_ready(item)]
    return result + len(filtered)

def _hidden():
    return True

def parent():
    def inner():
        _hidden()
    return 1

class A:
    def run(self):
        self._validate()

    def _validate(self):
        return True

class B:
    def run(self):
        self._validate()

    def _validate(self):
        return True
"""
    _write(root, {"ast_cases.py": code})
    out, err, rc = _run(root, ["--json", "--top-k", "6"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    analyze = next((c for c in data["candidates"] if c["symbol"] == "analyze"), None)
    if not analyze:
        return f"expected analyze candidate, got {data['candidates']}"
    if analyze["signals"]["decision_count"] != 6:
        return f"expected six AST decisions, got {analyze['signals']['decision_count']}"
    expected_helpers = {
        "_if_ready",
        "_while_ready",
        "_match_ready",
        "_expr_ready",
        "_item_ready",
    }
    actual_helpers = set(analyze["neighborhood"]["direct_private_helpers"])
    if actual_helpers != expected_helpers:
        return f"expected condition/expression helpers {expected_helpers}, got {actual_helpers}"
    if any(c["symbol"] == "parent" for c in data["candidates"]):
        return "parent inherited its nested function's private call"
    for symbol in ("A.run", "B.run"):
        candidate = next((c for c in data["candidates"] if c["symbol"] == symbol), None)
        if not candidate:
            return f"expected scoped private-helper candidate {symbol}"
        if candidate["signals"]["single_use_private_helper_count"] != 1:
            return f"expected one scoped helper for {symbol}, got {candidate['signals']}"
    return None


def test_queue_membership_is_eligibility_not_only_roster(base: Path) -> str | None:
    root = base / "queue_membership"
    code = """
def target(values):
    state = 0
    if values:
        if len(values) > 1:
            if values[0] > 0:
                state += 1

    state += 2
    _only_helper()
    return state

def _only_helper():
    return True

def mutation_winner():
    state = 0
    state += 1
    state += 2
    state += 3
    state += 4
    state += 5
    return state
"""
    _write(root, {"queues.py": code})
    out, err, rc = _run(root, ["--json", "--top-k", "1"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    target = next((c for c in data["candidates"] if c["symbol"] == "target"), None)
    if not target:
        return f"expected target candidate, got {data['candidates']}"
    if target["candidate_queues"] != ["control", "mutation", "navigation"]:
        return f"expected all eligible queues, got {target['candidate_queues']}"
    return None


def test_swift_ast_boundaries_and_ts_arrow_names(base: Path) -> str | None:
    if not (shutil.which("ast-grep") or shutil.which("sg")):
        return None

    root = base / "swift_ast"
    swift_code = """
final class SettlementCoordinator {
    @MainActor
    func executeSettlement(values: [Int]) -> Int {
        let fake = "if while guard && hiddenCall("
        // if while guard fakeCall(
        var balance = 0
        if !values.isEmpty {
            for value in values {
                guard value >= 0 else { break }
                balance += value
            }
        }
        recordSettlement(balance)

        func nested() {
            if balance > 1 {
                if balance > 2 {
                    if balance > 3 { print(fake) }
                }
            }
        }
        return balance
    }

    private func recordSettlement(_ value: Int) {
        print(value)
    }
}

struct Overloads {
    func work(_ value: Int) -> Int {
        if value > 0 {
            if value > 1 {
                if value > 2 { return value }
            }
        }
        return 0
    }

    func work(_ value: String) -> Int {
        if !value.isEmpty {
            if value.count > 1 {
                if value.count > 2 { return value.count }
            }
        }
        return 0
    }
}
"""
    ts_code = """
type Handler = (values: number[]) => Promise<number>;
export const runWorkflow: Handler = async (values) => {
    let total = 0;
    if (values.length > 0) {
        for (const value of values) {
            if (value > 0) total += value;
        }
    }
    return total;
};
"""
    _write(root, {"Sources/Settlement.swift": swift_code, "src/workflow.ts": ts_code})
    out, err, rc = _run(root, ["--json", "--top-k", "6"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    settlement = next(
        (c for c in data["candidates"] if c["symbol"] == "SettlementCoordinator.executeSettlement"),
        None,
    )
    if not settlement:
        return f"expected attributed owner-qualified Swift method, got {data['candidates']}"
    if settlement["signals"]["decision_count"] != 3:
        return f"expected three structural Swift decisions, got {settlement['signals']['decision_count']}"
    if settlement["neighborhood"]["direct_private_helpers"] != ["recordSettlement"]:
        return f"expected declaration-private Swift helper, got {settlement['neighborhood']}"
    overloads = [c for c in data["candidates"] if c["symbol"] == "Overloads.work"]
    if len(overloads) != 2:
        return f"expected two overload candidates with distinct ranges, got {overloads}"
    if not any(c["symbol"] == "runWorkflow" for c in data["candidates"]):
        return f"expected typed arrow name runWorkflow, got {data['candidates']}"
    if any(c["symbol"] == "async" for c in data["candidates"]):
        return "typed arrow was misnamed async"
    return None


def test_schema_v2_partial_coverage_and_top_k_validation(base: Path) -> str | None:
    root = base / "coverage"
    _write(
        root,
        {
            "valid.py": "def simple():\n    return 1\n",
            "broken.py": "def broken(:\n    pass\n",
        },
    )
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected report exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if data.get("schema_version") != 2:
        return f"expected schema_version 2, got {data.get('schema_version')}"
    if data.get("status") != "partial":
        return f"expected partial status for a parse failure, got {data.get('status')}"
    if data.get("coverage", {}).get("python") != {"discovered": 2, "scanned": 1, "failed": 1}:
        return f"unexpected Python coverage: {data.get('coverage')}"

    _, _, invalid_rc = _run(root, ["--json", "--top-k", "0"])
    if invalid_rc != 2:
        return f"expected argparse exit 2 for --top-k 0, got {invalid_rc}"
    return None


def test_ast_grep_failure_is_partial_without_raw_output(base: Path) -> str | None:
    root = base / "ast_grep_failure"
    _write(root, {"App.swift": "func work() { if true { print(1) } }\n"})
    fake_bin = root / "fake-bin"
    fake_bin.mkdir()
    fake_ast_grep = fake_bin / "ast-grep"
    fake_ast_grep.write_text(
        f"#!{sys.executable}\nimport sys\nsys.stderr.write('SECRET RAW DIAGNOSTIC')\nsys.exit(3)\n",
        encoding="utf-8",
    )
    fake_ast_grep.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = str(fake_bin)
    out, err, rc = _run(root, ["--json"], env=env)
    if rc != 0:
        return f"expected report exit 0, got {rc}: {err}"
    if "SECRET RAW DIAGNOSTIC" in out:
        return "raw ast-grep stderr reached the structured report"
    data = json.loads(out)
    if data["status"] != "partial":
        return f"expected partial status, got {data['status']}"
    expected = {"discovered": 1, "scanned": 0, "failed": 1, "outcome": "partial"}
    if data["coverage"]["ast_grep"] != expected:
        return f"unexpected ast-grep coverage: {data['coverage']['ast_grep']}"
    return None


# --- Test: ast-grep exit-1-no-match is a successful scan, not a failure -----
def test_swift_enum_only_counts_as_scanned(base: Path) -> str | None:
    if not (shutil.which("ast-grep") or shutil.which("sg")):
        return None
    root = base / "swift_enum_only"
    enum_code = """
enum Direction {
    case north
    case south
    case east
    case west
}
"""
    _write(root, {"Sources/Direction.swift": enum_code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    expected = {"discovered": 1, "scanned": 1, "failed": 0, "outcome": "ok"}
    if data["coverage"]["ast_grep"] != expected:
        return f"expected enum-only file scanned not failed, got {data['coverage']['ast_grep']}"
    if data["status"] != "ok":
        return f"expected status ok for enum-only Swift file, got {data['status']}"
    return None


def test_swift_function_bearing_file_scans_normally(base: Path) -> str | None:
    if not (shutil.which("ast-grep") or shutil.which("sg")):
        return None
    root = base / "swift_function_bearing"
    swift_code = """
struct Greeter {
    func greet(_ name: String) -> String {
        return "Hello, \\(name)"
    }
}
"""
    _write(root, {"Sources/Greeter.swift": swift_code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    expected = {"discovered": 1, "scanned": 1, "failed": 0, "outcome": "ok"}
    if data["coverage"]["ast_grep"] != expected:
        return f"expected function-bearing file scanned cleanly, got {data['coverage']['ast_grep']}"
    if data["status"] != "ok":
        return f"expected status ok, got {data['status']}"
    return None


def test_swift_tests_dir_extension_suffixed_file_excluded(base: Path) -> str | None:
    root = base / "swift_tests_dir"
    # Extension-suffixed filename deliberately dodges the separate _is_test_file
    # filename filter (which only catches suffix-named files like FooTests.swift);
    # this must be excluded via the Tests/ directory check instead.
    code = """
extension PlaybackReducerTests {
    func admissionStatusHelper() -> Bool {
        return true
    }
}
"""
    _write(root, {"Tests/PlaybackReducerTests+AdmissionStatus.swift": code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if data["coverage"]["ast_grep"]["discovered"] != 0:
        return f"expected Tests/ file excluded from discovery, got {data['coverage']['ast_grep']}"
    if data["status"] != "not_applicable":
        return f"expected not_applicable status with nothing discovered, got {data['status']}"
    return None


def test_deriveddata_dir_excluded(base: Path) -> str | None:
    # IGNORE_DIRS carried "DerivedData" (mixed case) alongside lowercase entries;
    # a naive part.lower()-only fix would silently stop excluding it.
    root = base / "deriveddata"
    code = "func work() { if true { print(1) } }\n"
    _write(root, {"DerivedData/Intermediates/App.swift": code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if data["coverage"]["ast_grep"]["discovered"] != 0:
        return f"expected DerivedData/ file excluded from discovery, got {data['coverage']['ast_grep']}"
    return None


def test_hidden_dir_excluded(base: Path) -> str | None:
    # Hidden dirs (.artifacts, .swiftpm, ...) are tooling/build state by convention.
    # Neither "artifacts" nor "swiftpm" is itself an IGNORE_DIRS/exact-case token --
    # this isolates the NEW hidden-dot rule from the pre-existing named-dir checks
    # (a fixture nested under "DerivedData" would pass for the wrong reason: that
    # name is already case-insensitively ignored).
    root = base / "hidden_dir"
    code = "func work() { if true { print(1) } }\n"
    _write(root, {".artifacts/App.swift": code, ".swiftpm/Plugin.swift": code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if data["coverage"]["ast_grep"]["discovered"] != 0:
        return (
            f"expected hidden-dir files excluded from discovery, got {data['coverage']['ast_grep']}"
        )
    return None


def test_capitalized_migrations_dir_is_discovered(base: Path) -> str | None:
    # "migrations" (lowercase) is Django-style generated code; "Migrations"
    # (capitalized) is hand-written Swift/Kotlin persistence source and must
    # NOT be swept up by the same case-insensitive ignore rule.
    root = base / "swift_migrations"
    code = """
struct SchemaV1toV2 {
    func migrate(_ value: Int) -> Int {
        if value > 0 {
            return value + 1
        }
        return value
    }
}
"""
    _write(root, {"Sources/App/Migrations/SchemaV1toV2.swift": code})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if data["coverage"]["ast_grep"]["discovered"] != 1:
        return (
            f"expected capitalized Migrations/ file discovered, got {data['coverage']['ast_grep']}"
        )
    return None


def test_lowercase_migrations_dir_excluded(base: Path) -> str | None:
    root = base / "django_migrations"
    _write(root, {"migrations/0001_initial.py": "def upgrade():\n    pass\n"})
    out, err, rc = _run(root, ["--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    if data["coverage"]["python"]["discovered"] != 0:
        return f"expected lowercase migrations/ excluded, got {data['coverage']['python']}"
    return None


def test_scope_restricts_walk_but_paths_stay_repo_relative(base: Path) -> str | None:
    # avalanche plan Phase 2B: --scope narrows the discovery WALK to a subtree, but
    # emitted candidate paths stay relative to repo_root -- never source-root-relative
    # (an output filter instead would fill top-k with out-of-scope candidates).
    root = base / "scoped_walk"
    hotspot_code = (
        "def route(a, b, c):\n"
        "    if a and b:\n"
        "        if c:\n"
        "            return 1\n"
        "    elif a or b:\n"
        "        return 2\n"
        "    return 0\n"
    )
    _write(
        root,
        {
            "src/hotspot.py": hotspot_code,
            "tools/other_hotspot.py": hotspot_code,
        },
    )
    out, err, rc = _run(root, ["--scope", "src", "--json"])
    if rc != 0:
        return f"expected exit 0, got {rc}\nstderr: {err}"
    data = json.loads(out)
    paths = {c["path"] for c in data["candidates"]}
    if paths != {"src/hotspot.py"}:
        return f"expected only the scoped subtree's candidate, repo-relative; got {paths}"
    if data["coverage"]["python"]["discovered"] != 1:
        return (
            f"expected --scope to exclude tools/ from discovery, got {data['coverage']['python']}"
        )
    return None


def test_tracked_fixture_manifests(_: Path) -> str | None:
    fixture_root = SKILL_ROOT / "evals" / "hotspot-fixtures"
    for manifest_path in sorted(fixture_root.glob("*/manifest.toml")):
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
        out, err, rc = _run(manifest_path.parent / "codebase", ["--json"])
        if rc != 0:
            return f"{manifest['id']} scanner exited {rc}: {err}"
        candidates = json.loads(out)["candidates"]
        if manifest["arm"] == "recall":
            planted = next(
                (c for c in candidates if c["symbol"] == manifest["planted_hotspot"]), None
            )
            if not planted:
                return f"{manifest['id']} missed {manifest['planted_hotspot']}"
            if not set(manifest["planted_queues"]).issubset(planted["candidate_queues"]):
                return (
                    f"{manifest['id']} expected queues {manifest['planted_queues']}, "
                    f"got {planted['candidate_queues']}"
                )
        else:
            expected = manifest["notes"]["expected_candidates_count"]
            if len(candidates) != expected:
                return f"{manifest['id']} expected {expected} candidates, got {len(candidates)}"
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
            ("python_ast_scope_and_expressions", test_python_ast_scope_and_expressions),
            (
                "queue_membership_is_eligibility_not_only_roster",
                test_queue_membership_is_eligibility_not_only_roster,
            ),
            (
                "swift_ast_boundaries_and_ts_arrow_names",
                test_swift_ast_boundaries_and_ts_arrow_names,
            ),
            (
                "schema_v2_partial_coverage_and_top_k_validation",
                test_schema_v2_partial_coverage_and_top_k_validation,
            ),
            (
                "ast_grep_failure_is_partial_without_raw_output",
                test_ast_grep_failure_is_partial_without_raw_output,
            ),
            ("tracked_fixture_manifests", test_tracked_fixture_manifests),
            ("swift_enum_only_counts_as_scanned", test_swift_enum_only_counts_as_scanned),
            (
                "swift_function_bearing_file_scans_normally",
                test_swift_function_bearing_file_scans_normally,
            ),
            (
                "swift_tests_dir_extension_suffixed_file_excluded",
                test_swift_tests_dir_extension_suffixed_file_excluded,
            ),
            ("deriveddata_dir_excluded", test_deriveddata_dir_excluded),
            ("hidden_dir_excluded", test_hidden_dir_excluded),
            (
                "capitalized_migrations_dir_is_discovered",
                test_capitalized_migrations_dir_is_discovered,
            ),
            ("lowercase_migrations_dir_excluded", test_lowercase_migrations_dir_excluded),
            (
                "scope_restricts_walk_but_paths_stay_repo_relative",
                test_scope_restricts_walk_but_paths_stay_repo_relative,
            ),
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
        print(f"OK: audit_hotspots — {len(cases)}/{len(cases)} selftest cases passing")
        return 0


if __name__ == "__main__":
    sys.exit(main())
