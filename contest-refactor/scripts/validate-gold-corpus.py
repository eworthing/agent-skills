#!/usr/bin/env python3
"""Gold-corpus manifest validator for the contest-refactor skill.

Layer-1 territory (see docs/contest-refactor-gold-corpus-2026-08-25.md,
"Corpus structure and provenance schema" -> "Manifest validator"): a
deterministic, no-model structural check over each pack's `provenance.json`.
Hard-blocking: exit 0 on success, non-zero on any violation.

Every pack directory under `<corpus-dir>/` must carry a `provenance.json`
with a required `variant_roles` object mapping each variant directory name to
one of the five closed roles (`red`, `green`, `alternate_green`, `near_miss`,
`mutant`) -- directory naming is per-case, not a convention, so the
role-dependent checks below key off this explicit tag rather than guessing
from names.

Checks per pack:
1. At least one `red` variant and at least one green-or-accepted
   (`green` / `alternate_green`) variant.
2. If any variant is `near_miss`, the pack's `must_not_find` list is
   non-empty (the negative oracle is the point of a NEAR-MISS).
3. No rejected legacy aliases `must_notice` / `must_not_claim` at the
   provenance.json top level; emits migration text naming the canonical
   replacement rather than accepting either spelling.
4. Every `must_find_if_present[].applies_to_variants` /
   `.not_required_in` entry names a directory that exists in the pack, and no
   entry lists the same variant in both lists.
5. Every `mutant` variant has a `hidden_oracles[]` entry whose
   `variant_expected_to_fail` names it. NOTE: this is a declaration check
   only -- the manifest schema has no field describing an executable test/
   oracle command, so "demonstrably fails the mutant" cannot be verified by
   this validator without a defined execution contract (flagged in the W2
   report as a spec gap, not silently narrowed).
6. `provenance.json` may only appear in `candidate_visible_files` when the
   pack declares `prompt_exposure: "provenance_labeled"`.
7. In hidden mode (`prompt_exposure` != `provenance_labeled`), no file listed
   in `candidate_visible_files` contains the pack's own PR number, commit
   SHAs (`base_sha`, `accepted_sha`, `subsequent_correction.sha`), or an
   original upstream symbol name from `contamination.renamed`.

An absent or empty corpus directory is not an error: this validator ships
ahead of the corpus, so it exits 0 with a "no packs found" line rather than
failing a build that has no packs to check yet.

Usage:
    python3 scripts/validate-gold-corpus.py evals/gold-corpus
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

VALID_ROLES = frozenset({"red", "green", "alternate_green", "near_miss", "mutant"})
GREEN_LIKE_ROLES = frozenset({"green", "alternate_green"})

# Rejected first-round vocabulary -> canonical replacement (doc line ~730).
LEGACY_ALIASES = {
    "must_notice": "must_find",
    "must_not_claim": "must_not_find",
}

_HEX_SHA_RE = re.compile(r"^[0-9a-fA-F]+$")
_MIN_SHA_LEN = 7


class Violation:
    """A single rule failure."""

    __slots__ = ("message", "path", "rule")

    def __init__(self, rule: str, message: str, path: Path | None = None) -> None:
        self.rule = rule
        self.message = message
        self.path = path

    def render(self) -> str:
        prefix = f"[{self.rule}]"
        if self.path is not None:
            return f"{prefix} {self.path}: {self.message}"
        return f"{prefix} {self.message}"


def _check_legacy_aliases(data: dict, manifest_path: Path) -> list[Violation]:
    """Check 3: rejected legacy field names, with migration text."""
    violations: list[Violation] = []
    for old, new in LEGACY_ALIASES.items():
        if old in data:
            violations.append(Violation("legacy-alias", f"Use {new}, not {old}.", manifest_path))
    return violations


def _check_variant_roles(
    pack_dir: Path, data: dict, manifest_path: Path
) -> tuple[dict[str, str] | None, list[Violation]]:
    """Required `variant_roles` field: present, closed-set values, dirs exist.

    Returns (clean_roles, violations). clean_roles is None only when the
    field itself is missing/malformed (nothing to hand to the role-dependent
    checks); otherwise it contains just the entries that passed both the
    closed-set and directory-existence checks, so downstream checks degrade
    gracefully instead of crashing on a partially-bad map.
    """
    roles = data.get("variant_roles")
    if not isinstance(roles, dict) or not roles:
        return None, [
            Violation(
                "missing-variant-roles",
                "provenance.json must declare a non-empty `variant_roles` object "
                "mapping each variant directory name to one of: "
                f"{', '.join(sorted(VALID_ROLES))}. Directory naming is per-case, not "
                "a convention -- the role-dependent checks (RED/GREEN/NEAR-MISS/"
                "MUTANT) need this explicit tag.",
                manifest_path,
            )
        ]
    violations: list[Violation] = []
    clean: dict[str, str] = {}
    for variant_dir, role in roles.items():
        if role not in VALID_ROLES:
            violations.append(
                Violation(
                    "unknown-variant-role",
                    f"variant_roles[{variant_dir!r}] = {role!r} not in {sorted(VALID_ROLES)}",
                    manifest_path,
                )
            )
            continue
        if not (pack_dir / str(variant_dir)).is_dir():
            violations.append(
                Violation(
                    "variant-role-dir-missing",
                    f"variant_roles names {variant_dir!r} but no such directory "
                    f"exists under {pack_dir.name}/",
                    manifest_path,
                )
            )
            continue
        clean[str(variant_dir)] = role
    return clean, violations


def _check_red_green(roles: dict[str, str], manifest_path: Path) -> list[Violation]:
    """Check 1: at least one RED and one GREEN-or-accepted variant."""
    values = set(roles.values())
    if "red" in values and (values & GREEN_LIKE_ROLES):
        return []
    return [
        Violation(
            "missing-red-or-green",
            "pack needs at least one RED variant and one GREEN-or-accepted "
            f"(green/alternate_green) variant; variant_roles gives "
            f"{sorted(values) or '(none)'}",
            manifest_path,
        )
    ]


def _check_near_miss_must_not_find(
    roles: dict[str, str], data: dict, manifest_path: Path
) -> list[Violation]:
    """Check 2: every NEAR-MISS pack has a non-empty must_not_find."""
    if "near_miss" not in roles.values():
        return []
    must_not_find = data.get("must_not_find")
    if isinstance(must_not_find, list) and must_not_find:
        return []
    return [
        Violation(
            "near-miss-missing-must-not-find",
            "pack has a near_miss variant but must_not_find is empty; the negative "
            "oracle is the point of a NEAR-MISS",
            manifest_path,
        )
    ]


def _check_mutant_oracle(roles: dict[str, str], data: dict, manifest_path: Path) -> list[Violation]:
    """Check 5: every MUTANT variant is named by a hidden_oracles entry.

    Declaration-only -- see the module docstring's note on check 5.
    """
    mutants = [d for d, r in roles.items() if r == "mutant"]
    if not mutants:
        return []
    covered: set[str] = set()
    oracles = data.get("hidden_oracles")
    if isinstance(oracles, list):
        for entry in oracles:
            if isinstance(entry, dict):
                target = entry.get("variant_expected_to_fail")
                if isinstance(target, str):
                    covered.add(target)
    return [
        Violation(
            "mutant-missing-oracle",
            f"mutant variant {m!r} has no hidden_oracles entry with "
            f"variant_expected_to_fail={m!r}; a MUTANT needs a hidden test or static "
            "oracle that fails against it",
            manifest_path,
        )
        for m in mutants
        if m not in covered
    ]


def _check_must_find_if_present(pack_dir: Path, data: dict, manifest_path: Path) -> list[Violation]:
    """Check 4: must_find_if_present variant references are real and non-overlapping."""
    entries = data.get("must_find_if_present")
    if not isinstance(entries, list):
        return []
    violations: list[Violation] = []
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        applies = entry.get("applies_to_variants")
        not_required = entry.get("not_required_in")
        applies = applies if isinstance(applies, list) else []
        not_required = not_required if isinstance(not_required, list) else []

        checked: set[str] = set()
        for variant in [*applies, *not_required]:
            if not isinstance(variant, str) or variant in checked:
                continue
            checked.add(variant)
            if not (pack_dir / variant).is_dir():
                violations.append(
                    Violation(
                        "dangling-variant-reference",
                        f"must_find_if_present[{idx}] names variant {variant!r} which "
                        f"does not exist as a directory under {pack_dir.name}/",
                        manifest_path,
                    )
                )
        overlap = {v for v in applies if isinstance(v, str)} & {
            v for v in not_required if isinstance(v, str)
        }
        for variant in sorted(overlap):
            violations.append(
                Violation(
                    "variant-listed-both-sides",
                    f"must_find_if_present[{idx}] lists {variant!r} in both "
                    "applies_to_variants and not_required_in",
                    manifest_path,
                )
            )
    return violations


def _check_provenance_visibility(data: dict, manifest_path: Path) -> list[Violation]:
    """Check 6: provenance.json is candidate-visible only when labeled."""
    visible = data.get("candidate_visible_files")
    if not isinstance(visible, list) or "provenance.json" not in visible:
        return []
    if data.get("prompt_exposure") == "provenance_labeled":
        return []
    return [
        Violation(
            "provenance-visible-without-label",
            "provenance.json is listed in candidate_visible_files but "
            "prompt_exposure is not 'provenance_labeled'; either remove it from "
            "candidate_visible_files or declare prompt_exposure: "
            '"provenance_labeled"',
            manifest_path,
        )
    ]


def _renamed_originals(contamination: object) -> list[str]:
    """Original (pre-rename) symbol names from contamination.renamed.

    The schema (doc line ~694) doesn't pin the entry shape beyond an example
    array of strings, so this accepts plain strings (the original name
    itself) and {"from"|"original"|"old": ...} dicts for a from/to pair --
    an interpretive choice, called out in the W2 report.
    """
    if not isinstance(contamination, dict):
        return []
    renamed = contamination.get("renamed")
    if not isinstance(renamed, list):
        return []
    names: list[str] = []
    for entry in renamed:
        if isinstance(entry, str) and entry.strip():
            names.append(entry.strip())
        elif isinstance(entry, dict):
            for key in ("from", "original", "old"):
                val = entry.get(key)
                if isinstance(val, str) and val.strip():
                    names.append(val.strip())
                    break
    return names


def _leak_needles(data: dict) -> list[tuple[str, str]]:
    """Collect (kind, needle) pairs check 7 must not find in hidden mode."""
    needles: list[tuple[str, str]] = []
    source_pr = data.get("source_pr")
    if isinstance(source_pr, int):
        needles.append(("pr-number", f"#{source_pr}"))
        needles.append(("pr-number", f"pull/{source_pr}"))
    for sha_field in ("base_sha", "accepted_sha"):
        sha = data.get(sha_field)
        if isinstance(sha, str) and len(sha) >= _MIN_SHA_LEN and _HEX_SHA_RE.match(sha):
            needles.append(("commit-sha", sha))
    subsequent = data.get("subsequent_correction")
    if isinstance(subsequent, dict):
        sha = subsequent.get("sha")
        if isinstance(sha, str) and len(sha) >= _MIN_SHA_LEN and _HEX_SHA_RE.match(sha):
            needles.append(("commit-sha", sha))
    for name in _renamed_originals(data.get("contamination")):
        needles.append(("symbol-name", name))
    return needles


def _check_hidden_leak(pack_dir: Path, data: dict, manifest_path: Path) -> list[Violation]:
    """Check 7: hidden-mode candidate-visible files must not leak provenance."""
    if data.get("prompt_exposure") == "provenance_labeled":
        return []  # leak check only binds in hidden mode
    visible = data.get("candidate_visible_files")
    if not isinstance(visible, list) or not visible:
        return []  # nothing declared visible -> nothing to scan (best-effort)
    needles = _leak_needles(data)
    if not needles:
        return []

    violations: list[Violation] = []
    for rel in visible:
        if not isinstance(rel, str):
            continue
        path = pack_dir / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for kind, needle in needles:
            hit = (
                re.search(rf"\b{re.escape(needle)}\b", text)
                if kind == "symbol-name"
                else needle in text
            )
            if hit:
                violations.append(
                    Violation(
                        "hidden-mode-leak",
                        f"candidate-visible file {rel!r} contains a {kind} leak "
                        f"({needle!r}); hidden mode must not expose original PR "
                        "numbers, commit SHAs, or real upstream symbol names",
                        manifest_path,
                    )
                )
    return violations


def _validate_one_pack(pack_dir: Path) -> list[Violation]:
    manifest_path = pack_dir / "provenance.json"
    if not manifest_path.is_file():
        return [Violation("missing-manifest", "pack has no provenance.json", manifest_path)]
    try:
        raw = manifest_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except OSError as exc:
        return [Violation("manifest-parse", f"provenance.json unreadable: {exc}", manifest_path)]
    except json.JSONDecodeError as exc:
        return [
            Violation("manifest-parse", f"provenance.json is not valid JSON: {exc}", manifest_path)
        ]
    if not isinstance(data, dict):
        return [
            Violation(
                "manifest-parse", "provenance.json top-level must be a JSON object", manifest_path
            )
        ]

    violations: list[Violation] = []
    violations.extend(_check_legacy_aliases(data, manifest_path))
    roles, role_violations = _check_variant_roles(pack_dir, data, manifest_path)
    violations.extend(role_violations)
    if roles is not None:
        violations.extend(_check_red_green(roles, manifest_path))
        violations.extend(_check_near_miss_must_not_find(roles, data, manifest_path))
        violations.extend(_check_mutant_oracle(roles, data, manifest_path))
    violations.extend(_check_must_find_if_present(pack_dir, data, manifest_path))
    violations.extend(_check_provenance_visibility(data, manifest_path))
    violations.extend(_check_hidden_leak(pack_dir, data, manifest_path))
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "corpus_dir",
        type=Path,
        help="directory containing one subdirectory per gold-corpus pack "
        "(e.g., evals/gold-corpus/); absent or empty is not an error",
    )
    args = parser.parse_args(argv)
    corpus_dir: Path = args.corpus_dir

    if not corpus_dir.exists():
        sys.stdout.write(
            f"validate-gold-corpus: OK (no packs found -- {corpus_dir} does not exist yet)\n"
        )
        return 0
    if not corpus_dir.is_dir():
        sys.stderr.write(f"error: not a directory: {corpus_dir}\n")
        return 2

    pack_dirs = sorted(
        (p for p in corpus_dir.iterdir() if p.is_dir() and not p.name.startswith(".")),
        key=lambda p: p.name,
    )
    if not pack_dirs:
        sys.stdout.write(f"validate-gold-corpus: OK (no packs found in {corpus_dir})\n")
        return 0

    violations: list[Violation] = []
    for pack_dir in pack_dirs:
        violations.extend(_validate_one_pack(pack_dir))

    if violations:
        for v in violations:
            sys.stderr.write(v.render() + "\n")
        sys.stderr.write(
            f"\nvalidate-gold-corpus: {len(violations)} violation(s) across "
            f"{len(pack_dirs)} pack(s)\n"
        )
        return 1
    sys.stdout.write(f"validate-gold-corpus: OK ({len(pack_dirs)} pack(s) passed)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
