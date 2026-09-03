#!/usr/bin/env python3
"""Selftest for evals/ocr-corpus/run_corpus.py (OCR-GAP-REMEDIATION-PLAN-2026-09-03,
wave W0). Run directly; exit 0 = pass.

Guards: the frozen manifest's schema and `fid` uniqueness; that every target
path resolves at `pre_fix_rev` when `BENCHHYPE_ROOT` is reachable (a clean,
non-failing skip otherwise); the runner's five result states
(`skipped_missing_root`, `skipped_missing_revision`, `invalid_coverage`,
`passed`, `failed`) and `--assert`'s exit-code contract for each; and that the
clean-swift restraint corpus is internally well-formed (no empty file, every
declared name shows up more than once in the folder).

Revision- and coverage-dependent cases run against a disposable local git
fixture repo, never against BenchHype/Tiercade -- those stay run-gated on
their own env vars, per the plan's "a missing root is a typed skip" rule.
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS_DIR = HERE.parent / "evals" / "ocr-corpus"
sys.path.insert(0, str(CORPUS_DIR))
import run_corpus as RC

MANIFEST_PATH = CORPUS_DIR / "benchhype-domain-2026-09.json"
TIERCADE_MANIFEST_PATH = CORPUS_DIR / "tiercade-restraint.json"
CLEAN_SWIFT_DIR = CORPUS_DIR / "clean-swift"

# Type declarations can start at column 0; member declarations (func/case/
# var/let) must be indented -- a column-0 func is a free top-level function,
# which the real dead-surface scan's v1 declaration scope excludes (only
# type-member declarations are candidates). Matches `summarizeDiagnostics` in
# Diagnostics.swift being exempt from the "referenced elsewhere" check below.
_TYPE_DECL_RE = re.compile(
    r"^\s*(?:public\s+|private\s+)*(?:struct|enum|protocol)\s+(?P<name>[A-Za-z_]\w*)",
    re.MULTILINE,
)
_MEMBER_DECL_RE = re.compile(
    r"^[ \t]+(?:public\s+|private\s+|static\s+)*(?:func|case|var|let)\s+(?P<name>[A-Za-z_]\w*)",
    re.MULTILINE,
)

STUB_SCRIPT = """#!/usr/bin/env python3
import argparse, json, os, sys

parser = argparse.ArgumentParser()
parser.add_argument("repo_root")
parser.add_argument("--json", action="store_true")
parser.add_argument("--scope")
parser.add_argument("--experimental-invariant-queue", action="store_true")
parser.add_argument("--invariant-json")
args = parser.parse_args()

fixture = json.loads(os.environ["RUN_CORPUS_STUB_FIXTURE"])
doc = {
    "status": fixture["status"],
    "coverage": fixture.get("coverage", {}),
    "rows": fixture.get("rows", []),
}
print(json.dumps(doc))
if args.invariant_json:
    with open(args.invariant_json, "w") as fh:
        json.dump({"candidates": fixture.get("candidates", [])}, fh)
