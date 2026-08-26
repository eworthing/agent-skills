#!/usr/bin/env python3
"""Clustered's own bundled test suite (this variant).

Run directly: python3 test_clustered.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clustered import Clustered, plot_legend_labels

RECORDS = [
    {"team": "north", "x": 1},
    {"team": "north", "x": 3},
    {"team": "south", "x": 5},
]


def test_lanes_split_by_key() -> None:
    lanes = Clustered(RECORDS, key=lambda r: r["team"]).lanes("x")
    by_key = {lane.key: lane.values for lane in lanes}
    assert by_key == {"north": [1, 3], "south": [5]}, by_key


def test_plot_legend_labels_for_lanes() -> None:
    """Regression coverage carried over from the refactor: Lane legends
    still show the right key. (No equivalent Panel-legend test exists in
    this variant -- see CHANGES.md and grading.md.)"""
    lanes = Clustered(RECORDS, key=lambda r: r["team"]).lanes("x")
    labels = plot_legend_labels(lanes)
    assert labels == ["north", "south"], labels


def main() -> int:
    test_lanes_split_by_key()
    test_plot_legend_labels_for_lanes()
    print("OK: dedicated-path-incomplete test_clustered.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
