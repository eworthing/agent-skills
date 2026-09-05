#!/usr/bin/env python3
"""Self-test: check_required_artifacts rejects a valid-JSON-but-wrong-shape
REVIEW_HISTORY.json / findings_registry.json instead of returning it as-is.

Before this guard, `_load_json()` returning a list (valid JSON, wrong shape) for
these two files flowed through untyped as `dict | None`, and every downstream
`.get(...)` call (G16's registry.get("entries"), history.get(...)) raised
AttributeError instead of becoming a required-artifact Issue.

Run: python3 scripts/_required_artifacts_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _selftest_lib import load_validator as _load_validator


def main() -> int:
    va = _load_validator()
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="required-artifacts-selftest-") as td:
        artifact_dir = Path(td)
        (artifact_dir / "CURRENT_REVIEW.md").write_text("# review\n")
        (artifact_dir / "REVIEW_HISTORY.md").write_text("# history\n")
        (artifact_dir / "REVIEW_HISTORY.json").write_text(json.dumps([1, 2]))
        (artifact_dir / "findings_registry.json").write_text(json.dumps({"entries": []}))

        current_review = {"schema_version": 4}
        try:
            issues, history, _registry = va.check_required_artifacts(artifact_dir, current_review)
        except Exception as exc:
            failures.append(f"non-object REVIEW_HISTORY.json crashed: {exc!r}")
        else:
            if history is not None:
                failures.append(
                    f"non-dict REVIEW_HISTORY.json should normalize to None, got {history!r}"
                )
            if not any(
                i.rule == "required-artifact" and "REVIEW_HISTORY.json" in i.message for i in issues
            ):
                failures.append(
                    f"non-dict REVIEW_HISTORY.json did not fire a required-artifact Issue, got {issues}"
                )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: check_required_artifacts rejects non-object REVIEW_HISTORY.json/findings_registry.json"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
