#!/usr/bin/env python3
"""
ppr_paths.py — Canonical temp-path helper for peer-plan-review sessions.

Thin CLI wrapper around the vendored ``_common.session.paths`` module
(synced from /common/common/ via sync_common.py). Kept so the host-side
shell snippet in SKILL.md has a stable entrypoint:

    eval "$(python3 <skill-dir>/scripts/ppr_paths.py --review-id <id> --format shell)"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _common.session.paths import (
    build_paths,
    load_review_id,
    main,
    render_shell,
)

if __name__ == "__main__":
    main()
