#!/usr/bin/env python3
"""Hidden oracle battery for streaming-decoder-error-state. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Same probe pattern as swiftnio-write-before-active's oracles.py:
`oracle_probe.swift` (grader-only) is copied to a scratch file literally
named `main.swift` (swiftc only allows top-level statements in a file with
that exact name) and compiled against each variant's own
`frame_decoder.swift` in turn. The resulting binary takes one argument (a
protocol input, lines separated by embedded newlines) and prints the
frames the decoder actually delivered to its consumer, in order.

This pack is a RESTRAINT control, not a defect hunt: the parser's states
are the domain, and the point is that a reviewer should inspect and
DISMISS this code as a complexity hotspot, not simplify it. Accordingly
only one of this pack's three checks is a defect-finding discriminator in
the usual sense (no_delivery_after_consumer_error, against the mutant);
the other discriminator (distinct_states_not_collapsible) exists to prove
the near-miss's *simplification* is the actual defect, and the control
exists to prove the fixture itself is not broken.

Runs three checks:

    distinct_states_not_collapsible -- THE NEAR-MISS KILLER. Feeds the
                                 sequence "#*", "#0", ".": an unbounded
                                 frame is opened, its first body line
                                 happens to look exactly like a valid
                                 zero-length counted header, and its
                                 terminator follows. The correct decoder
                                 never inspects a body line's shape once a
                                 frame is open, so it reports ONE frame:
                                 unbounded:[#0]. The near-miss's
                                 `remaining == 0`-as-"awaiting header"
                                 proxy reads 0 throughout an unbounded
                                 frame's entire body (that mode never
                                 touches `remaining`), so it misreads the
                                 body line as a second header and reports
                                 TWO frames instead: an empty counted
                                 frame it invented, then an emptied-out
                                 unbounded frame. Same three lines, two
                                 different parses.
    no_delivery_after_consumer_error -- THE MUTANT KILLER. Feeds a frame
                                 whose body is the sentinel "BOOM" (the
                                 probe's consumer throws upon receiving
                                 it), then feeds two more well-formed
                                 frames. Counts deliveries AFTER the
                                 triggering frame (total delivered minus
                                 the one frame that caused the throw,
                                 which every variant delivers). Zero for
                                 the accepted variant and the near-miss
                                 (both correctly latch). Nonzero for the
                                 mutant, whose missing error-latch keeps
                                 calling the consumer. RED predates the
                                 error-latch entirely and is graded
                                 honestly rather than forced to match: it,
                                 too, keeps delivering after the throw,
                                 which is the specific gap #837-equivalent
                                 work exists to close, not a defect this
                                 pack asks a reviewer to find in RED.
    ordinary_message_decodes_identically -- CONTROL: an unremarkable,
                                 non-adversarial counted frame decodes to
                                 the exact same single frame in all four
                                 variants. Holds everywhere in this pack's
                                 correct design; it would only fail if the
                                 fixture itself were broken in a way that
                                 made the other two checks' results
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
    "hand-rolled-buffer-loop",
    "protocol-decoder-with-error-state",
    "flattened-states-with-flags",
    "mutant-missing-error-state",
]

KILLER_SEQUENCE = "#*\n#0\n.\n"
ERROR_SEQUENCE = "#1\nBOOM\n#1\nok\n#1\nok2\n"
CONTROL_SEQUENCE = "#2\nalpha\nbeta\n"


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s frame_decoder.swift against the grader-only
    probe (copied to scratch as main.swift)."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(str(PACK_DIR / variant / "frame_decoder.swift"), str(main_path), "-o", str(binary_path))
    return binary_path


def run_probe(binary: Path, input_text: str) -> list[str]:
    """Returns the list of delivered frame descriptions, in order."""
    result = subprocess.run([str(binary), input_text], capture_output=True, text=True, check=True)
    lines = result.stdout.strip().splitlines()
    count = int(lines[0].removeprefix("frames:"))
    frames = lines[1 : 1 + count]
    return frames


def distinct_states_not_collapsible(binaries: dict[str, Path]) -> dict[str, list[str]]:
    return {variant: run_probe(binary, KILLER_SEQUENCE) for variant, binary in binaries.items()}


def no_delivery_after_consumer_error(binaries: dict[str, Path]) -> dict[str, int]:
    results = {}
    for variant, binary in binaries.items():
        frames = run_probe(binary, ERROR_SEQUENCE)
        # The frame that triggers the throw is always delivered; every
        # delivery beyond that first one happened after the consumer
        # threw.
        results[variant] = max(0, len(frames) - 1)
    return results


def ordinary_message_decodes_identically(binaries: dict[str, Path]) -> dict[str, list[str]]:
    return {variant: run_probe(binary, CONTROL_SEQUENCE) for variant, binary in binaries.items()}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="streaming-decoder-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        killer_results = distinct_states_not_collapsible(binaries)
        error_results = no_delivery_after_consumer_error(binaries)
        control_results = ordinary_message_decodes_identically(binaries)

        print("=== distinct_states_not_collapsible ===")
        for name, frames in killer_results.items():
            print(f"  {name}: {frames}")
        print("=== no_delivery_after_consumer_error (deliveries after the throw) ===")
        for name, count in error_results.items():
            print(f"  {name}: {count}")
        print("=== ordinary_message_decodes_identically (control) ===")
        for name, frames in control_results.items():
            print(f"  {name}: {frames}")

        failures = []

        expected_killer = {
            "protocol-decoder-with-error-state": ["unbounded:[#0]"],
            "flattened-states-with-flags": ["counted:[]", "unbounded:[]"],
        }
        for name, expected in expected_killer.items():
            if killer_results.get(name) != expected:
                failures.append(
                    f"{name}: expected distinct_states_not_collapsible={expected}, "
                    f"got {killer_results.get(name)}"
                )

        expected_error_zero = ["protocol-decoder-with-error-state", "flattened-states-with-flags"]
        for name in expected_error_zero:
            if error_results.get(name) != 0:
                failures.append(
                    f"{name}: expected no_delivery_after_consumer_error=0, got {error_results.get(name)}"
                )
        if error_results.get("mutant-missing-error-state", 0) == 0:
            failures.append(
                "mutant-missing-error-state: expected no_delivery_after_consumer_error != 0, got 0"
            )
        # RED (hand-rolled-buffer-loop) predates the error-latch and is
        # deliberately not asserted against either value here -- see the
        # module docstring and grading.md.

        expected_control = ["counted:[alpha|beta]"]
        for name in VARIANTS:
            if control_results.get(name) != expected_control:
                failures.append(
                    f"{name}: ordinary_message_decodes_identically must hold, "
                    f"expected {expected_control}, got {control_results.get(name)}"
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
