"""ppr_launch.sh wrapper tests — flag pairing, exit-code capture, tee, warning.

The wrapper resolves SKILL_DIR from ${BASH_SOURCE[0]}, so the injection seam is
a temp skill dir: copied ppr_launch.sh + a stub run_review.py (records argv,
exits with a chosen code, optionally writes a session JSON) + copied
ppr_paths.py and the _common tree it imports. No env-var override needed.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent

STUB_RUNNER = '''#!/usr/bin/env python3
"""Stub run_review.py: records argv, emits output, exits per env."""
import json, os, sys

with open(os.environ["STUB_ARGV_FILE"], "w", encoding="utf-8") as fh:
    json.dump(sys.argv[1:], fh)
print("stub-stdout-line")
print("stub-stderr-line", file=sys.stderr)
args = sys.argv[1:]
if os.environ.get("STUB_WRITE_SESSION") and "--session-file" in args:
    session_file = args[args.index("--session-file") + 1]
    with open(session_file, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "resume_requested": True,
                "resume_attempted": False,
                "resume_reason": "no_session_id",
            },
            fh,
        )
sys.exit(int(os.environ.get("STUB_EXIT", "0")))
'''


class TestPprLaunch(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ppr-launch-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

        # Temp skill dir: scripts/{ppr_launch.sh, run_review.py(stub),
        # ppr_paths.py, _common/}
        skill = self.tmp / "skill"
        scripts = skill / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(SCRIPTS_DIR / "ppr_launch.sh", scripts / "ppr_launch.sh")
        shutil.copy2(SCRIPTS_DIR / "ppr_paths.py", scripts / "ppr_paths.py")
        shutil.copytree(SCRIPTS_DIR / "_common", scripts / "_common")
        stub = scripts / "run_review.py"
        stub.write_text(STUB_RUNNER, encoding="utf-8")
        stub.chmod(0o755)
        self.wrapper = scripts / "ppr_launch.sh"

        # Unique review id per test; canonical paths land in the real tmpdir,
        # so register cleanup for every ppr-<id>-* file.
        self.review_id = f"test{uuid.uuid4().hex[:12]}"
        self.tmpdir = Path(tempfile.gettempdir())
        self.addCleanup(self._cleanup_review_files)

        # The wrapper fails fast unless plan + prompt exist.
        (self.tmpdir / f"ppr-{self.review_id}-plan.md").write_text("plan\n")
        (self.tmpdir / f"ppr-{self.review_id}-prompt.md").write_text("prompt\n")

        self.argv_file = self.tmp / "stub-argv.json"

    def _cleanup_review_files(self):
        for p in self.tmpdir.glob(f"ppr-{self.review_id}-*"):
            p.unlink(missing_ok=True)

    def _run(self, *extra, env_overrides=None):
        env = os.environ.copy()
        env["STUB_ARGV_FILE"] = str(self.argv_file)
        env.update(env_overrides or {})
        return subprocess.run(
            ["bash", str(self.wrapper), "--review-id", self.review_id, *extra],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )

    def _stub_argv(self):
        return json.loads(self.argv_file.read_text(encoding="utf-8"))

    def _flag_value(self, argv, flag):
        self.assertIn(flag, argv)
        return argv[argv.index(flag) + 1]

    def test_full_flag_set_paired_and_exit_zero(self):
        result = self._run("--reviewer", "codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self._stub_argv()
        # The coupled pair can never be dropped.
        self.assertEqual(self._flag_value(argv, "--review-id"), self.review_id)
        self.assertIn("--error-log", argv)
        # Every canonical path flag present.
        for flag in (
            "--plan-file",
            "--prompt-file",
            "--output-file",
            "--session-file",
            "--events-file",
            "--codex-home-manifest",
            "--timeout",
        ):
            self.assertIn(flag, argv)
        # Omitted optionals are not forwarded (no empty values).
        self.assertNotIn("--model", argv)
        self.assertNotIn("--effort", argv)
        self.assertNotIn("--resume", argv)
        # Default timeout matches the runner's new default.
        self.assertEqual(self._flag_value(argv, "--timeout"), "1200")
        # exit.code file records the truth.
        exit_file = self.tmpdir / f"ppr-{self.review_id}-exit.code"
        self.assertEqual(exit_file.read_text().strip(), "0")

    def test_model_effort_resume_forwarded_when_supplied(self):
        result = self._run(
            "--reviewer", "codex", "--model", "gpt-5.5", "--effort", "high", "--resume"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self._stub_argv()
        self.assertEqual(self._flag_value(argv, "--model"), "gpt-5.5")
        self.assertEqual(self._flag_value(argv, "--effort"), "high")
        self.assertIn("--resume", argv)

    def test_unrecognized_flags_pass_through(self):
        result = self._run("--reviewer", "codex", "--summary-file", "/tmp/s.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = self._stub_argv()
        self.assertEqual(self._flag_value(argv, "--summary-file"), "/tmp/s.json")

    def test_nonzero_exit_propagates_through_tee(self):
        result = self._run("--reviewer", "codex", env_overrides={"STUB_EXIT": "7"})
        self.assertEqual(result.returncode, 7)
        exit_file = self.tmpdir / f"ppr-{self.review_id}-exit.code"
        self.assertEqual(exit_file.read_text().strip(), "7")

    def test_runner_log_tees_stdout_and_stderr(self):
        result = self._run("--reviewer", "codex")
        self.assertEqual(result.returncode, 0, result.stderr)
        log = (self.tmpdir / f"ppr-{self.review_id}-runner.log").read_text()
        self.assertIn("stub-stdout-line", log)
        self.assertIn("stub-stderr-line", log)

    def test_resume_degradation_warning_emitted(self):
        result = self._run(
            "--reviewer", "codex", "--resume", env_overrides={"STUB_WRITE_SESSION": "1"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = "WARNING: resume degraded to fresh exec (resume_reason=no_session_id)"
        self.assertIn(expected, result.stderr)
        log = (self.tmpdir / f"ppr-{self.review_id}-runner.log").read_text()
        self.assertIn(expected, log)

    def test_warning_never_masks_runner_exit(self):
        result = self._run(
            "--reviewer",
            "codex",
            "--resume",
            env_overrides={"STUB_WRITE_SESSION": "1", "STUB_EXIT": "3"},
        )
        self.assertEqual(result.returncode, 3)
        exit_file = self.tmpdir / f"ppr-{self.review_id}-exit.code"
        self.assertEqual(exit_file.read_text().strip(), "3")

    def test_missing_review_id_fails_fast(self):
        env = os.environ.copy()
        env["STUB_ARGV_FILE"] = str(self.argv_file)
        result = subprocess.run(
            ["bash", str(self.wrapper), "--reviewer", "codex"],
            capture_output=True,
            text=True,
            env=env,
            timeout=60,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("--review-id is required", result.stderr)

    def test_missing_plan_snapshot_fails_fast(self):
        (self.tmpdir / f"ppr-{self.review_id}-plan.md").unlink()
        result = self._run("--reviewer", "codex")
        self.assertEqual(result.returncode, 2)
        self.assertIn("plan snapshot missing", result.stderr)
        self.assertFalse(self.argv_file.exists())  # runner never invoked


if __name__ == "__main__":
    unittest.main()
