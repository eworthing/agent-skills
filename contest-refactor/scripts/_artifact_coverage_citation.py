"""_artifact_coverage_citation.py — G17, indirect coverage citation.

G17 has been specified in three places since PR 3 and implemented in none:
`references/validation.md` (the Critic's checklist), `output-format-json-rules.md`
rule 22, and the canonical keyword list in `output-format-json.md`. A production
run against a Swift repo reached terminal HALT_SUCCESS with `what_changed`
containing "collapsed", a single non-test source file in `changed_paths`, and
`interface_test_coverage_path: null` — G17's trigger, with no citation, unflagged.

--- The flip switch -------------------------------------------------------
Shadow-first, mirroring _artifact_transitions.py: every violation prints a
'[G17 ...]' line, but the check always returns an empty Issue list, so it can
never fail `--mode strict` or block validate-fixtures.py. Flip REPORT_ONLY to
False to make it return real Issues. This is the ONE place that decision is made.

Report-only is also what makes this safe under backlog item 30: adding a
required-field check at an existing schema_version retroactively invalidates
artifacts committed before the check existed. The promotion bar for flipping
the switch is recorded in docs/behavioral-validation-ledger.md, sweep #4.
---------------------------------------------------------------------------

--- Blindness is an outcome, not a pass -----------------------------------
`loop_result.changed_paths` arrived at **v3** (output-format-json.md:401) and the
v2->v3 migration default-fills it to `[]` (output-format-migrations.md:71). So an
absent or default-filled value is indistinguishable from "the loop changed no
test file" -- and reading it as the latter fires G17 on every migrated v2
artifact. When the trigger matches but the evidence cannot be read, this prints
`[g17-check-blind ...]` and reports nothing. Same discipline as
`[transition-check-blind ...]` and exit code 2 elsewhere in this repo:
cannot-measure is its own outcome, never a clean result.
---------------------------------------------------------------------------

Deliberately no new G-number is minted: G17 already exists in canon and already
carries its validation.md checklist bullet, so this implements a numbered rule
rather than adding one. The bullet was aligned to this module's accepted-kind
regex in the same change; _g17_selftest.py pins the two together.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from _artifact_core import Issue
from coverage_ledger import _is_test_name

REPORT_ONLY = True

SKILL_ROOT = Path(__file__).resolve().parent.parent
_SCHEMA_DOC = SKILL_ROOT / "references" / "output-format-json.md"

# output-format-json.md states "no keyword drift between schema and gate text",
# so the list is DERIVED from that prose rather than copied here. A copy is a
# second thing to keep correct; the drift it invites is exactly what the source
# document forbids. Same reasoning as _provider_detection_selftest's default-model
# table.
_KEYWORD_SECTION_RE = re.compile(
    r"^## Deepening Keywords \(canonical\)\s*$.*?^```\s*$(?P<body>.*?)^```\s*$",
    re.M | re.S,
)

# The accepted-kind contract. output-format-json-rules.md rule 22 admits
# role-bearing variants with a stated rationale; validation.md's checklist was
# aligned to this regex rather than the reverse, because a report-only check that
# fires on legitimate variants trains its reader to ignore it.
ACCEPTED_KIND_RE = r"^(new|existing_deepened|existing_[a-z_]+_interface)$"
_ACCEPTED_KIND = re.compile(ACCEPTED_KIND_RE)

_TEST_DIR_NAMES = frozenset({"test", "tests", "__tests__", "spec", "specs"})


def _is_test_dir(seg: str) -> bool:
    """Bounded on purpose.

    A substring test (`"Test" in seg`) matches `ABTesting` and `Testimonial` --
    ordinary production directories -- and misclassifying a source path as a test
    SUPPRESSES the diagnostic, which no later adjudication can see. A false
    positive fires and gets adjudicated; a false negative is invisible. So the
    rule leans toward firing: `BenchHypeUITestsShared` and `TestSupport` classify
    as source and G17 will fire on them, which is the recoverable direction.

    Case-sensitivity is load-bearing: the lowercase substring `test` matches
    `contest-refactor`, this repo's own directory name.
    """
    return seg.endswith("Tests") or seg.lower() in _TEST_DIR_NAMES


def _is_test_path(p: str) -> bool | None:
    """True/False, or None when the path names no file (caller treats as blind).

    `_is_test_name` is a BASENAME helper -- coverage_ledger composes it with a
    separate directory walk, and so must this. Using either alone misses
    `Tests/Support.swift`, and audit_boundaries._is_test_file (the repo's
    designated SSOT) is Python-only and misses `FooTests.swift` entirely.
    """
    if not isinstance(p, str) or not p or p.endswith(("/", "\\")):
        # `Tests/` -> ('Tests',) and `src/` -> ('src',): neither names a file.
        return None
    parts = PurePosixPath(p.replace("\\", "/")).parts
    if not parts or parts[-1] in ("/", "//", "..", ""):
        # `.` yields (), `/` yields ('/',).
        return None
    return any(_is_test_dir(d) for d in parts[:-1]) or _is_test_name(parts[-1])


def deepening_keywords(doc: str | None = None) -> tuple[str, ...]:
    """The canonical keyword list, parsed from the schema prose. Empty = blind."""
    if doc is None:
        try:
            doc = _SCHEMA_DOC.read_text(encoding="utf-8")
        except OSError:
            return ()
    m = _KEYWORD_SECTION_RE.search(doc)
    if not m:
        return ()
    return tuple(w for w in (part.strip() for part in m.group("body").split("|")) if w)


def _blind(reason: str, loop) -> list[Issue]:
    print(f"[g17-check-blind reason={reason} loop={loop}]")
    return []


def check_g17_coverage_citation(current_review: dict, canon=None) -> list[Issue]:
    """G17: a deepening refactor with no test-file change must cite indirect coverage.

    canon is accepted and unused -- the trigger vocabulary lives in the schema
    prose, not in canon/, and the signature matches its sibling checks.
    """
    del canon
    issues: list[Issue] = []
    if (current_review.get("schema_version") or 1) < 2:
        return issues
    lr = current_review.get("loop_result")
    if not isinstance(lr, dict):
        return issues
    what = lr.get("what_changed")
    if not isinstance(what, str) or not what.strip():
        return issues

    loop = current_review.get("loop")

    keywords = deepening_keywords()
    if not keywords:
        return _blind("deepening keyword list unparseable", loop)
    lowered = what.lower()
    if not any(k in lowered for k in keywords):
        return issues

    changed = lr.get("changed_paths")
    if not isinstance(changed, list) or not changed:
        # v2 predates the field and the v2->v3 migration default-fills it to [].
        return _blind("changed_paths absent or empty (v3+ field)", loop)

    for entry in changed:
        verdict = _is_test_path(entry) if isinstance(entry, str) else None
        if verdict is None:
            return _blind("changed_paths holds an entry that names no file", loop)
        if verdict:
            return issues  # a test file changed -- the carve-out does not apply

    citations = lr.get("interface_test_coverage_path")
    if not isinstance(citations, list) or not citations:
        issues.append(
            Issue(
                "G17",
                f"loop {loop}: what_changed is a deepening refactor and no test file "
                "appears in changed_paths, so loop_result.interface_test_coverage_path "
                "must be a non-empty list",
            )
        )
    else:
        for i, c in enumerate(citations):
            if not isinstance(c, dict):
                issues.append(
                    Issue("G17", f"loop {loop}: interface_test_coverage_path[{i}] is not an object")
                )
                continue
            sym = c.get("target_symbol")
            if not isinstance(sym, str) or not sym.strip():
                issues.append(
                    Issue(
                        "G17",
                        f"loop {loop}: interface_test_coverage_path[{i}].target_symbol is required",
                    )
                )
            kind = c.get("target_symbol_kind")
            if not isinstance(kind, str) or not _ACCEPTED_KIND.match(kind):
                issues.append(
                    Issue(
                        "G17",
                        f"loop {loop}: interface_test_coverage_path[{i}].target_symbol_kind "
                        f"{kind!r} does not match {ACCEPTED_KIND_RE}",
                    )
                )
            if c.get("distinguishes_no_op") is not True:
                issues.append(
                    Issue(
                        "G17",
                        f"loop {loop}: interface_test_coverage_path[{i}].distinguishes_no_op "
                        "must be true -- a citation that passes against a no-op is not coverage",
                    )
                )

    for issue in issues:
        print(f"[{issue.rule}] {issue.message}")
    if REPORT_ONLY:
        return []
    return issues
