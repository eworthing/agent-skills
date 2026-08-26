#!/usr/bin/env python3
"""Hidden oracle battery for swiftnio-write-before-active. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Same probe pattern as swift-collections-platform-guard-scope's oracles.py:
`oracle_probe.swift` (grader-only) is copied to a scratch file literally
named `main.swift` (swiftc only allows top-level statements in a file with
that exact name) and compiled against each variant's own
`pipe_support.swift` in turn. The resulting binary takes a comma-separated
op sequence (w<N> write, f flush, a activate) and prints each write's
boolean result plus the final emitted sequence.

Runs four checks:

    activation_emits_pending_writes -- scoped to the three variants whose
                                 write never rejects (flush-buffered-writes-
                                 on-activation, near-miss-buffer-without-
                                 activation-flush, mutant-drop-before-ready
                                 -- reject-before-ready's write returns
                                 false in this scenario, a separately
                                 covered property, not this one). After
                                 write-then-activate with NO follow-up
                                 flush, is the value already emitted? True
                                 only for the accepted variant, whose
                                 activation itself attempts to send
                                 anything waiting.
    no_accepted_write_is_permanently_lost -- THE DISCRIMINATOR between the
                                 near-miss and the mutant, which look
                                 identical by every other measure here:
                                 neither ever rejects a write. If a write
                                 was accepted, does SOME later flush after
                                 activation ever deliver it? True (trivially)
                                 for reject-before-ready, whose write was
                                 never accepted in the first place. True
                                 for the accepted variant (already
                                 delivered). True for the near-miss (stuck
                                 after activation alone, but a later flush
                                 recovers it). False only for the mutant,
                                 which never buffered the value at all, so
                                 no later operation can recover it.
    emitted_preserves_write_order -- CONTROL: wherever any variant does
                                 emit anything, three writes issued in
                                 order come out in that same order. Holds
                                 everywhere in this pack's correct design.
    stale_test_trap              -- DEMONSTRATION, not a discriminator: a
                                 variant's own bundled main.swift passing
                                 is not proof its behavior is correct.
                                 True for every variant, INCLUDING
                                 reject-before-ready, whose own suite
                                 certifies the very behavior this pack
                                 exists to correct -- exactly the trap the
                                 real upstream test suite fell into.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "reject-before-ready",
    "flush-buffered-writes-on-activation",
    "near-miss-buffer-without-activation-flush",
    "mutant-drop-before-ready",
]
NEVER_REJECTS = [
    "flush-buffered-writes-on-activation",
    "near-miss-buffer-without-activation-flush",
    "mutant-drop-before-ready",
]


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s pipe_support.swift against the grader-only
    probe (copied to scratch as main.swift)."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(str(PACK_DIR / variant / "pipe_support.swift"), str(main_path), "-o", str(binary_path))
    return binary_path


def run_ops(binary: Path, ops: str) -> tuple[list[bool], list[int]]:
    result = subprocess.run([str(binary), ops], capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    writes_raw = lines[0].removeprefix("writes:")
    emitted_raw = lines[1].removeprefix("emitted:")
    writes = [w == "true" for w in writes_raw.split(",")] if writes_raw else []
    emitted = [int(v) for v in emitted_raw.split(",")] if emitted_raw else []
    return writes, emitted


def activation_emits_pending_writes(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant in NEVER_REJECTS:
        _writes, emitted = run_ops(binaries[variant], "w1,a")
        results[variant] = emitted == [1]
    return results


def no_accepted_write_is_permanently_lost(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        writes, emitted = run_ops(binary, "w1,a,f")
        results[variant] = (not writes[0]) or (emitted == [1])
    return results


def emitted_preserves_write_order(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        _writes, emitted = run_ops(binary, "w1,w2,w3,a,f")
        results[variant] = emitted in ([], [1, 2, 3])
    return results


def stale_test_trap(dirs: dict[str, Path]) -> dict[str, bool]:
    """Run each variant's OWN bundled main.swift as a compiled subprocess.
    A variant's suite passing is not proof its behavior is correct --
    reject-before-ready's suite is expected to pass despite certifying the
    defect this pack exists to correct."""
    results = {}
    for name, variant_dir in dirs.items():
        with tempfile.TemporaryDirectory(prefix="swiftnio-stale-test-") as tmp:
            binary_path = Path(tmp) / f"selftest_{name}"
            try:
                _swiftc(
                    str(variant_dir / "pipe_support.swift"),
                    str(variant_dir / "main.swift"),
                    "-o",
                    str(binary_path),
                )
            except RuntimeError:
                results[name] = False
                continue
            proc = subprocess.run([str(binary_path)], capture_output=True, text=True, check=False)
            results[name] = proc.returncode == 0
    return results


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="swiftnio-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}
        dirs = {variant: PACK_DIR / variant for variant in VARIANTS}

        activation_results = activation_emits_pending_writes(binaries)
        recovery_results = no_accepted_write_is_permanently_lost(binaries)
        order_results = emitted_preserves_write_order(binaries)
        trap_results = stale_test_trap(dirs)

        print("=== activation_emits_pending_writes ===")
        for name, ok in activation_results.items():
            print(f"  {name}: {'emits immediately' if ok else 'STAYS BUFFERED'}")
        print("=== no_accepted_write_is_permanently_lost ===")
        for name, ok in recovery_results.items():
            print(f"  {name}: {'recoverable' if ok else 'PERMANENTLY LOST'}")
        print("=== emitted_preserves_write_order (control) ===")
        for name, ok in order_results.items():
            print(f"  {name}: {'ordered' if ok else 'REORDERED'}")
        print("=== stale_test_trap (demonstration) ===")
        for name, ok in trap_results.items():
            print(f"  {name}: {'suite passes' if ok else 'suite FAILS'}")

        failures = []

        expected_activation = {
            "flush-buffered-writes-on-activation": True,
            "near-miss-buffer-without-activation-flush": False,
            "mutant-drop-before-ready": False,
        }
        for name, expected in expected_activation.items():
            if activation_results.get(name) != expected:
                failures.append(
                    f"{name}: expected activation_emits_pending_writes={expected}, "
                    f"got {activation_results.get(name)}"
                )

        expected_recovery = {
            "reject-before-ready": True,
            "flush-buffered-writes-on-activation": True,
            "near-miss-buffer-without-activation-flush": True,
            "mutant-drop-before-ready": False,
        }
        for name, expected in expected_recovery.items():
            if recovery_results.get(name) != expected:
                failures.append(
                    f"{name}: expected no_accepted_write_is_permanently_lost={expected}, "
                    f"got {recovery_results.get(name)}"
                )

        for name in VARIANTS:
            if order_results.get(name) is not True:
                failures.append(
                    f"{name}: emitted_preserves_write_order must hold, got {order_results.get(name)}"
                )
            if trap_results.get(name) is not True:
                failures.append(
                    f"{name}: stale_test_trap must hold (own suite must pass), "
                    f"got {trap_results.get(name)}"
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
