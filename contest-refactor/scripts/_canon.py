"""Shared canon loader.

Reads every canon/*.toml once into a frozen namespace. Both validate-repo.py
and validate-artifact.py import from here so enum ownership lives in one place.

No inline enum constants anywhere else in scripts/.
"""

from __future__ import annotations

import sys
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

CANON_DIR_NAME = "canon"


@dataclass(frozen=True)
class Canon:
    """Frozen snapshot of every canon/*.toml file."""

    states: tuple[str, ...]
    halt_subtypes: tuple[str, ...]
    finding_statuses: tuple[str, ...]
    verdicts: tuple[str, ...]
    severity_anchors: tuple[str, ...]
    scorecard_dimensions: tuple[str, ...]
    scorecard_dimension_labels: Mapping[str, str]
    dependency_categories: tuple[str, ...]
    retirement_reasons: tuple[str, ...]
    risk_boundary_kinds: tuple[str, ...]
    risk_evidence_verifications: tuple[str, ...]
    match_kinds: tuple[str, ...]
    residual_blocker_kinds: tuple[str, ...]
    exhaustion_kinds: tuple[str, ...]
    detection_modes: tuple[str, ...]
    finding_families: tuple[str, ...]
    effort_levels: tuple[str, ...]
    repair_revalidation_outcomes: tuple[str, ...]
    invalid_reasons: tuple[str, ...]
    validation_gates: Mapping[str, str]
    # Extended enums that are useful to validators but not common enough to
    # promote into first-class Canon fields live in .extra.
    extra: Mapping[str, Any]


def _load_toml(path: Path) -> Any:
    if not path.exists():
        sys.stderr.write(f"error: canon file missing: {path}\n")
        sys.exit(2)
    try:
        with path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        sys.stderr.write(f"error: canon file malformed: {path}: {exc}\n")
        sys.exit(2)
    if not data:
        sys.stderr.write(f"error: canon file empty: {path}\n")
        sys.exit(2)
    return data


def _require_list(data: Mapping[str, Any], key: str, path: Path) -> tuple[str, ...]:
    if key not in data:
        sys.stderr.write(f"error: canon file {path}: missing top-level key '{key}'\n")
        sys.exit(2)
    values = data[key]
    if not isinstance(values, list):
        sys.stderr.write(f"error: canon file {path}: '{key}' must be a list\n")
        sys.exit(2)
    return tuple(values)


