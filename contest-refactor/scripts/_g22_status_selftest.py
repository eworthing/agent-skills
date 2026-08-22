#!/usr/bin/env python3
"""Self-test: the G22 commit-subject regexes accept every occurrence `status`.

There is no pytest harness in this repo (pyproject configures only ruff), so this
standalone check guards the G22 status alternation against drift. It loads the
regexes from validate-artifact.py (hyphenated filename → loaded by path) and
asserts each documented status round-trips and a garbage status is rejected.

`withdrawn` is the status added so the Critic can record "audited → reclassified
not-a-finding" (no code change) distinct from `resolved` (a landed fix). Before it
was added to the alternation, a withdrawal-targeted commit subject failed G22 and
the loop could not commit a no-code audit that retired a false-positive finding.

Run: python3 scripts/_g22_status_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys

from _selftest_lib import load_validator as _load_validator

# Every status the occurrence enum can carry into a loop commit subject.
# Keep in sync with output-format-state-schemas.md and validation.md G22.
COMMIT_STATUSES = (
    "resolved",
    "carried_forward",
    "fixed_by_user",
    "rejected_attempt",
    "withdrawn",
)


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    for status in COMMIT_STATUSES:
        v2 = (
            f"loop 4: audit F-010; finding F4 (stable_id F-010) {status} "
            f"[registry: +0 findings, ~1 occurrences]"
        )
        v1 = f"loop 4: audit F-010; finding F4 (stable_id F-010) {status}"
        if not va._G22_COMMIT_SUBJECT_RE.match(v2):
            failures.append(f"v2 subject rejected for status {status!r}")
        if not va._G22_COMMIT_SUBJECT_V1_RE.match(v1):
            failures.append(f"v1 subject rejected for status {status!r}")

    garbage = "loop 4: bogus; finding F4 (stable_id F-010) bananas [registry: +0 findings]"
    if va._G22_COMMIT_SUBJECT_RE.match(garbage):
        failures.append("garbage status accepted (alternation too permissive)")

    # The v1 regex carries its OWN independent copy of the status alternation, and
    # only the v2 copy was ever tested against garbage -- loosening v1's alternation
    # passed. v1 is what classifies "legacy subject in a v2+ artifact" versus
    # "malformed", so a permissive v1 silently reclassifies malformed subjects as
    # merely legacy, which is the tolerant branch.
    garbage_v1 = "loop 4: bogus; finding F4 (stable_id F-010) bananas"
    if va._G22_COMMIT_SUBJECT_V1_RE.match(garbage_v1):
        failures.append("garbage status accepted by the v1 regex (alternation too permissive)")

    # v1 must also stay strict about the suffix it exists to distinguish.
    v1_with_suffix = (
        "loop 4: audit F-010; finding F4 (stable_id F-010) resolved [registry: +0 findings]"
    )
    if va._G22_COMMIT_SUBJECT_V1_RE.match(v1_with_suffix):
        failures.append("v1 regex matched a subject carrying the registry suffix")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: G22 accepts all {len(COMMIT_STATUSES)} statuses incl. 'withdrawn'; garbage rejected"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
