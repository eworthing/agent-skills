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
    {"team": "north", "x": 1, "y": 2},
    {"team": "north", "x": 3, "y": 4},
    {"team": "south", "x": 5, "y": 6},
]


def test_plot_legend_labels_for_lanes() -> None:
    lanes = Clustered(RECORDS, key=lambda r: r["team"]).lanes("x")
    labels = plot_legend_labels(lanes)
    assert labels == ["north", "south"], labels


def test_plot_legend_labels_for_panels() -> None:
    """The legend works again -- this suite has no test for whether the
    group objects themselves were mutated to make it work."""
    panels = Clustered(RECORDS, key=lambda r: r["team"]).panels(["x", "y"])
    labels = plot_legend_labels(panels)
    assert labels == ["north", "south"], labels


def main() -> int:
    test_plot_legend_labels_for_lanes()
    test_plot_legend_labels_for_panels()
    print("OK: test_clustered.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
