#!/usr/bin/env python3
"""Phase-scoped validation (Tier-3 five-phase model).

`validate-artifact.py` runs its whole battery at once. That is right at a
terminal, committed artifact and wrong earlier in the loop: a gate whose input
is not yet fresh does not fail, it goes SILENT (measured: an artifact state
missing REVIEW_HISTORY.json produced findings from one rule while ~20 gates
never ran). Silence then reads as compliance, so an incomplete phase scores
cleaner than a complete one.

This module makes that silence legible. Given a phase, it reports which gates
canon declares un-runnable there, so a caller can say `skipped_for_phase`
instead of implying a pass. It does not decide whether a gate is correct -- it
only reports what canon says could have run.

Canon: canon/validator-phases.toml. Selftest: _validator_phases_selftest.py.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
PHASES_FILE = SKILL_ROOT / "canon" / "validator-phases.toml"


def load_phase_model(root: Path | None = None) -> dict:
    path = (root or SKILL_ROOT) / "canon" / "validator-phases.toml"
    if not path.is_file():
        sys.stderr.write(f"error: phase model missing: {path}\n")
        raise SystemExit(2)
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        sys.stderr.write(f"error: phase model malformed: {path}: {exc}\n")
        raise SystemExit(2) from exc


def phase_names(root: Path | None = None) -> tuple[str, ...]:
    return tuple(load_phase_model(root)["phases"])


def deferred_gates(phase: str, root: Path | None = None) -> tuple[str, ...]:
    """Gate ids canon declares un-runnable at `phase`, in canon order."""
    model = load_phase_model(root)
    if phase not in model["phases"]:
        sys.stderr.write(f"error: unknown phase {phase!r}; known: {', '.join(model['phases'])}\n")
        raise SystemExit(2)
    return tuple(model["deferred"][phase]["gates"])


def _matches(rule: str, gate: str) -> bool:
    """A fired rule belongs to `gate` when it equals it or is a sub-rule
    (`G21-scorecard` under `G21`) -- the same predicate validate-artifact.py's
    `_gate_matches` and validate-fixtures.py's `_gate_satisfies` already use.
    """
    return rule == gate or rule.startswith(f"{gate}-")


def partition(issues: list, phase: str, root: Path | None = None) -> tuple[list, tuple[str, ...]]:
    """Split issues into (reportable, skipped_gate_ids) for `phase`.

    An issue from a deferred gate is withheld rather than reported: at that
    phase its input is stale, so the finding is an artifact of phase, not a
    defect. The gate id is returned instead, so the caller states plainly that
    it did not run.
    """
    skipped = deferred_gates(phase, root)
    if not skipped:
        return list(issues), ()
    keep = [i for i in issues if not any(_matches(i.rule, g) for g in skipped)]
    return keep, skipped
