#!/usr/bin/env python3
"""Hidden oracle battery for strict-concurrency-fake-fixes. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Same probe pattern as this corpus's other Swift packs: `oracle_probe.swift`
(grader-only) is copied to a scratch file literally named `main.swift`
(swiftc only allows top-level statements in a file with that exact name)
and compiled against each variant's own `hit_counter.swift` PLUS that
variant's own grader-only `probe_adapter.swift`, never against that
variant's own `main.swift`. See oracle_probe.swift's header for why every
adapter entry point is `async` uniformly even where a variant never
actually suspends.

CRITICAL DESIGN NOTE, because it is not obvious from the numbers alone:
this pack never spawns real concurrent tasks anywhere -- no Task, no
threads, no timing. `scripted_interleaving_preserves_update` observes a
lost update purely through *which operations a variant's real API lets
the grader call, and in what order*. unsynchronized-shared-state,
mutant-unchecked-marker, and near-miss-unsafe-optout-with-claimed-
invariant all expose `count` at ordinary (module-internal) access --
`nonisolated(unsafe)` opts out of isolation checking, it does not
restrict access -- so this probe can read it twice before writing it
back twice, exactly what unprotected concurrent access would do, and the
update is genuinely lost for all three. guarded-value-container and
near-miss-blanket-global-isolation make `count` inaccessible except
through increment() (private in the first, actor-isolated in the
second), so the probe is *structurally forced* through the real,
indivisible operation -- there is no way to express the bad interleaving
against them at all. near-miss-unsafe-optout-with-claimed-invariant's
distinct defect -- a false invariant claim, not a lost update -- is
caught by `claimed_invariant_actually_holds` below, not by this oracle;
the two near-misses fail on two different, independent grounds, and a
reviewer collapsing them into "both a bit unsafe" has missed the
distinction this pack is built to test.

Two of this pack's four checks need no compiled probe at all:
`unrelated_call_site_stays_callable` compiles a tiny grader-only snippet
against a variant's own hit_counter.swift with `swiftc -typecheck` and
reads the exit code.

Runs four checks:

    scripted_interleaving_preserves_update -- THE lost-update check.
                                 Simulates two logical callers racing on
                                 the same read-modify-write: read A, read
                                 B, write A, write B, with no operation in
                                 between that could let a real write land.
                                 True (2) for guarded-value-container and
                                 near-miss-blanket-global-isolation, whose
                                 `count` is unreachable except through
                                 increment(). False (1, the update is
                                 lost) for unsynchronized-shared-state,
                                 mutant-unchecked-marker, AND near-miss-
                                 unsafe-optout-with-claimed-invariant --
                                 all three leave `count` plain and
                                 directly reachable by this probe, and the
                                 near-miss's variant is genuinely just as
                                 racy as the mutant on this specific
                                 axis. What distinguishes it from the
                                 mutant is not this oracle; it is the
                                 false invariant claimed_invariant_
                                 actually_holds catches below.
    unrelated_call_site_stays_callable -- THE topology check, and near-
                                 miss-blanket-global-isolation's killer.
                                 statusLine() has nothing to do with
                                 concurrent access to `count`. Compiles a
                                 snippet that constructs a counter and
                                 calls statusLine() synchronously, with no
                                 await. True (stays callable) everywhere
                                 except near-miss-blanket-global-
                                 isolation, where isolating the whole type
                                 to a global actor cascaded to statusLine()
                                 too, and the same synchronous call is now
                                 a compile error.
    claimed_invariant_actually_holds -- near-miss-unsafe-optout-with-
                                 claimed-invariant's killer, and the one
                                 this pack's build brief calls out as
                                 passing vacuously elsewhere: calls
                                 setup() then drives the second path
                                 (increment(), the same operation both
                                 call sites use) and checks whether the
                                 state changed as a result. True (holds)
                                 for every variant except near-miss-
                                 unsafe-optout-with-claimed-invariant,
                                 which is the only variant that claims an
                                 "only touched during setup" invariant in
                                 the first place -- the other four make no
                                 such claim, so there is nothing for their
                                 own probeInvariantViolated to find, and
                                 they report false (no violation)
                                 honestly, not as a loophole.
    ordinary_sequential_calls_are_recorded -- CONTROL: two ordinary,
                                 non-adversarial calls (recordPageView,
                                 then recordAPIHit) both land, for every
                                 variant including mutant-unchecked-
                                 marker, whose defect only shows up under
                                 the adversarial interleaving above. Holds
                                 everywhere in this pack's correct design
                                 -- a baseline that would fail if this
                                 fixture itself were broken in a way that
                                 made the other three oracles' results
                                 meaningless.

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
MODULE_FILENAME = "hit_counter.swift"
ADAPTER_FILENAME = "probe_adapter.swift"

VARIANTS = [
    "unsynchronized-shared-state",
    "guarded-value-container",
    "near-miss-blanket-global-isolation",
    "near-miss-unsafe-optout-with-claimed-invariant",
    "mutant-unchecked-marker",
]

UNRELATED_CALL_SITE_SNIPPET = """\
// Grader-only compile-fail probe. statusLine() has nothing to do with
// concurrent access to `count` -- calling it synchronously, with no
// await, should stay legal wherever isolation was applied narrowly, and
// become illegal wherever isolation cascaded to the whole type.
let counter = HitCounter()
_ = counter.statusLine()
"""


def _swiftc(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)


def _swiftc_or_raise(*args: str) -> None:
    result = _swiftc(*args)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s hit_counter.swift and its own grader-only
    probe_adapter.swift against the grader-only probe (copied to scratch
    as main.swift)."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc_or_raise(
        str(PACK_DIR / variant / MODULE_FILENAME),
        str(PACK_DIR / variant / ADAPTER_FILENAME),
        str(main_path),
        "-o",
        str(binary_path),
    )
    return binary_path


def run_probe(binary: Path, command: str) -> str:
    result = subprocess.run([str(binary), command], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def scripted_interleaving_preserves_update(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: run_probe(binary, "interleaving") == "2" for variant, binary in binaries.items()
    }


def ordinary_sequential_calls_are_recorded(binaries: dict[str, Path]) -> dict[str, bool]:
    return {variant: run_probe(binary, "ordinary") == "2" for variant, binary in binaries.items()}


def claimed_invariant_actually_holds(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: run_probe(binary, "invariant") == "false" for variant, binary in binaries.items()
    }


def unrelated_call_site_stays_callable(dirs: dict[str, Path]) -> dict[str, bool]:
    results = {}
    with tempfile.TemporaryDirectory(prefix="scc-repr-topology-") as tmp:
        scratch_dir = Path(tmp)
        main_path = scratch_dir / "main.swift"
        main_path.write_text(UNRELATED_CALL_SITE_SNIPPET, encoding="utf-8")
        for variant, variant_dir in dirs.items():
            module_path = variant_dir / MODULE_FILENAME
            compiled = _swiftc("-typecheck", str(module_path), str(main_path)).returncode == 0
            results[variant] = compiled
    return results


def main() -> int:
    dirs = {variant: PACK_DIR / variant for variant in VARIANTS}

    with tempfile.TemporaryDirectory(prefix="scc-repr-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        interleaving_results = scripted_interleaving_preserves_update(binaries)
        topology_results = unrelated_call_site_stays_callable(dirs)
        invariant_results = claimed_invariant_actually_holds(binaries)
        control_results = ordinary_sequential_calls_are_recorded(binaries)

    print("=== scripted_interleaving_preserves_update ===")
    for name, ok in interleaving_results.items():
        print(f"  {name}: {'preserved' if ok else 'LOST UPDATE'}")
    print("=== unrelated_call_site_stays_callable ===")
    for name, ok in topology_results.items():
        print(f"  {name}: {'stays callable' if ok else 'CASCADED, NO LONGER CALLABLE'}")
    print("=== claimed_invariant_actually_holds ===")
    for name, ok in invariant_results.items():
        print(f"  {name}: {'holds' if ok else 'VIOLATED'}")
    print("=== ordinary_sequential_calls_are_recorded (control) ===")
    for name, ok in control_results.items():
        print(f"  {name}: {'recorded' if ok else 'MISSING'}")

    failures: list[str] = []

    expected_interleaving = {
        "unsynchronized-shared-state": False,
        "guarded-value-container": True,
        "near-miss-blanket-global-isolation": True,
        "near-miss-unsafe-optout-with-claimed-invariant": False,
        "mutant-unchecked-marker": False,
    }
    for name, expected in expected_interleaving.items():
        if interleaving_results.get(name) != expected:
            failures.append(
                f"{name}: expected scripted_interleaving_preserves_update={expected}, "
                f"got {interleaving_results.get(name)}"
            )

    expected_topology = {
        "unsynchronized-shared-state": True,
        "guarded-value-container": True,
        "near-miss-blanket-global-isolation": False,
        "near-miss-unsafe-optout-with-claimed-invariant": True,
        "mutant-unchecked-marker": True,
    }
    for name, expected in expected_topology.items():
        if topology_results.get(name) != expected:
            failures.append(
                f"{name}: expected unrelated_call_site_stays_callable={expected}, "
                f"got {topology_results.get(name)}"
            )

    expected_invariant = {
        "unsynchronized-shared-state": True,
        "guarded-value-container": True,
        "near-miss-blanket-global-isolation": True,
        "near-miss-unsafe-optout-with-claimed-invariant": False,
        "mutant-unchecked-marker": True,
    }
    for name, expected in expected_invariant.items():
        if invariant_results.get(name) != expected:
            failures.append(
                f"{name}: expected claimed_invariant_actually_holds={expected}, "
                f"got {invariant_results.get(name)}"
            )

    for name in VARIANTS:
        if control_results.get(name) is not True:
            failures.append(
                f"{name}: ordinary_sequential_calls_are_recorded must hold, "
                f"got {control_results.get(name)}"
            )

    if failures:
        print("\nFAIL:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("\nOK: observed matrix matches declared expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
