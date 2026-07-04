#!/usr/bin/env python3
"""
test_run_quorum.py — Deterministic test suite for run_quorum.py (v3).

Tier 1: Local tests that exercise orchestrator logic (no external CLIs).

Run:  python3 scripts/test_run_quorum.py
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Resolve paths relative to this test file
SCRIPT_DIR = str(
    Path(__file__).resolve().parent.parent
)  # scripts/ (this file is scripts/tests/_helpers.py)
SCRIPT = str(Path(SCRIPT_DIR) / "run_quorum.py")

# Import functions for direct unit tests
sys.path.insert(0, SCRIPT_DIR)
import run_quorum
import run_review
from run_quorum import (
    CROSS_CRITIQUE_INSTRUCTIONS,
    EXIT_APPROVED,
    EXIT_INDETERMINATE,
    EXIT_REVISE,
    MAX_ROUNDS_LIMIT,
    MIN_QUORUM_SIZE,
    REVIEW_CONTRACT_V2,
    _extract_section,
    _is_unanimous,
    _make_issue,
    _role_for_mode,
    apply_merge_pipeline,
    build_issue_ledger,
    classify_merge_candidate,
    compile_compressed_context,
    compile_deliberation,
    derive_verdict,
    format_issue_consensus,
    format_ledger_summary,
    generate_merge_candidates,
    generate_verification_prompts,
    load_ledger,
    load_review_md,
    parse_args,
    parse_cross_critique,
    parse_reviewer_spec,
    parse_structured_review,
    parse_verdict,
    parse_verification_response,
    save_ledger,
    should_exit_early,
    tally_verdicts,
    validate_panel,
    write_cross_critique_prompt,
    write_deliberation_prompt,
    write_initial_prompt,
)


def run_script(*extra_args):
    """Run run_quorum.py as subprocess, return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SCRIPT, *list(extra_args)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def make_issue(
    issue_id,
    summary,
    *,
    severity="blocking",
    status="open",
    support_count=1,
    dispute_count=0,
    verification_status="pending",
    anchor=None,
):
    """Build a v3-style issue record for tests."""
    issue = run_quorum._make_issue(
        issue_id,
        severity,
        1,
        1,
        issue_id,
        summary,
        anchor=anchor,
    )
    issue["status"] = status
    issue["adjudication"]["status"] = status
    issue["adjudication"]["proposed_by"] = [1]
    issue["adjudication"]["endorsed_by"] = list(range(2, support_count + 1))
    issue["adjudication"]["refined_by"] = []
    issue["adjudication"]["disputed_by"] = list(range(100, 100 + dispute_count))
    if status == "invalidated_by_verifier" and verification_status == "pending":
        verification_status = "invalidated"
    issue["verification"]["status"] = verification_status
    if verification_status == "invalidated":
        issue["status"] = "invalidated_by_verifier"
        issue["adjudication"]["status"] = "invalidated_by_verifier"
    return run_quorum._sync_issue_aliases(issue)


# Re-export EVERYTHING (including single-underscore helpers like _role_for_mode,
# _extract_section, _is_unanimous, _make_issue) so `from ._helpers import *` in the
# split test modules carries them — `import *` otherwise drops names starting with "_".
__all__ = [n for n in dir() if not n.startswith("__")]
