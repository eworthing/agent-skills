"""Credential quarantine gate: G44.

The loop's own persistence sinks are payload it writes about untrusted source --
a finding whose evidence quotes a hardcoded credential writes the value into
CURRENT_REVIEW.md, then CURRENT_REVIEW.json, then the REVIEW_HISTORY archive,
committed. Layer 1 (method.md's "Credential redaction" rule, forwarded to the
implementation-reviewer and halt-verifier dispatch prompts -- see
scripts/_redaction_dispatch_selftest.py) is the preventive instruction. This is
Layer 2, the mechanical backstop: it scans what actually got written, independent
of whether the rule was followed.

Fails closed (blocks convergence like any other gate), reports sink + line +
credential TYPE + pattern name, and NEVER reproduces the matched value or any
substring of it -- the Issue message is built entirely from constants (pattern
name, transform label, sink filename, line number), never from the matched text.

Scope, deliberately narrow (out of scope: retrospective history audit, history
rewriting, arbitrary repo files):
- The 5 files the loop actually persists to (references/output-format.md
  "## Artifacts"). LOOP_STATE.json is excluded on purpose -- see
  _LOOP_STATE_EXCLUDED_BECAUSE below.
- Two named transformations only: base64 encoding and `"a" + "b"`-style string
  concatenation. Nothing beyond those two is implied or attempted.
"""

from __future__ import annotations

import base64
import re
from pathlib import Path

from _artifact_core import Issue

# The loop's full persistence contract (references/output-format.md "## Artifacts").
_LOOP_STATE_EXCLUDED_BECAUSE = (
    "LOOP_STATE.json's `evidence` field carries [start, end] line-number pairs "
    "plus a SHA-256 hash of the evidence list (output-format-state-schemas.md "
    "§ findings_registry.json schema), never raw quoted text -- it structurally "
    "cannot carry a quoted credential value."
)
CREDENTIAL_SINKS: tuple[str, ...] = (
    "CURRENT_REVIEW.md",
    "CURRENT_REVIEW.json",
    "REVIEW_HISTORY.md",
    "REVIEW_HISTORY.json",
    "findings_registry.json",
)

# (type name, pattern). Precision over recall: every pattern is fixed-prefix +
# fixed/near-fixed length, or proximity-scoped, to keep false positives near zero
# on legitimate review prose that merely *discusses* credentials by type.
_CREDENTIAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "AWS access key ID",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        # FP: near zero. AWS's own fixed 4-char prefix + exactly 16 upper/digit
        # chars; prose that merely names the prefix ("AKIA-prefixed literal")
        # does not match -- no 16 chars follow before the non-alnum boundary.
    ),
    (
        "AWS secret access key (proximity heuristic)",
        re.compile(r"(?i)aws.{0,40}?\b[A-Za-z0-9/+=]{40}\b"),
        # FP: highest structural risk in this table. A bare 40-char base64-alphabet
        # run has no marker of its own (could be a hash, a signature, a UUID
        # blob) -- scoped to within 40 chars of the literal word "aws" to cut
        # incidental hits. Kept because AWS secret keys carry no fixed prefix.
    ),
    (
        "API secret key (sk- prefix)",
        re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        # FP: low-moderate. "sk-" (hyphen, not underscore) is OpenAI's shape;
        # >=20-char tail keeps it off short unrelated hyphenated tokens.
    ),
    (
        "GitHub personal access token",
        re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),
        # FP: near zero. Fixed prefix + fixed 36-char length is GitHub's own format.
    ),
    (
        "GitHub OAuth token",
        re.compile(r"\bgho_[A-Za-z0-9]{36}\b"),
        # FP: near zero, same reasoning as ghp_.
    ),
    (
        "Slack bot token",
        re.compile(r"\bxoxb-[0-9A-Za-z-]{10,}\b"),
        # FP: near zero. "xoxb-" has no legitimate non-token use.
    ),
    (
        "Slack user token",
        re.compile(r"\bxoxp-[0-9A-Za-z-]{10,}\b"),
        # FP: near zero, same reasoning as xoxb-.
    ),
    (
        "private key (PEM header)",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----"),
        # FP: near zero. This exact banner has no legitimate reason to appear in
        # review prose; a real PEM key is never "quoted for illustration".
    ),
    (
        "generic API key (key=value)",
        re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][A-Za-z0-9]{16,}['\"]"),
        # FP: highest in this table. A finding legitimately discussing *how* a
        # key is assigned can trip this if the discussion quotes a 16+ char
        # alnum-only placeholder value in the key-colon-quoted-value shape (an
        # underscored placeholder does NOT match -- `_` is outside
        # `[A-Za-z0-9]`; see scripts/_g44_selftest.py's FP-guard cases).
        # Kept because it is the only pattern covering providers with no
        # fixed-prefix format.
    ),
)

