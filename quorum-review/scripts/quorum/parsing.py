"""quorum.parsing — text, anchor, and structured-review parsers.

Sections (in order):
    # === text normalization ===            ``_normalized_tokens``, ``_normalized_text``,
                                            ``_normalize_text``, ``_summary_tokens``
    # === anchor parsers ===                ``_parse_anchor_line``, ``_extract_issue_anchor``,
                                            ``_normalize_anchor``
    # === telemetry (v3.1) ===              ``_failure_log_path``, ``_log_parse_failure``
    # === verdict / review I/O ===          ``parse_verdict``, ``read_review``,
                                            ``read_session_meta``
    # === section extraction ===            ``_extract_section``,
                                            ``_extract_section_with_presence``
    # === structured review (v2) ===        ``parse_structured_review``
    # === cross-critique (v2) ===           ``parse_cross_critique``

This module is a leaf — it has no imports from other ``quorum.*`` modules
so that ledger/merge/verification/orchestrator can pull from it freely
without risking a cycle. When adding a function, slot it under the matching
section header rather than appending to the bottom (see CONTRIBUTING.md).

v3.1 (Phase D): the parsers above use a two-tier scheme — strict exact-
contract match first, then explicit syntactic variants (case, whitespace,
trailing punctuation). A failed parse logs to ``parse-failures.jsonl``
via ``_log_parse_failure`` for operator audit, and returns ``None`` /
empty so callers behave exactly as before (None verdict → REVISE).
"""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# === text normalization ===
# ---------------------------------------------------------------------------

_WORD_RE = re.compile(r"[a-z0-9]+")

_COMMON_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}

_NEGATION_WORDS = {
    "avoid",
    "cannot",
    "denies",
    "deny",
    "disable",
    "disabled",
    "excluding",
    "exclude",
    "false",
    "lacks",
    "lack",
    "missing",
    "never",
    "no",
    "not",
    "off",
    "without",
}

_ACTION_OPPOSITES = (
    ("add", "remove"),
    ("allow", "deny"),
    ("enable", "disable"),
    ("include", "exclude"),
    ("keep", "remove"),
    ("use", "avoid"),
)

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "may",
    "of",
    "on",
    "or",
    "our",
    "should",
    "that",
    "the",
    "their",
    "this",
    "to",
    "use",
    "with",
}


def _normalized_tokens(text):
    return [tok for tok in _WORD_RE.findall((text or "").lower()) if tok not in _COMMON_WORDS]


def _normalized_text(text):
    return " ".join(_normalized_tokens(text))


def _normalize_text(text):
    text = " ".join((text or "").lower().split())
    return re.sub(r"[^a-z0-9\s]+", " ", text).strip()


def _summary_tokens(text):
    tokens = [t for t in re.findall(r"[a-z0-9]+", _normalize_text(text)) if t not in _STOPWORDS]
    return tokens


# ---------------------------------------------------------------------------
# === anchor parsers ===
# ---------------------------------------------------------------------------


def _parse_anchor_line(line):
    """Parse an anchor-ish line such as `Section: X (lines 12-18)`."""
    stripped = line.strip()
    if not stripped:
        return {}

    key, sep, value = stripped.partition(":")
    if not sep:
        return {}

    key = key.strip().lower()
    value = value.strip()
    if key not in {"section", "anchor", "file", "path", "hunk"}:
        return {}

    anchor = {"kind": key, "raw": stripped}
    if key in {"section", "anchor"}:
        anchor["section"] = value
        line_match = re.search(
            r"\((?:lines?|line)\s*(\d+)(?:\s*-\s*(\d+))?\)\s*$",
            value,
            re.IGNORECASE,
        )
        if line_match:
            anchor["line_start"] = int(line_match.group(1))
            anchor["line_end"] = int(line_match.group(2) or line_match.group(1))
            anchor["section"] = re.sub(
                r"\s*\((?:lines?|line)\s*\d+(?:\s*-\s*\d+)?\)\s*$",
                "",
                value,
                flags=re.IGNORECASE,
            ).strip()
    else:
        anchor["path"] = value

    return anchor


