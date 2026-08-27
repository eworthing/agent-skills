#!/usr/bin/env python3
"""Hidden oracle battery for demand-signalling-state-machine.
Grader-only: never shown to a candidate (listed in provenance.json's
grader_only_files).

Swift has no sibling-file import and `swiftc a.swift b.swift` only allows
top-level statements when the entry file is literally named `main.swift`.
Each variant already ships its own candidate-visible `main.swift` (its own
bundled test), so this harness's own entry point -- `oracle_probe.swift`,
grader-only -- is copied to a scratch file named `main.swift` and compiled
against each variant's `signal_relay.swift` in turn, never against that
variant's own `main.swift`. The resulting binary is a tiny CLI:

    <binary> <sourceCount> <event> [<event> ...]

which prints one line of actions per event (see oracle_probe.swift's own
header for the event/action token grammar), letting this harness observe
`Relay.step` uniformly across variants whose internals differ completely.

Runs five checks:

    every_continuation_resumed_exactly_once_under_cancellation -- across a
                                     battery of scripted cancellation
                                     scenarios, every request that was ever
                                     outstanding must be resumed exactly
                                     once by the end of the sequence.
                                     task-per-demand, demand-signalled-
                                     state-machine, and collapsed-
                                     suspension-flag all genuinely hold
                                     here -- reported honestly, not forced --
                                     because none of their defects touch
                                     cancellation while exactly one request
                                     is outstanding. Fails only for mutant-
                                     dropped-cancellation, whose dropped
                                     transition leaves a request outstanding
                                     at cancellation time unresumed forever.
    distinct_states_not_collapsible -- the one event sequence collapsed-
                                     suspension-flag's single suspended-flag-
                                     plus-one-slot representation cannot
                                     track: two demands arriving before
                                     either is satisfied. Compares full,
                                     ordered action lists (not a structural
                                     count) between demand-signalled-state-
                                     machine and collapsed-suspension-flag
                                     only -- task-per-demand is out of scope
                                     for this specific check because its
                                     unrelated per-demand restart behavior
                                     would create a mismatch for a different
                                     reason, and mutant-dropped-cancellation
                                     is out of scope because this sequence
                                     contains no cancellation event, so its
                                     one dropped transition never fires and
                                     a match here would not mean anything.
                                     Fails for collapsed-suspension-flag,
                                     whose single pendingRequest slot is
                                     silently overwritten by the second
                                     demand, permanently losing the first.
    no_per_demand_task_creation -- counts "start a source's work" actions
                                     across several demands served from one
                                     source with no intervening produce or
                                     finish. task-per-demand's count equals
                                     the number of demands (it restarts
                                     every live source on every demand);
                                     every other variant's count stays at 1
                                     regardless of how many demands arrive,
                                     because each starts a source's work
                                     exactly once, the first time any demand
                                     ever arrives.
    buffered_value_survives_source_completion -- a value produced while no
                                     demand is outstanding is buffered, and
                                     its source then finishes while that
                                     value is still owed. The buffered value
                                     must still be delivered, and only the
                                     demand after it may be told the relay is
                                     finished. Added after a blind review
                                     sweep: two of three independent
                                     reviewers found that the accepted
                                     variant hung here, and they were right --
                                     draining the last buffered value fell
                                     through to a non-terminal phase without
                                     re-checking whether every source had
                                     already finished, so the next demand
                                     waited for a value that could never
                                     arrive. task-per-demand had the same
                                     gap. Both are fixed; this check is what
                                     stops either regressing. Fails for
                                     collapsed-suspension-flag, which drops
                                     the buffered value outright and reports
                                     finished a demand early -- a second,
                                     independent consequence of its single-
                                     slot representation.
    control_simple_demand_then_yield -- CONTROL: a single source, one
                                     demand, one produced value, that
                                     source finishing, and one further
                                     demand afterward must produce the
                                     exact same four-step action sequence
                                     in every variant. Holds everywhere, on
                                     purpose -- none of this pack's three
                                     defects (redundant restarts, a lost
                                     second demand, a dropped cancellation
                                     resume) touch this ordinary, single-
                                     demand-at-a-time path at all.

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
RED = "task-per-demand"
GREEN = "demand-signalled-state-machine"
NEAR_MISS = "collapsed-suspension-flag"
MUTANT = "mutant-dropped-cancellation"
VARIANTS = [RED, GREEN, NEAR_MISS, MUTANT]


def _swiftc(*args: str) -> None:
    result = subprocess.run(["swiftc", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"swiftc failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}")


def build_probe(variant: str, scratch_dir: Path) -> Path:
    """Compile `variant`'s signal_relay.swift against the grader-only probe
    (copied to scratch as main.swift, since swiftc only allows top-level
    statements in a file with that exact name)."""
    main_path = scratch_dir / "main.swift"
    shutil.copyfile(PACK_DIR / "oracle_probe.swift", main_path)
    binary_path = scratch_dir / f"probe_{variant}"
    _swiftc(str(PACK_DIR / variant / "signal_relay.swift"), str(main_path), "-o", str(binary_path))
    return binary_path


def run_probe(binary: Path, source_count: int, events: list[str]) -> list[list[str]]:
    result = subprocess.run(
        [str(binary), str(source_count), *events], capture_output=True, text=True, check=True
    )
    raw = result.stdout.strip("\n")
    lines = raw.split("\n") if raw else []
    return [[] if line == "EMPTY" else line.split(" ") for line in lines]


# ---------------------------------------------------------------------------
# every_continuation_resumed_exactly_once_under_cancellation
# ---------------------------------------------------------------------------

CANCEL_SCENARIOS: dict[str, tuple[int, list[str]]] = {
    "single_outstanding": (2, ["demand:1", "cancel"]),
    "resolved_then_outstanding": (2, ["demand:5", "produce:0:9", "demand:6", "cancel"]),
}


def every_continuation_resumed_exactly_once_under_cancellation(
    binaries: dict[str, Path],
) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for variant, binary in binaries.items():
        ok = True
        for _name, (source_count, events) in CANCEL_SCENARIOS.items():
            steps = run_probe(binary, source_count, events)
            resumes: dict[int, int] = {}
            outstanding: set[int] = set()
            for event, actions in zip(events, steps, strict=True):
                if event.startswith("demand:"):
                    outstanding.add(int(event.split(":")[1]))
                for action in actions:
                    if action.startswith(("resume:", "finish:")):
                        request = int(action.split(":")[1])
                        resumes[request] = resumes.get(request, 0) + 1
                        outstanding.discard(request)
            ok = ok and not outstanding and all(count == 1 for count in resumes.values())
        results[variant] = ok
    return results


# ---------------------------------------------------------------------------
# distinct_states_not_collapsible
# ---------------------------------------------------------------------------

DISTINCT_STATES_SOURCE_COUNT = 2
DISTINCT_STATES_EVENTS = ["demand:100", "demand:200", "produce:0:7"]
DISTINCT_STATES_EXPECTED: dict[str, list[list[str]]] = {
    GREEN: [["start:0", "start:1"], [], ["resume:100:7"]],
    NEAR_MISS: [["start:0", "start:1"], [], ["resume:200:7"]],
}


def distinct_states_not_collapsible(binaries: dict[str, Path]) -> dict[str, list[list[str]]]:
    return {
        variant: run_probe(binaries[variant], DISTINCT_STATES_SOURCE_COUNT, DISTINCT_STATES_EVENTS)
        for variant in (GREEN, NEAR_MISS)
    }


# ---------------------------------------------------------------------------
# no_per_demand_task_creation
# ---------------------------------------------------------------------------

TASK_CREATION_DEMAND_COUNTS = [3, 5]


def no_per_demand_task_creation(binaries: dict[str, Path]) -> dict[str, dict[int, int]]:
    results: dict[str, dict[int, int]] = {}
    for variant, binary in binaries.items():
        per_count: dict[int, int] = {}
        for n in TASK_CREATION_DEMAND_COUNTS:
            events = [f"demand:{i}" for i in range(1, n + 1)]
            steps = run_probe(binary, 1, events)
            per_count[n] = sum(1 for actions in steps for a in actions if a.startswith("start:"))
        results[variant] = per_count
    return results


# ---------------------------------------------------------------------------
# control_simple_demand_then_yield
# ---------------------------------------------------------------------------

CONTROL_SOURCE_COUNT = 1
CONTROL_EVENTS = ["demand:1", "produce:0:42", "finish:0", "demand:2"]
CONTROL_EXPECTED = [["start:0"], ["resume:1:42"], [], ["finish:2"]]


def control_simple_demand_then_yield(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: run_probe(binary, CONTROL_SOURCE_COUNT, CONTROL_EVENTS) == CONTROL_EXPECTED
        for variant, binary in binaries.items()
    }


BUFFERED_SOURCE_COUNT = 1
#: A value produced while no demand is outstanding buffers; the source then
#: finishes while that value is still owed. The buffered value must still be
#: delivered, and only the demand after it may be told the relay is finished.
BUFFERED_EVENTS = ["demand:1", "produce:0:7", "produce:0:8", "finish:0", "demand:2", "demand:3"]
BUFFERED_EXPECTED = [["start:0"], ["resume:1:7"], [], [], ["resume:2:8"], ["finish:3"]]


def buffered_value_survives_source_completion(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: run_probe(binary, BUFFERED_SOURCE_COUNT, BUFFERED_EVENTS) == BUFFERED_EXPECTED
        for variant, binary in binaries.items()
    }


#: SourceID can represent two sources. A caller asking for more than that must
#: not leave the finished-count target permanently out of reach: the surplus
#: sources do not exist, so they can never report finishing. Same event sequence
#: at a representable count is the paired control -- it isolates the over-count
#: from the ordinary finish path, which is what makes a failure here readable.
OVERCOUNT_EVENTS = ["demand:1", "finish:0", "finish:1", "demand:2"]
OVERCOUNT_EXPECTED = [["start:0", "start:1"], [], ["finish:1"], ["finish:2"]]


def surplus_source_count_does_not_strand_relay(binaries: dict[str, Path]) -> dict[str, bool]:
    return {
        variant: run_probe(binary, 3, OVERCOUNT_EVENTS) == OVERCOUNT_EXPECTED
        and run_probe(binary, 2, OVERCOUNT_EVENTS) == OVERCOUNT_EXPECTED
        for variant, binary in binaries.items()
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="signal-relay-oracles-") as tmp:
        scratch_dir = Path(tmp)
        binaries = {variant: build_probe(variant, scratch_dir) for variant in VARIANTS}

        cancellation_results = every_continuation_resumed_exactly_once_under_cancellation(binaries)
        distinct_results = distinct_states_not_collapsible(binaries)
        task_creation_results = no_per_demand_task_creation(binaries)
        buffered_results = buffered_value_survives_source_completion(binaries)
        overcount_results = surplus_source_count_does_not_strand_relay(binaries)
        control_results = control_simple_demand_then_yield(binaries)

        print("=== every_continuation_resumed_exactly_once_under_cancellation ===")
        for name, ok in cancellation_results.items():
            print(
                f"  {name}: {'every continuation resumed exactly once' if ok else 'AT LEAST ONE NEVER RESUMED'}"
            )
        print("=== distinct_states_not_collapsible ===")
        for name, steps in distinct_results.items():
            print(f"  {name}: {steps}")
        print("=== no_per_demand_task_creation ===")
        for name, counts in task_creation_results.items():
            print(f"  {name}: {counts}")
        print("=== buffered_value_survives_source_completion ===")
        for name, ok in buffered_results.items():
            print(f"  {name}: {'delivered then finished' if ok else 'BUFFERED VALUE LOST OR HUNG'}")
        print("=== surplus_source_count_does_not_strand_relay (control) ===")
        for name, ok in overcount_results.items():
            print(f"  {name}: {'terminates' if ok else 'RELAY STRANDED'}")
        print("=== control_simple_demand_then_yield (control) ===")
        for name, ok in control_results.items():
            print(f"  {name}: {'matches expected sequence' if ok else 'DIVERGES FROM EXPECTED'}")

        failures: list[str] = []

        expected_cancellation = {RED: True, GREEN: True, NEAR_MISS: True, MUTANT: False}
        for name, expected in expected_cancellation.items():
            if cancellation_results.get(name) != expected:
                failures.append(
                    f"{name}: expected every_continuation_resumed_exactly_once_under_cancellation="
                    f"{expected}, got {cancellation_results.get(name)}"
                )

        for name, expected in DISTINCT_STATES_EXPECTED.items():
            if distinct_results.get(name) != expected:
                failures.append(
                    f"{name}: expected distinct_states_not_collapsible action list {expected}, "
                    f"got {distinct_results.get(name)}"
                )

        expected_task_creation = {
            RED: {3: 3, 5: 5},
            GREEN: {3: 1, 5: 1},
            NEAR_MISS: {3: 1, 5: 1},
            MUTANT: {3: 1, 5: 1},
        }
        for name, expected in expected_task_creation.items():
            if task_creation_results.get(name) != expected:
                failures.append(
                    f"{name}: expected no_per_demand_task_creation counts {expected}, "
                    f"got {task_creation_results.get(name)}"
                )

        expected_buffered = {RED: True, GREEN: True, NEAR_MISS: False, MUTANT: True}
        for name, expected in expected_buffered.items():
            if buffered_results.get(name) != expected:
                failures.append(
                    f"{name}: expected buffered_value_survives_source_completion={expected}, "
                    f"got {buffered_results.get(name)}"
                )

        for name in VARIANTS:
            if overcount_results.get(name) is not True:
                failures.append(
                    f"{name}: surplus_source_count_does_not_strand_relay must hold, "
                    f"got {overcount_results.get(name)}"
                )

        for name in VARIANTS:
            if control_results.get(name) is not True:
                failures.append(
                    f"{name}: control_simple_demand_then_yield must hold, got {control_results.get(name)}"
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
