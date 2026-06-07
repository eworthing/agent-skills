#!/usr/bin/env python3
"""
ppr_paths.py — Thin CLI wrapper over the vendored canonical temp-path helper.

The implementation lives in the shared ``_common`` tree
(``_common/session/paths.py``, synced from /common/common/ via
sync_common.py). This wrapper preserves the historical
``python3 <skill-dir>/scripts/ppr_paths.py`` entry point used by SKILL.md
shell snippets so they keep working unchanged after the _common migration.
"""

import sys
from pathlib import Path

# _common/ is a sibling of this script (vendored from /common/common/).
sys.path.insert(0, str(Path(__file__).parent))

from _common.session.paths import main

if __name__ == "__main__":
    main()
