#!/usr/bin/env python3
"""Self-test: validate-repo.py lints the skill's OWN reference tree for two structural
defects it previously could not see — references nested deeper than one level, and
intra-skill markdown links that point at a file that doesn't exist (doc-rot).

Design note — what is NOT adopted, and why. alirezarezvani's skill_structure_validator
ships a `detect_circular_refs` that flags any mutual link A<->B. An empirical scan of
contest-refactor's references/ tree found **18 legitimate** mutual pairs (an index file
and its children, lenses that cross-reference the method, etc.): bidirectional
navigation links between reference docs are normal and good, not a defect. Adopting that
check verbatim would red-flag the current 100/100 tree. So the cycle check is
deliberately omitted; the broken-link resolver below is the structural-integrity check
that actually serves this skill (the repo has already had real doc-rot — commit d7340ae).

No pytest in this repo (pyproject configures only ruff), so this standalone check loads
validate-repo.py, builds throwaway skill trees in a tempdir, and asserts the new
parameterized check functions flag violations and stay silent on a clean tree.

Run: python3 scripts/_ref_tree_lint_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path


def _load_validator():
    path = Path(__file__).with_name("validate-repo.py")
    spec = importlib.util.spec_from_file_location("_vr_reftree", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_clean_tree(root: Path) -> None:
    (root / "references").mkdir(parents=True)
    (root / "SKILL.md").write_text(
        "# Skill\nSee [a](references/a.md).\n", encoding="utf-8"
    )
    (root / "references" / "a.md").write_text(
        "# A\nSee [b](b.md) and the [skill](../SKILL.md).\n", encoding="utf-8"
    )
    (root / "references" / "b.md").write_text(
        "# B\nBack to [a](a.md#top).\n", encoding="utf-8"
    )


def main() -> int:
    vr = _load_validator()
    for fn in ("check_references_one_level_deep", "check_reference_links_resolve"):
        if not hasattr(vr, fn):
            print(f"FAIL: validate-repo.py is missing {fn}()")
            return 1

    failures: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        # 1) clean tree -> both checks silent.
        clean = base / "clean"
        _make_clean_tree(clean)
        d = vr.check_references_one_level_deep(clean)
        link = vr.check_reference_links_resolve(clean)
        if d:
            failures.append(f"clean: depth check should be silent, got {[v.render() for v in d]}")
        if link:
            failures.append(f"clean: link check should be silent, got {[v.render() for v in link]}")

        # 2) a reference nested two levels deep -> depth check flags it.
        deep = base / "deep"
        _make_clean_tree(deep)
        (deep / "references" / "sub").mkdir()
        (deep / "references" / "sub" / "nested.md").write_text("# nested\n", encoding="utf-8")
        d = vr.check_references_one_level_deep(deep)
        if not d:
            failures.append("deep: expected a depth violation for references/sub/nested.md, got none")

        # 3) an intra-skill link to a missing file -> link check flags it.
        rot = base / "rot"
        _make_clean_tree(rot)
        (rot / "references" / "a.md").write_text(
            "# A\nSee [gone](missing.md).\n", encoding="utf-8"
        )
        link = vr.check_reference_links_resolve(rot)
        if not link:
            failures.append("rot: expected a broken-link violation for references/missing.md, got none")
        # external + anchor-only links must NOT be flagged.
        ext = base / "ext"
        _make_clean_tree(ext)
        (ext / "references" / "a.md").write_text(
            "# A\n[web](https://example.com/x.md) and [self](#section) and [b](b.md).\n",
            encoding="utf-8",
        )
        link = vr.check_reference_links_resolve(ext)
        if link:
            failures.append(f"ext: http/anchor links must not be flagged, got {[v.render() for v in link]}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: ref-tree lint — depth>1 references and broken intra-skill .md links are "
        "flagged; clean trees, external URLs, and anchor-only links stay silent"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
