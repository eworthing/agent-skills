"""Shared loader for contest-refactor selftests.

D2 finding: 14+ selftest files independently retyped the same five-line
importlib.util incantation to load a sibling validator script (usually
validate-artifact.py) as a throwaway module, so its functions could be
called directly without a package install. It's boilerplate, not a
contract worth re-deriving per file -- one copy anyone can import beats
14 copies anyone could get wrong. The `failures:`-list assertion epilogue
that follows each load is real test content and stays at each call site;
only the load itself lives here.

The loaded module is never registered in sys.modules (spec_from_file_location
+ module_from_spec + exec_module skips that step on purpose, so parallel
selftests loading the same script don't collide), so the name passed to
spec_from_file_location only ever shows up in tracebacks.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def load_validator(filename: str = "validate-artifact.py"):
    """Load a sibling script in this directory (scripts/) as a fresh module.

    Most selftests validate validate-artifact.py (the default); pass
    filename= to load a different sibling, e.g. "validate-repo.py".
    """
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(f"_selftest_{path.stem.replace('-', '_')}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
