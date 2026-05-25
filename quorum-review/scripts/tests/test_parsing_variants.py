"""Phase-D tests: parser hardening (Tier-1 strict, Tier-2 explicit variants, telemetry).

Covers:
- parse_verdict: accepted variants (case, whitespace, punctuation) + malformed boundary cases
- Telemetry: each test isolates QUORUM_PARSE_FAILURES_LOG via the
  parse_failures_log fixture, then asserts a parser_name *multiset* on
  the resulting JSONL rows.

Why multiset (not raw row count)? Some inputs trigger multiple parsers
within one call path. Counting rows by parser_name (Counter) is robust
to that; counting total rows is not.

The fixtures live inline rather than as files so each test is self-
contained and can be read without flipping between source and data.
"""

from collections import Counter

import pytest

from quorum.parsing import parse_verdict


def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# parse_verdict — Tier 1 (exact contract)
# ---------------------------------------------------------------------------


class TestVerdictTier1:
    def test_exact_approved(self, tmp_path, parse_failures_log, read_failures):
        p = _write(tmp_path, "r.md", "Some review prose.\n\nVERDICT: APPROVED\n")
        assert parse_verdict(p) == "APPROVED"
        assert read_failures(parse_failures_log) == []

    def test_exact_revise(self, tmp_path, parse_failures_log, read_failures):
        p = _write(tmp_path, "r.md", "Issues found.\n\nVERDICT: REVISE\n")
        assert parse_verdict(p) == "REVISE"
        assert read_failures(parse_failures_log) == []


# ---------------------------------------------------------------------------
# parse_verdict — Tier 2 (explicit syntactic variants)
# ---------------------------------------------------------------------------


class TestVerdictTier2Variants:
    @pytest.mark.parametrize("body,expected", [
        # Whitespace variants
        ("VERDICT:APPROVED",       "APPROVED"),    # no space after colon
        ("VERDICT:  APPROVED",     "APPROVED"),    # multiple spaces
        ("  VERDICT: APPROVED  ",  "APPROVED"),    # surrounding whitespace
        # Case variants
        ("Verdict: Approved",      "APPROVED"),
        ("verdict: revise",        "REVISE"),
        ("VeRdIcT: aPpRoVeD",      "APPROVED"),
        # Trailing punctuation
        ("VERDICT: REVISE.",       "REVISE"),
        ("VERDICT: APPROVED!",     "APPROVED"),
        ("VERDICT: APPROVED .",    "APPROVED"),    # space then period
    ])
    def test_accepted_variant(self, tmp_path, parse_failures_log, read_failures, body, expected):
        p = _write(tmp_path, "r.md", body + "\n")
        assert parse_verdict(p) == expected
        # Tier-2 acceptance must NOT log a parse failure.
        assert read_failures(parse_failures_log) == []


# ---------------------------------------------------------------------------
# parse_verdict — malformed (logs telemetry, returns None)
# ---------------------------------------------------------------------------


class TestVerdictMalformed:
    @pytest.mark.parametrize("body,description", [
        ("Some review without a verdict line.",            "no verdict at all"),
        ("VERDICT IS APPROVED",                            "missing colon"),
        ("approved",                                       "bare word"),
        ("VERDICT: MAYBE",                                 "unknown value"),
        ("VERDICT: APPROVED REVISE",                       "ambiguous"),
        # Truncated — last non-empty line is cut off mid-word
        ("VERDICT: APPR",                                  "truncated value"),
    ])
    def test_malformed_returns_none_and_logs(
        self, tmp_path, parse_failures_log, read_failures, body, description
    ):
        p = _write(tmp_path, "r.md", body + "\n")
        assert parse_verdict(p) is None, f"should reject: {description}"

        rows = read_failures(parse_failures_log)
        # Multiset assertion: exactly one verdict-parser failure row.
        assert Counter(r["parser_name"] for r in rows) == {"verdict": 1}

    def test_empty_input_no_log(self, tmp_path, parse_failures_log, read_failures):
        """Empty input is a missing-input case, not a malformed-input case."""
        p = _write(tmp_path, "r.md", "")
        assert parse_verdict(p) is None
        # No parse failure logged — the file is just empty.
        assert read_failures(parse_failures_log) == []

    def test_missing_file_no_log(self, tmp_path, parse_failures_log, read_failures):
        assert parse_verdict(str(tmp_path / "nope.md")) is None
        assert read_failures(parse_failures_log) == []


# ---------------------------------------------------------------------------
# Boundary cases
# ---------------------------------------------------------------------------


class TestVerdictBoundary:
    def test_unicode_in_preceding_prose(self, tmp_path, parse_failures_log, read_failures):
        # Anchor text with non-ASCII path segments, emoji prose — must not
        # affect verdict parsing on the last line.
        body = (
            "## Reasoning\n"
            "the dépendency in `src/utf-8 paths/main.py` looks ✨ fine\n"
            "but `src/auth/管理者.py` is concerning\n"
            "\n"
            "VERDICT: REVISE\n"
        )
        p = _write(tmp_path, "r.md", body)
        assert parse_verdict(p) == "REVISE"
        assert read_failures(parse_failures_log) == []

    def test_only_trailing_blank_lines(self, tmp_path, parse_failures_log):
        body = "VERDICT: APPROVED\n\n\n\n"
        p = _write(tmp_path, "r.md", body)
        assert parse_verdict(p) == "APPROVED"

    def test_crlf_line_endings(self, tmp_path, parse_failures_log):
        """Windows-style line endings shouldn't change parsing."""
        body = "Stuff\r\n\r\nVERDICT: APPROVED\r\n"
        p = _write(tmp_path, "r.md", body)
        assert parse_verdict(p) == "APPROVED"


# ---------------------------------------------------------------------------
# Telemetry — env var override + multiset across multiple inputs
# ---------------------------------------------------------------------------


class TestTelemetryIsolation:
    def test_env_var_redirects_log(self, tmp_path, monkeypatch, read_failures):
        """The fixture's monkeypatch redirect lands writes at the per-test path."""
        log = tmp_path / "custom-failures.jsonl"
        monkeypatch.setenv("QUORUM_PARSE_FAILURES_LOG", str(log))
        bad = _write(tmp_path, "r.md", "VERDICT IS APPROVED\n")
        assert parse_verdict(bad) is None
        assert log.exists()
        assert Counter(r["parser_name"] for r in read_failures(log)) == {"verdict": 1}

    def test_multiset_across_two_failures(self, tmp_path, parse_failures_log, read_failures):
        """Two malformed inputs in one test → exactly two verdict rows."""
        for body in ("approved", "VERDICT: MAYBE"):
            p = _write(tmp_path, f"r-{body[:5]}.md", body + "\n")
            assert parse_verdict(p) is None
        assert Counter(r["parser_name"] for r in read_failures(parse_failures_log)) == {"verdict": 2}
