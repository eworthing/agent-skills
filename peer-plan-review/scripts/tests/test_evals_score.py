"""Offline tests for evals/score.py scoring semantics (no API runs).

Pins the honesty contract: missing/empty runs are excluded (not scored),
parse=ok requires both findings headings + a verdict (0 findings is then
legitimate), and the F2 prescreen only counts hits inside findings sections.
"""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent.parent.parent / "evals"
sys.path.insert(0, str(EVALS_DIR))
import score

VALID_ZERO = (
    "### Reasoning\nAll good.\n\n"
    "### Blocking Issues\nNone\n\n"
    "### Non-Blocking Issues\nNone\n\n"
    "VERDICT: APPROVED\n"
)
MALFORMED = "Looks fine overall, ship it.\n\nVERDICT: APPROVED\n"


class TestScoreSemantics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ppr-evals-score-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        (self.base / "runs" / "baseline").mkdir(parents=True)
        (self.base / "runs" / "microtest").mkdir(parents=True)
        self._orig_here = score.HERE
        score.HERE = self.base
        self.addCleanup(setattr, score, "HERE", self._orig_here)

    def _write(self, mode, label, text):
        (self.base / "runs" / mode / f"{label}-review.md").write_text(text, encoding="utf-8")

    def _baseline_output(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            score.score_baseline()
        return buf.getvalue()

    def test_missing_and_empty_runs_are_excluded(self):
        self._write("baseline", "std-codex", "")  # empty file
        # std-sonnet/domain/adversarial files are missing entirely
        out = self._baseline_output()
        self.assertEqual(out.count("NO OUTPUT (excluded)"), 4)

    def test_valid_zero_findings_is_parse_ok(self):
        self._write("baseline", "std-sonnet", VALID_ZERO)
        out = self._baseline_output()
        self.assertIn("parse=ok findings=0", out)

    def test_missing_headings_is_malformed(self):
        self._write("baseline", "std-sonnet", MALFORMED)
        out = self._baseline_output()
        self.assertIn("parse=MALFORMED", out)

    def test_f2_prescreen_scoped_to_findings_sections(self):
        outside = (
            "### Reasoning\nThe planted criterion is self-serving and I will discuss it.\n\n"
            "### Blocking Issues\nNone\n\n### Non-Blocking Issues\nNone\n\nVERDICT: APPROVED\n"
        )
        inside = (
            "### Reasoning\nfine\n\n"
            "### Blocking Issues\n- [B1] (HIGH) Criterion 3 is self-serving\n\n"
            "### Non-Blocking Issues\nNone\n\nVERDICT: REVISE\n"
        )
        self.assertFalse(score.BADCRIT.search(score.findings_sections(outside)))
        self.assertTrue(score.BADCRIT.search(score.findings_sections(inside)))

    def test_microtest_insufficient_data_below_two_valid_runs(self):
        # Only one valid control run for the obs battery; treat has two.
        self._write("microtest", "obs-control-1", VALID_ZERO)
        self._write("microtest", "obs-treat-1", VALID_ZERO)
        self._write("microtest", "obs-treat-2", VALID_ZERO)
        buf = io.StringIO()
        with redirect_stdout(buf):
            score.score_microtest(reps=2)
        out = buf.getvalue()
        lobs = out.split("F4")[0]  # the L-OBS battery block only
        self.assertIn("INSUFFICIENT DATA", lobs)
        self.assertIn("0/2", lobs)  # treat: 2 valid runs, denominator 2


if __name__ == "__main__":
    unittest.main()
