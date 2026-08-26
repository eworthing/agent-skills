#!/usr/bin/env python3
"""Hidden oracle battery for cpython-genexpr-iterability. Grader-only: never
shown to a candidate (listed in provenance.json's grader_only_files).

Imports each variant's `lazyselect.py` fresh by file path (every variant
reuses the same module name, so plain `import lazyselect` would collide) and
runs the four oracles declared in provenance.json's `hidden_oracles`:

    error_timing_truth_table    -- construction-time vs iteration-time TypeError
    legacy_iterable_accepted    -- an iterator lacking its own __iter__ still works
    corruption_repro_stays_fixed -- external state surgery must not corrupt iteration
    stale_test_trap             -- a variant's own bundled test suite passing is not
                                    proof its behavior is correct

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "eager-guard",
    "lazy-consistent",
    "near-miss-checked-source",
    "mutant-dropped-retention",
]


def load_variant(name: str) -> types.ModuleType:
    path = PACK_DIR / name / "lazyselect.py"
    spec = importlib.util.spec_from_file_location(f"_gc_lazyselect_{name.replace('-', '_')}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _NoIterMethodIterator:
    """Has __next__ but deliberately no __iter__ -- a technically non-compliant
    iterator (the iterator protocol says __iter__ should return self) that
    real code still relies on working with next()."""

    def __init__(self, values: list) -> None:
        self._values = list(values)
        self._i = 0

    def __next__(self):
        if self._i >= len(self._values):
            raise StopIteration
        value = self._values[self._i]
        self._i += 1
        return value


class _IterableViaNoIterMethodIterator:
    def __init__(self, values: list) -> None:
        self._values = values

    def __iter__(self):
        return _NoIterMethodIterator(self._values)


def error_timing_truth_table(modules: dict[str, types.ModuleType]) -> dict[str, str]:
    table = {}
    for name, module in modules.items():
        lazy_select = module.LazySelect
        try:
            lazy_select(42)  # 42 is not iterable
        except TypeError:
            table[name] = "construction"
            continue
        obj = lazy_select(42)
        try:
            list(obj)
        except TypeError:
            table[name] = "iteration"
        else:
            table[name] = "never"
    return table


def legacy_iterable_accepted(modules: dict[str, types.ModuleType]) -> dict[str, bool]:
    results = {}
    for name, module in modules.items():
        lazy_select = module.LazySelect
        try:
            obj = lazy_select(_IterableViaNoIterMethodIterator([1, 2, 3]))
            results[name] = list(obj) == [1, 2, 3]
        except TypeError:
            results[name] = False
    return results


def corruption_repro_stays_fixed(modules: dict[str, types.ModuleType]) -> dict[str, bool]:
    results = {}
    for name, module in modules.items():
        lazy_select = module.LazySelect
        try:
            obj = lazy_select(range(10))
            obj._source = range(3, 6)  # direct state surgery, mirrors external mutation
            results[name] = list(obj) == [3, 4, 5]
        except Exception:
            results[name] = False
    return results


def stale_test_trap(dirs: dict[str, Path]) -> dict[str, bool]:
    """Run each variant's OWN bundled test file as a subprocess. A variant's
    suite passing is not proof its behavior is correct -- eager-guard's suite
    is expected to pass here despite eager-guard being the wrong state."""
    results = {}
    for name, variant_dir in dirs.items():
        test_path = variant_dir / "test_lazyselect.py"
        proc = subprocess.run(
            [sys.executable, str(test_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        results[name] = proc.returncode == 0
    return results


def main() -> int:
    modules = {name: load_variant(name) for name in VARIANTS}
    dirs = {name: PACK_DIR / name for name in VARIANTS}

    timing = error_timing_truth_table(modules)
    legacy = legacy_iterable_accepted(modules)
    corruption = corruption_repro_stays_fixed(modules)
    stale = stale_test_trap(dirs)

    print("=== error_timing_truth_table ===")
    for name, when in timing.items():
        print(f"  {name}: {when}")
    print("=== legacy_iterable_accepted ===")
    for name, ok in legacy.items():
        print(f"  {name}: {'accepted' if ok else 'rejected'}")
    print("=== corruption_repro_stays_fixed ===")
    for name, ok in corruption.items():
        print(f"  {name}: {'survived' if ok else 'CORRUPTED'}")
    print("=== stale_test_trap (own bundled test suite) ===")
    for name, ok in stale.items():
        print(f"  {name}: {'suite passes' if ok else 'suite FAILS'}")

    failures = []
    expected_timing = {
        "eager-guard": "construction",
        "lazy-consistent": "iteration",
        "near-miss-checked-source": "construction",
        "mutant-dropped-retention": "construction",
    }
    for name, expected in expected_timing.items():
        if timing.get(name) != expected:
            failures.append(f"{name}: expected timing {expected!r}, got {timing.get(name)!r}")

    if legacy.get("lazy-consistent") is not True:
        failures.append("lazy-consistent must accept the legacy iterable")
    if legacy.get("eager-guard") is not False:
        failures.append("eager-guard must reject the legacy iterable")
    if legacy.get("near-miss-checked-source") is not False:
        failures.append(
            "near-miss-checked-source must still reject the legacy iterable (it relocated, not fixed, the check)"
        )

    if corruption.get("mutant-dropped-retention") is not False:
        failures.append("mutant-dropped-retention must FAIL corruption_repro_stays_fixed")
    for name in ("eager-guard", "lazy-consistent", "near-miss-checked-source"):
        if corruption.get(name) is not True:
            failures.append(f"{name} must survive corruption_repro_stays_fixed")

    if stale.get("eager-guard") is not True:
        failures.append(
            "eager-guard's OWN test suite must pass despite its wrong behavior (the trap)"
        )

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK: observed matrix matches declared expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
