"""Make `import common` resolve when pytest runs from the package root."""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_ROOT = _REPO_ROOT / "common"
if str(_COMMON_ROOT) not in sys.path:
    sys.path.insert(0, str(_COMMON_ROOT))