def _extract_issue_anchor(block_text):
    """Extract anchor metadata from trailing issue lines."""
    anchor = {}
    for line in block_text.splitlines():
        parsed = _parse_anchor_line(line)
        if parsed:
            anchor = parsed
            break
    return anchor


def _normalize_anchor(anchor, artifact_kind="plan"):
    anchor = anchor if isinstance(anchor, dict) else {}
    artifact_path = anchor.get("artifact_path") or anchor.get("path")
    anchor_kind = anchor.get("anchor_kind") or anchor.get("kind")
    if not anchor_kind:
        if anchor.get("anchor_start") is not None or anchor.get("line_start") is not None:
            anchor_kind = "line_range"
        elif anchor.get("section"):
            anchor_kind = "section"
    return {
        "artifact_kind": anchor.get("artifact_kind") or artifact_kind,
        "artifact_path": artifact_path,
        "anchor_kind": anchor_kind,
        "anchor_start": anchor.get("anchor_start", anchor.get("line_start")),
        "anchor_end": anchor.get("anchor_end", anchor.get("line_end")),
        "anchor_hash": anchor.get("anchor_hash"),
        "section": anchor.get("section"),
        "raw": anchor.get("raw"),
    }


# ---------------------------------------------------------------------------
# === telemetry (v3.1) ===
# ---------------------------------------------------------------------------


def _failure_log_path(quorum_id=None):
    """Resolve the parse-failures.jsonl path.

    Override via ``QUORUM_PARSE_FAILURES_LOG`` env var (tests use a per-test
    tmp path). Otherwise falls back to ``${TMPDIR}/qr-<quorum_id>-parse-
    failures.jsonl`` when a quorum_id is provided, or a generic default
    when not. The default file is created lazily on first write.
    """
    override = os.environ.get("QUORUM_PARSE_FAILURES_LOG")
    if override:
        return Path(override)
    tmpdir = Path(os.environ.get("TMPDIR", "/tmp"))
    if quorum_id:
        return tmpdir / f"qr-{quorum_id}-parse-failures.jsonl"
    return tmpdir / "qr-parse-failures.jsonl"


def _log_parse_failure(parser_name, *, excerpt="", quorum_id=None):
    """Append one JSONL row to the parse-failures log.

    Best-effort — logging failures never raise. The row records
    ``parser_name`` so multiset assertions in tests can verify which
    parser surface tripped.
    """
    row = {
        "ts": datetime.now(UTC).isoformat(),
        "parser_name": parser_name,
        "excerpt": excerpt[:200] if excerpt else "",
    }
    if quorum_id:
        row["quorum_id"] = quorum_id
    try:
        # newline="" prevents \n→\r\n translation on Windows
        with _failure_log_path(quorum_id).open("a", encoding="utf-8", newline="") as f:
            f.write(json.dumps(row, default=str) + "\n")
    except OSError:
        pass  # logging is best-effort


# ---------------------------------------------------------------------------
# === verdict / review I/O ===
# ---------------------------------------------------------------------------

# Tier 1: exact contract — last non-empty line is exactly "VERDICT: APPROVED|REVISE".
# Tier 2: explicit syntactic variants — accommodate harmless whitespace, case,
# and trailing-punctuation drift, but reject anything ambiguous.
_RE_VERDICT_TIER2 = re.compile(
    r"^verdict\s*:\s*(approved|revise)\s*[.!]?\s*$",
    re.IGNORECASE,
)


