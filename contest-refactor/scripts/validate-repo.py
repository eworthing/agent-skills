#!/usr/bin/env python3
"""Repo validator for the contest-refactor skill.

Hard-blocking: exit 0 on success, non-zero on any violation.

Checks:
- Evidence Chain coverage in 7 required files (Claim -> Source -> Consequence -> Remedy)
- Step 1.5 bridge sentence + Step 1.6 adjacency in method.md (ordered-list walker)
- G30 + G31 list items in validation.md
- G3 cross-reference to Evidence Chain section
- Gate sequencing (unique, sequential, no gaps up to highest canon gate)
- Canon alignment (enum tokens in references match canon/*.toml)
- `.contest-refactor.example.toml` parses; required keys; accepted_residuals fields complete
- No obvious secrets in the example config
- References tree is one level deep (no nested references/)
- Intra-skill `.md` links from SKILL.md / references resolve (doc-rot guard)

Usage:
    python3 scripts/validate-repo.py
"""

from __future__ import annotations

import re
import sys
import tomllib
from datetime import date
from pathlib import Path
from typing import List, Sequence, Tuple

# Local sibling imports
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import _canon  # type: ignore[import-not-found]  # noqa: E402

SKILL_ROOT = SCRIPT_DIR.parent
REFERENCES_DIR = SKILL_ROOT / "references"

EVIDENCE_CHAIN_FILES = [
    "method.md",
    "lens-apple.md",
    "lens-generic.md",
    "implementation-reviewer.md",
    "output-format-markdown.md",
    "output-format-json.md",
    "validation.md",
]

EVIDENCE_CHAIN_REGEX = re.compile(
    r"Claim\s*[→\-]\s*Source\s*[→\-]\s*Consequence\s*[→\-]\s*Remedy"
)

OBVIOUS_SECRET_REGEXES = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),  # AWS access key
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),  # OpenAI/Anthropic-style API key
    re.compile(r"\bxox[bpar]-[A-Za-z0-9-]+\b"),  # Slack bot token
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),  # PEM key
    re.compile(r"/Users/[A-Za-z][A-Za-z0-9._-]*/"),  # user-specific absolute path
]

REQUIRED_ACCEPTED_RESIDUAL_FIELDS = (
    "id",
    "pattern",
    "reason",
    "accepted_by",
    "accepted_on",
    "expires",
)

KNOWN_TOP_LEVEL_CONFIG_KEYS = {"version", "defaults", "ignore", "accepted_residuals"}
KNOWN_DEFAULT_KEYS = {"lens", "loop_cap", "test_command"}


class Violation:
    """A single rule failure."""

    __slots__ = ("rule", "message", "path")

    def __init__(self, rule: str, message: str, path: Path | None = None) -> None:
        self.rule = rule
        self.message = message
        self.path = path

    def render(self) -> str:
        prefix = f"[{self.rule}]"
        if self.path is not None:
            try:
                rel = self.path.relative_to(SKILL_ROOT)
            except ValueError:
                rel = self.path
            return f"{prefix} {rel}: {self.message}"
        return f"{prefix} {self.message}"


def check_evidence_chain_coverage() -> List[Violation]:
    """Each of the 7 required files contains the Evidence Chain 4-token pattern."""
    violations: List[Violation] = []
    for name in EVIDENCE_CHAIN_FILES:
        path = REFERENCES_DIR / name
        if not path.exists():
            violations.append(
                Violation("evidence-chain", "required file missing", path)
            )
            continue
        text = path.read_text(encoding="utf-8")
        if not EVIDENCE_CHAIN_REGEX.search(text):
            violations.append(
                Violation(
                    "evidence-chain",
                    "missing Claim -> Source -> Consequence -> Remedy cross-reference",
                    path,
                )
            )
    return violations


def _walk_ordered_list(text: str) -> List[Tuple[str, int, int]]:
    """Return ordered-list items at top-level indentation in document order.

    Each entry: (label, start_index, end_index). Labels are the leading
    ordinal token (e.g. "1", "1.5", "1.6", "2"). Only items with no leading
    whitespace are considered top-level siblings.
    """
    pattern = re.compile(r"^(?P<label>\d+(?:\.\d+)?)\.\s+", re.MULTILINE)
    items: List[Tuple[str, int, int]] = []
    matches = list(pattern.finditer(text))
    for idx, match in enumerate(matches):
        # Confirm zero-indent (start of line, no leading spaces)
        line_start = text.rfind("\n", 0, match.start()) + 1
        if line_start != match.start():
            # Non-zero indent prefix — skip
            continue
        label = match.group("label")
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        items.append((label, start, end))
    return items


