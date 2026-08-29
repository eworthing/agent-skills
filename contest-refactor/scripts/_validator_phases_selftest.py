#!/usr/bin/env python3
"""Selftest for canon/validator-phases.toml (Tier-3 five-phase model).

Guards the one invariant the phase model exists to protect: a gate that cannot
run at a phase must be DECLARED deferred there, so the validator can report
`skipped_for_phase` instead of silently contributing a pass. A gate absent from
both the deferred list and the gate registry is undetectable drift.

Run directly; exit 0 = pass.
"""

from __future__ import annotations

import sys
import tomllib
from itertools import pairwise
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import _canon  # type: ignore[import-not-found]

PHASES_FILE = SKILL_ROOT / "canon" / "validator-phases.toml"
# Rule ids the validator emits that are not `G<n>` gate-registry ids.
NON_GATE_RULES = {"transition-legality", "retirement-rule"}


def load() -> dict:
    with PHASES_FILE.open("rb") as fh:
        return tomllib.load(fh)


def main() -> int:
    data = load()
    canon = _canon.load_canon(SKILL_ROOT)
    checks = 0

    phases = data["phases"]
    assert len(phases) == len(set(phases)), "phase ids must be unique"
    assert phases, "at least one phase required"
    checks += 1

    # Every phase declares both an input row and a deferral row.
    for p in phases:
        assert p in data["inputs"], f"phase {p!r} has no [inputs] row"
        assert p in data["deferred"], f"phase {p!r} has no [deferred] row"
        row = data["inputs"][p]
        assert row.get("note"), f"phase {p!r} input row needs a note"
        assert "fresh" in row and "stale" in row, f"phase {p!r} needs fresh+stale"
        overlap = set(row["fresh"]) & set(row["stale"])
        assert not overlap, f"phase {p!r}: {overlap} cannot be both fresh and stale"
        checks += 1

    # Every deferred gate id resolves: either a registry gate or a known rule id.
    known = set(canon.validation_gates) | NON_GATE_RULES
    for p in phases:
        gates = data["deferred"][p]["gates"]
        assert len(gates) == len(set(gates)), f"{p}: duplicate deferred gate"
        for g in gates:
            assert g in known, f"{p}: deferred gate {g!r} is not a canon gate or known rule"
        if gates:
            assert data["deferred"][p].get("reasons"), f"{p}: deferred gates need reasons"
        checks += 1

    # Monotonicity: later phases never defer MORE than earlier ones. A gate that
    # became runnable cannot become un-runnable again as inputs only accumulate.
    for earlier, later in pairwise(phases):
        a = set(data["deferred"][earlier]["gates"])
        b = set(data["deferred"][later]["gates"])
        regained = b - a
        assert not regained, (
            f"{later} defers {regained} that {earlier} did not — inputs only accumulate"
        )
        checks += 1

    # The enforcement phase must defer nothing: the hook fires there, so a
    # deferral would mean the hook enforces a battery with silent holes.
    enforce = "postchallenge-precommit"
    assert enforce in phases, "the hook's enforcement phase must exist"
    assert not data["deferred"][enforce]["gates"], (
        f"{enforce} is the Tier-3 hook's interception point; it must defer nothing"
    )
    checks += 1

    print(f"_validator_phases_selftest: OK ({checks} assertions, {len(phases)} phases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
