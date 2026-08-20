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


def _fail(path: Path, msg: str) -> None:
    sys.stderr.write(f"error: canon file {path}: {msg}\n")
    sys.exit(2)


def _require_list(data: Mapping[str, Any], key: str, path: Path) -> tuple[str, ...]:
    if key not in data:
        _fail(path, f"missing top-level key '{key}'")
    values = data[key]
    if not isinstance(values, list):
        _fail(path, f"'{key}' must be a list")
    return tuple(values)


def _list_from(canon_dir: Path, filename: str, key: str) -> tuple[str, ...]:
    """One canon file, one required list. The filename is spelled once."""
    path = canon_dir / filename
    return _require_list(_load_toml(path), key, path)


def _id_map(
    canon_dir: Path, filename: str, list_key: str, value_key: str, noun: str
) -> dict[str, str]:
    """`[[list_key]]` entries with a unique `id` -> {id: value_key}, order preserved."""
    path = canon_dir / filename
    data = _load_toml(path)
    if not isinstance(data, dict) or list_key not in data:
        _fail(path, f"missing '{list_key}' key")
    entries = data[list_key]
    if not isinstance(entries, list):
        _fail(path, f"'{list_key}' must be a list")
    out: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict) or "id" not in entry or value_key not in entry:
            _fail(path, f"each entry needs 'id' and '{value_key}'")
        key = str(entry["id"])
        if key in out:
            _fail(path, f"duplicate {noun}'{key}'")
        out[key] = str(entry[value_key])
    return out


def load_canon(skill_root: Path | None = None) -> Canon:
    """Load every canon/*.toml file into a frozen Canon instance.

    `skill_root` defaults to the parent of this script's directory.
    """
    root = skill_root or Path(__file__).resolve().parent.parent
    canon_dir = root / CANON_DIR_NAME
    if not canon_dir.is_dir():
        sys.stderr.write(f"error: canon directory missing: {canon_dir}\n")
        sys.exit(2)

    # Files contributing exactly one list each.
    simple = {
        key: _list_from(canon_dir, filename, key)
        for filename, key in (
            ("halt-subtypes.toml", "halt_subtypes"),
            ("finding-statuses.toml", "finding_statuses"),
            ("verdicts.toml", "verdicts"),
            ("severity-anchors.toml", "severity_anchors"),
            ("dependency-categories.toml", "dependency_categories"),
            ("retirement-reasons.toml", "retirement_reasons"),
            ("risk-boundary-kinds.toml", "risk_boundary_kinds"),
            ("risk-evidence-verifications.toml", "risk_evidence_verifications"),
            ("match-kinds.toml", "match_kinds"),
            ("residual-blocker-kinds.toml", "residual_blocker_kinds"),
        )
    }

    # Files contributing several lists, or read again below for non-list keys.
    states_path = canon_dir / "states.toml"
    states_data = _load_toml(states_path)
    states = _require_list(states_data, "states", states_path)

    exhaustion_path = canon_dir / "exhaustion-kinds.toml"
    exhaustion_data = _load_toml(exhaustion_path)

    remediation_path = canon_dir / "remediation-fields.toml"
    remediation_data = _load_toml(remediation_path)

    trial_path = canon_dir / "trial-validity.toml"
    trial_data = _load_toml(trial_path)
    max_invalid_rate = trial_data.get("max_invalid_rate_per_arm")
    max_asymmetry = trial_data.get("max_between_arm_asymmetry")
    if max_invalid_rate is None or max_asymmetry is None:
        _fail(trial_path, "missing 'max_invalid_rate_per_arm' or 'max_between_arm_asymmetry'")

    scorecard_labels = _id_map(
        canon_dir, "scorecard-dimensions.toml", "scorecard_dimensions", "display_label", "id "
    )
    gates_map = _id_map(canon_dir, "validation-gates.toml", "validation_gates", "title", "gate id ")

    extra: dict[str, Any] = {}
    # Optional files: absent is legal, present must be well-formed.
    for filename, key in (
        ("fixture-rule-kinds.toml", "fixture_rule_kinds"),
        ("premium-models.toml", "premium_models"),
        ("fix-kinds.toml", "fix_kinds"),
    ):
        if (canon_dir / filename).exists():
            extra[key] = _list_from(canon_dir, filename, key)
    # Noise-floor significance-test constants (backlog item 20, D5): scalars, not enums, so
    # they live in .extra like trial-validity's two thresholds below. Optional-file pattern
    # (unlike trial-validity.toml, which is mandatory) because today only
    # scripts/_noise_floor.py consumes them -- no other validator needs this file to exist.
    noise_floor_path = canon_dir / "noise-floor.toml"
    if noise_floor_path.exists():
        noise_floor_data = _load_toml(noise_floor_path)
        for key in ("alpha", "min_effect", "power_target", "multiple_comparison_method"):
            if key not in noise_floor_data:
                sys.stderr.write(f"error: canon file {noise_floor_path}: missing '{key}'\n")
                sys.exit(2)
            extra[f"noise_floor_{key}"] = noise_floor_data[key]
    # states.toml schema_version >= 2 (backlog item 12): declarative transition table + closed
    # guard vocabulary. Additive over the v1 `states` list, so older consumers are unaffected.
    extra["states_schema_version"] = states_data.get("schema_version", 1)
    extra["transition_guards"] = tuple(states_data.get("guards", ()))
    extra["transitions"] = states_data.get("transitions", {})
    # Trial-validity void-rule thresholds (backlog item 21, D4): scalars, not enums.
    extra["trial_validity_max_invalid_rate_per_arm"] = max_invalid_rate
    extra["trial_validity_max_between_arm_asymmetry"] = max_asymmetry

    return Canon(
        states=states,
        scorecard_dimensions=tuple(scorecard_labels),
        scorecard_dimension_labels=MappingProxyType(scorecard_labels),
        exhaustion_kinds=_require_list(exhaustion_data, "exhaustion_kinds", exhaustion_path),
        detection_modes=_require_list(exhaustion_data, "detection_modes", exhaustion_path),
        finding_families=_require_list(remediation_data, "finding_families", remediation_path),
        effort_levels=_require_list(remediation_data, "effort_levels", remediation_path),
        repair_revalidation_outcomes=_require_list(
            remediation_data, "repair_revalidation_outcomes", remediation_path
        ),
        invalid_reasons=_require_list(trial_data, "invalid_reasons", trial_path),
        validation_gates=MappingProxyType(gates_map),
        extra=MappingProxyType(extra),
        **simple,
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