def check_step_1_5_and_1_6_adjacency() -> List[Violation]:
    """method.md must contain Step 1.5 with the bridge sentence AND Step 1.6 immediately after."""
    violations: List[Violation] = []
    path = REFERENCES_DIR / "method.md"
    if not path.exists():
        return [Violation("step-1.6", "method.md missing", path)]
    text = path.read_text(encoding="utf-8")
    items = _walk_ordered_list(text)
    labels = [item[0] for item in items]
    if "1.5" not in labels:
        violations.append(
            Violation("step-1.6", "method.md missing Step 1.5", path)
        )
        return violations
    idx_1_5 = labels.index("1.5")
    block_1_5 = text[items[idx_1_5][1] : items[idx_1_5][2]]
    if not re.search(
        r"Registry lookup feeds Step 1\.6 eligibility and retirement", block_1_5
    ):
        violations.append(
            Violation(
                "step-1.6",
                "method.md Step 1.5 missing bridge sentence "
                "'Registry lookup feeds Step 1.6 eligibility and retirement'",
                path,
            )
        )
    if idx_1_5 + 1 >= len(items):
        violations.append(
            Violation(
                "step-1.6",
                "method.md Step 1.5 is the last item; Step 1.6 must follow immediately",
                path,
            )
        )
        return violations
    next_label = labels[idx_1_5 + 1]
    if next_label != "1.6":
        violations.append(
            Violation(
                "step-1.6",
                f"method.md Step 1.5 not immediately followed by Step 1.6 (got {next_label!r})",
                path,
            )
        )
    else:
        # Verify Step 1.6 body declares Backlog Eligibility and Per-Finding Retirement
        block_1_6 = text[items[idx_1_5 + 1][1] : items[idx_1_5 + 1][2]]
        # Tolerate a trailing period or other punctuation inside the bold span
        if not re.search(
            r"\*\*Backlog Eligibility and Per-Finding Retirement[.\s]*\*\*", block_1_6
        ):
            violations.append(
                Violation(
                    "step-1.6",
                    "method.md Step 1.6 missing canonical title "
                    "'**Backlog Eligibility and Per-Finding Retirement**'",
                    path,
                )
            )
    return violations


def check_g30_g31_present() -> List[Violation]:
    """validation.md must declare both G30 and G31 as list items."""
    violations: List[Violation] = []
    path = REFERENCES_DIR / "validation.md"
    if not path.exists():
        return [Violation("g30-g31", "validation.md missing", path)]
    text = path.read_text(encoding="utf-8")
    if not re.search(r"\*\*G30 Retirement Precedence\*\*", text):
        violations.append(
            Violation("g30-g31", "validation.md missing G30 Retirement Precedence entry", path)
        )
    if not re.search(r"\*\*G31 Fingerprint Integrity\*\*", text):
        violations.append(
            Violation("g30-g31", "validation.md missing G31 Fingerprint Integrity entry", path)
        )
    return violations


def check_g3_evidence_chain_cross_reference() -> List[Violation]:
    """G3 entry in validation.md must cross-reference the Evidence Chain section."""
    violations: List[Violation] = []
    path = REFERENCES_DIR / "validation.md"
    if not path.exists():
        return [Violation("g3-evidence-chain", "validation.md missing", path)]
    text = path.read_text(encoding="utf-8")
    # Locate the G3 list item and confirm it mentions Evidence Chain
    g3_match = re.search(
        r"\*\*G3 Evidence chain\*\*[^\n]*?Evidence Chain", text, flags=re.IGNORECASE
    )
    if not g3_match:
        violations.append(
            Violation(
                "g3-evidence-chain",
                "validation.md G3 entry does not cross-reference 'Evidence Chain' (must point at the method.md canonical section)",
                path,
            )
        )
    return violations


