"""Tests for common/scripts/eval_guard.py (repo-wide eval-guard gate).

eval_guard.py is a standalone checker script (like sync_common.py /
check_module_size.py), not part of the common.common package, so it is
imported the same way check_shim_contract.py imports its own targets:
by inserting common/scripts/ onto sys.path.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import eval_guard


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _git_out(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _write(repo: Path, rel: str, text: str) -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "test@example.com")
    _git(r, "config", "user.name", "Test")
    _write(r, ".gitkeep", "")
    _git(r, "add", ".")
    _git(r, "commit", "-q", "-m", "init")
    return r


SKILL_MD_V1 = """---
name: demo-skill
description: Demo skill. Use when testing eval-guard.
---

# demo-skill

Original prose body.
"""


class TestFrontmatterAndWhitespaceExemptions:
    def test_frontmatter_only_change_passes(self, repo):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace(
            "description: Demo skill. Use when testing eval-guard.",
            "description: Demo skill, retitled. Use when testing eval-guard.",
        )
        _write(repo, "demo-skill/SKILL.md", v2)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "bump frontmatter")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_PASS

    def test_whitespace_only_change_passes(self, repo):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace("Original prose body.\n", "Original   prose   body.\n\n\n")
        _write(repo, "demo-skill/SKILL.md", v2)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "reflow whitespace")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_PASS


class TestEvalTouchGate:
    def test_substantive_without_eval_touch_flagged(self, repo, capsys):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace(
            "Original prose body.", "Completely new guidance replaces the old body."
        )
        _write(repo, "demo-skill/SKILL.md", v2)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "rewrite guidance")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_FAIL
        out = capsys.readouterr()
        assert "demo-skill" in out.err
        assert "MISSING eval/test touch" in out.err

    def test_report_only_default_downgrades_to_pass(self, repo, capsys):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New guidance, no --enforce this time.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "rewrite guidance")
        head = _git_out(repo, "rev-parse", "HEAD")

        # No --enforce: relies on the module's REPORT_ONLY = True default.
        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo)])
        assert rc == eval_guard.EXIT_PASS
        out = capsys.readouterr()
        assert "REPORT-ONLY" in out.err

    def test_substantive_with_eval_touch_passes(self, repo):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _write(repo, "demo-skill/evals/case1.md", "case v1")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill + evals")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New behavior description entirely.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _write(repo, "demo-skill/evals/case1.md", "case v2, updated for the new behavior")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "rewrite guidance + update eval")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_PASS

    def test_substantive_with_selftest_touch_passes(self, repo):
        # This repo's convention: a scripts/_*selftest*.py guard counts, same as evals/.
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _write(repo, "demo-skill/scripts/_case_selftest.py", "def main(): pass\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill + selftest")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New behavior via the selftest guard.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _write(repo, "demo-skill/scripts/_case_selftest.py", "def main(): assert True\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "rewrite guidance + update selftest")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_PASS

    def test_substantive_with_unrelated_scripts_file_flagged(self, repo, capsys):
        # A scripts/ file that isn't a selftest doesn't satisfy the gate.
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _write(repo, "demo-skill/scripts/helper.py", "print('hi')\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill + helper script")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New behavior, unrelated script touched.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _write(repo, "demo-skill/scripts/helper.py", "print('hi again')\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "rewrite guidance + tweak helper")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_FAIL
        out = capsys.readouterr()
        assert "MISSING eval/test touch" in out.err

    def test_substantive_with_tests_dir_touch_passes(self, repo):
        # Some skills use tests/ instead of evals/ — either counts.
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _write(repo, "demo-skill/tests/test_case.py", "def test_v1(): pass\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill + tests")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New behavior via the tests/ convention.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _write(repo, "demo-skill/tests/test_case.py", "def test_v2(): pass\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "rewrite guidance + update test")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_PASS


class TestWaiverTrailer:
    def test_valid_waiver_trailer_passes_and_is_recorded(self, repo, capsys):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New behavior with no eval yet.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _git(repo, "add", ".")
        _git(
            repo,
            "commit",
            "-q",
            "-m",
            "rewrite guidance\n\nEval-waiver: pending follow-up ticket AB-123",
        )
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        out = capsys.readouterr()
        assert rc == eval_guard.EXIT_PASS
        assert "Eval-waiver: pending follow-up ticket AB-123" in out.out

    def test_malformed_waiver_trailer_flagged(self, repo, capsys):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")
        base = _git_out(repo, "rev-parse", "HEAD")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New behavior with an empty waiver.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "rewrite guidance\n\nEval-waiver:")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_FAIL
        out = capsys.readouterr()
        assert "malformed waiver trailer" in out.err


class TestRenameAndDeletion:
    def test_pure_rename_no_content_change_passes(self, repo):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _write(
            repo,
            "demo-skill/references/old-name.md",
            "---\ntitle: x\n---\n\nSame content throughout.\n",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill + reference")
        base = _git_out(repo, "rev-parse", "HEAD")

        _git(repo, "mv", "demo-skill/references/old-name.md", "demo-skill/references/new-name.md")
        _git(repo, "commit", "-q", "-m", "rename reference doc")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_PASS

    def test_deletion_without_eval_touch_flagged(self, repo, capsys):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")
        base = _git_out(repo, "rev-parse", "HEAD")

        _git(repo, "rm", "-q", "demo-skill/SKILL.md")
        _git(repo, "commit", "-q", "-m", "delete skill prose")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_FAIL
        out = capsys.readouterr()
        assert "demo-skill" in out.err


class TestModesAndPlumbing:
    def test_staged_never_blocks_even_with_enforce(self, repo, capsys):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New unstaged-message-blind change.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _git(repo, "add", ".")
        # No commit yet — this is exactly what pre-commit sees.

        rc = eval_guard.main(["--staged", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_PASS
        out = capsys.readouterr()
        assert "demo-skill" in out.err  # still warns, just never blocks

    def test_commit_msg_mode_respects_waiver(self, repo, tmp_path):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New body pending eval work.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _git(repo, "add", ".")

        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text(
            "rewrite guidance\n\nEval-waiver: tracked in ticket AB-9\n", encoding="utf-8"
        )

        rc = eval_guard.main(["--commit-msg", str(msg_file), "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_PASS

    def test_commit_msg_mode_blocks_without_waiver_when_enforced(self, repo, tmp_path):
        _write(repo, "demo-skill/SKILL.md", SKILL_MD_V1)
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add skill")

        v2 = SKILL_MD_V1.replace("Original prose body.", "New body, no waiver, no eval.")
        _write(repo, "demo-skill/SKILL.md", v2)
        _git(repo, "add", ".")

        msg_file = tmp_path / "COMMIT_EDITMSG"
        msg_file.write_text("rewrite guidance\n", encoding="utf-8")

        rc = eval_guard.main(["--commit-msg", str(msg_file), "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_FAIL

    def test_range_bad_spec_is_plumbing_error(self, repo):
        rc = eval_guard.main(["--range", "not-a-range", "--repo", str(repo)])
        assert rc == eval_guard.EXIT_PLUMBING_ERROR

    def test_commit_msg_missing_file_is_plumbing_error(self, repo, tmp_path):
        rc = eval_guard.main(["--commit-msg", str(tmp_path / "nope.txt"), "--repo", str(repo)])
        assert rc == eval_guard.EXIT_PLUMBING_ERROR

    def test_no_prose_changes_passes_quietly(self, repo):
        _write(repo, "demo-skill/scripts/helper.py", "print('hi')\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "add unrelated script")
        base = _git_out(repo, "rev-parse", "HEAD")

        _write(repo, "demo-skill/scripts/helper.py", "print('hi again')\n")
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "tweak script")
        head = _git_out(repo, "rev-parse", "HEAD")

        rc = eval_guard.main(["--range", f"{base}..{head}", "--repo", str(repo), "--enforce"])
        assert rc == eval_guard.EXIT_PASS


class TestWaiverParsing:
    def test_parse_waiver_absent(self):
        reason, error = eval_guard.parse_waiver("just a normal commit message\n")
        assert reason is None
        assert error is None

    def test_parse_waiver_wrong_case(self):
        reason, error = eval_guard.parse_waiver("subject\n\neval-waiver: lowercase key\n")
        assert reason is None
        assert error is not None
        assert "wrong" in error.lower() or "expected" in error.lower()
