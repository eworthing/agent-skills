#!/usr/bin/env python3
"""
test_run_review.py — Deterministic test suite for run_review.py.

Tier 1: Local tests that exercise pure script logic (no external CLIs).
Tier 2: Optional self-checks for installed provider CLIs.

Run:  python3 scripts/test_run_review.py
"""

import argparse
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# Resolve paths relative to this test file
SCRIPT_DIR = str(Path(__file__).resolve().parent.parent)  # scripts/ (this file is scripts/tests/_helpers.py)
SCRIPT = str(Path(SCRIPT_DIR) / "run_review.py")
PATHS_SCRIPT = str(Path(SCRIPT_DIR) / "ppr_paths.py")
FIXTURES_DIR = str(Path(SCRIPT_DIR) / "fixtures")

# Import functions from run_review for direct unit tests
sys.path.insert(0, SCRIPT_DIR)
import run_review  # noqa: E402
from _common.session import parse_structured_review  # noqa: E402
from run_review import extract_metadata, extract_text_from_output, self_check  # noqa: E402


def run_script(*extra_args):
    """Run run_review.py as subprocess, return (returncode, stdout, stderr)."""
    cmd = [sys.executable, SCRIPT, *list(extra_args)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


def run_paths_script(*extra_args, env=None):
    """Run ppr_paths.py as subprocess, return (returncode, stdout, stderr)."""
    cmd = [sys.executable, PATHS_SCRIPT, *list(extra_args)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def make_args(**overrides):
    """Create a Namespace matching run_review.py argument names."""
    data = {
        "reviewer": "claude",
        "plan_file": None,
        "prompt_file": None,
        "output_file": None,
        "session_file": None,
        "events_file": None,
        "model": None,
        "effort": None,
        "resume": False,
        "timeout": 600,
        "self_check": False,
        "list_models": False,
        "error_log": None,
        "review_id": None,
        "summary_file": None,
    }
    data.update(overrides)
    return argparse.Namespace(**data)



_CREATE_NEW_PROCESS_GROUP = 0x00000200  # Windows constant sentinel for testing

from _common.session import probe_writable, validate_prompt_file  # noqa: E402
from _common.log import EventLogger  # noqa: E402
from _common.metadata.extractors import compute_plan_metadata  # noqa: E402
from _common.providers import PROVIDERS  # noqa: E402
