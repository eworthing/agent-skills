#!/usr/bin/env python3
"""Discovery runner — runs the split unittest suite under tests/. Entrypoint preserved
(`python3 scripts/test_run_review.py`). The test classes live in scripts/tests/test_*.py."""
import sys
import unittest
from pathlib import Path

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))

if __name__ == "__main__":
    suite = unittest.TestLoader().discover(
        str(here / "tests"), pattern="test_*.py", top_level_dir=str(here)
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
