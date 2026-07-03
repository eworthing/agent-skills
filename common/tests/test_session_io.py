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
    path_has_content,
    probe_writable,
    save_session,
    validate_prompt_file,
    write_failure_summary,
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

    def test_bold_verdict(self, tmp_path):
        p = tmp_path / "review.md"
        p.write_text("blah\n\n**VERDICT: APPROVED**\n", encoding="utf-8")
        assert _parse_verdict(str(p)) == "APPROVED"

    def test_trailing_punctuation(self, tmp_path):
        p = tmp_path / "review.md"
        p.write_text("blah\nVERDICT: REVISE.\n", encoding="utf-8")
        assert _parse_verdict(str(p)) == "REVISE"


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

    def test_no_space_finding_tag_stops_previous_block_scan(self):
        # "-[B2]" (no space after the dash) must still be recognized as a new
        # finding tag, so it doesn't get walked past and have its Section:
        # line misattributed to the preceding finding.
        text = (
            "### Blocking Issues\n"
            "- [B1] first finding\n"
            "-[B2] second finding\n"
            "  Section: bar.py (lines 3-4)\n"
        )
        findings = parse_structured_review(text)
        ids = [f["id"] for f in findings]
        assert ids == ["B1", "B2"]
        b1, b2 = findings
        assert "section" not in b1
        assert b2["section"] == "bar.py"
        assert b2["lines"] == "3-4"


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

    def test_copilot_null_data_does_not_crash(self, tmp_path):
        p = tmp_path / "out.jsonl"
        raw = json.dumps({"type": "assistant.message", "data": None})
        p.write_text(raw + "\n", encoding="utf-8")
        extract_text_from_output(str(p), "copilot")
        assert p.read_text(encoding="utf-8") == raw

    def test_claude_top_level_null_falls_back_to_raw(self, tmp_path):
        p = tmp_path / "out.json"
        p.write_text("null", encoding="utf-8")
        extract_text_from_output(str(p), "claude")
        assert p.read_text(encoding="utf-8") == "null"

    def _oc(self, *events):
        return "\n".join(json.dumps(e) for e in events) + "\n"

    def test_opencode_keeps_only_stop_step_text(self, tmp_path):
        # A tool-using reviewer narrates in a step that finishes "tool-calls";
        # the real review is the text in the step that finishes "stop". Only
        # the stop-step text should survive — narration must be dropped.
        p = tmp_path / "out.jsonl"
        p.write_text(
            self._oc(
                {"type": "step_start", "part": {"type": "step-start"}},
                {"type": "text", "part": {"type": "text",
                                          "text": "Let me check the deploy script first."}},
                {"type": "step_finish", "part": {"type": "step-finish", "reason": "tool-calls"}},
                {"type": "step_start", "part": {"type": "step-start"}},
                {"type": "text", "part": {"type": "text",
                                          "text": "### Blocking Issues\n- [B1] gap\n\nVERDICT: REVISE"}},
                {"type": "step_finish", "part": {"type": "step-finish", "reason": "stop"}},
            ),
            encoding="utf-8",
        )
        extract_text_from_output(str(p), "opencode")
        out = p.read_text(encoding="utf-8")
        assert "VERDICT: REVISE" in out
        assert "Blocking Issues" in out
        assert "Let me check the deploy script" not in out

    def test_opencode_single_step_review_preserved(self, tmp_path):
        # Backward compat: a clean run with one stop step keeps its full text,
        # including multiple text parts streamed within that step.
        p = tmp_path / "out.jsonl"
        p.write_text(
            self._oc(
                {"type": "step_start", "part": {"type": "step-start"}},
                {"type": "text", "part": {"type": "text", "text": "### Blocking Issues\n- [B1] a"}},
                {"type": "text", "part": {"type": "text", "text": "\nVERDICT: APPROVED"}},
                {"type": "step_finish", "part": {"type": "step-finish", "reason": "stop"}},
            ),
            encoding="utf-8",
        )
        extract_text_from_output(str(p), "opencode")
        out = p.read_text(encoding="utf-8")
        assert "Blocking Issues" in out
        assert "VERDICT: APPROVED" in out

    def test_opencode_no_stop_step_falls_back_to_all_text(self, tmp_path):
        # Truncated/killed run never emits a stop step — keep every text part
        # rather than silently dropping the whole review.
        p = tmp_path / "out.jsonl"
        p.write_text(
            self._oc(
                {"type": "step_start", "part": {"type": "step-start"}},
                {"type": "text", "part": {"type": "text", "text": "partial review body"}},
            ),
            encoding="utf-8",
        )
        extract_text_from_output(str(p), "opencode")
        assert "partial review body" in p.read_text(encoding="utf-8")

    def test_opencode_empty_stop_step_falls_back_to_all_texts(self, tmp_path):
        # A stop-reason step_finish with an empty step buffer must not disable
        # the all_texts fallback — otherwise the raw JSONL gets written as the
        # review instead of the actual content from an earlier non-stop step.
        p = tmp_path / "out.jsonl"
        p.write_text(
            self._oc(
                {"type": "step_start", "part": {"type": "step-start"}},
                {"type": "text", "part": {"type": "text", "text": "actual review content"}},
                {"type": "step_finish", "part": {"type": "step-finish", "reason": "tool-calls"}},
                {"type": "step_start", "part": {"type": "step-start"}},
                {"type": "step_finish", "part": {"type": "step-finish", "reason": "stop"}},
            ),
            encoding="utf-8",
        )
        extract_text_from_output(str(p), "opencode")
        assert p.read_text(encoding="utf-8") == "actual review content"

    def test_opencode_null_part_text_does_not_crash(self, tmp_path):
        p = tmp_path / "out.jsonl"
        raw = json.dumps({"type": "text", "part": None})
        p.write_text(raw + "\n", encoding="utf-8")
        extract_text_from_output(str(p), "opencode")
        assert p.read_text(encoding="utf-8") == raw

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


