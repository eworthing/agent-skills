#!/usr/bin/env python3
"""Hidden oracle battery for pandas-groupby-plot-imperfect-gold. Grader-only:
never shown to a candidate (listed in provenance.json's grader_only_files).

Imports each variant's `clustered.py` fresh by file path (every variant
reuses the same module name, so plain `import clustered` would collide) and
runs the four oracles declared in provenance.json's `hidden_oracles`:

    series_group_label_present  -- single-column (Lane) groups get a legend
                                    label. Should hold everywhere -- the
                                    control that proves the residual below is
                                    specific to the other group shape.
    frame_group_label_present   -- multi-column (Panel) groups get a legend
                                    label. THE RESIDUAL ORACLE: the accepted,
                                    merged variant (dedicated-path-incomplete)
                                    is expected to FAIL this. That is the
                                    pack's imperfect-gold point, not a bug in
                                    the oracle.
    no_side_effect_pinning      -- plotting must not mutate a group object
                                    with a `.label` attribute as a side
                                    effect of being plotted.
    legend_labels_correct       -- a present legend label must equal the
                                    group's own key, never its position in
                                    the sequence passed to the plotting path.

Run: python3 oracles.py
Exit 0 iff every observed result matches its declared expectation.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent
VARIANTS = [
    "side-effect-pinning",
    "dedicated-path-incomplete",
    "key-forwarded",
    "near-miss-restore-pinning",
    "mutant-mislabeled-groups",
]

RECORDS = [
    {"team": "north", "x": 1, "y": 2},
    {"team": "north", "x": 3, "y": 4},
    {"team": "south", "x": 5, "y": 6},
    {"team": "south", "x": 7, "y": 8},
]


def load_variant(name: str) -> types.ModuleType:
    path = PACK_DIR / name / "clustered.py"
    spec = importlib.util.spec_from_file_location(f"_gc_clustered_{name.replace('-', '_')}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lanes(module: types.ModuleType) -> list:
    return module.Clustered(RECORDS, key=lambda r: r["team"]).lanes("x")


def _panels(module: types.ModuleType) -> list:
    return module.Clustered(RECORDS, key=lambda r: r["team"]).panels(["x", "y"])


def series_group_label_present(modules: dict[str, types.ModuleType]) -> dict[str, bool]:
    results = {}
    for name, module in modules.items():
        labels = module.plot_legend_labels(_lanes(module))
        results[name] = all(label is not None for label in labels)
    return results


def frame_group_label_present(modules: dict[str, types.ModuleType]) -> dict[str, bool]:
    results = {}
    for name, module in modules.items():
        labels = module.plot_legend_labels(_panels(module))
        results[name] = all(label is not None for label in labels)
    return results


def no_side_effect_pinning(modules: dict[str, types.ModuleType]) -> dict[str, bool]:
    results = {}
    for name, module in modules.items():
        groups = _lanes(module) + _panels(module)
        module.plot_legend_labels(groups)
        results[name] = not any(hasattr(g, "label") for g in groups)
    return results


def legend_labels_correct(modules: dict[str, types.ModuleType]) -> dict[str, bool]:
    """A present label must equal its group's own key. Absent (None) labels
    are skipped here -- that is frame_group_label_present's job to catch;
    this oracle is about labels that ARE present but wrong."""
    results = {}
    for name, module in modules.items():
        ok = True
        for groups in (_lanes(module), _panels(module)):
            labels = module.plot_legend_labels(groups)
            for group, label in zip(groups, labels, strict=True):
                if label is not None and label != group.key:
                    ok = False
        results[name] = ok
    return results


def main() -> int:
    modules = {name: load_variant(name) for name in VARIANTS}

    series = series_group_label_present(modules)
    frame = frame_group_label_present(modules)
    pinning = no_side_effect_pinning(modules)
    correct = legend_labels_correct(modules)

    print("=== series_group_label_present ===")
    for name, ok in series.items():
        print(f"  {name}: {'present' if ok else 'MISSING'}")
    print("=== frame_group_label_present ===")
    for name, ok in frame.items():
        print(f"  {name}: {'present' if ok else 'MISSING'}")
    print("=== no_side_effect_pinning ===")
    for name, ok in pinning.items():
        print(f"  {name}: {'clean' if ok else 'MUTATED'}")
    print("=== legend_labels_correct ===")
    for name, ok in correct.items():
        print(f"  {name}: {'correct' if ok else 'WRONG'}")

    failures = []

    # series_group_label_present: expected True everywhere (the control).
    for name, ok in series.items():
        if not ok:
            failures.append(f"{name}: series_group_label_present must be present, got missing")

    # frame_group_label_present: expected False ONLY for the accepted,
    # imperfect-gold variant -- that is this pack's whole point.
    expected_frame = {
        "side-effect-pinning": True,
        "dedicated-path-incomplete": False,
        "key-forwarded": True,
        "near-miss-restore-pinning": True,
        "mutant-mislabeled-groups": True,
    }
    for name, expected in expected_frame.items():
        if frame.get(name) != expected:
            failures.append(
                f"{name}: expected frame_group_label_present={expected}, got {frame.get(name)}"
            )

    # no_side_effect_pinning: expected to FAIL (mutation observed) in both
    # variants that pin a label onto a group as a side effect.
    expected_pinning = {
        "side-effect-pinning": False,
        "dedicated-path-incomplete": True,
        "key-forwarded": True,
        "near-miss-restore-pinning": False,
        "mutant-mislabeled-groups": True,
    }
    for name, expected in expected_pinning.items():
        if pinning.get(name) != expected:
            failures.append(
                f"{name}: expected no_side_effect_pinning={expected}, got {pinning.get(name)}"
            )

    # legend_labels_correct: expected to FAIL only for the mutant (wrong,
    # not missing, labels).
    expected_correct = {
        "side-effect-pinning": True,
        "dedicated-path-incomplete": True,
        "key-forwarded": True,
        "near-miss-restore-pinning": True,
        "mutant-mislabeled-groups": False,
    }
    for name, expected in expected_correct.items():
        if correct.get(name) != expected:
            failures.append(
                f"{name}: expected legend_labels_correct={expected}, got {correct.get(name)}"
            )

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK: observed matrix matches declared expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