def load_canon(skill_root: Path | None = None) -> Canon:
    """Load every canon/*.toml file into a frozen Canon instance.

    `skill_root` defaults to the parent of this script's directory.
    """
    root = skill_root or Path(__file__).resolve().parent.parent
    canon_dir = root / CANON_DIR_NAME

    if not canon_dir.is_dir():
        sys.stderr.write(f"error: canon directory missing: {canon_dir}\n")
        sys.exit(2)

    states_path = canon_dir / "states.toml"
    states_data = _load_toml(states_path)
    states = _require_list(states_data, "states", states_path)
    halt_subtypes = _require_list(
        _load_toml(canon_dir / "halt-subtypes.toml"),
        "halt_subtypes",
        canon_dir / "halt-subtypes.toml",
    )
    finding_statuses = _require_list(
        _load_toml(canon_dir / "finding-statuses.toml"),
        "finding_statuses",
        canon_dir / "finding-statuses.toml",
    )
    verdicts = _require_list(
        _load_toml(canon_dir / "verdicts.toml"), "verdicts", canon_dir / "verdicts.toml"
    )
    severity_anchors = _require_list(
        _load_toml(canon_dir / "severity-anchors.toml"),
        "severity_anchors",
        canon_dir / "severity-anchors.toml",
    )
    scorecard_data = _load_toml(canon_dir / "scorecard-dimensions.toml")
    if not isinstance(scorecard_data, dict) or "scorecard_dimensions" not in scorecard_data:
        sys.stderr.write(
            f"error: canon file {canon_dir / 'scorecard-dimensions.toml'}: missing 'scorecard_dimensions' key\n"
        )
        sys.exit(2)
    scorecard_list = scorecard_data["scorecard_dimensions"]
    if not isinstance(scorecard_list, list):
        sys.stderr.write(
            f"error: canon file {canon_dir / 'scorecard-dimensions.toml'}: 'scorecard_dimensions' must be a list\n"
        )
        sys.exit(2)
    scorecard_ids: list[str] = []
    scorecard_labels: dict[str, str] = {}
    for entry in scorecard_list:
        if not isinstance(entry, dict) or "id" not in entry or "display_label" not in entry:
            sys.stderr.write(
                f"error: canon file {canon_dir / 'scorecard-dimensions.toml'}: each entry needs 'id' and 'display_label'\n"
            )
            sys.exit(2)
        dim_id = str(entry["id"])
        if dim_id in scorecard_labels:
            sys.stderr.write(
                f"error: canon file {canon_dir / 'scorecard-dimensions.toml'}: duplicate id '{dim_id}'\n"
            )
            sys.exit(2)
        scorecard_ids.append(dim_id)
        scorecard_labels[dim_id] = str(entry["display_label"])
    scorecard_dimensions = tuple(scorecard_ids)
    dependency_categories = _require_list(
        _load_toml(canon_dir / "dependency-categories.toml"),
        "dependency_categories",
        canon_dir / "dependency-categories.toml",
    )
    retirement_reasons = _require_list(
        _load_toml(canon_dir / "retirement-reasons.toml"),
        "retirement_reasons",
        canon_dir / "retirement-reasons.toml",
    )
    risk_boundary_kinds = _require_list(
        _load_toml(canon_dir / "risk-boundary-kinds.toml"),
        "risk_boundary_kinds",
        canon_dir / "risk-boundary-kinds.toml",
    )
    risk_evidence_verifications = _require_list(
        _load_toml(canon_dir / "risk-evidence-verifications.toml"),
        "risk_evidence_verifications",
        canon_dir / "risk-evidence-verifications.toml",
    )
    match_kinds = _require_list(
        _load_toml(canon_dir / "match-kinds.toml"),
        "match_kinds",
        canon_dir / "match-kinds.toml",
    )
    residual_blocker_kinds = _require_list(
        _load_toml(canon_dir / "residual-blocker-kinds.toml"),
        "residual_blocker_kinds",
        canon_dir / "residual-blocker-kinds.toml",
    )
    exhaustion_kinds_path = canon_dir / "exhaustion-kinds.toml"
    exhaustion_kinds_data = _load_toml(exhaustion_kinds_path)
    exhaustion_kinds = _require_list(
        exhaustion_kinds_data, "exhaustion_kinds", exhaustion_kinds_path
    )
    detection_modes = _require_list(exhaustion_kinds_data, "detection_modes", exhaustion_kinds_path)

    remediation_fields_path = canon_dir / "remediation-fields.toml"
    remediation_fields_data = _load_toml(remediation_fields_path)
    finding_families = _require_list(
        remediation_fields_data, "finding_families", remediation_fields_path
    )
    effort_levels = _require_list(remediation_fields_data, "effort_levels", remediation_fields_path)
    repair_revalidation_outcomes = _require_list(
        remediation_fields_data, "repair_revalidation_outcomes", remediation_fields_path
    )

    trial_validity_path = canon_dir / "trial-validity.toml"
    trial_validity_data = _load_toml(trial_validity_path)
    invalid_reasons = _require_list(trial_validity_data, "invalid_reasons", trial_validity_path)
    trial_validity_max_invalid_rate_per_arm = trial_validity_data.get("max_invalid_rate_per_arm")
    trial_validity_max_between_arm_asymmetry = trial_validity_data.get("max_between_arm_asymmetry")
    if (
        trial_validity_max_invalid_rate_per_arm is None
        or trial_validity_max_between_arm_asymmetry is None
    ):
        sys.stderr.write(
            f"error: canon file {trial_validity_path}: missing 'max_invalid_rate_per_arm' or "
            "'max_between_arm_asymmetry'\n"
        )
        sys.exit(2)

    gates_data = _load_toml(canon_dir / "validation-gates.toml")
    if not isinstance(gates_data, dict) or "validation_gates" not in gates_data:
        sys.stderr.write(
            f"error: canon file {canon_dir / 'validation-gates.toml'}: missing 'validation_gates' key\n"
        )
        sys.exit(2)
    gates_list = gates_data["validation_gates"]
    if not isinstance(gates_list, list):
        sys.stderr.write(
            f"error: canon file {canon_dir / 'validation-gates.toml'}: 'validation_gates' must be a list\n"
        )
        sys.exit(2)
    gates_map: dict[str, str] = {}
    for entry in gates_list:
        if not isinstance(entry, dict) or "id" not in entry or "title" not in entry:
            sys.stderr.write(
                f"error: canon file {canon_dir / 'validation-gates.toml'}: each entry needs 'id' and 'title'\n"
            )
            sys.exit(2)
        gate_id = str(entry["id"])
        if gate_id in gates_map:
            sys.stderr.write(
                f"error: canon file {canon_dir / 'validation-gates.toml'}: duplicate gate id '{gate_id}'\n"
            )
            sys.exit(2)
        gates_map[gate_id] = str(entry["title"])

    extra: dict[str, Any] = {}
    fixture_kinds_path = canon_dir / "fixture-rule-kinds.toml"
    if fixture_kinds_path.exists():
        kinds_data = _load_toml(fixture_kinds_path)
        extra["fixture_rule_kinds"] = _require_list(
            kinds_data, "fixture_rule_kinds", fixture_kinds_path
        )
    premium_models_path = canon_dir / "premium-models.toml"
    if premium_models_path.exists():
        premium_models_data = _load_toml(premium_models_path)
        extra["premium_models"] = _require_list(
            premium_models_data, "premium_models", premium_models_path
        )
    fix_kinds_path = canon_dir / "fix-kinds.toml"
    if fix_kinds_path.exists():
        fix_kinds_data = _load_toml(fix_kinds_path)
        extra["fix_kinds"] = _require_list(fix_kinds_data, "fix_kinds", fix_kinds_path)
    # states.toml schema_version >= 2 (backlog item 12): declarative transition
    # table + closed guard vocabulary. Additive over the v1 `states` list read
    # above, so older consumers of `states` are unaffected by these being absent.
    extra["states_schema_version"] = states_data.get("schema_version", 1)
    extra["transition_guards"] = tuple(states_data.get("guards", ()))
    extra["transitions"] = states_data.get("transitions", {})
    # Trial-validity void-rule thresholds (backlog item 21, D4): scalars, not enums, so they
    # live in .extra rather than as typed dataclass fields (see the class docstring above).
    extra["trial_validity_max_invalid_rate_per_arm"] = trial_validity_max_invalid_rate_per_arm
    extra["trial_validity_max_between_arm_asymmetry"] = trial_validity_max_between_arm_asymmetry

    return Canon(
        states=states,
        halt_subtypes=halt_subtypes,
        finding_statuses=finding_statuses,
        verdicts=verdicts,
        severity_anchors=severity_anchors,
        scorecard_dimensions=scorecard_dimensions,
        scorecard_dimension_labels=MappingProxyType(scorecard_labels),
        dependency_categories=dependency_categories,
        retirement_reasons=retirement_reasons,
        risk_boundary_kinds=risk_boundary_kinds,
        risk_evidence_verifications=risk_evidence_verifications,
        match_kinds=match_kinds,
        residual_blocker_kinds=residual_blocker_kinds,
        exhaustion_kinds=exhaustion_kinds,
        detection_modes=detection_modes,
        finding_families=finding_families,
        effort_levels=effort_levels,
        repair_revalidation_outcomes=repair_revalidation_outcomes,
        invalid_reasons=invalid_reasons,
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
    print(
        f"scorecard_dimensions ({len(canon.scorecard_dimensions)}): {', '.join(canon.scorecard_dimensions)}"
    )
    print(
        f"dependency_categories ({len(canon.dependency_categories)}): {', '.join(canon.dependency_categories)}"
    )
    print(
        f"retirement_reasons ({len(canon.retirement_reasons)}): {', '.join(canon.retirement_reasons)}"
    )
    print(
        f"risk_boundary_kinds ({len(canon.risk_boundary_kinds)}): {', '.join(canon.risk_boundary_kinds)}"
    )
    print(
        f"risk_evidence_verifications ({len(canon.risk_evidence_verifications)}): {', '.join(canon.risk_evidence_verifications)}"
    )
    print(f"match_kinds ({len(canon.match_kinds)}): {', '.join(canon.match_kinds)}")
    print(
        f"residual_blocker_kinds ({len(canon.residual_blocker_kinds)}): {', '.join(canon.residual_blocker_kinds)}"
    )
    print(f"exhaustion_kinds ({len(canon.exhaustion_kinds)}): {', '.join(canon.exhaustion_kinds)}")
    print(f"detection_modes ({len(canon.detection_modes)}): {', '.join(canon.detection_modes)}")
    print(f"finding_families ({len(canon.finding_families)}): {', '.join(canon.finding_families)}")
    print(f"effort_levels ({len(canon.effort_levels)}): {', '.join(canon.effort_levels)}")
    print(
        f"repair_revalidation_outcomes ({len(canon.repair_revalidation_outcomes)}): "
        f"{', '.join(canon.repair_revalidation_outcomes)}"
    )
    print(f"invalid_reasons ({len(canon.invalid_reasons)}): {', '.join(canon.invalid_reasons)}")
    print(
        f"validation_gates ({len(canon.validation_gates)}): {', '.join(canon.validation_gates.keys())}"
    )
    if canon.extra:
        print(f"extra keys: {', '.join(canon.extra.keys())}")