def check_gate_sequencing(canon: _canon.Canon) -> List[Violation]:
    """Gates in canon/validation-gates.toml are unique, sequential, no gaps."""
    violations: List[Violation] = []
    gate_ids = list(canon.validation_gates.keys())
    # Expect IDs of the form G<n>
    parsed: List[int] = []
    for gid in gate_ids:
        match = re.match(r"^G(\d+)$", gid)
        if not match:
            violations.append(
                Violation("gate-sequencing", f"gate id {gid!r} does not match G<n>")
            )
            continue
        parsed.append(int(match.group(1)))
    if not parsed:
        return violations
    if len(parsed) != len(set(parsed)):
        violations.append(
            Violation("gate-sequencing", "duplicate gate IDs in canon/validation-gates.toml")
        )
    parsed_sorted = sorted(parsed)
    expected = list(range(1, parsed_sorted[-1] + 1))
    if parsed_sorted != expected:
        missing = sorted(set(expected) - set(parsed_sorted))
        violations.append(
            Violation(
                "gate-sequencing",
                f"gate sequence has gaps: missing G{missing}",
            )
        )
    # Cross-check: validation.md uses the same set
    val_path = REFERENCES_DIR / "validation.md"
    if val_path.exists():
        val_text = val_path.read_text(encoding="utf-8")
        ref_ids = set(re.findall(r"\*\*G(\d+)\s+", val_text))
        canon_ids = {str(n) for n in parsed}
        # Validation file should reference every gate
        missing_in_validation = canon_ids - ref_ids
        if missing_in_validation:
            ordered = sorted(int(x) for x in missing_in_validation)
            violations.append(
                Violation(
                    "gate-sequencing",
                    f"validation.md missing gate references: G{ordered}",
                    val_path,
                )
            )
    return violations


def _enum_tokens_from_text(text: str) -> set[str]:
    """Pull every backticked token + enum entry from a markdown file."""
    tokens: set[str] = set()
    for match in re.findall(r"`([^`\n]+)`", text):
        tokens.add(match)
    return tokens


def check_canon_alignment(canon: _canon.Canon) -> List[Violation]:
    """Spot-check that headline canon tokens appear in references."""
    violations: List[Violation] = []
    # For each reference file, ensure canonical enums that are referenced are
    # genuinely canon values. Conservative: we list a few load-bearing
    # invariants here.
    invariants: List[Tuple[str, Sequence[str], str]] = [
        (
            "output-format-state-schemas.md",
            canon.finding_statuses,
            "occurrence status enum",
        ),
        ("validation.md", canon.states, "state enum"),
        ("output-format-json.md", canon.halt_subtypes, "halt_subtype enum"),
        # Retirement reasons are documented as dispositions in the emit-time rules file
        # (output-format-json-rules.md halt_handoff.remaining_serious_findings_disposition,
        # carved out of output-format-json.md by A1a); method.md only names the
        # load-bearing branches by name.
        ("output-format-json-rules.md", canon.retirement_reasons, "retirement reasons"),
    ]
    for fname, required, label in invariants:
        path = REFERENCES_DIR / fname
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in required:
            if token not in text:
                violations.append(
                    Violation(
                        "canon-alignment",
                        f"{label} value {token!r} missing from references",
                        path,
                    )
                )
    return violations


def check_example_config() -> List[Violation]:
    """`.contest-refactor.example.toml` parse + required keys + accepted_residuals shape."""
    violations: List[Violation] = []
    path = SKILL_ROOT / ".contest-refactor.example.toml"
    if not path.exists():
        return [
            Violation(
                "example-config", ".contest-refactor.example.toml missing", path
            )
        ]
    raw = path.read_text(encoding="utf-8")
    # Obvious secrets check
    for secret_re in OBVIOUS_SECRET_REGEXES:
        if secret_re.search(raw):
            violations.append(
                Violation(
                    "example-config",
                    f"obvious secret-shaped value detected ({secret_re.pattern!r})",
                    path,
                )
            )
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        return [Violation("example-config", f"TOML parse failed: {exc}", path)]
    if not isinstance(data, dict):
        return [Violation("example-config", "top-level must be a mapping", path)]
    # Recognize keys
    extra = set(data.keys()) - KNOWN_TOP_LEVEL_CONFIG_KEYS
    if extra:
        violations.append(
            Violation(
                "example-config",
                f"unknown top-level keys: {sorted(extra)}",
                path,
            )
        )
    # Defaults sub-keys
    defaults = data.get("defaults") or {}
    if not isinstance(defaults, dict):
        violations.append(
            Violation("example-config", "defaults must be a mapping", path)
        )
    else:
        unknown_defaults = set(defaults.keys()) - KNOWN_DEFAULT_KEYS
        if unknown_defaults:
            violations.append(
                Violation(
                    "example-config",
                    f"unknown defaults keys: {sorted(unknown_defaults)}",
                    path,
                )
            )
    # ignore is an array
    ignore = data.get("ignore")
    if ignore is not None and not isinstance(ignore, list):
        violations.append(
            Violation("example-config", "ignore must be a list", path)
        )
    # accepted_residuals shape
    residuals = data.get("accepted_residuals", [])
    if not isinstance(residuals, list):
        violations.append(
            Violation("example-config", "accepted_residuals must be a list", path)
        )
        residuals = []
    seen_ids: set[str] = set()
    for idx, entry in enumerate(residuals):
        if not isinstance(entry, dict):
            violations.append(
                Violation(
                    "example-config",
                    f"accepted_residuals[{idx}] must be a mapping",
                    path,
                )
            )
            continue
        for field in REQUIRED_ACCEPTED_RESIDUAL_FIELDS:
            value = entry.get(field)
            if value in (None, "", [], {}):
                violations.append(
                    Violation(
                        "example-config",
                        f"accepted_residuals[{idx}] missing required field {field!r}",
                        path,
                    )
                )
        entry_id = entry.get("id")
        if entry_id is not None:
            if entry_id in seen_ids:
                violations.append(
                    Violation(
                        "example-config",
                        f"accepted_residuals[{idx}] duplicate id {entry_id!r}",
                        path,
                    )
                )
            seen_ids.add(entry_id)
        # `expires` and `accepted_on` must be ISO-8601 dates
        for date_field in ("accepted_on", "expires"):
            value = entry.get(date_field)
            if value is None:
                continue
            if isinstance(value, date):
                continue  # tomllib parses YYYY-MM-DD as datetime.date
            if not isinstance(value, str) or not re.match(
                r"^\d{4}-\d{2}-\d{2}$", value
            ):
                violations.append(
                    Violation(
                        "example-config",
                        f"accepted_residuals[{idx}].{date_field}={value!r} is not YYYY-MM-DD",
                        path,
                    )
                )
    return violations


