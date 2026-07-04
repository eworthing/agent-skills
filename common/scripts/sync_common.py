#!/usr/bin/env python3
"""
sync_common.py — Vendor common/ into consumer skills' scripts/_common/.

Source of truth: common/common/ (this repo).
Vendored copies:   <skill>/scripts/_common/ (per consumer skill).

Three modes:
- Default: sync every consumer skill (any skill with an existing _common/).
- ``--skill <name>``: sync one specific consumer.
- ``--check``: verify every consumer's _common/ is byte-identical to the
  source tree AND has no extra files. Exit non-zero on any divergence.

The check mode is the gate run by pre-commit and CI. It catches:
- source-changed-without-resync (a file in source has no match or differs in vendored)
- direct-edit (a vendored file has changes the source doesn't have)
- extras (a vendored file/directory doesn't exist in source)

Usage:

    sync_common.py                # sync all consumers
    sync_common.py --skill quorum-review
    sync_common.py --check        # gate mode (exit non-zero on drift)
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = REPO_ROOT / "common" / "common"
VENDOR_RELPATH = Path("scripts") / "_common"


def find_consumer_skills(repo_root: Path) -> list[Path]:
    """Return every top-level directory under repo_root that has scripts/_common/."""
    out: list[Path] = []
    for child in sorted(repo_root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / VENDOR_RELPATH).is_dir():
            out.append(child)
    return out


def _iter_files(root: Path) -> list[Path]:
    """Return all regular files under root, sorted, as paths relative to root.

    Skips:
    - __pycache__ and .pyc       — Python runtime caches
    - VENDORED_FROM              — provenance marker written by sync_common.py
                                   itself, not part of the source tree

    Symlinks are rejected. A symlink under ``common/common/`` would be
    silently dereferenced by ``shutil.copytree`` (its default
    ``symlinks=False``), pulling content from outside the source tree
    into every consumer's vendor directory. Treat that as a sync error
    so a malicious or accidental symlink can't widen the blast radius
    of an edit (security review finding R2-B1).
    """
    files: list[Path] = []
    for p in root.rglob("*"):
        if p.is_symlink():
            raise SystemExit(
                f"error: symlink not allowed in source tree: {p}\n"
                "common/ must contain only regular files; remove the symlink "
                "and re-run sync_common.py."
            )
        if not p.is_file():
            continue
        if "__pycache__" in p.parts or p.suffix == ".pyc":
            continue
        if p.name == "VENDORED_FROM":
            continue
        files.append(p.relative_to(root))
    return sorted(files)


def check_skill(skill_dir: Path, source_dir: Path) -> list[str]:
    """Return a list of drift descriptions (empty list = clean)."""
    vendor_dir = skill_dir / VENDOR_RELPATH
    drifts: list[str] = []

    source_files = set(_iter_files(source_dir))
    vendor_files = set(_iter_files(vendor_dir))

    missing = source_files - vendor_files
    extras = vendor_files - source_files
    common = source_files & vendor_files

    for rel in sorted(missing):
        drifts.append(f"  MISSING in vendor: {rel}")
    for rel in sorted(extras):
        drifts.append(f"  EXTRA in vendor (not in source): {rel}")
    for rel in sorted(common):
        # filecmp.cmp(shallow=False) does a full byte comparison after
        # the cheap stat check fails. Identical files are fast; differing
        # files do one extra read.
        if not filecmp.cmp(source_dir / rel, vendor_dir / rel, shallow=False):
            drifts.append(f"  DIFFERS: {rel}")

    return drifts


def sync_skill(skill_dir: Path, source_dir: Path) -> None:
    """Replace skill's _common/ with an exact copy of source.

    Excludes __pycache__/.pyc so vendored trees don't accumulate runtime
    artifacts (which would also fail --check since the source doesn't
    have them either, depending on test-run timing).
    """
    vendor_dir = skill_dir / VENDOR_RELPATH
    if vendor_dir.exists():
        shutil.rmtree(vendor_dir)
    shutil.copytree(
        source_dir,
        vendor_dir,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    # Record provenance. The check ignores this file by name.
    (vendor_dir / "VENDORED_FROM").write_text(
        f"source: common/common (in {REPO_ROOT})\n"
        f"synced by: common/scripts/sync_common.py\n"
        f"do not edit this tree directly — edit common/common/ and re-run sync_common.py\n",
        encoding="utf-8",
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify vendored trees match source; exit non-zero on drift.",
    )
    parser.add_argument(
        "--skill", help="Limit to one consumer skill (directory name under the repo root)."
    )
    args = parser.parse_args(argv)

    if not SOURCE_DIR.is_dir():
        print(f"error: source not found: {SOURCE_DIR}", file=sys.stderr)
        return 2

    consumers = find_consumer_skills(REPO_ROOT)
    if args.skill:
        consumers = [c for c in consumers if c.name == args.skill]
        if not consumers:
            print(
                f"error: no consumer skill found with scripts/_common/ named {args.skill!r}",
                file=sys.stderr,
            )
            return 2

    if not consumers:
        # No consumers yet — that's fine for Phase A. The check is vacuously true.
        if args.check:
            print("sync_common: no consumer skills (no <skill>/scripts/_common/ found).")
            return 0
        print(
            "sync_common: no consumer skills to sync. Create <skill>/scripts/_common/ first, then re-run."
        )
        return 0

    if args.check:
        any_drift = False
        for skill in consumers:
            drifts = check_skill(skill, SOURCE_DIR)
            if drifts:
                any_drift = True
                print(f"DRIFT in {skill.name}/scripts/_common/:", file=sys.stderr)
                for d in drifts:
                    print(d, file=sys.stderr)
        if any_drift:
            print(
                "\nto resolve: re-run `python3 common/scripts/sync_common.py`, "
                "review the diff, and commit the regenerated _common/ tree.",
                file=sys.stderr,
            )
            return 1
        print(f"sync_common: clean — {len(consumers)} consumer(s) byte-identical to source.")
        return 0
    for skill in consumers:
        sync_skill(skill, SOURCE_DIR)
        print(f"synced: {skill.name}/scripts/_common/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
