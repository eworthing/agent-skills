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

    # --- partition(): the behaviour the canon file exists to drive ----------
    import _validator_phase as vp

    class _I:
        def __init__(self, rule):
            self.rule = rule

    early = "step1-post-write"
    enforce = "postchallenge-precommit"

    # A deferred gate's finding is withheld and the gate is named instead.
    keep, skipped = vp.partition([_I("G18"), _I("G5")], early, SKILL_ROOT)
    assert [i.rule for i in keep] == ["G5"], "deferred G18 must be withheld at an early phase"
    assert "G18" in skipped, "withheld gate must be reported as skipped"
    checks += 1

    # Sub-rules follow their gate (G21-scorecard under G21), matching the
    # predicate validate-artifact.py and validate-fixtures.py already use.
    keep, _ = vp.partition([_I("G32-binding")], early, SKILL_ROOT)
    assert keep == [], "a sub-rule of a deferred gate must be withheld too"
    checks += 1

    # The enforcement phase withholds NOTHING -- the hook fires there.
    issues = [_I("G18"), _I("G5"), _I("G47")]
    keep, skipped = vp.partition(issues, enforce, SKILL_ROOT)
    assert len(keep) == len(issues) and skipped == (), (
        "the hook's enforcement phase must never withhold a finding"
    )
    checks += 1

    # A gate that is NOT deferred keeps firing -- the model scopes, it does not
    # blanket-suppress.
    keep, _ = vp.partition([_I("G5")], early, SKILL_ROOT)
    assert [i.rule for i in keep] == ["G5"], "non-deferred gate must survive partitioning"
    checks += 1

    # Unknown phase is a usage error, not a silent empty deferral.
    try:
        vp.partition([], "no-such-phase", SKILL_ROOT)
    except SystemExit as exc:
        assert exc.code == 2, "unknown phase must exit 2"
    else:
        raise AssertionError("unknown phase must not be accepted")
    checks += 1

    print(f"_validator_phases_selftest: OK ({checks} assertions, {len(phases)} phases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