# Base64 transform: any token in this shape is a *candidate*; it only becomes a
# hit if it decodes to valid UTF-8 that itself matches a credential pattern above.
# That double requirement (valid base64 AND valid-utf8-AND-credential-shaped
# decoded text) is what keeps this precise -- a git SHA or hex checksum decodes
# to near-random bytes that essentially never pass both checks.
_BASE64_TOKEN_RE = re.compile(r"\b[A-Za-z0-9+/]{16,}={0,2}\b")

# Concat-split transform: two adjacent quoted string literals joined by `+`
# ("simple string-concatenation split" only -- no other join style is attempted).
# The `\\?` before each quote tolerates a JSON-escaped `\"` -- a JSON sink (e.g.
# CURRENT_REVIEW.json's evidence[] string) serializes an embedded `"` as `\"`,
# and without this the pattern only ever matched in the unescaped .md sinks.
_CONCAT_RE = re.compile(
    r"""\\?['"]([A-Za-z0-9/+=_.\-]+)\\?['"]\s*\+\s*\\?['"]([A-Za-z0-9/+=_.\-]+)\\?['"]"""
)


def _decode_base64_candidates(line: str) -> list[str]:
    decoded: list[str] = []
    for tok in _BASE64_TOKEN_RE.findall(line):
        padded = tok + "=" * (-len(tok) % 4)
        try:
            raw = base64.b64decode(padded, validate=True)
            decoded.append(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            # base64.b64decode(validate=True) raises binascii.Error on invalid
            # input, a ValueError subclass -- caught here without importing
            # binascii separately.
            continue
    return decoded


def _concat_candidates(line: str) -> list[str]:
    return [a + b for a, b in _CONCAT_RE.findall(line)]


def _scan_line(text: str) -> list[tuple[str, str]]:
    """Return [(pattern_name, transform_label)] hits for one line of raw text."""
    hits: list[tuple[str, str]] = []
    for name, pattern in _CREDENTIAL_PATTERNS:
        if pattern.search(text):
            hits.append((name, "plain"))
    for decoded in _decode_base64_candidates(text):
        for name, pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(decoded):
                hits.append((name, "base64"))
    for concatenated in _concat_candidates(text):
        for name, pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(concatenated):
                hits.append((name, "concat-split"))
    return hits


def check_g44_credential_quarantine(artifact_dir: Path) -> list[Issue]:
    """G44: scan every persistence sink for credential-shaped values.

    Fails closed on any hit. Quarantine is non-destructive -- the artifact stays
    on disk untouched; this gate's report (sink + line + TYPE + pattern name) IS
    the quarantine record. Never reproduces the matched value or any substring of
    it: every message below is built from constants, not from the matched text.
    """
    issues: list[Issue] = []
    for sink in CREDENTIAL_SINKS:
        path = artifact_dir / sink
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for name, transform in _scan_line(line):
                marker = f"[G44-hit type={name} sink={sink}:{lineno}]"
                suffix = "" if transform == "plain" else f" ({transform}-transformed)"
                issues.append(
                    Issue(
                        "G44",
                        f"{marker} credential-shaped value detected{suffix} -- "
                        "quarantine: cite file:line + TYPE only, never the value; "
                        "rotate the credential.",
                        context=f"{sink}:{lineno}",
                    )
                )
    return issues
