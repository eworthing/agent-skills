"""Tests for common.session.io."""

import json

import pytest

from common.session import (
    _extract_section,
    _parse_verdict,
    _strip_markdown_wrappers,
    extract_text_from_output,
    load_session,
    parse_structured_review,
    probe_writable,
    save_session,
    validate_prompt_file,
    write_summary,
)


class TestSessionRoundtrip:
    def test_save_load(self, tmp_path):
        sf = tmp_path / "session.json"
        data = {"session_id": "abc", "model": "claude-opus-4-7", "round": 2}
        save_session(str(sf), data)
        assert load_session(str(sf)) == data

    def test_load_missing_returns_empty(self, tmp_path):
        assert load_session(str(tmp_path / "nope.json")) == {}

    def test_load_corrupt_returns_empty(self, tmp_path):
        sf = tmp_path / "session.json"
        sf.write_text("{broken", encoding="utf-8")
        assert load_session(str(sf)) == {}

    def test_atomic_write_no_tmp_residue(self, tmp_path):
        sf = tmp_path / "session.json"
        save_session(str(sf), {"x": 1})
        # The .tmp sibling must not survive a successful write.
        assert not (tmp_path / "session.json.tmp").exists()


class TestParseVerdict:
    def test_approved(self, tmp_path):
        p = tmp_path / "review.md"
        p.write_text("blah\n\nVERDICT: APPROVED\n", encoding="utf-8")
        assert _parse_verdict(str(p)) == "APPROVED"

    def test_revise(self, tmp_path):
        p = tmp_path / "review.md"
        p.write_text("blah\nVERDICT: REVISE", encoding="utf-8")
        assert _parse_verdict(str(p)) == "REVISE"

    def test_no_verdict(self, tmp_path):
        p = tmp_path / "review.md"
        p.write_text("no decision here", encoding="utf-8")
        assert _parse_verdict(str(p)) is None

    def test_picks_last_verdict_line(self, tmp_path):
        p = tmp_path / "review.md"
        p.write_text("VERDICT: REVISE\nlater text\nVERDICT: APPROVED\n", encoding="utf-8")
        assert _parse_verdict(str(p)) == "APPROVED"


class TestExtractSection:
    def test_basic(self):
        text = "### Reasoning\nfoo\n### Blocking Issues\nbar\n### Non-Blocking Issues\nbaz\n"
        assert _extract_section(text, "Blocking Issues").strip() == "bar"

    def test_missing_returns_empty(self):
        assert _extract_section("nothing here", "Blocking Issues") == ""


class TestStripMarkdownWrappers:
    def test_bold(self):
        assert _strip_markdown_wrappers("**text**") == "text"

    def test_italic(self):
        assert _strip_markdown_wrappers("*text*") == "text"

    def test_nested(self):
        assert _strip_markdown_wrappers("**__text__**") == "text"

    def test_unwrapped(self):
        assert _strip_markdown_wrappers("plain") == "plain"


class TestParseStructuredReview:
    def test_basic_blocking_finding(self):
        text = (
            "### Blocking Issues\n"
            "- [B1] (HIGH) Missing auth check\n"
            "  Section: src/auth.py (lines 10-20)\n"
            "  Recommendation: Add JWT validation\n"
            "\n"
            "### Non-Blocking Issues\n"
            "- [N1] Consider caching\n"
        )
        findings = parse_structured_review(text)
        assert len(findings) == 2
        b1, n1 = findings
        assert b1["id"] == "B1"
        assert b1["severity"] == "blocking"
        assert b1["confidence"] == "HIGH"
        assert b1["description"] == "Missing auth check"
        assert b1["section"] == "src/auth.py"
        assert b1["lines"] == "10-20"
        assert b1["recommendation"] == "Add JWT validation"
        assert n1["id"] == "N1"
        assert n1["severity"] == "non_blocking"

    def test_scoped_to_section_headers(self):
        """Findings in ### Reasoning must NOT be picked up — only Blocking/Non-Blocking."""
        text = (
            "### Reasoning\n"
            "- [B999] not a real finding, just discussion\n"
            "\n"
            "### Blocking Issues\n"
            "- [B1] real one\n"
        )
        findings = parse_structured_review(text)
        ids = [f["id"] for f in findings]
        assert ids == ["B1"]

    def test_no_findings_returns_empty(self):
        assert parse_structured_review("") == []
        assert parse_structured_review("### Reasoning\njust prose") == []


class TestExtractTextFromOutput:
    def test_claude_extracts_result_field(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text(json.dumps({"result": "the review text", "model": "x"}), encoding="utf-8")
        extract_text_from_output(str(p), "claude")
        assert p.read_text(encoding="utf-8") == "the review text"

    def test_copilot_jsonl(self, tmp_path):
        p = tmp_path / "out.jsonl"
        p.write_text(
            json.dumps({"type": "assistant.message", "data": {"content": "first"}}) + "\n"
            + json.dumps({"type": "assistant.message", "data": {"content": "second"}}) + "\n",
            encoding="utf-8",
        )
        extract_text_from_output(str(p), "copilot")
        assert p.read_text(encoding="utf-8") == "first\nsecond"

    def test_content_arg_bypasses_file_read(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text("ignored on-disk", encoding="utf-8")
        extract_text_from_output(
            str(p),
            "claude",
            content=json.dumps({"result": "from arg"}),
        )
        assert p.read_text(encoding="utf-8") == "from arg"


class TestValidatePromptFile:
    def test_ok(self, tmp_path):
        p = tmp_path / "prompt.md"
        p.write_text("hi", encoding="utf-8")
        ok, err = validate_prompt_file(str(p))
        assert ok and err is None

    def test_missing(self, tmp_path):
        ok, err = validate_prompt_file(str(tmp_path / "nope.md"))
        assert not ok
        assert "not found" in err

    def test_empty(self, tmp_path):
        p = tmp_path / "prompt.md"
        p.write_text("", encoding="utf-8")
        ok, err = validate_prompt_file(str(p))
        assert not ok
        assert "empty" in err


class TestProbeWritable:
    def test_ok_in_empty_dir(self, tmp_path):
        ok, err = probe_writable(str(tmp_path / "future.txt"))
        assert ok and err is None

    def test_directory_not_existing(self, tmp_path):
        ok, err = probe_writable(str(tmp_path / "no-such-dir" / "f.txt"))
        assert not ok

    def test_non_regular_file(self, tmp_path):
        ok, err = probe_writable(str(tmp_path))  # directory itself
        assert not ok


class TestWriteSummary:
    def test_writes_summary_with_finding_counts(self, tmp_path):
        review = tmp_path / "review.md"
        review.write_text(
            "### Blocking Issues\n- [B1] (HIGH) a\n"
            "### Non-Blocking Issues\n- [N1] b\n"
            "VERDICT: REVISE\n",
            encoding="utf-8",
        )
        sf = tmp_path / "summary.json"
        write_summary(str(sf), str(review), {
            "reviewer": "claude", "model": "x", "effort": "high", "round": 2,
        })
        data = json.loads(sf.read_text(encoding="utf-8"))
        assert data["verdict"] == "REVISE"
        assert data["finding_count"] == 2
        assert data["blocking_count"] == 1
        assert data["reviewer"] == "claude"
