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

Also covers two register "Instrumented run #7" fixes (register § Additional
defects #5, work order P0 #4): the no-finding subject form (a loop with an
empty backlog has nothing to fill `finding F<n> (stable_id F-<NNN>) <status>`
with, so before this form existed the only escape was a fabricated id —
observed in production as two BenchHype commits carrying `stable_id F-NEW`),
and the fixed `check_g22_archive_divider` skip-guard (previously skipped
whenever no `.contest-refactor.toml` was findable, which is exactly the shape
that let the two F-NEW commits pass strict validation with zero Issues).

Run: python3 scripts/_g22_status_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from _selftest_lib import load_validator as _load_validator

CHECK_SUBJECT_CLI = Path(__file__).with_name("check_commit_subject.py")
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "evals" / "fixtures"

# The exact malformed subject observed on BenchHype commits 0e4f31cd/8c5bf1d7
# (register "Instrumented run #7"): a fabricated finding id, not a real one.
F_NEW_SUBJECT = "loop 3: emit HALT_SUCCESS_candidate; finding F1 (stable_id F-NEW) carried_forward"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def _mkrepo_with_commit(td: Path, subject: str) -> Path:
    """A throwaway git repo OUTSIDE the skills checkout, one commit with `subject`."""
    repo = td / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@t")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("x\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", subject)
    return repo


def _check_subject_cli_exit(subject: str) -> int:
    proc = subprocess.run(
        [sys.executable, str(CHECK_SUBJECT_CLI), "--subject", subject],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode


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

    # --- no-finding subject form (register P0 #4) ---
    no_finding_v2 = (
        "loop 3: emit HALT_SUCCESS_candidate — empty backlog; no findings [registry: +0 findings]"
    )
    no_finding_v1 = "loop 3: emit HALT_SUCCESS_candidate — empty backlog; no findings"
    if not va._G22_COMMIT_SUBJECT_NO_FINDING_RE.match(no_finding_v2):
        failures.append("no-finding v2 subject rejected")
    if va._G22_COMMIT_SUBJECT_RE.match(no_finding_v2):
        failures.append("no-finding subject matched the finding-bearing regex (should be disjoint)")
    if not va._G22_COMMIT_SUBJECT_NO_FINDING_V1_RE.match(no_finding_v1):
        failures.append("no-finding v1 (no registry suffix) subject rejected")
    if va._G22_COMMIT_SUBJECT_NO_FINDING_V1_RE.match(no_finding_v2):
        failures.append("no-finding v1 regex matched a subject carrying the registry suffix")
    # A stray stable_id inside a no-finding subject must not sneak past — the
    # form's whole point is "no finding, no stable_id".
    no_finding_with_stable_id = (
        "loop 3: emit HALT_SUCCESS_candidate; no findings (stable_id F-001) [registry: +0 findings]"
    )
    if va._G22_COMMIT_SUBJECT_NO_FINDING_RE.match(no_finding_with_stable_id):
        failures.append("no-finding regex accepted a subject carrying a stable_id")

    # --- the exact observed F-NEW subject must fail every G22 form ---
    for name, pattern in (
        ("finding-bearing v2", va._G22_COMMIT_SUBJECT_RE),
        ("finding-bearing v1", va._G22_COMMIT_SUBJECT_V1_RE),
        ("no-finding v2", va._G22_COMMIT_SUBJECT_NO_FINDING_RE),
        ("no-finding v1", va._G22_COMMIT_SUBJECT_NO_FINDING_V1_RE),
    ):
        if pattern.match(F_NEW_SUBJECT):
            failures.append(f"F-NEW subject was accepted by the {name} regex")

    # --- check_g22_archive_divider: skip-guard must not skip a real repo
    #     merely because it has no .contest-refactor.toml (the observed miss) ---
    with tempfile.TemporaryDirectory(prefix="g22-selftest-") as td:
        repo = _mkrepo_with_commit(Path(td), F_NEW_SUBJECT)
        issues = va.check_g22_archive_divider(repo, {"schema_version": 4, "loop": 1})
        if not any(i.rule == "G22" for i in issues):
            failures.append(
                "RED case: real repo, no .contest-refactor.toml, F-NEW subject in HEAD — "
                "expected a G22 Issue, got silence (the observed zero-Issue miss)"
            )

    # ...and the new no-finding form must pass cleanly in that same real-repo path.
    with tempfile.TemporaryDirectory(prefix="g22-selftest-") as td:
        repo = _mkrepo_with_commit(
            Path(td),
            "loop 1: emit HALT_SUCCESS_candidate — empty backlog; no findings [registry: +0 findings]",
        )
        issues = va.check_g22_archive_divider(repo, {"schema_version": 4, "loop": 1})
        if any(i.rule == "G22" for i in issues):
            failures.append(
                f"valid no-finding subject in a real repo fired G22: {[i.message for i in issues]}"
            )

    # A fixture-style dir nested INSIDE the skills repo checkout must still skip —
    # this repo's real recent commit subjects (e.g. Conventional Commits) don't
    # match any G22 form, so if the skip regressed this would spuriously fire.
    fixture_issues = va.check_g22_archive_divider(FIXTURES_DIR, {"schema_version": 4, "loop": 5})
    if any(i.rule == "G22" for i in fixture_issues):
        failures.append(
            "fixture dir nested inside the skills repo should skip the commit-subject "
            f"check, got: {[i.message for i in fixture_issues]}"
        )

    # --- pre-commit CLI (check_commit_subject.py): reuses these same regexes ---
    valid_finding = (
        "loop 4: audit F-010; finding F4 (stable_id F-010) resolved "
        "[registry: +0 findings, ~1 occurrences]"
    )
    valid_no_finding = "loop 3: emit HALT_SUCCESS_candidate; no findings [registry: +0 findings]"
    if _check_subject_cli_exit(valid_finding) != 0:
        failures.append("check_commit_subject.py rejected a valid finding-bearing subject")
    if _check_subject_cli_exit(valid_no_finding) != 0:
        failures.append("check_commit_subject.py rejected a valid no-finding subject")
    if _check_subject_cli_exit(F_NEW_SUBJECT) == 0:
        failures.append("check_commit_subject.py accepted the fabricated F-NEW subject")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: G22 accepts all {len(COMMIT_STATUSES)} statuses incl. 'withdrawn'; garbage "
        "rejected; no-finding form accepted, F-NEW rejected everywhere, skip-guard fixed, "
        "pre-commit CLI wired"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
