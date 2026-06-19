#!/usr/bin/env python3
"""
qr_paths.py — Thin CLI wrapper around the vendored ``_common.session.paths``.

Kept so quorum-review's SKILL.md has a stable entrypoint for terminal cleanup
of per-run Codex homes (manifest + session files) once a review concludes:

    python3 <skill-dir>/scripts/qr_paths.py --cleanup --id-prefix "qr-<quorum_id>"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _common.session.paths import main  # noqa: F401 — re-exported for callers

if __name__ == "__main__":
    main()