sys.exit(0)
"""


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


def test_manifest_schema_and_fid_uniqueness() -> None:
    m = _load_manifest()
    for key in (
        "repo_env",
        "pre_fix_rev",
        "post_fix_rev",
        "scope",
        "targets",
        "excluded_targets",
        "must_stay_silent",
    ):
        assert key in m, f"manifest missing '{key}'"
    assert m["repo_env"] == "BENCHHYPE_ROOT"

    v_targets = [t for t in m["targets"] if t["class"] == "V"]
    z_targets = [t for t in m["targets"] if t["class"] == "Z"]
    assert len(v_targets) == 10, f"expected 10 V targets, got {len(v_targets)}"
    assert len(z_targets) == 10, f"expected 10 Z targets, got {len(z_targets)}"
    for t in v_targets:
        assert t["detector"] == "invariant", t
        assert t["line_start"] > 0 and t["line_end"] >= t["line_start"], t
    for t in z_targets:
        assert t["detector"] == "dead_surface", t
        assert t["kind"] in ("enum_case", "protocol_requirement", "declaration"), t
        assert "type_name" in t and "name" in t, t

    assert len(m["excluded_targets"]) == 2, m["excluded_targets"]
    assert len(m["must_stay_silent"]) == 4, m["must_stay_silent"]
    for s in m["must_stay_silent"]:
        assert s["detector"] == "invariant", s
        assert "symbol" in s and "path" in s, s

    all_fids = (
        [t["fid"] for t in m["targets"]]
        + [t["fid"] for t in m["excluded_targets"]]
        + [t["fid"] for t in m["must_stay_silent"]]
    )
    assert len(all_fids) == len(set(all_fids)), f"duplicate fid across sections: {all_fids}"


SETTINGS_MANIFEST_PATH = CORPUS_DIR / "benchhype-settings-2026-09.json"
_QUESTION_IDS = {f"Q{i}" for i in range(1, 9)}


def _check_sites(m: dict, expect_real: int, expect_rejected: int) -> None:
    sites = m["sites"]
    fids = [s["fid"] for s in sites]
    assert len(fids) == len(set(fids)), "duplicate fid in sites"
    for s in sites:
        assert s["verdict"] in ("real", "rejected"), s
        assert isinstance(s["path"], str) and s["path"].endswith(".swift"), s
        assert 0 < s["line_start"] <= s["line_end"], s
        assert isinstance(s["claim"], str) and s["claim"], s
        assert s["question"] is None or s["question"] in _QUESTION_IDS, s
    counts = {v: sum(1 for s in sites if s["verdict"] == v) for v in ("real", "rejected")}
    assert counts == {"real": expect_real, "rejected": expect_rejected}, counts


def test_site_manifests_schema() -> None:
    """SITE-PASS plan W0: `sites[]` shape on both corpora; counts pinned to the validated scans."""
    _check_sites(_load_manifest(), 157, 126)
    sm = json.loads(SETTINGS_MANIFEST_PATH.read_text())
    assert sm["repo_env"] == "BENCHHYPE_ROOT" and sm["pre_fix_rev"] == "909164fb", sm["pre_fix_rev"]
    assert sm["scope"] == "BenchHypeKit/Sources/BenchHypeSettingsFeature"
    assert sm["targets"] == [] and sm["must_stay_silent"] == []
    _check_sites(sm, 29, 10)
    assert all(s["path"].startswith(sm["scope"] + "/") for s in sm["sites"])


def test_tiercade_manifest_shape() -> None:
    m = json.loads(TIERCADE_MANIFEST_PATH.read_text())
    assert m == {"repo_env": "TIERCADE_ROOT", "rev": "92e2347", "scope": "."}, m


def test_target_paths_exist_at_pre_fix_rev() -> None:
    root = os.environ.get("BENCHHYPE_ROOT")
    if not root or not Path(root).is_dir():
        print("SKIP test_target_paths_exist_at_pre_fix_rev: BENCHHYPE_ROOT not set")
        return
    m = _load_manifest()
    rev = m["pre_fix_rev"]
    for t in m["targets"]:
        check = subprocess.run(
            ["git", "-C", root, "cat-file", "-e", f"{rev}:{t['path']}"],
            capture_output=True,
        )
        assert check.returncode == 0, f"fid {t['fid']}: {t['path']} missing at {rev}"


def _run_main(argv: list[str]) -> tuple[int, dict]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = RC.main(argv)
    return code, json.loads(buf.getvalue())


def test_skipped_missing_root() -> None:
    backup = os.environ.pop("BENCHHYPE_ROOT", None)
    try:
        code, result = _run_main(
            [
                "--detector",
                "invariant",
                "--manifest",
                str(MANIFEST_PATH),
                "--rev",
                "pre",
                "--assert",
            ]
        )
        assert result["status"] == "skipped_missing_root", result
        assert code == 0, code
    finally:
        if backup is not None:
            os.environ["BENCHHYPE_ROOT"] = backup


def _make_fixture_repo() -> tuple[Path, str]:
    d = Path(tempfile.mkdtemp(prefix="run-corpus-selftest-repo-"))
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(d), "config", "user.name", "test"], check=True)
    (d / "Placeholder.swift").write_text("public enum Placeholder {}\n")
    subprocess.run(["git", "-C", str(d), "add", "."], check=True)
    subprocess.run(["git", "-C", str(d), "commit", "-q", "-m", "init"], check=True)
    sha = subprocess.run(
        ["git", "-C", str(d), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    return d, sha


def test_skipped_missing_revision() -> None:
    repo, _sha = _make_fixture_repo()
    manifest = {
        "repo_env": "RUN_CORPUS_SELFTEST_ROOT",
        "pre_fix_rev": "0000000000000000000000000000000000zzzz",
        "post_fix_rev": "0000000000000000000000000000000000zzzz",
        "scope": ".",
        "targets": [],
        "excluded_targets": [],
        "must_stay_silent": [],
    }
    manifest_path = repo.parent / "bogus-rev-manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    os.environ["RUN_CORPUS_SELFTEST_ROOT"] = str(repo)
    try:
        code, result = _run_main(
            [
                "--detector",
                "invariant",
                "--manifest",
                str(manifest_path),
                "--rev",
                "pre",
                "--assert",
            ]
        )
        assert result["status"] == "skipped_missing_revision", result
        assert code == 0, code
    finally:
        del os.environ["RUN_CORPUS_SELFTEST_ROOT"]


def _make_stub_scripts_dir() -> Path:
    d = Path(tempfile.mkdtemp(prefix="run-corpus-selftest-scripts-"))
    for name in ("audit_hotspots.py", "audit_dead_surface.py"):
        (d / name).write_text(STUB_SCRIPT)
    return d


def _run_stubbed(
    detector: str, fixture: dict, extra_manifest: dict | None = None
) -> tuple[int, dict]:
    repo, sha = _make_fixture_repo()
    stub_dir = _make_stub_scripts_dir()
    manifest = {
        "repo_env": "RUN_CORPUS_SELFTEST_ROOT",
        "pre_fix_rev": sha,
        "post_fix_rev": sha,
        "scope": ".",
        "targets": [],
        "excluded_targets": [],
        "must_stay_silent": [],
    }
    if extra_manifest:
        manifest.update(extra_manifest)
    manifest_path = repo.parent / "stub-manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    os.environ["RUN_CORPUS_SELFTEST_ROOT"] = str(repo)
    os.environ["RUN_CORPUS_STUB_FIXTURE"] = json.dumps(fixture)
    original_scripts_dir = RC.SCRIPTS_DIR
    RC.SCRIPTS_DIR = stub_dir
    try:
        return _run_main(
            [
                "--detector",
                detector,
                "--manifest",
                str(manifest_path),
                "--rev",
                "pre",
                "--assert",
            ]
        )
    finally:
        RC.SCRIPTS_DIR = original_scripts_dir
        del os.environ["RUN_CORPUS_SELFTEST_ROOT"]
        del os.environ["RUN_CORPUS_STUB_FIXTURE"]


def test_stubbed_partial_maps_to_invalid_coverage() -> None:
    for detector in ("invariant", "dead_surface"):
        code, result = _run_stubbed(detector, {"status": "partial"})
        assert result["status"] == "invalid_coverage", (detector, result)
        assert code == 1, (detector, code)


def test_assert_exit_codes_passed_and_failed() -> None:
    candidate = {
        "path": "Placeholder.swift",
        "symbol": "Placeholder.thing",
        "start_line": 1,
        "end_line": 1,
        "candidate_queues": ["invariant"],
    }
    target_manifest = {
        "targets": [
            {
                "fid": 1,
                "class": "V",
                "detector": "invariant",
                "signal": "one_sided_guard",
                "path": "Placeholder.swift",
                "symbol": "Placeholder.thing",
                "line_start": 1,
                "line_end": 1,
            }
        ],
        "must_stay_silent": [],
    }
    code, result = _run_stubbed(
        "invariant", {"status": "ok", "candidates": [candidate]}, target_manifest
    )
    assert result["status"] == "passed", result
    assert result["hits"] == [1], result
    assert code == 0, code

    silent_manifest = {
        "targets": [],
        "must_stay_silent": [
            {
                "fid": 999,
                "detector": "invariant",
                "path": "Placeholder.swift",
                "symbol": "Placeholder.thing",
            }
        ],
    }
    code, result = _run_stubbed(
        "invariant", {"status": "ok", "candidates": [candidate]}, silent_manifest
    )
    assert result["status"] == "failed", result
    assert result["flagged_silent"] == [999], result
    assert code == 1, code


def test_clean_corpus_parses() -> None:
    swift_files = sorted(CLEAN_SWIFT_DIR.glob("*.swift"))
    assert len(swift_files) == 10, f"expected 10 clean-swift files, found {len(swift_files)}"
    assert (CLEAN_SWIFT_DIR / "README.md").is_file(), "clean-swift/README.md missing"

    texts = {f.name: f.read_text() for f in swift_files}
    joined = "\n".join(texts.values())
    for name, text in texts.items():
        assert text.strip(), f"{name} is empty"
        matches = list(_TYPE_DECL_RE.finditer(text)) + list(_MEMBER_DECL_RE.finditer(text))
        for match in matches:
            decl_name = match.group("name")
            count = len(re.findall(rf"\b{re.escape(decl_name)}\b", joined))
            assert count >= 2, f"{name}: '{decl_name}' looks unreferenced ({count} occurrence(s))"


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print(f"PASS {_name}")
    print("run_corpus (_ocr_corpus) selftest: OK")