def parse_verdict(review_file):
    """Parse VERDICT from the last non-empty line of review output.

    Two-tier scheme (v3.1):
      Tier 1: exact contract ``VERDICT: APPROVED`` / ``VERDICT: REVISE``.
      Tier 2: explicit syntactic variants (case, whitespace, trailing
              punctuation). No loose keyword heuristic — explicitly
              rejected by the plan as fail-open.

    On total failure the parser returns ``None`` (callers treat None as
    REVISE per the v2.1 contract) and emits a telemetry row to the
    parse-failures log for operator audit.

    Returns 'APPROVED', 'REVISE', or None.
    """
    if not review_file or not Path(review_file).exists():
        return None
    try:
        with Path(review_file).open(encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        last = ""
        for line in reversed(lines):
            stripped = line.strip()
            if stripped:
                last = stripped
                break
        if not last:
            return None
        # Tier 1: exact contract
        if last == "VERDICT: APPROVED":
            return "APPROVED"
        if last == "VERDICT: REVISE":
            return "REVISE"
        # Tier 2: explicit syntactic variants
        m = _RE_VERDICT_TIER2.match(last)
        if m:
            return m.group(1).upper()
        # No Tier 3 — log + return None.
        _log_parse_failure("verdict", excerpt=last)
        return None
    except OSError:
        return None


def read_review(review_file):
    """Read the full review text from a reviewer's output file."""
    if not review_file or not Path(review_file).exists():
        return ""
    try:
        with Path(review_file).open(encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def read_session_meta(session_file):
    """Read session metadata JSON."""
    if not session_file or not Path(session_file).exists():
        return {}
    try:
        with Path(session_file).open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# === section extraction ===
# ---------------------------------------------------------------------------


def _extract_section(text, header):
    """Extract text under a ### header, up to the next ### header or end of text.

    Returns the section body text, or the full text if the header is not found
    (backward compatibility with unstructured reviews).
    """
    section_text, _found = _extract_section_with_presence(text, header)
    return section_text


def _extract_section_with_presence(text, header):
    """Return (section_text, found) for a ### section header."""
    pattern = re.compile(
        r"(?:^|\n)###\s+" + re.escape(header) + r"\s*\n",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return text, False  # fallback: search entire text

    start = match.end()
    # Find the next ### header (but not #### sub-headers)
    next_header = re.search(r"\n###\s+(?!#)", text[start:])
    if next_header:
        return text[start : start + next_header.start()], True
    return text[start:], True


# ---------------------------------------------------------------------------
# === structured review (v2) ===
# ---------------------------------------------------------------------------

_RE_BLOCKING = re.compile(r"^\s*(?:-\s*)?\*{0,2}\[B(\d+)\]\*{0,2}\s*(.+)", re.MULTILINE)
_RE_BLOCKING_WITH_CONF = re.compile(
    r"^\s*(?:-\s*)?\*{0,2}\[B(\d+)\]\s*\((HIGH|MEDIUM|LOW)\)\*{0,2}\s*(.+)",
    re.MULTILINE | re.IGNORECASE,
)
_RE_NON_BLOCKING = re.compile(r"^\s*(?:-\s*)?\*{0,2}\[N(\d+)\]\*{0,2}\s*(.+)", re.MULTILINE)
_RE_CONFIDENCE = re.compile(
    r"(?:^|\n)\s*(?:###?\s*)?Confidence\s*[:\-]?\s*\n?\s*(HIGH|MEDIUM|LOW)",
    re.IGNORECASE,
)
_RE_SCOPE = re.compile(
    r"(?:^|\n)\s*(?:###?\s*)?Scope\s*[:\-]?\s*\n?\s*(.+)",
)


def parse_structured_review(review_file):
    """Parse structured review output into issue records.

    Returns dict with:
      - blocking: list of {"id": "B1", "text": "...", "anchor": {...}}
      - non_blocking: list of {"id": "N1", "text": "...", "anchor": {...}}
      - confidence: "HIGH"|"MEDIUM"|"LOW"|None
      - scope: list of strings
      - verdict: "APPROVED"|"REVISE"|None
      - raw_text: full review text
      - structured: bool (True if any structured sections found)
    """
    text = read_review(review_file)
    verdict = parse_verdict(review_file)

    # Extract section text to avoid matching issues from Reasoning section
    blocking_section, has_blocking_section = _extract_section_with_presence(text, "Blocking Issues")
    nb_section, has_nb_section = _extract_section_with_presence(text, "Non-Blocking Issues")

    # Parse blocking issues — try per-issue confidence first
    conf_matches = {
        m.group(1): (m.group(2).upper(), m.group(3).strip())
        for m in _RE_BLOCKING_WITH_CONF.finditer(blocking_section)
    }
    blocking_matches = list(_RE_BLOCKING.finditer(blocking_section))
    blocking = []
    for idx, m in enumerate(blocking_matches):
        bid = m.group(1)
        next_start = (
            blocking_matches[idx + 1].start()
            if idx + 1 < len(blocking_matches)
            else len(blocking_section)
        )
        anchor = _extract_issue_anchor(blocking_section[m.end() : next_start])
        if bid in conf_matches:
            issue_conf, issue_text = conf_matches[bid]
            blocking.append(
                {
                    "id": f"B{bid}",
                    "text": issue_text,
                    "confidence": issue_conf,
                    "anchor": anchor or None,
                }
            )
        else:
            blocking.append(
                {
                    "id": f"B{bid}",
                    "text": m.group(2).strip(),
                    "confidence": None,
                    "anchor": anchor or None,
                }
            )

    nb_matches = list(_RE_NON_BLOCKING.finditer(nb_section))
    non_blocking = []
    for idx, m in enumerate(nb_matches):
        next_start = nb_matches[idx + 1].start() if idx + 1 < len(nb_matches) else len(nb_section)
        anchor = _extract_issue_anchor(nb_section[m.end() : next_start])
        non_blocking.append(
            {
                "id": f"N{m.group(1)}",
                "text": m.group(2).strip(),
                "anchor": anchor or None,
            }
        )

    conf_match = _RE_CONFIDENCE.search(text)
    confidence = conf_match.group(1).upper() if conf_match else None

    scope_match = _RE_SCOPE.search(text)
    scope = []
    if scope_match:
        scope = [s.strip().strip('"').strip("'") for s in scope_match.group(1).split(",")]
        scope = [s for s in scope if s]

    structured = bool(blocking or non_blocking or confidence or scope)

    return {
        "blocking": blocking,
        "non_blocking": non_blocking,
        "confidence": confidence,
        "scope": scope,
        "verdict": verdict,
        "raw_text": text,
        "structured": structured,
        "has_blocking_section": has_blocking_section,
        "has_non_blocking_section": has_nb_section,
    }


# ---------------------------------------------------------------------------
# === cross-critique (v2) ===
# ---------------------------------------------------------------------------

_RE_AGREE = re.compile(r"^\s*\*{0,2}\[AGREE\s+(BLK-\d+|NB-\d+)\]\*{0,2}", re.MULTILINE)
_RE_DISAGREE = re.compile(r"^\s*\*{0,2}\[DISAGREE\s+(BLK-\d+|NB-\d+)\]\*{0,2}\s*(.*)", re.MULTILINE)
_RE_REFINE = re.compile(r"^\s*\*{0,2}\[REFINE\s+(BLK-\d+|NB-\d+)\]\*{0,2}\s*(.*)", re.MULTILINE)
_RE_NEW_BLOCKING = re.compile(r"^\s*\*{0,2}\[B-NEW\]\*{0,2}\s*(.+)", re.MULTILINE)
_RE_NEW_NON_BLOCKING = re.compile(r"^\s*\*{0,2}\[N-NEW\]\*{0,2}\s*(.+)", re.MULTILINE)


def parse_cross_critique(review_file):
    """Extract per-issue AGREE/DISAGREE/REFINE responses from round 2+ reviews.

    Returns dict with:
      - agrees: list of canonical issue IDs
      - disagrees: list of {"id": canonical_id, "reason": "..."}
      - refines: list of {"id": canonical_id, "text": "..."}
      - new_blocking: list of text descriptions
      - new_non_blocking: list of text descriptions
    """
    text = read_review(review_file)

    agrees = [m.group(1) for m in _RE_AGREE.finditer(text)]
    disagrees = [
        {"id": m.group(1), "reason": m.group(2).strip()} for m in _RE_DISAGREE.finditer(text)
    ]
    refines = [{"id": m.group(1), "text": m.group(2).strip()} for m in _RE_REFINE.finditer(text)]
    new_blocking = [m.group(1).strip() for m in _RE_NEW_BLOCKING.finditer(text)]
    new_non_blocking = [m.group(1).strip() for m in _RE_NEW_NON_BLOCKING.finditer(text)]

    return {
        "agrees": agrees,
        "disagrees": disagrees,
        "refines": refines,
        "new_blocking": new_blocking,
        "new_non_blocking": new_non_blocking,
    }
