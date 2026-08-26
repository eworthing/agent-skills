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


def test_plot_legend_labels_are_present() -> None:
    """Weak by construction: only checks a label was produced, never that
    it is the right one. That gap is exactly why this variant's own suite
    passes despite every legend label being wrong (see oracles.py's
    legend_labels_correct)."""
    lanes = Clustered(RECORDS, key=lambda r: r["team"]).lanes("x")
    labels = plot_legend_labels(lanes)
    assert all(label is not None for label in labels), labels


def main() -> int:
    test_plot_legend_labels_are_present()
    print("OK: mutant-mislabeled-groups test_clustered.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
