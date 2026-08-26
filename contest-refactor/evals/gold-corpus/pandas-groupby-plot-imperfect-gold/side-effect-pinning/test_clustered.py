#!/usr/bin/env python3
"""Clustered's own bundled test suite (this variant).

Run directly: python3 test_clustered.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clustered import Clustered, apply_general, plot_legend_labels

RECORDS = [
    {"team": "north", "x": 1},
    {"team": "north", "x": 3},
    {"team": "south", "x": 5},
]


def test_lanes_split_by_key() -> None:
    lanes = Clustered(RECORDS, key=lambda r: r["team"]).lanes("x")
    by_key = {lane.key: lane.values for lane in lanes}
    assert by_key == {"north": [1, 3], "south": [5]}, by_key


def test_apply_general_pins_label_for_aggregation() -> None:
    lanes = Clustered(RECORDS, key=lambda r: r["team"]).lanes("x")
    totals = apply_general(lanes, lambda lane: (lane.label, sum(lane.values)))
    assert totals == [("north", 4), ("south", 5)], totals


def test_plot_legend_labels_uses_pinned_key() -> None:
    lanes = Clustered(RECORDS, key=lambda r: r["team"]).lanes("x")
    labels = plot_legend_labels(lanes)
    assert labels == ["north", "south"], labels


def main() -> int:
    test_lanes_split_by_key()
    test_apply_general_pins_label_for_aggregation()
    test_plot_legend_labels_uses_pinned_key()
    print("OK: test_clustered.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
