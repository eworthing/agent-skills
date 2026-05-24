"""Shared canon loader.

Reads every canon/*.yaml once into a frozen namespace. Both validate-repo.py
and validate-artifact.py import from here so enum ownership lives in one place.

No inline enum constants anywhere else in scripts/.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Tuple

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "error: PyYAML required. Install with: pip install -r scripts/requirements.txt\n"
    )
    sys.exit(2)


CANON_DIR_NAME = "canon"


@dataclass(frozen=True)
class Canon:
    """Frozen snapshot of every canon/*.yaml file."""

    states: Tuple[str, ...]
    halt_subtypes: Tuple[str, ...]
    finding_statuses: Tuple[str, ...]
    verdicts: Tuple[str, ...]
    severity_anchors: Tuple[str, ...]
    scorecard_dimensions: Tuple[str, ...]
    dependency_categories: Tuple[str, ...]
    retirement_reasons: Tuple[str, ...]
    validation_gates: Mapping[str, str]
    # PR2 will add fixture_rule_kinds; lazy lookup via .extra
    extra: Mapping[str, Any]


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        sys.stderr.write(f"error: canon file missing: {path}\n")
        sys.exit(2)
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        sys.stderr.write(f"error: canon file malformed: {path}: {exc}\n")
        sys.exit(2)
    if data is None:
        sys.stderr.write(f"error: canon file empty: {path}\n")
        sys.exit(2)
    return data


def _require_list(data: Mapping[str, Any], key: str, path: Path) -> Tuple[str, ...]:
    if key not in data:
        sys.stderr.write(f"error: canon file {path}: missing top-level key '{key}'\n")
        sys.exit(2)
    values = data[key]
    if not isinstance(values, list):
        sys.stderr.write(f"error: canon file {path}: '{key}' must be a list\n")
        sys.exit(2)
    return tuple(values)


def load_canon(skill_root: Path | None = None) -> Canon:
    """Load every canon/*.yaml file into a frozen Canon instance.

    `skill_root` defaults to the parent of this script's directory.
    """
    root = skill_root or Path(__file__).resolve().parent.parent
    canon_dir = root / CANON_DIR_NAME

    if not canon_dir.is_dir():
        sys.stderr.write(f"error: canon directory missing: {canon_dir}\n")
        sys.exit(2)

    states = _require_list(_load_yaml(canon_dir / "states.yaml"), "states", canon_dir / "states.yaml")
    halt_subtypes = _require_list(
        _load_yaml(canon_dir / "halt-subtypes.yaml"), "halt_subtypes", canon_dir / "halt-subtypes.yaml"
    )
    finding_statuses = _require_list(
        _load_yaml(canon_dir / "finding-statuses.yaml"), "finding_statuses", canon_dir / "finding-statuses.yaml"
    )
    verdicts = _require_list(_load_yaml(canon_dir / "verdicts.yaml"), "verdicts", canon_dir / "verdicts.yaml")
    severity_anchors = _require_list(
        _load_yaml(canon_dir / "severity-anchors.yaml"), "severity_anchors", canon_dir / "severity-anchors.yaml"
    )
    scorecard_dimensions = _require_list(
        _load_yaml(canon_dir / "scorecard-dimensions.yaml"),
        "scorecard_dimensions",
        canon_dir / "scorecard-dimensions.yaml",
    )
    dependency_categories = _require_list(
        _load_yaml(canon_dir / "dependency-categories.yaml"),
        "dependency_categories",
        canon_dir / "dependency-categories.yaml",
    )
    retirement_reasons = _require_list(
        _load_yaml(canon_dir / "retirement-reasons.yaml"),
        "retirement_reasons",
        canon_dir / "retirement-reasons.yaml",
    )

    gates_data = _load_yaml(canon_dir / "validation-gates.yaml")
    if not isinstance(gates_data, dict) or "validation_gates" not in gates_data:
        sys.stderr.write(
            f"error: canon file {canon_dir / 'validation-gates.yaml'}: missing 'validation_gates' key\n"
        )
        sys.exit(2)
    gates_list = gates_data["validation_gates"]
    if not isinstance(gates_list, list):
        sys.stderr.write(
            f"error: canon file {canon_dir / 'validation-gates.yaml'}: 'validation_gates' must be a list\n"
        )
        sys.exit(2)
    gates_map: dict[str, str] = {}
    for entry in gates_list:
        if not isinstance(entry, dict) or "id" not in entry or "title" not in entry:
            sys.stderr.write(
                f"error: canon file {canon_dir / 'validation-gates.yaml'}: each entry needs 'id' and 'title'\n"
            )
            sys.exit(2)
        gate_id = str(entry["id"])
        if gate_id in gates_map:
            sys.stderr.write(
                f"error: canon file {canon_dir / 'validation-gates.yaml'}: duplicate gate id '{gate_id}'\n"
            )
            sys.exit(2)
        gates_map[gate_id] = str(entry["title"])

    extra: dict[str, Any] = {}
    fixture_kinds_path = canon_dir / "fixture-rule-kinds.yaml"
    if fixture_kinds_path.exists():
        kinds_data = _load_yaml(fixture_kinds_path)
        extra["fixture_rule_kinds"] = _require_list(
            kinds_data, "fixture_rule_kinds", fixture_kinds_path
        )

    return Canon(
        states=states,
        halt_subtypes=halt_subtypes,
        finding_statuses=finding_statuses,
        verdicts=verdicts,
        severity_anchors=severity_anchors,
        scorecard_dimensions=scorecard_dimensions,
        dependency_categories=dependency_categories,
        retirement_reasons=retirement_reasons,
        validation_gates=MappingProxyType(gates_map),
        extra=MappingProxyType(extra),
    )


if __name__ == "__main__":
    canon = load_canon()
    print(f"states ({len(canon.states)}): {', '.join(canon.states)}")
    print(f"halt_subtypes ({len(canon.halt_subtypes)}): {', '.join(canon.halt_subtypes)}")
    print(f"finding_statuses ({len(canon.finding_statuses)}): {', '.join(canon.finding_statuses)}")
    print(f"verdicts ({len(canon.verdicts)}): {', '.join(canon.verdicts)}")
    print(f"severity_anchors ({len(canon.severity_anchors)}): {', '.join(canon.severity_anchors)}")
    print(f"scorecard_dimensions ({len(canon.scorecard_dimensions)})")
    print(f"dependency_categories ({len(canon.dependency_categories)}): {', '.join(canon.dependency_categories)}")
    print(f"retirement_reasons ({len(canon.retirement_reasons)}): {', '.join(canon.retirement_reasons)}")
    print(f"validation_gates ({len(canon.validation_gates)}): {', '.join(canon.validation_gates.keys())}")
    if canon.extra:
        print(f"extra keys: {', '.join(canon.extra.keys())}")
