"""Selftest for _artifact_md_flag.py (G51): Markdown System Flag vs JSON state.

Run: python3 scripts/_md_flag_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _artifact_md_flag import check_g51_md_state_parity

POST_EPOCH_REV = "000c7d8"  # _ruleset_epoch.MD_STATE_PARITY_REV
PRE_EPOCH_REV = "1609cd6"  # _ruleset_epoch.ATTESTATION_SKIP_REV (an ancestor)


def _run(state, md: str | None, skill_rev: str = POST_EPOCH_REV) -> list[str]:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        review = {"schema_version": 4, "skill_rev": skill_rev, "state": state}
        (d / "CURRENT_REVIEW.json").write_text(json.dumps(review), encoding="utf-8")
        if md is not None:
            (d / "CURRENT_REVIEW.md").write_text(md, encoding="utf-8")
        return [i.rule for i in check_g51_md_state_parity(d, review)]


MD = "# Review\n\n### System Flag\n[STATE: {flag}]\n\n## Handoff\n```\n[STATE: HALT_SUCCESS]\n```\n"


def main() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    # (1) The live defect: JSON promoted, Markdown still the candidate -> FAIL.
    got = _run("HALT_SUCCESS", MD.format(flag="HALT_SUCCESS_candidate"))
    check(got == ["G51"], f"candidate flag under a HALT_SUCCESS JSON must fire G51, got {got}")
    # (2) Parity -> clean; the repeated token inside the handoff block is ignored.
    got = _run("HALT_SUCCESS", MD.format(flag="HALT_SUCCESS"))
    check(got == [], f"matching flags must be clean, got {got}")
    got = _run("CONTINUE", MD.format(flag="CONTINUE"))
    check(got == [], f"a CONTINUE loop with a matching flag must be clean, got {got}")
    # (3) Pre-epoch artifact with the same defect stays green (run 8747656f's commits).
    got = _run("HALT_SUCCESS", MD.format(flag="HALT_SUCCESS_candidate"), skill_rev=PRE_EPOCH_REV)
    check(got == [], f"pre-epoch skill_rev must stay green, got {got}")
    # (4) No flag line at all -> FAIL (the section is mandatory).
    got = _run("CONTINUE", "# Review\n\nno flag here\n")
    check(got == ["G51"], f"a missing System Flag line must fire G51, got {got}")
    # (5) Ownership boundaries: null state is G36's, a missing Markdown is required-artifact's.
    check(_run(None, MD.format(flag="CONTINUE")) == [], "null state is not G51's to judge")
    check(_run("CONTINUE", None) == [], "a missing CURRENT_REVIEW.md is not G51's to judge")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print("OK: G51 selftest — 7 cases (2 trigger)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