MARKDOWN_LINK_REGEX = re.compile(r"\]\(([^)]+)\)")


def check_references_one_level_deep(skill_root: Path = SKILL_ROOT) -> List[Violation]:
    """No reference markdown may be nested below references/ (depth must stay 1).

    Progressive-disclosure references live directly in references/; a file in a
    sub-directory is a structural smell (alirezarezvani's references_one_level_deep).
    """
    violations: List[Violation] = []
    refs = skill_root / "references"
    if not refs.is_dir():
        return violations
    for md in sorted(refs.rglob("*.md")):
        if md.parent != refs:
            violations.append(
                Violation(
                    "ref-tree-depth",
                    "reference nested deeper than one level (references/ must stay "
                    f"flat): {md.relative_to(refs)}",
                    md,
                )
            )
    return violations


def check_reference_links_resolve(skill_root: Path = SKILL_ROOT) -> List[Violation]:
    """Every intra-skill `.md` link from SKILL.md / references/*.md must resolve.

    Catches doc-rot: a renamed or deleted reference leaves a dangling link. External
    URLs (`://`, `mailto:`), anchor-only links (`#...`), non-`.md` targets, and links
    that resolve outside this skill are skipped — only files that should exist inside
    the skill are policed.

    (The mutual-link cycle check from alirezarezvani's validator is intentionally NOT
    adopted: an empirical scan found 18 legitimate bidirectional navigation links in
    references/, so it would only produce false positives on this tree.)
    """
    violations: List[Violation] = []
    sources: List[Path] = []
    skill_md = skill_root / "SKILL.md"
    if skill_md.is_file():
        sources.append(skill_md)
    refs = skill_root / "references"
    if refs.is_dir():
        sources.extend(sorted(refs.glob("*.md")))

    skill_root_resolved = skill_root.resolve()
    for src in sources:
        text = src.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK_REGEX.finditer(text):
            target = match.group(1).strip()
            if not target or target.startswith("#"):
                continue
            if "://" in target or target.startswith("mailto:"):
                continue
            path_part = target.split("#", 1)[0].strip()
            if not path_part.endswith(".md"):
                continue
            resolved = (src.parent / path_part).resolve()
            try:
                resolved.relative_to(skill_root_resolved)  # only police in-skill links
            except ValueError:
                continue
            if not resolved.is_file():
                violations.append(
                    Violation(
                        "ref-link",
                        f"intra-skill link to a missing file: {target}",
                        src,
                    )
                )
    return violations


def main() -> int:
    canon = _canon.load_canon(SKILL_ROOT)
    violations: List[Violation] = []
    violations.extend(check_evidence_chain_coverage())
    violations.extend(check_step_1_5_and_1_6_adjacency())
    violations.extend(check_g30_g31_present())
    violations.extend(check_g3_evidence_chain_cross_reference())
    violations.extend(check_gate_sequencing(canon))
    violations.extend(check_canon_alignment(canon))
    violations.extend(check_example_config())
    violations.extend(check_references_one_level_deep())
    violations.extend(check_reference_links_resolve())

    if violations:
        for v in violations:
            sys.stderr.write(v.render() + "\n")
        sys.stderr.write(f"\nvalidate-repo: {len(violations)} violation(s)\n")
        return 1
    sys.stdout.write("validate-repo: OK (all checks passed)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