class TestPathHasContent:
    def test_true_for_nonempty_file(self, tmp_path):
        p = tmp_path / "f.txt"
        p.write_text("data", encoding="utf-8")
        assert path_has_content(p) is True

    def test_false_for_empty_file(self, tmp_path):
        p = tmp_path / "f.txt"
        p.write_text("", encoding="utf-8")
        assert path_has_content(p) is False

    def test_false_for_missing_path(self, tmp_path):
        assert path_has_content(tmp_path / "nope.txt") is False


class TestWriteFailureSummary:
    def test_writes_minimal_shape(self, tmp_path):
        sf = tmp_path / "summary.json"
        write_failure_summary(str(sf), {"round": 1}, "timeout: 600s")
        data = json.loads(sf.read_text(encoding="utf-8"))
        # Subset of write_summary()'s keys — round/verdict/error only — so a
        # caller can't confuse a failure summary with a completed round.
        assert data == {"round": 2, "verdict": None, "error": "timeout: 600s"}

    def test_no_summary_file_is_noop(self):
        write_failure_summary(None, {"round": 1}, "reason")  # must not raise

    def test_non_dict_session_round_is_none(self, tmp_path):
        sf = tmp_path / "summary.json"
        write_failure_summary(str(sf), None, "reason")
        data = json.loads(sf.read_text(encoding="utf-8"))
        assert data["round"] is None

    def test_replaces_stale_content(self, tmp_path):
        sf = tmp_path / "summary.json"
        sf.write_text('{"verdict": "APPROVED", "round": 1}', encoding="utf-8")
        write_failure_summary(str(sf), {"round": 5}, "os_error: boom")
        data = json.loads(sf.read_text(encoding="utf-8"))
        assert data["verdict"] is None
        assert data["round"] == 6
        assert data["error"] == "os_error: boom"
