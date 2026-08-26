#!/usr/bin/env python3
"""Hidden oracle battery for swift-collections-platform-guard-scope.
Grader-only: never shown to a candidate (listed in provenance.json's
grader_only_files).

Swift has no sibling-file import and `swiftc a.swift b.swift` only allows
top-level statements when the entry file is literally named `main.swift`.
Each variant already ships its own candidate-visible `main.swift` (its own
bundled test), so this harness's own entry point -- `oracle_probe.swift`,
grader-only -- is copied to a scratch file named `main.swift` and compiled
against each variant's `platform_support.swift` in turn, never against
that variant's own `main.swift`. The resulting binary is a tiny CLI:

    <binary> affected <platform> <major> <minor>   -> prints true/false
    <binary> admits <platform>                     -> prints true/false

which is how this harness observes `isPotentiallyAffected` and
`guardAdmits` uniformly across variants whose internals differ.

Runs four checks:

    guard_admits_exactly_legacy_four   -- for the platforms with a real,
                                     distinct guard concept (explicit-
                                     platform-list, near-miss-capability-
                                     guard-broad-admit -- guard-removed-
                                     availability-only and mutant-dropped-
                                     threshold have no guard at all, both
                                     admit everyone by design, so this
                                     check does not apply to them), the
                                     admitted platform set must equal
                                     exactly the four legacy platforms.
                                     Fails for the near-miss, which also
                                     admits the newly-shipped platform.
    threshold_preserved_vs_baseline -- for each of the four legacy
                                     platforms, at an old (pre-threshold)
                                     and a new (post-threshold) version,
                                     every variant's affected/unaffected
                                     answer must match explicit-platform-
                                     list's own. Fails only for
                                     mutant-dropped-threshold, whose
                                     dropped wrist entry reports an old,
                                     genuinely affected wrist version as
                                     unaffected.
    guard_removal_is_behaviorally_neutral -- DEMONSTRATION, not a
                                     discriminator: on the two platforms
                                     explicit-platform-list's guard
                                     excludes (the newly-shipped platform
                                     and an unrelated platform family), at
                                     several versions, every variant's
                                     answer matches explicit-platform-
                                     list's own. Holds everywhere, on
                                     purpose -- this is what makes removing
                                     the guard behaviorally safe, the
                                     empirical fact the accepted variant's
                                     whole justification rests on. It is
                                     the kind of oracle this pack's design
                                     doc calls a demonstration: its
                                     uniformity is the finding, not a
                                     defect it is meant to catch.
    old_affected_version_still_reported_affected -- CONTROL: an old,
                                     genuinely affected anchor version
                                     must report affected in every
                                     variant. Holds everywhere (mutant
                                     only touches wrist) -- a baseline that
                                     would fail if this fixture itself
                                     were broken in a way that made the
                                     other three oracles' results
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
VARIANTS = [
    "explicit-platform-list",
    "guard-removed-availability-only",
    "near-miss-capability-guard-broad-admit",
    "mutant-dropped-threshold",
]
BASELINE = "explicit-platform-list"
PLATFORMS = ["anchor", "companion", "wrist", "parlor", "overlay", "openfield"]
LEGACY_FOUR = {"anchor", "companion", "wrist", "parlor"}

# name -> (old_major, old_minor, new_major, new_minor); "old" is below the
# real threshold, "new" is exactly at it.
LEGACY_VERSIONS = {
    "anchor": (10, 0, 12, 0),
    "companion": (14, 0, 15, 0),
    "wrist": (6, 0, 8, 0),
    "parlor": (14, 0, 15, 0),
}

EXCLUDED_PLATFORMS = ["overlay", "openfield"]
EXCLUDED_VERSIONS = [(0, 0), (99, 0)]


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s platform_support.swift against the grader-only
    probe (copied to scratch as main.swift, since swiftc only allows
    top-level statements in a file with that exact name)."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(
        str(PACK_DIR / variant / "platform_support.swift"), str(main_path), "-o", str(binary_path)
    )
    return binary_path


def probe_affected(binary: Path, platform: str, major: int, minor: int) -> bool:
    result = subprocess.run(
        [str(binary), "affected", platform, str(major), str(minor)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip() == "true"


def probe_admits(binary: Path, platform: str) -> bool:
    result = subprocess.run(
        [str(binary), "admits", platform], capture_output=True, text=True, check=True
    )
    return result.stdout.strip() == "true"


def guard_admits_exactly_legacy_four(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant in ("explicit-platform-list", "near-miss-capability-guard-broad-admit"):
        admitted = {p for p in PLATFORMS if probe_admits(binaries[variant], p)}
        results[variant] = admitted == LEGACY_FOUR
    return results


def threshold_preserved_vs_baseline(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        ok = True
        for platform, (old_maj, old_min, new_maj, new_min) in LEGACY_VERSIONS.items():
            baseline_old = probe_affected(binaries[BASELINE], platform, old_maj, old_min)
            baseline_new = probe_affected(binaries[BASELINE], platform, new_maj, new_min)
            ok = ok and probe_affected(binary, platform, old_maj, old_min) == baseline_old
            ok = ok and probe_affected(binary, platform, new_maj, new_min) == baseline_new
        results[variant] = ok
    return results


def guard_removal_is_behaviorally_neutral(binaries: dict[str, Path]) -> dict[str, bool]:
    results = {}
    for variant, binary in binaries.items():
        ok = True
        for platform in EXCLUDED_PLATFORMS:
            for major, minor in EXCLUDED_VERSIONS:
                baseline = probe_affected(binaries[BASELINE], platform, major, minor)
                ok = ok and probe_affected(binary, platform, major, minor) == baseline
        results[variant] = ok
    return results


def old_affected_version_still_reported_affected(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: probe_affected(binary, "anchor", 10, 0) for variant, binary in binaries.items()
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="swift-platform-guard-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        admits_results = guard_admits_exactly_legacy_four(binaries)
        threshold_results = threshold_preserved_vs_baseline(binaries)
        neutral_results = guard_removal_is_behaviorally_neutral(binaries)
        control_results = old_affected_version_still_reported_affected(binaries)

        print("=== guard_admits_exactly_legacy_four ===")
        for name, ok in admits_results.items():
            print(f"  {name}: {'exactly the four' if ok else 'OVER/UNDER-ADMITS'}")
        print("=== threshold_preserved_vs_baseline ===")
        for name, ok in threshold_results.items():
            print(f"  {name}: {'preserved' if ok else 'DIVERGES FROM BASELINE'}")
        print("=== guard_removal_is_behaviorally_neutral (demonstration) ===")
        for name, ok in neutral_results.items():
            print(f"  {name}: {'neutral' if ok else 'DIVERGES ON EXCLUDED PLATFORM'}")
        print("=== old_affected_version_still_reported_affected (control) ===")
        for name, ok in control_results.items():
            print(f"  {name}: {'affected' if ok else 'NOT REPORTED AFFECTED'}")

        failures = []

        expected_admits = {
            "explicit-platform-list": True,
            "near-miss-capability-guard-broad-admit": False,
        }
        for name, expected in expected_admits.items():
            if admits_results.get(name) != expected:
                failures.append(
                    f"{name}: expected guard_admits_exactly_legacy_four={expected}, "
                    f"got {admits_results.get(name)}"
                )

        expected_threshold = {
            "explicit-platform-list": True,
            "guard-removed-availability-only": True,
            "near-miss-capability-guard-broad-admit": True,
            "mutant-dropped-threshold": False,
        }
        for name, expected in expected_threshold.items():
            if threshold_results.get(name) != expected:
                failures.append(
                    f"{name}: expected threshold_preserved_vs_baseline={expected}, "
                    f"got {threshold_results.get(name)}"
                )

        for name in VARIANTS:
            if neutral_results.get(name) is not True:
                failures.append(
                    f"{name}: guard_removal_is_behaviorally_neutral must hold, "
                    f"got {neutral_results.get(name)}"
                )
            if control_results.get(name) is not True:
                failures.append(
                    f"{name}: old_affected_version_still_reported_affected must hold, "
                    f"got {control_results.get(name)}"
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
